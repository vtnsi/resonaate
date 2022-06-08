# Standard Library Imports
import logging
from abc import ABCMeta, abstractmethod, abstractproperty, abstractclassmethod
# Third Party Imports
from numpy import ndarray
from sqlalchemy.orm import Query
# RESONAATE Imports
from ..common.utilities import getTypeString
from ..data.data_interface import DataInterface
from ..data.ephemeris import TruthEphemeris
from ..dynamics.dynamics_base import Dynamics
from ..parallel.async_functions import asyncPredict, asyncPropagate
from ..parallel.job_handler import CallbackRegistration
from ..scenario.clock import ScenarioClock


class Agent(metaclass=ABCMeta):
    """Abstract base class for a generic Agent object, i.e. an actor in the simulation."""

    def __init__(self, _id, name, agent_type, initial_state, clock, dynamics, realtime, visual_cross_section):
        """Construct an Agent object.

        Args:
            _id (``int``): unique identification number
            name (``str``): unique identification name
            agent_type (``str``): name signifying the type of agent `('Spacecraft', 'GroundFacility', )`
            initial_state (``numpy.ndarray``): 6x1 ECI initial state vector
            clock (:class:`.ScenarioClock`): clock instance for retrieving proper times
            dynamics (:class:`.Dynamics`): Agent's simulation dynamics
            realtime (``bool``): whether to use :attr:`.dynamics` or import data for propagation
            visual_cross_section (``float``): constant visual cross-section of the agent

        Raises:
            TypeError: raised on incompatible types for input params
            ValueError: raised if invalid viz cross section is provided
        """
        # Define a logger for the Agent
        self._logger = logging.getLogger("resonaate")

        if not isinstance(_id, int):
            self._logger.error("Incorrect type for _id param")
            raise TypeError(type(_id))
        # Agent's integer ID number
        self._id = _id

        if not isinstance(name, str):
            self._logger.error("Incorrect type for name param")
            raise TypeError(type(name))
        # String for the Agent's name.
        self._name = name

        if not isinstance(agent_type, str):
            self._logger.error("Incorrect type for agent_type param")
            raise TypeError(type(agent_type))
        # String for the Agent's type.
        self._type = agent_type

        if not isinstance(initial_state, ndarray):
            self._logger.error("Incorrect type for initial_state param")
            raise TypeError(type(initial_state))
        # ECI initial state vector describing the Agent's position & velocity
        self._initial_state = initial_state.reshape(6)

        if not isinstance(clock, ScenarioClock):
            self._logger.error("Incorrect type for clock param")
            raise TypeError(type(clock))
        # Time associated with the state in the state property (seconds)
        self._time = clock.time

        # Julian date of start time
        self.julian_date_start = clock.julian_date_start

        if not isinstance(dynamics, Dynamics):
            self._logger.error("Incorrect type for dynamics param")
            raise TypeError(type(dynamics))
        # Dynamics class for propagating the Agent's state
        self._dynamics = dynamics

        if not isinstance(realtime, bool):
            self._logger.error("Incorrect type for realtime param")
            raise TypeError(type(realtime))
        # Flag for using real-time propagation
        self._realtime = realtime

        if not isinstance(visual_cross_section, (int, float)):
            self._logger.error("Incorrect type for visual_cross_section param")
            raise TypeError(type(visual_cross_section))
        elif visual_cross_section < 0.0:
            self._logger.error("Invalid value for visual_cross_section param")
            raise ValueError(visual_cross_section)
        # Visible cross sectional area (m^2)
        self._visual_cross_section = visual_cross_section

        # Set callback associated with parallel propagation
        self.callback = self.setCallback()

    def setCallback(self):
        """Set the callback associated when :meth:`.executeJobs()` is executed.

        Note:
            Assumes that :class:`.EstimateAgent` objects don't have importable :class:`.Ephemeris`:

            1. If an instance of :class:`.EstimateAgent`, use :func:`.asyncPredict`.
            #. If the :attr:`realtime` is ``True``, use :func:`.asyncPropagate`.
            #. If neither are true query the database for :class:`.Ephemeris` items.
            #. If a valid :class:`.Ephemeris` returns, use :meth:`.importState`.
            #. Otherwise, fall back to :func:`.asyncPropagate`.

        Returns:
            :meth:`.importstate`, or instance of :class:`.CallbackRegistration`
        """
        if getTypeString(self) == "EstimateAgent":
            # This is an `EstimateAgent`, so use `::asyncPredict()`
            callback = CallbackRegistration(
                self,
                self.updateTask,
                asyncPredict,
                self.jobCompleteCallback
            )
        elif self._realtime is True:
            # Realtime propagation is on, so use `::asyncPropagate()`
            callback = CallbackRegistration(
                self,
                self.updateTask,
                asyncPropagate,
                self.jobCompleteCallback
            )
        else:
            # Realtime propagation is off, attempt to query database for valid `Ephemeris` objects
            shared_interface = DataInterface.getSharedInterface()
            query = Query([TruthEphemeris]).filter(TruthEphemeris.unique_id == self.simulation_id)
            truth_ephem = shared_interface.getData(query, multi=False)

            # If minimal truth data exists in the database, use importer model, otherwise default to
            # realtime propagation (and print warning that this happened).
            if truth_ephem is None:
                self._logger.warning(
                    "Could not find importer truth for {0}. Defaulting to realtime propagation!".format(
                        self.simulation_id
                    )
                )
                callback = CallbackRegistration(
                    self,
                    self.updateTask,
                    asyncPropagate,
                    self.jobCompleteCallback
                )
            else:
                callback = self.importState

        return callback

    ### Abstract Methods & Properties ###

    @abstractmethod
    def getCurrentEphemeris(self):
        """Retrieve the Agent's current state for publishing to the DB.

        Returns:
            :class:`._EphemerisMixin`: valid data for inserting into the DB
        """
        raise NotImplementedError

    @abstractmethod
    def updateTask(self, new_time):
        """Create a task to be processed in parallel and update :attr:`time` appropriately.

        Args:
            new_time (:class:`.ScenarioTime`): payload sent by :class:`.PropagateJobHandler` to
                indicate the current simulation time

        Returns
            :class:`.Task`: Task to be processed in parallel.
        """
        raise NotImplementedError

    @abstractmethod
    def jobCompleteCallback(self, job):
        """Execute when the job submitted in :meth:`~.Agent.updateTask` completes.

        Args:
            job (:class:`.Task`): job object that's returned when a job completes
        """
        raise NotImplementedError

    @abstractmethod
    def importState(self, ephemeris):
        """Set the state of this Agent based on a given :class:`.Ephemeris` object.

        Args:
            ephemeris (:class:`.Ephemeris`): data object to update this Agent's state with
        """
        raise NotImplementedError

    @abstractproperty
    def eci_state(self):
        """``numpy.ndarray``: Returns the 6x1 ECI current state vector."""
        raise NotImplementedError

    @abstractproperty
    def ecef_state(self):
        """``numpy.ndarray``: Returns the 6x1 ECEF current state vector."""
        raise NotImplementedError

    @abstractproperty
    def lla_state(self):
        """``numpy.ndarray``: Returns the 3x1 current position vector in lat, lon, & alt."""
        raise NotImplementedError

    @abstractclassmethod
    def fromConfig(cls, config, events):
        """Factory to initialize `Agent`s based on given configuration.

        Args:
            config (``dict``): formatted configuration parameters
            events (``dict``): corresponding formatted events

        Returns:
            :class:`.Agent`: properly constructed `Agent` object
        """
        raise NotImplementedError

    ### Read-Only Instance Properties ###

    @property
    def initial_state(self):
        """``numpy.ndarray``: Returns the 6x1 initial ECI state vector."""
        return self._initial_state

    @property
    def julian_date_epoch(self):
        """:class:`.JulianDate`: Returns the current Julian date."""
        return self._time.convertToJulianDate(self.julian_date_start)

    @property
    def name(self):
        """``str``: Returns an Agent's name."""
        return self._name

    @property
    def agent_type(self):
        """``str``: Returns an Agent's type."""
        return self._type

    @property
    def dynamics(self):
        """:class:`.Dynamics`: Returns an Agent's dynamics class instance."""
        return self._dynamics

    @property
    def realtime(self):
        """``bool``: Returns whether this Agent is being propagated in realtime, or if an importer model is used."""
        return self._realtime

    @property
    def simulation_id(self):
        """``int``: Returns an ID number associated with the Agent.

        - Spacecraft: SATCAT ID
        - Non-Spacecraft: 10000+
        """
        return self._id

    @property
    def time(self):
        """:class:`.ScenarioTime`: Returns current epoch seconds."""
        return self._time

    @property
    def visual_cross_section(self):
        """``float``: Returns the visual cross-sectional area."""
        return self._visual_cross_section
