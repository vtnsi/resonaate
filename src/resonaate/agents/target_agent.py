# Standard Library Imports
# Third Party Imports
from numpy import ndarray, copy, asarray
from numpy.random import default_rng
from sqlalchemy.orm import Query
# RESONAATE Imports
from .agent_base import Agent, DEFAULT_VIS_X_SECTION
from ..data.importer_database import ImporterDatabase
from ..data.ephemeris import TruthEphemeris
from ..common.exceptions import ShapeError
from ..parallel.async_functions import asyncPropagate
from ..parallel.job_handler import CallbackRegistration
from ..parallel.job import Job
from ..physics.orbit import Orbit
from ..physics.time.stardate import JulianDate
from ..physics.transforms.methods import ecef2lla, eci2ecef
from ..dynamics.integration_events.station_keeping import StationKeeper


class TargetAgent(Agent):
    """Define the behavior of the **true** target agents in the simulation."""

    def __init__(self, _id, name, agent_type, initial_state, clock, dynamics,
                 realtime, process_noise, seed=None, station_keeping=None):
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
            station_keeping (list, optional): list of :class:`.StationKeeper` objects describing the station keeping to
                be performed

        Raises:
            TypeError: raised on incompatible types for input params
            ShapeError: raised if process noise is not a 6x6 matrix
        """
        super(TargetAgent, self).__init__(
            _id, name, agent_type, initial_state, clock, dynamics, realtime, DEFAULT_VIS_X_SECTION,
            station_keeping=station_keeping
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
        return TruthEphemeris.fromECIVector(
            agent_id=self.simulation_id,
            julian_date=self.julian_date_epoch,
            eci=self.eci_state.tolist()
        )

    def updateJob(self, new_time):
        """Create a job to be processed in parallel and update :attr:`time` appropriately.

        This relies on a common interface for :meth:`.Dynamics.propagate`

        Args:
            new_time (:class:`.ScenarioTime`): payload sent by :class:`.PropagateJobHandler` to
                indicate the current simulation time

        Returns
            :class:`.Job`: Job to be processed in parallel.
        """
        job = Job(
            self.callback.job_computation,
            args=[
                self._dynamics,
                self._time,
                new_time,
                self._truth_state
            ],
            kwargs={
                "station_keeping": self.station_keeping
            }
        )
        self._time = new_time

        return job

    def setCallback(self, importer):
        """Set the callback associated when :meth:`.executeJobs()` is executed.

        Args:
            importer (``bool``): whether a proper :class:`.ImporterDatabase` exists
        Note:
            #. If the :attr:`realtime` is ``True``, use :func:`.asyncPropagate`.
            #. If neither are true query the database for :class:`.Ephemeris` items.
            #. If a valid :class:`.Ephemeris` returns, use :meth:`.importState`.
            #. Otherwise, fall back to :func:`.asyncPropagate`.

        Returns:
            :meth:`.importstate`, or instance of :class:`.CallbackRegistration`
        """
        if self._realtime is True:
            # Realtime propagation is on, so use `::asyncPropagate()`
            self.callback = CallbackRegistration(
                self,
                self.updateJob,
                asyncPropagate,
                self.jobCompleteCallback
            )
        elif importer:
            # Realtime propagation is off, attempt to query database for valid `Ephemeris` objects
            query = Query(TruthEphemeris).filter(TruthEphemeris.agent_id == self.simulation_id)
            truth_ephem = ImporterDatabase.getSharedInterface().getData(query, multi=False)

            # If minimal truth data exists in the database, use importer model, otherwise default to
            # realtime propagation (and print warning that this happened).
            if truth_ephem is None:
                self._logger.warning(
                    "Could not find importer truth for {0}. Defaulting to realtime propagation!".format(
                        self.simulation_id
                    )
                )
                self.callback = CallbackRegistration(
                    self,
                    self.updateJob,
                    asyncPropagate,
                    self.jobCompleteCallback
                )
            else:
                self.callback = self.importState

        else:
            self._logger.error("A valid ImporterDatabase was not established")
            raise ValueError(importer)

        return self.callback

    def jobCompleteCallback(self, job):
        """Execute when the job submitted in :meth:`~.TargetAgent.updateJob` completes.

        Args:
            job (:class:`.Job`): job object that's returned when a job completes
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
        if tgt.coe_set:
            orbit = Orbit.buildFromCOEConfig(tgt.init_coe)
            initial_state = orbit.coe2rv()
        elif tgt.eci_set:
            initial_state = asarray(tgt.init_eci)
        else:
            raise ValueError("Target dict doesn't contain initial state information: {0}".format(tgt))

        station_keeping = []
        for config_str in tgt.station_keeping:
            station_keeping.append(StationKeeper.factory(config_str, tgt.sat_num, initial_state))

        return cls(
            tgt.sat_num,
            tgt.sat_name,
            "Spacecraft",
            initial_state,
            config["clock"],
            config["dynamics"],
            config["realtime"],
            config["noise"],
            seed=config["random_seed"],
            station_keeping=station_keeping
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
