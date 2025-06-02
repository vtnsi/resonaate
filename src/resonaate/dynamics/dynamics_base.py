"""Defines the abstract base class :class:`.Dynamics`."""

from __future__ import annotations

# Standard Library Imports
from abc import abstractmethod
from enum import Flag, auto
from typing import TYPE_CHECKING

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Iterable

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..physics.time.stardate import ScenarioTime
    from .integration_events import ScheduledEventType
    from .integration_events.station_keeping import StationKeeper


class DynamicsErrorFlag(Flag):
    """Flags to indicate which errors should halt propagation."""

    COLLISION = auto()
    """Halt on any sort of collision."""


class Dynamics:
    """Abstract dynamics base class.

    The Dynamics class gives a general foundation for any dynamics model that describes
    how an Agent will behave within a specified scenario.
    """

    RELATIVE_TOL = 10**-10
    ABSOLUTE_TOL = 10**-12

    @abstractmethod
    def propagate(
        self,
        initial_time: ScenarioTime | float,
        final_time: ScenarioTime | float,
        initial_state: ndarray,
        station_keeping: Iterable[StationKeeper] | None = None,
        scheduled_events: Iterable[ScheduledEventType] | None = None,
        error_flags: DynamicsErrorFlag = DynamicsErrorFlag.COLLISION,
    ) -> ndarray:
        """Abstract method for forwards propagation."""
        raise NotImplementedError
