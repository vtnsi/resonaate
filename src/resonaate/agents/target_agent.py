# Standard Library Imports
# Third Party Imports
from numpy import ndarray, copy, asarray
from numpy.random import default_rng
# RESONAATE Imports
from .agent_base import Agent
from ..data.ephemeris import TruthEphemeris
from ..common.exceptions import ShapeError
from ..parallel.task import Task
from ..physics.orbit import Orbit
from ..physics.time.stardate import JulianDate, julianDateToDatetime
from ..physics.transforms.methods import ecef2lla, eci2ecef


class TargetAgent(Agent):
    """Define the behavior of the **true** target agents in the simulation."""

    def __init__(self, _id, name, agent_type, initial_state, clock, dynamics, realtime, process_noise, seed=None):
        """Construct a TargetAgent object.

        Args:
            _id (``int``): unique identification number
            name (``str``): unique identification name
            agent_type (``str``): name signifying the type of agent `('Spacecraft', 'GroundFacility', )`
            initial_state (``numpy.ndarray``): 6x1 ECI initial state vector
            clock (:class:`.ScenarioClock`): clock instance for retrieving proper times
            dynamics (:class:`.Dynamics`): TargetAgent's simulation dynamics
            realtime (``bool``): whether to use :attr:`dynamics` or import data for propagation
            process_noise (``numpy.ndarray``): 6x6 process noise covariance
            seed (int, optional): number to seed random number generator. Defaults to ``None``.

        Raises:
            TypeError: raised on incompatible types for input params
            ShapeError: raised if process noise is not a 6x6 matrix
        """
        # [TODO]: Make visual cross-section better
        super(TargetAgent, self).__init__(
            _id, name, agent_type, initial_state, clock, dynamics, realtime, visual_cross_section=25.0
        )
        if not isinstance(process_noise, ndarray):
            self._logger.error("Incorrect type for process_noise param")
            raise TypeError(type(process_noise))
        elif process_noise.shape != (6, 6):
            self._logger.error("Incorrect shape for process_noise param")
            raise ShapeError(process_noise.shape)
        # Process noise covariance used for generating noise
        self._process_noise_covar = process_noise

        if not isinstance(seed, int) and seed is not None:
            self._logger.error("Incorrect type for seed param")
            raise TypeError(type(seed))
        # Save the random number generator for generating noise
        self._rng = default_rng(seed)

        # Properly initialize the TargetAgent's state types
        self._truth_state = copy(initial_state)
        self._ecef_state = eci2ecef(self._truth_state)
        self._lla_state = ecef2lla(self._ecef_state)

    def getCurrentEphemeris(self):
        """Returns the TargetAgent's current ephemeris information.

        This is used for bulk-updating the output database with state information.

        Returns:
            :class:`.TruthEphemeris`: valid data object for insertion into output database.
        """
        date_time = julianDateToDatetime(self.julian_date_epoch)

        return TruthEphemeris.fromECIVector(
            unique_id=self.simulation_id,
            name=self.name,
            julian_date=self.julian_date_epoch,
            timestampISO=date_time.isoformat() + '.000Z',
            eci=self.eci_state.tolist()
        )

    def updateTask(self, new_time):
        """Create a task to be processed in parallel and update :attr:`time` appropriately.

        This relies on a common interface for :meth:`.Dynamics.propagate`

        Args:
            new_time (:class:`.ScenarioTime`): payload sent by :class:`.PropagateJobHandler` to
                indicate the current simulation time

        Returns
            :class:`.Task`: Task to be processed in parallel.
        """
        task = Task(
            self.callback.job_computation,
            args=[
                self._dynamics,
                self._time,
                new_time,
                self._truth_state
            ]
        )
        self._time = new_time

        return task

    def jobCompleteCallback(self, job):
        """Execute when the job submitted in :meth:`~.TargetAgent.updateTask` completes.

        Args:
            job (:class:`.Task`): job object that's returned when a job completes
        """
        self.eci_state = job.retval

    def importState(self, ephemeris):
        """Set the state of this TargetAgent based on a given :class:`.Ephemeris` object.

        Args:
            ephemeris (:class:`.Ephemeris`): data object to update this TargetAgent's state with
        """
        self.eci_state = asarray(ephemeris.eci)
        self._time = JulianDate(ephemeris.julian_date).convertToScenarioTime(self.julian_date_start)

    @classmethod
    def fromConfig(cls, config, events):
        """Factory to initialize `TargetAgent`s based on given configuration.

        Args:
            config (``dict``): formatted configuration parameters
            events (``dict``): corresponding formatted events

        Returns:
            :class:`.TargetAgent`: properly constructed `TargetAgent` object
        """
        ## [TODO]: Make this not coupled to only `Satellite` targets
        tgt = config["target"]

        # Determine the target's initial ECI state
        initial_coe = tgt.get("init_coe")
        initial_eci = tgt.get("init_eci")

        if initial_coe is not None:
            orbit = Orbit.buildFromCOEConfig(initial_coe)
            initial_state = orbit.coe2rv()
        elif initial_eci is not None:
            initial_state = asarray(initial_eci)
        else:
            raise ValueError("Target dict doesn't contain initial state information: {0}".format(tgt))

        return cls(
            tgt["sat_num"],
            tgt["sat_name"],
            "Spacecraft",
            initial_state,
            config["clock"],
            config["dynamics"],
            config["realtime"],
            config["noise"],
            seed=config["random_seed"]
        )

    @property
    def eci_state(self):
        """``numpy.ndarray``: Returns the 6x1 ECI current state vector."""
        return self._truth_state

    @eci_state.setter
    def eci_state(self, new_state):
        """Set the TargetAgent's new 6x1 ECI state vector.

        Args:
            new_state (``numpy.ndarray``): 6x1 ECI state vector
        """
        self._truth_state = new_state
        self._ecef_state = eci2ecef(new_state)
        self._lla_state = ecef2lla(self._ecef_state)

    @property
    def ecef_state(self):
        """``numpy.ndarray``: Returns the 6x1 ECEF current state vector."""
        return self._ecef_state

    @property
    def lla_state(self):
        """``numpy.ndarray``: Returns the 3x1 current position vector in lat, lon, & alt."""
        return self._lla_state

    @property
    def process_noise(self):
        """``numpy.ndarray``: Returns the 6x1 scaled process noise vector."""
        return self._rng.multivariate_normal(self.eci_state, self.process_noise_covariance)

    @property
    def process_noise_covariance(self):
        """``numpy.ndarray``: Returns the 6x6 process noise matrix."""
        return self._process_noise_covar
