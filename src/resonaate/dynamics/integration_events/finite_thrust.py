"""Defines finite thrust burn and maneuver events for basic control of satellites."""

from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, concatenate, zeros

# Local Imports
from ...physics.maths import fpe_equals
from ...physics.transforms.methods import ntw2eci
from .continuous_state_change_event import ContinuousStateChangeEvent
from .event_stack import EventRecord, EventStack

# Type checking
if TYPE_CHECKING:
    # Standard Library Imports
    from functools import partial

    # Third Party Imports
    from numpy import ndarray

    # RESONAATE Imports
    from resonaate.physics.time.stardate import ScenarioTime


def spiralThrust(state: ndarray, magnitude: float):
    """Perform a continuous spiral climb (positive magnitude) or spiral descent (negative magnitude).

    References:
        :cite:t:`pollard_2000_aero_simplified`

    Args:
        state (numpy.ndarray): current state vector for satellite
        magnitude (int, float): magnitude of burn in km/s^2

    Returns:
        (numpy.ndarray): acceleration vector in ECI coordinates
    """
    delta_a = array([0, magnitude, 0])
    acc_vector = concatenate((delta_a, zeros(3)))
    return ntw2eci(state, acc_vector)


def planeChangeThrust(state: ndarray, magnitude: float):
    """Perform a continuous plane change thrust.

    References:
        :cite:t:`pollard_2000_aero_simplified`

    Args:
        state (numpy.ndarray): current state vector for satellite
        magnitude (int, float): magnitude of burn in km/s^2

    Returns:
        (numpy.ndarray): acceleration vector in ECI coordinates
    """
    delta_a = array([0, 0, magnitude])
    delta_a = array([0, 0, magnitude]) if state[2] >= 0 else array([0, 0, -magnitude])
    acc_vector = concatenate((delta_a, zeros(3)))
    return ntw2eci(state, acc_vector)


def ntwBurn(state: ndarray, acc_vector: ndarray):
    """Perform a continuous burn in NTW coordinates.

    Args:
        state (numpy.ndarray): current state vector for satellite
        acc_vector (numpy.ndarray): 3x1 NTW acceleration vector in km/s^2

    Returns:
        (numpy.ndarray): acceleration vector in ECI coordinates
    """
    full_a_vec = concatenate((acc_vector, zeros(3)))
    return ntw2eci(state, full_a_vec)


def eciBurn(state: ndarray, acc_vector: ndarray):
    """Perform a continuous burn in ECI coordinates.

    Args:
        state (numpy.ndarray): current state vector for satellite
        acc_vector (numpy.ndarray): 3x1 ECI acceleration vector in km/s^2

    Returns:
        (numpy.ndarray): acceleration vector in ECI coordinates
    """
    return concatenate((acc_vector, zeros(3)))


class ScheduledFiniteThrust(ContinuousStateChangeEvent, metaclass=ABCMeta):
    """Describes a continuous maneuver that takes place over a specific period."""

    def __init__(
        self,
        start_time: ScenarioTime,
        end_time: ScenarioTime,
        thrust_func: partial,
        agent_id: int,
    ):
        """Instantiate a :class:`.ScheduledFiniteThrust` object.

        Args:
            start_time (``ScenarioTime``): scenario time when thrust begins
            end_time (``ScenarioTime``): scenario time when thrust ends
            thrust_func (functools.partial): a partial function describing the desired thrust
            agent_id (``int``): agent ID who executes this state change event
        """
        if thrust_func.func not in self.valid_thrust_funcs:
            raise ValueError("Thrust function must be a valid member of finite thrust functions")
        self.thrust_func = thrust_func
        self.start_time = start_time
        self.end_time = end_time
        self.agent_id = agent_id

    def __call__(self, time: ScenarioTime, state: ndarray):
        """When this function returns zero during integration, it interrupts the integration process.

        See Also:
            :meth:`.ContinuousStateChangeEvent.__call__()`
        """
        _ival = self.start_time - time
        _fval = self.end_time - time
        if fpe_equals(_ival, 0.0) or fpe_equals(_fval, 0.0):
            return 0.0
        return _ival

    def __eq__(self, other: ScheduledFiniteThrust):
        """Check for equality between maneuver events.

        See Also:
            :meth:`.ContinuousStateChangeEvent.__eq__()`
        """
        if not isinstance(other, ScheduledFiniteThrust):
            return NotImplemented
        return all(
            [
                self.start_time == other.start_time,
                self.end_time == other.end_time,
                self.thrust_func.func == other.thrust_func.func,
                self.agent_id == other.agent_id,
            ],
        )

    @property
    @abstractmethod
    def valid_thrust_funcs(self):
        """Valid thrust functions for event type."""
        raise NotImplementedError

    def getStateChangeCallback(self, time: ScenarioTime):
        """Return the thrust function.

        See Also:
            :meth:`.ContinuousStateChangeEvent.getStateChangeCallback()`
        """
        if fpe_equals(self.end_time - time, 0.0):
            EventStack.pushEvent(EventRecord(f"Finite thrust ended at {time}", self.agent_id))
            return None
        EventStack.pushEvent(EventRecord(f"Finite thrust at {time}", self.agent_id))
        return self.thrust_func


class ScheduledFiniteManeuver(ScheduledFiniteThrust):
    """Describes a continuous thrust in a controlled direction that takes place over a specific period."""

    _VALID_THRUST_FUNCS = (spiralThrust, planeChangeThrust)

    @property
    def valid_thrust_funcs(self):
        """Valid maneuver functions for finite maneuvers."""
        return self._VALID_THRUST_FUNCS


class ScheduledFiniteBurn(ScheduledFiniteThrust):
    """Describes a continuous thrust in a constant direction that takes place over a specific period."""

    _VALID_THRUST_FUNCS = (ntwBurn, eciBurn)

    @property
    def valid_thrust_funcs(self):
        """Valid thrust functions for finite burns."""
        return self._VALID_THRUST_FUNCS
