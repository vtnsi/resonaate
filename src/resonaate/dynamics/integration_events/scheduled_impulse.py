"""Defines scheduled impulsive burn events to control spacecraft."""
# Standard Library Imports
from abc import ABCMeta

# Third Party Imports
from numpy import concatenate, zeros

# Local Imports
from ...physics.maths import fpe_equals
from ...physics.transforms.methods import ntw2eci
from .discrete_state_change_event import DiscreteStateChangeEvent
from .event_stack import EventRecord, EventStack


class ScheduledImpulse(DiscreteStateChangeEvent, metaclass=ABCMeta):  # noqa: B024
    """Describes an impulsive maneuver that takes place at a specific time."""

    def __init__(self, time, delta_v, scope_instance_id):
        """Instantiate a :class:`.ScheduledImpulse` object.

        Args:
            time (``float``): time of impulsive event in epoch seconds
            delta_v (``ndarray``): 3x1 array of thrust vectors (km/sec)
            scope_instance_id (``int``): ID of the agent to perform the impulsive burn
        """
        self.time = time
        self.thrust = concatenate((zeros(3), delta_v))
        self.scope_instance_id = scope_instance_id

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
        EventStack.pushEvent(EventRecord("ECI Impulse", self.scope_instance_id))
        return self.thrust


class ScheduledNTWImpulse(ScheduledImpulse):
    """Describes an impulsive maneuver that's applied in the NTW frame."""

    def getStateChange(self, time, state):
        """Return the delta between `state` and the desired end state.

        See Also:
            :meth:`.DiscreteStateChangeEvent.getStateChange()`
        """
        # [FIXME] Pass RSO ID in to `ScheduledImpulse` so event can be recorded properly
        EventStack.pushEvent(EventRecord("NTW Impulse", self.scope_instance_id))
        return ntw2eci(state, self.thrust)
