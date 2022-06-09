"""Defines finite thrust burn and maneuver events for basic control of satellites."""
# Standard Library Imports
from abc import ABCMeta, abstractmethod
# Third Party Imports
from numpy import asarray, concatenate, zeros
# RESONAATE Imports
from ...physics.transforms.methods import ntw2eci
from ...physics.math import fpe_equals
from .continuous_state_change_event import ContinuousStateChangeEvent
from .event_stack import EventStack, EventRecord


def spiralThrust(state, magnitude):
    """Perform a continuous spiral climb (positive magnitude) or spiral descent (negative magnitude).

    References:
        :cite:t:`pollard_2000_aero_simplified`

    Args:
        state (numpy.ndarray): current state vector for satellite
        magnitude (int, float): magnitude of burn in km/s^2

    Returns:
        (numpy.ndarray): acceleration vector in ECI coordinates
    """
    delta_a = asarray([0, magnitude, 0])
    acc_vector = concatenate((delta_a, zeros(3)))
    return ntw2eci(state, acc_vector)


def planeChangeThrust(state, magnitude):
    """Perform a continuous plane change thrust.

    References:
        :cite:t:`pollard_2000_aero_simplified`

    Args:
        state (numpy.ndarray): current state vector for satellite
        magnitude (int, float): magnitude of burn in km/s^2

    Returns:
        (numpy.ndarray): acceleration vector in ECI coordinates
    """
    delta_a = asarray([0, 0, magnitude])
    if state[2] >= 0:
        delta_a = asarray([0, 0, magnitude])
    else:
        delta_a = asarray([0, 0, -magnitude])
    acc_vector = concatenate((delta_a, zeros(3)))
    return ntw2eci(state, acc_vector)


def ntwBurn(state, acc_vector):
    """Perform a continuous burn in NTW coordinates.

    Args:
        state (numpy.ndarray): current state vector for satellite
        acc_vector (numpy.ndarray): 3x1 NTW acceleration vector in km/s^2

    Returns:
        (numpy.ndarray): acceleration vector in ECI coordinates
    """
    full_a_vec = concatenate((acc_vector, zeros(3)))
    return ntw2eci(state, full_a_vec)


def _returnAccVec(state, full_a_vec):  # pylint: disable=unused-argument
    """Placeholder function to return acceleration vector."""
    return full_a_vec


def eciBurn(state, acc_vector):
    """Perform a continuous burn in ECI coordinates.

    Args:
        state (numpy.ndarray): current state vector for satellite
        acc_vector (numpy.ndarray): 3x1 ECI acceleration vector in km/s^2

    Returns:
        (numpy.ndarray): acceleration vector in ECI coordinates
    """
    full_a_vec = concatenate((acc_vector, zeros(3)))
    return _returnAccVec(state, full_a_vec)


class ScheduledFiniteThrust(ContinuousStateChangeEvent, metaclass=ABCMeta):
    """Describes a continuous maneuver that takes place over a specific period."""

    def __init__(self, time_bounds, thrust_func):
        """Instantiate a :class:`.ScheduledFiniteThrust` object.

        Args:
            time_bounds (numpy.ndarray): 2x1 array of continuous event times in epoch seconds, where the
                first entry is the initial time and the second entry is the final time.
            thrust_func (functools.partial): a partial function describing the desired thrust
        """
        if thrust_func.func not in self.valid_thrust_funcs:
            raise ValueError("Thrust function must be a valid member of finite thrust functions")
        self.thrust = thrust_func
        self.time = time_bounds[0]
        self.end_time = time_bounds[1]

    def __call__(self, time, state):
        """When this function returns zero during integration, it interrupts the integration process.

        See Also:
            :meth:`.ContinuousStateChangeEvent.__call__()`
        """
        _ival = self.time - time
        _fval = self.end_time - time
        if fpe_equals(_ival, 0.0) or fpe_equals(_fval, 0.0):
            return 0.0
        return _ival

    def __eq__(self, other):
        """Check for equality between maneuver events.

        See Also:
            :meth:`.ContinuousStateChangeEvent.__eq__()`
        """
        if not isinstance(other, ScheduledFiniteThrust):
            return NotImplemented
        return self.time == other.time and self.end_time == other.end_time and self.thrust.func == other.thrust.func

    @property
    @abstractmethod
    def valid_thrust_funcs(self):
        """Valid thrust functions for event type."""
        raise NotImplementedError()

    def getStateChangeCallback(self, time, state):
        """Return the thrust function.

        See Also:
            :meth:`.ContinuousStateChangeEvent.getStateChangeCallback()`
        """
        # [FIXME] Pass RSO ID in to `ScheduledImpulse` so event can be recorded properly
        if fpe_equals(self.end_time - time, 0.0):
            EventStack.pushEvent(EventRecord(f"Finite maneuver ended at {time}", 0))
            return None
        EventStack.pushEvent(EventRecord(f"Finite maneuver at {time}", 0))
        return self.thrust


class ScheduledFiniteManeuver(ScheduledFiniteThrust):
    """Describes a continuous maneuver that takes place over a specific period."""

    _VALID_THRUST_FUNCS = (spiralThrust, planeChangeThrust)

    @property
    def valid_thrust_funcs(self):
        """Valid thrust functions for finite maneuvers."""
        return self._VALID_THRUST_FUNCS


class ScheduledFiniteBurn(ScheduledFiniteThrust):
    """Describes a continuous burn that takes place over a specific period."""

    _VALID_THRUST_FUNCS = (ntwBurn, eciBurn)

    @property
    def valid_thrust_funcs(self):
        """Valid thrust functions for finite burns."""
        return self._VALID_THRUST_FUNCS
