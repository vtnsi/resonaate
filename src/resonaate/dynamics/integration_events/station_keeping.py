"""Defines station-keeping events that allow satellites to control their orbit "autonomously"."""
# Standard Library Imports
from abc import ABCMeta, abstractmethod
# Third Party Imports
from numpy import sin, cos, asarray
from scipy.linalg import norm
# RESONAATE Imports
from ...physics.constants import DEG2RAD
from ...physics.orbits.elements import ClassicalElements
from ...physics.math import safeArccos
from ...physics.transforms.methods import ntw2eci, eci2ecef, ecef2lla
from .discrete_state_change_event import DiscreteStateChangeEvent
from .event_stack import EventStack, EventRecord


class StationKeeper(DiscreteStateChangeEvent, metaclass=ABCMeta):
    """Abstract base class defining shared functionality for staion keeping objects."""

    CONF_STR_REGISTRY = None
    """dict: Correlates concrete classes' string configurations to their implementations."""

    def __init__(self, rso_id):
        """Initialization common across all :class:`.StationKeeper` objects.

        Args:
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
        """
        self._integration_time = None
        self._integration_state = None
        self._rso_id = rso_id

    @classmethod
    @abstractmethod
    def fromInitECI(cls, rso_id, initial_eci):
        """Instantiate a :class:`.StationKeeper` object.

        This abstract method defines a uniform way to instantiate :class:`.StationKeeper` objects.

        Args:
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
            initial_eci (``numpy.ndarray``): (6, ) initial ECI vector of the satellite, (km, km/s)
        """
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def getConfigString(cls):
        """str: Configuration string indicating this :class:`.StationKeeper` should be used."""
        raise NotImplementedError()

    @classmethod
    def _generateRegistry(cls):
        """Populate :attr:`.CONF_STR_REGISTRY` based on subclasses."""
        if cls.CONF_STR_REGISTRY is None:
            cls.CONF_STR_REGISTRY = dict()
            for subclass in cls.__subclasses__():
                cls.CONF_STR_REGISTRY[subclass.getConfigString()] = subclass

    @classmethod
    def validConfigs(cls):
        """Returns a list of valid config strings."""
        cls._generateRegistry()
        return list(cls.CONF_STR_REGISTRY.keys())

    @classmethod
    def factory(cls, conf_str, rso_id, initial_eci):
        """Construct a concrete :class:`.StationKeeper` object based on specified parameters.

        Args:
            conf_str (str): Configuration string used to indicate which :class:`.StationKeeper` to construct.
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
            initial_eci (numpy.ndarray): Initial ECI state of the RSO that's performing these station keeping maneuvers

        Returns:
            StationKeeper: A concrete :class:`.StationKeeper` object based on specified parameters.
        """
        cls._generateRegistry()
        return cls.CONF_STR_REGISTRY[conf_str].fromInitECI(rso_id, initial_eci)

    @abstractmethod
    def interruptRequired(self, time, state):
        """Return boolean indication of whether this :class:`.StationKeeper` needs to activate.

        Args:
            time (float): current integration time in epoch seconds
            state (numpy.ndarray): current integration state vector

        Returns:
            bool: Indication of whether this :class:`.StationKeeper` needs to activate.
        """
        raise NotImplementedError()

    def __call__(self, time, state):
        """When this function returns zero during integration, it interrupts the integration process.

        See Also:
            :meth:`.DiscreteStateChangeEvent.__call__()`
        """
        if self.interruptRequired(time, state):
            self.recordActivation(time, state)
            return 0
        return 1

    def recordActivation(self, time, state):
        """Record the results of the integration step where this :class:`.StationKeeper` was activated.

        Args:
            time (float): integration time (in epoch seconds) when this :class:`.StationKeeper` was activated.
            state (numpy.ndarray): integration state vector when this :class:`.StationKeeper` was activated.
        """
        self._integration_time = time
        self._integration_state = state

    def getActivationDetails(self):
        """float, numpy.ndarray: The integration time and state vector when activation occurred."""
        return self._integration_time, self._integration_state


class KeepGeoEastWest(StationKeeper):
    """Encapsulation of GEO maneuvers to compensate for longitudinal variations.

    References:
        :cite:t:`chao_2005_perturbations`, Section 8.1.1, Eqn 8.7
    """

    LON_DRIFT_THRESHOLD = 0.5 * DEG2RAD
    """float: Threshold of longitudinal drift that indicates a station keeping maneuver might take place."""

    BURN_THRESHOLD = 0.0000010  # km/s
    """float: Minimum magnitude of burn to apply."""

    def __init__(self, rso_id, initial_eci, initial_lon, initial_coe):
        """Instantiate a :class:`.KeepGeoEastWest` object.

        Args:
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
            initial_eci (numpy.ndarray): (6, ) initial ECI vector of the satellite, (km, km/s)
            initial_lon (float): initial longitude of the satellite
            initial_coe (ClassicalElements): classical orbital element set describing satellite's initial orbit
        """
        super().__init__(rso_id)
        self.initial_eci = initial_eci
        self.initial_lon = initial_lon
        self.initial_coe = initial_coe
        self.ntw_delta_v = 0.0

        self._integration_result = None  # for testing purposes mainly

    @classmethod
    def fromInitECI(cls, rso_id, initial_eci):
        """Factory method.

        See Also:
            :meth:`.StationKeeper.fromInitECI()`
        """
        initial_lon = ecef2lla(eci2ecef(initial_eci))[1]  # radians
        initial_coe = ClassicalElements.fromECI(initial_eci)
        return cls(rso_id, initial_eci, initial_lon, initial_coe)

    @classmethod
    def getConfigString(cls):
        """Returns the config string that corresponds to this kind of station keeping maneuver."""
        return "GEO EW"

    def interruptRequired(self, time, state):
        """Return boolean indication of whether this :class:`.StationKeeper` needs to activate.

        Args:
            time (float): current integration time in epoch seconds
            state (numpy.ndarray): current integration state vector

        Returns:
            bool: Indication of whether this :class:`.StationKeeper` needs to activate.
        """
        self.ntw_delta_v = 0
        delta_lon = self.initial_lon - ecef2lla(eci2ecef(state))[1]  # radians
        if abs(delta_lon) >= self.LON_DRIFT_THRESHOLD:
            current_coe = ClassicalElements.fromECI(state)
            delta_a = self.initial_coe.sma - current_coe.sma  # km
            ntw_delta_v = current_coe.mean_motion * delta_a / 2  # km/s
            if abs(ntw_delta_v) >= self.BURN_THRESHOLD:
                self.ntw_delta_v = ntw_delta_v
                return True
        return False

    def getStateChange(self, time, state):
        """Return burn vector to compensate for longitudinal variations.

        If delta_a > 0, West burn, velocity direction.
        If delta_a < 0, East burn, anti-velocity direction.
        Convention is to do a burn if long has changed by 0.5 degrees.

        Args:
            time (float): current integration time in epoch seconds
            state (numpy.ndarray): (6, ) current ECI vector of the satellite, (km, km/s)

        Returns:
            numpy.ndarray: (6, ) ECI burn vector of the satellite, (km, km/s)
        """
        if self.ntw_delta_v == 0.0:
            raise Exception("No state change to apply.")

        if self.ntw_delta_v > 0:
            direction = "West"
        else:
            direction = "East"
        EventStack.pushEvent(EventRecord(f"Station Keep GEO {direction}", self._rso_id))

        # apply to 'T' direction
        return ntw2eci(state, asarray([0, 0, 0, 0, self.ntw_delta_v, 0], dtype=float))


class KeepGeoNorthSouth(StationKeeper):
    """Encapsulation of GEO maneuvers to compensate for latitudinal variations.

    References:
        :cite:t:`chao_2005_perturbations`, Section 8.2, Eqn 8.11 & 8.12
    """

    LAT_DRIFT_THRESHOLD = 1.0 * DEG2RAD
    """float: Threshold of latitudinal drift that indicates a station keeping maneuver might take place."""

    BURN_THRESHOLD = 0.0010  # km/s
    """float: Minimum magnitude of burn to apply."""

    def __init__(self, rso_id, initial_eci, initial_lat, initial_coe):
        """Instantiate a :class:`.KeepGeoNorthSouth` object.

        Args:
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
            initial_eci (numpy.ndarray): (6, ) initial ECI vector of the satellite, (km, km/s)
            initial_lat (float): initial latitude of the satellite
            initial_coe (ClassicalElements): classical orbital element set describing satellite's initial orbit
        """
        super().__init__(rso_id)
        self.initial_eci = initial_eci
        self.initial_lat = initial_lat
        self.initial_coe = initial_coe
        self.ntw_delta_v = 0.0

    @classmethod
    def fromInitECI(cls, rso_id, initial_eci):
        """Factory method.

        See Also:
            :meth:`.StationKeeper.fromInitECI()`
        """
        initial_lat = ecef2lla(eci2ecef(initial_eci))[0]  # radians
        initial_coe = ClassicalElements.fromECI(initial_eci)
        return cls(rso_id, initial_eci, initial_lat, initial_coe)

    @classmethod
    def getConfigString(cls):
        """Returns the config string that corresponds to this kind of station keeping maneuver."""
        return "GEO NS"

    def interruptRequired(self, time, state):
        """Return boolean indication of whether this :class:`.StationKeeper` needs to activate.

        Args:
            time (float): current integration time in epoch seconds
            state (numpy.ndarray): current integration state vector

        Returns:
            bool: Indication of whether this :class:`.StationKeeper` needs to activate.
        """
        self.ntw_delta_v = 0
        delta_lat = self.initial_lat - ecef2lla(eci2ecef(state))[0]
        if abs(delta_lat) >= self.LAT_DRIFT_THRESHOLD:
            current_vel = norm(state[3:])  # km/s
            current_coe = ClassicalElements.fromECI(state)
            delta_theta = safeArccos(
                (sin(current_coe.inc)**2) * cos(current_coe.raan - self.initial_coe.raan) + cos(current_coe.inc)**2
            )
            ntw_delta_v = 2 * current_vel * sin(delta_theta)  # km/s (sin assumes radians)
            if abs(ntw_delta_v) >= self.BURN_THRESHOLD:
                self.ntw_delta_v = ntw_delta_v
                return True
        return False

    def getStateChange(self, time, state):
        """Return burn vector to compensate for latitudinal variations.

        If ntw_delta_v > 0, North burn, velocity direction.
        If ntw_delta_v < 0, South burn, anti-velocity direction.
        Convention is to do a burn if latitude has changed by 1 degrees.

        Args:
            time (float): current integration time in epoch seconds
            state (numpy.ndarray): (6, ) current ECI vector of the satellite, (km, km/s)

        Returns:
            numpy.ndarray: (6, ) ECI burn vector of the satellite, (km, km/s)
        """
        if self.ntw_delta_v == 0.0:
            raise Exception("No state change to apply.")

        if self.ntw_delta_v > 0:
            direction = "North"
        else:
            direction = "South"
        EventStack.pushEvent(EventRecord(f"Station Keep GEO {direction}", self._rso_id))

        # apply to 'W' direction
        return ntw2eci(state, asarray([0, 0, 0, 0, 0, self.ntw_delta_v], dtype=float))


class KeepLeoUp(StationKeeper):
    """Encapsulation of LEO maneuvers to compensate for gravity / drag / 3rd body effects.

    References:
        :cite:t:`chao_2005_perturbations`, Section 7.1.1, Eqn 7.6
    """

    ALT_DRIFT_THRESHOLD = 2.  # km
    """float: Threshold of altitude drift that indicates a station keeping maneuver might take place."""

    BURN_THRESHOLD = 0.0000010  # km/s
    """float: Minimum magnitude of burn to apply."""

    def __init__(self, rso_id, initial_eci, initial_coe):
        """Instantiate a :class:`.KeepGeoNorthSouth` object.

        Args:
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
            initial_eci (numpy.ndarray): (6, ) initial ECI vector of the satellite, (km, km/s)
            initial_coe (ClassicalElements): classical orbital element set describing satellite's initial orbit
        """
        super().__init__(rso_id)
        self.initial_eci = initial_eci
        self.initial_coe = initial_coe
        self.ntw_delta_v = 0.0

    @classmethod
    def fromInitECI(cls, rso_id, initial_eci):
        """Factory method.

        See Also:
            :meth:`.StationKeeper.fromInitECI()`
        """
        initial_coe = ClassicalElements.fromECI(initial_eci)
        return cls(rso_id, initial_eci, initial_coe)

    @classmethod
    def getConfigString(cls):
        """Returns the config string that corresponds to this kind of station keeping maneuver."""
        return "LEO"

    def interruptRequired(self, time, state):
        """Return boolean indication of whether this :class:`.StationKeeper` needs to activate.

        Args:
            time (float): current integration time in epoch seconds
            state (numpy.ndarray): current integration state vector

        Returns:
            bool: Indication of whether this :class:`.StationKeeper` needs to activate.
        """
        self.ntw_delta_v = 0
        current_coe = ClassicalElements.fromECI(state)
        delta_a = self.initial_coe.sma - current_coe.sma  # km
        if delta_a >= self.ALT_DRIFT_THRESHOLD:
            ntw_delta_v = current_coe.mean_motion * delta_a / 2  # km/s
            if abs(ntw_delta_v) >= self.BURN_THRESHOLD:
                self.ntw_delta_v = ntw_delta_v
                return True
        return False

    def getStateChange(self, time, state):
        """Return burn vector to compensate for gravity / drag / 3rd body effects.

        Args:
            time (float): current integration time in epoch seconds
            state (numpy.ndarray): (6, ) current ECI vector of the satellite, (km, km/s)

        Returns:
            numpy.ndarray: (6, ) ECI burn vector of the satellite, (km, km/s)
        """
        if self.ntw_delta_v == 0.0:
            raise Exception("No state change to apply.")

        EventStack.pushEvent(EventRecord("Station Keep LEO Alt Incr", self._rso_id))

        # apply to 'T' direction
        return ntw2eci(state, asarray([0, 0, 0, 0, self.ntw_delta_v, 0], dtype=float))
