"""Defines scheduled impulsive burn events to control spaceraft."""
# Standard Library Imports
from abc import ABCMeta
# Third Party Imports
from numpy import concatenate, zeros
# RESONAATE Imports
from ...physics.transforms.methods import ntw2eci
from ...physics.math import fpe_equals
from .discrete_state_change_event import DiscreteStateChangeEvent
from .event_stack import EventStack, EventRecord


class ScheduledImpulse(DiscreteStateChangeEvent, metaclass=ABCMeta):
    """Describes an impulsive maneuver that takes place at a specific time."""

    def __init__(self, time, delta_v):
        """Instantiate a :class:`.ScheduledImpulse` object.

        Args:
            time (float): time of impulsive event in epoch seconds
            deltaV (numpy.ndarray): 3x1 array of thrust vectors (km/sec)
        """
        self.time = time
        self.thrust = concatenate((zeros(3), delta_v))

    def __call__(self, time, state):
        """When this function returns zero during integration, it interrupts the integration process.

        See Also:
            :meth:`.DiscreteStateChangeEvent.__call__()`
        """
        _val = time - self.time
        if fpe_equals(_val, 0.0):
            return 0.0
        return _val


class ScheduledECIImpulse(ScheduledImpulse):
    """Describes an impulsive maneuver that's applied in the ECI frame."""

    def getStateChange(self, time, state):
        """Return the delta between `state` and the desired end state.

        See Also:
            :meth:`.DiscreteStateChangeEvent.getStateChange()`
        """
        # [FIXME] Pass RSO ID in to `ScheduledImpulse` so event can be recorded properly
        EventStack.pushEvent(EventRecord("ECI Impulse", 0))
        return self.thrust


class ScheduledNTWImpulse(ScheduledImpulse):
    """Describes an impulsive maneuver that's applied in the NTW frame."""

    def getStateChange(self, time, state):
        """Return the delta between `state` and the desired end state.

        See Also:
            :meth:`.DiscreteStateChangeEvent.getStateChange()`
        """
        # [FIXME] Pass RSO ID in to `ScheduledImpulse` so event can be recorded properly
        EventStack.pushEvent(EventRecord("NTW Impulse", 0))
        return ntw2eci(state, self.thrust)
