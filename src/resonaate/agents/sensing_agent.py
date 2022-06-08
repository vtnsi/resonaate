# Standard Library Imports
import logging
# Third Party Imports
from numpy import copy, asarray
# RESONAATE Imports
from .agent_base import Agent
from ..data.ephemeris import TruthEphemeris
from ..dynamics.terrestrial import Terrestrial
from ..parallel.task import Task
from ..physics.time.stardate import JulianDate, julianDateToDatetime
from ..physics.transforms.methods import ecef2lla, eci2ecef, ecef2eci, lla2ecef
from ..sensors import sensorFactory
from ..sensors.sensor_base import Sensor


class SensingAgent(Agent):
    """Define the behavior of the sensing agents in the simulation."""

    def __init__(self, _id, name, agent_type, initial_state, clock, sensors, dynamics, realtime):
        """Construct a SensingAgent object.

        Args:
            _id (``int``): unique identification number
            name (``str``): unique identification name
            agent_type (``str``): name signifying the type of agent `('Spacecraft', 'GroundFacility', )`
            initial_state (``numpy.ndarray``): 6x1 ECI initial state vector
            clock (:class:`.ScenarioClock`): clock instance for retrieving proper times
            sensors (:class:`.Sensor`): sensor object associated this SensingAgent object
            dynamics (:class:`.Dynamics`): SensingAgent's simulation dynamics
            realtime (``bool``): whether to use :attr:`dynamics` or import data for propagation

        Raises:
            TypeError: raised on incompatible types for input params
        """
        # [TODO]: Make visual cross-section better
        super(SensingAgent, self).__init__(
            _id, name, agent_type, initial_state, clock, dynamics, realtime, visual_cross_section=25.0
        )
        # [TODO]: Make sensors attribute a collection, so we can attach multiple sensors to an agent
        # if not isinstance(sensors, Collection):
        #     self._logger.error("Incorrect type for sensors param")
        #     raise TypeError(type(sensors))
        # for sensor in sensors:
        if not isinstance(sensors, Sensor):
            self._logger.error("Item in sensors param is not a `Sensor` object")
            raise TypeError(type(sensors))
        self._sensors = sensors
        self._sensors.host = self

        # Properly initialize the SensingAgent's state types
        self._truth_state = copy(initial_state)
        self._ecef_state = eci2ecef(self._truth_state)
        self._lla_state = ecef2lla(self._ecef_state)

    def getCurrentEphemeris(self):
        """Returns the SensingAgent's current ephemeris information.

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

        his relies on a common interface for :meth:`.Dynamics.propagate`

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
        """Execute when the job submitted in :meth:`~.SensingAgent.updateTask` completes.

        Args:
            job (:class:`.Task`): job object that's returned when a job completes
        """
        self.eci_state = job.retval

    def importState(self, ephemeris):
        """Set the state of this SensingAgent based on a given :class:`.Ephemeris` object.

        Args:
            ephemeris (:class:`.Ephemeris`): data object to update this SensingAgent's state with
        """
        self.eci_state = asarray(ephemeris.eci)
        self._time = JulianDate(ephemeris.julian_date).convertToScenarioTime(self.julian_date_start)

    @classmethod
    def fromConfig(cls, config, events):
        """Factory to initialize `SensingAgent`s based on given configuration.

        Args:
            config (``dict``): formatted configuration parameters
            events (``dict``): corresponding formatted events

        Returns:
            :class:`.SensingAgent`: properly constructed `SensingAgent` object
        """
        agent = config["agent"]
        agent_type = agent["host_type"]

        # Build the sensor based on the agent configuration
        sensor = sensorFactory(agent)

        # Build generic agent kwargs
        if agent_type == "GroundFacility":
            # Assumes geodetic latitude
            lla_orig = asarray([
                agent["lat"], agent["lon"], agent["alt"]  # radians, radians, km
            ])
            ecef_state = lla2ecef(lla_orig)
            dynamics = Terrestrial(config["clock"].julian_date_start, ecef_state)
            initial_state = ecef2eci(ecef_state)
            use_realtime = True
        elif agent_type == "Spacecraft":
            initial_state = asarray(agent["eci_state"])
            # [TODO]: Find a way to pass down dynamics config?
            dynamics = config["satellite_dynamics"]
            use_realtime = config["realtime"]
        else:
            logger = logging.getLogger("resonaate")
            logger.error("Invalid value for 'host_type' key for sensor agent '{0}'".format(agent["name"]))
            raise ValueError(agent_type)

        return cls(
            agent["id"], agent["name"], agent_type, initial_state, config["clock"], sensor, dynamics, use_realtime
        )

    @property
    def eci_state(self):
        """``numpy.ndarray``: Returns the 6x1 ECI current state vector."""
        return self._truth_state

    @eci_state.setter
    def eci_state(self, new_state):
        """Set the SensingAgent's new 6x1 ECI state vector.

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
    def sensors(self):
        """``collections.abc.Collection``: Returns the collection of sensors associated with this SensingAgent."""
        return self._sensors
