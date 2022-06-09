# Standard Library Imports
import logging
from abc import ABCMeta, abstractmethod, abstractproperty, abstractclassmethod
# Third Party Imports
from numpy import ndarray
# RESONAATE Imports
from ..common.utilities import checkTypes
from ..dynamics.dynamics_base import Dynamics
from ..scenario.clock import ScenarioClock
from ..dynamics.integration_events.station_keeping import StationKeeper


DEFAULT_VIS_X_SECTION = 25.0
"""float: Default value for `visual_cross_section`.

TODO: Make this better
"""


class Agent(metaclass=ABCMeta):
    """Abstract base class for a generic Agent object, i.e. an actor in the simulation."""

    TYPES = {
        "_id": int,
        "name": str,
        "agent_type": str,
        "initial_state": ndarray,
        "clock": ScenarioClock,
        "dynamics": Dynamics,
        "realtime": bool,
        "visual_cross_section": (int, float),
        "station_keeping": (list, type(None))
    }

    def __init__(self, _id, name, agent_type, initial_state, clock, dynamics,
                 realtime, visual_cross_section, station_keeping=None):
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
            station_keeping (list, optional): list of :class:`.StationKeeper` objects describing the station keeping to
                be performed

        Raises:
            TypeError: raised on incompatible types for input params
            ValueError: raised if invalid viz cross section is provided
        """
        # Define a logger for the Agent
        self._logger = logging.getLogger("resonaate")
        checkTypes(locals(), self.TYPES)

        # Agent's integer ID number
        self._id = _id
        # String for the Agent's name.
        self._name = name
        # String for the Agent's type.
        self._type = agent_type
        # ECI initial state vector describing the Agent's position & velocity
        self._initial_state = initial_state.reshape(6)
        # Time associated with the state in the state property (seconds)
        self._time = clock.time
        # Julian date of start time
        self.julian_date_start = clock.julian_date_start
        # Dynamics class for propagating the Agent's state
        self._dynamics = dynamics
        # Flag for using real-time propagation
        self._realtime = realtime

        if visual_cross_section < 0.0:
            self._logger.error("Invalid value for visual_cross_section param")
            raise ValueError(visual_cross_section)
        # Visible cross sectional area (m^2)
        self._visual_cross_section = visual_cross_section

        # Default callback is `None`
        self.callback = None

        if station_keeping:
            self._station_keeping = station_keeping
        else:
            self._station_keeping = []
        for station_keeper in self._station_keeping:
            if not isinstance(station_keeper, StationKeeper):
                err = f"{station_keeper} is not a valid StationKeeper object."
                raise TypeError(err)

    @abstractmethod
    def setCallback(self, importer):
        """Set the callback associated when :meth:`.executeJobs()` is executed.

        Args:
            importer (``bool``): whether a proper :class:`.ImporterDatabase` exists

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
        raise NotImplementedError

    ### Abstract Methods & Properties ###

    @abstractmethod
    def getCurrentEphemeris(self):
        """Retrieve the Agent's current state for publishing to the DB.

        Returns:
            :class:`._EphemerisMixin`: valid data for inserting into the DB
        """
        raise NotImplementedError

    @abstractmethod
    def updateJob(self, new_time):
        """Create a job to be processed in parallel and update :attr:`time` appropriately.

        Args:
            new_time (:class:`.ScenarioTime`): payload sent by :class:`.PropagateJobHandler` to
                indicate the current simulation time

        Returns
            :class:`.Job`: Job to be processed in parallel.
        """
        raise NotImplementedError

    @abstractmethod
    def jobCompleteCallback(self, job):
        """Execute when the job submitted in :meth:`~.Agent.updateJob` completes.

        Args:
            job (:class:`.Job`): job object that's returned when a job completes
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
    def station_keeping(self):
        """``list``: Returns the station_keeping list."""
        return self._station_keeping

    @property
    def visual_cross_section(self):
        """``float``: Returns the visual cross-sectional area."""
        return self._visual_cross_section
