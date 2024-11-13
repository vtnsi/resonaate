"""Defines station-keeping events that allow satellites to control their orbit "autonomously"."""

from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod

# Third Party Imports
from numpy import asarray, cos, sin
from scipy.linalg import norm

# Local Imports
from ...physics.constants import DEG2RAD
from ...physics.maths import safeArccos
from ...physics.orbits.elements import ClassicalElements
from ...physics.time.stardate import JulianDate, julianDateToDatetime
from ...physics.transforms.methods import ecef2lla, eci2ecef, ntw2eci
from ..special_perturbations import _getRotationMatrix
from .discrete_state_change_event import DiscreteStateChangeEvent
from .event_stack import EventRecord, EventStack


class StationKeepingError(Exception):
    """Error with station-keeping algorithm."""


class StationKeeper(DiscreteStateChangeEvent, metaclass=ABCMeta):
    """Abstract base class defining shared functionality for station keeping objects."""

    CONF_STR_REGISTRY: dict = None
    """dict: Correlates concrete classes' string configurations to their implementations."""

    def __init__(self, rso_id):
        """Initialization common across all :class:`.StationKeeper` objects.

        Args:
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
        """
        self._integration_time = None
        self._integration_state = None
        self._rso_id = rso_id
        self.reductions = None

    @classmethod
    @abstractmethod
    def fromInitECI(cls, rso_id, initial_eci, julian_date_start):
        """Instantiate a :class:`.StationKeeper` object.

        This abstract method defines a uniform way to instantiate :class:`.StationKeeper` objects.

        Args:
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
            initial_eci (``numpy.ndarray``): (6, ) initial ECI vector of the satellite, (km, km/s)
            julian_date_start (:class:`.JulianDate`): Julian date of initial epoch, for later reference.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def getConfigString(cls):
        """str: Configuration string indicating this :class:`.StationKeeper` should be used."""
        raise NotImplementedError

    @classmethod
    def _generateRegistry(cls):
        """Populate :attr:`.CONF_STR_REGISTRY` based on subclasses."""
        if cls.CONF_STR_REGISTRY is None:
            cls.CONF_STR_REGISTRY = {}
            for subclass in cls.__subclasses__():
                cls.CONF_STR_REGISTRY[subclass.getConfigString()] = subclass

    @classmethod
    def validConfigs(cls):
        """Returns a list of valid config strings."""
        cls._generateRegistry()
        return list(cls.CONF_STR_REGISTRY.keys())

    @classmethod
    def factory(cls, conf_str, rso_id, initial_eci, julian_date_start):
        """Construct a concrete :class:`.StationKeeper` object based on specified parameters.

        Args:
            conf_str (str): Configuration string used to indicate which :class:`.StationKeeper` to construct.
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
            initial_eci (numpy.ndarray): Initial ECI state of the RSO that's performing these station keeping maneuvers
            julian_date_start (:class:`.JulianDate`): epoch associated with the initial state.

        Returns:
            StationKeeper: A concrete :class:`.StationKeeper` object based on specified parameters.
        """
        cls._generateRegistry()
        return cls.CONF_STR_REGISTRY[conf_str].fromInitECI(rso_id, initial_eci, julian_date_start)

    @abstractmethod
    def interruptRequired(self, time, state):
        """Return boolean indication of whether this :class:`.StationKeeper` needs to activate.

        Args:
            time (float): current integration time in epoch seconds
            state (numpy.ndarray): current integration state vector

        Returns:
            bool: Indication of whether this :class:`.StationKeeper` needs to activate.
        """
        raise NotImplementedError

    def __call__(self, time, state):
        """When this function returns zero during integration, it interrupts the integration process.

        See Also:
            :meth:`.DiscreteStateChangeEvent.__call__()`
        """
        # [FIXME]: I think this should return a 'continuous' float of the `trigger` value
        #   This could be related to Issue 41:
        #       https://code.vt.edu/space-research/resonaate/resonaate/-/issues/41
        #
        #   Basically, scipy event handling may _look_ for the crossing using the value returned,
        #   and a discontinuous jump may not provide enough information for the root
        #   finding algorithm.
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

    def __init__(self, rso_id, initial_eci, initial_lon, initial_coe, julian_date_start):
        """Instantiate a :class:`.KeepGeoEastWest` object.

        Args:
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
            initial_eci (numpy.ndarray): (6, ) initial ECI vector of the satellite, (km, km/s)
            initial_lon (float): initial longitude of the satellite
            initial_coe (ClassicalElements): classical orbital element set describing satellite's initial orbit
            julian_date_start (:class:`.JulianDate`): Julian date of initial epoch, for later reference.
        """
        super().__init__(rso_id)
        self.julian_date_start = julian_date_start
        self.initial_eci = initial_eci
        self.initial_lon = initial_lon
        self.initial_coe = initial_coe
        self.ntw_delta_v = 0.0

        self._integration_result = None  # for testing purposes mainly

    @classmethod
    def fromInitECI(cls, rso_id, initial_eci, julian_date_start):
        """Factory method.

        See Also:
            :meth:`.StationKeeper.fromInitECI()`
        """
        initial_lon = ecef2lla(eci2ecef(initial_eci, julianDateToDatetime(julian_date_start)))[
            1
        ]  # radians
        initial_coe = ClassicalElements.fromECI(initial_eci)
        return cls(rso_id, initial_eci, initial_lon, initial_coe, julian_date_start)

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
        julian_date = JulianDate(self.julian_date_start + time / 86400)
        matrix = _getRotationMatrix(julian_date, self.reductions).T
        delta_lon = self.initial_lon - ecef2lla(matrix.dot(state[:3]))[1]  # radians
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
            raise StationKeepingError("No state change to apply.")

        direction = "West" if self.ntw_delta_v > 0 else "East"
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

    def __init__(self, rso_id, initial_eci, initial_lat, initial_coe, julian_date_start):
        """Instantiate a :class:`.KeepGeoNorthSouth` object.

        Args:
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
            initial_eci (numpy.ndarray): (6, ) initial ECI vector of the satellite, (km, km/s)
            initial_lat (float): initial latitude of the satellite
            initial_coe (ClassicalElements): classical orbital element set describing satellite's initial orbit
            julian_date_start (:class:`.JulianDate`): Julian date of initial epoch, for later reference.
        """
        super().__init__(rso_id)
        self.julian_date_start = julian_date_start
        self.initial_eci = initial_eci
        self.initial_lat = initial_lat
        self.initial_coe = initial_coe
        self.ntw_delta_v = 0.0

    @classmethod
    def fromInitECI(cls, rso_id, initial_eci, julian_date_start):
        """Factory method.

        See Also:
            :meth:`.StationKeeper.fromInitECI()`
        """
        # radians
        initial_lat = ecef2lla(eci2ecef(initial_eci, julianDateToDatetime(julian_date_start)))[0]
        initial_coe = ClassicalElements.fromECI(initial_eci)
        return cls(rso_id, initial_eci, initial_lat, initial_coe, julian_date_start)

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
        julian_date = JulianDate(self.julian_date_start + time / 86400)
        matrix = _getRotationMatrix(julian_date, self.reductions).T
        delta_lat = self.initial_lat - ecef2lla(matrix.dot(state[:3]))[0]  # radians
        if abs(delta_lat) >= self.LAT_DRIFT_THRESHOLD:
            current_vel = norm(state[3:])  # km/s
            current_coe = ClassicalElements.fromECI(state)
            delta_theta = safeArccos(
                (sin(current_coe.inc) ** 2) * cos(current_coe.raan - self.initial_coe.raan)
                + cos(current_coe.inc) ** 2,
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
            raise StationKeepingError("No state change to apply.")

        direction = "North" if self.ntw_delta_v > 0 else "South"
        EventStack.pushEvent(EventRecord(f"Station Keep GEO {direction}", self._rso_id))

        # apply to 'W' direction
        return ntw2eci(state, asarray([0, 0, 0, 0, 0, self.ntw_delta_v], dtype=float))


class KeepLeoUp(StationKeeper):
    """Encapsulation of LEO maneuvers to compensate for gravity / drag / 3rd body effects.

    References:
        :cite:t:`chao_2005_perturbations`, Section 7.1.1, Eqn 7.7
    """

    ALT_DRIFT_THRESHOLD = 2.0  # km
    """float: Threshold of altitude drift that indicates a station keeping maneuver might take place."""

    BURN_THRESHOLD = 0.0000010  # km/s
    """float: Minimum magnitude of burn to apply."""

    def __init__(self, rso_id, initial_eci, initial_coe, julian_date_start):
        """Instantiate a :class:`.KeepGeoNorthSouth` object.

        Args:
            rso_id (int): Identifier for the RSO that's performing these station keeping maneuvers
            initial_eci (numpy.ndarray): (6, ) initial ECI vector of the satellite, (km, km/s)
            initial_coe (ClassicalElements): classical orbital element set describing satellite's initial orbit
            julian_date_start (:class:`.JulianDate`): Julian date of initial epoch, for later reference.
        """
        super().__init__(rso_id)
        self.julian_date_start = julian_date_start
        self.initial_eci = initial_eci
        self.initial_coe = initial_coe
        self.ntw_delta_v = 0.0

    @classmethod
    def fromInitECI(cls, rso_id, initial_eci, julian_date_start):
        """Factory method.

        See Also:
            :meth:`.StationKeeper.fromInitECI()`
        """
        initial_coe = ClassicalElements.fromECI(initial_eci)
        return cls(rso_id, initial_eci, initial_coe, julian_date_start)

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
        # [FIXME]: Disabling LEO Station Keeping for initially eccentric RSO
        if self.initial_coe.is_eccentric:
            return False
        current_coe = ClassicalElements.fromECI(state)
        if (delta_a := self.initial_coe.sma - current_coe.sma) >= self.ALT_DRIFT_THRESHOLD:
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
            raise StationKeepingError("No state change to apply.")

        EventStack.pushEvent(EventRecord("Station Keep LEO Alt Incr", self._rso_id))

        # apply to 'T' direction
        return ntw2eci(state, asarray([0, 0, 0, 0, self.ntw_delta_v, 0], dtype=float))
