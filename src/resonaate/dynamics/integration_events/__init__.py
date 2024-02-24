"""Package describing events that take place during :class:`.Dynamics`'s propagation."""

from __future__ import annotations

# Standard Library Imports
from typing import Union

# Local Imports
from .continuous_state_change_event import ContinuousStateChangeEvent
from .discrete_state_change_event import DiscreteStateChangeEvent

ScheduledEventType = Union[ContinuousStateChangeEvent, DiscreteStateChangeEvent]
