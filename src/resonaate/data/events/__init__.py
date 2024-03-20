"""Package describing different types of events that can take place during a resonaate scenario.

This module defines the common functions used to interact with the events data objects.
"""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from sqlalchemy.orm import Query, with_polymorphic

# Local Imports
from .agent_removal import AgentRemovalEvent
from .base import Event, EventScope
from .finite_burn import ScheduledFiniteBurnEvent
from .finite_maneuver import ScheduledFiniteManeuverEvent
from .scheduled_impulse import ScheduledImpulseEvent
from .sensor_addition import SensorAdditionEvent
from .sensor_time_bias import SensorTimeBiasEvent
from .target_addition import TargetAdditionEvent
from .target_task_priority import TargetTaskPriority

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

    # Local Imports
    from ...common.logger import Logger
    from ...data.resonaate_database import ResonaateDatabase
    from ...physics.time.stardate import JulianDate

__all__ = [
    "AgentRemovalEvent",
    "Event",
    "EventScope",
    "ScheduledFiniteBurnEvent",
    "ScheduledFiniteManeuverEvent",
    "ScheduledImpulseEvent",
    "SensorAdditionEvent",
    "SensorTimeBiasEvent",
    "TargetAdditionEvent",
    "TargetTaskPriority",
]


def getRelevantEvents(
    database: ResonaateDatabase,
    event_scope: EventScope,
    julian_date_lb: JulianDate,
    julian_date_ub: JulianDate,
    scope_instance_id: int | None = None,
) -> list[Event]:
    """Return a list of :class:`.Event` objects for the current time step and scope.

    Args:
        database (:class:`.ResonaateDatabase`): Database for retrieving events from.
        event_scope (:class:`.EventScope`): Relevant scope to query events for.
        julian_date_lb (:class:`JulianDate`): Lower bound on Julian Date to search.
        julian_date_ub (:class:`JulianDate`): Upper bound on Julian Date to search.
        scope_instance_id (``int``, optional): Unique ID of the object that needs to handle the events returned by
            the query.

    Returns:
        ``list``: relevant :class:`.Event` objects.
    """
    event_alias = with_polymorphic(Event, "*")
    query = Query(event_alias).filter(
        event_alias.scope == event_scope.value,
        event_alias.start_time_jd <= julian_date_ub,
        event_alias.end_time_jd > julian_date_lb,
    )
    if scope_instance_id is not None:
        query.filter(event_alias.scope_instance_id == scope_instance_id)
    return database.getData(query)


def handleRelevantEvents(
    scope_instance: Any,
    database: ResonaateDatabase,
    event_scope: EventScope,
    julian_date_lb: JulianDate,
    julian_date_ub: JulianDate,
    logger: Logger,
    scope_instance_id: int | None = None,
) -> None:
    """Handle events relevant for a given scope and time.

    Args:
        scope_instance (``any``): Scope object that will handle the relevant events.
        database (:class:`.ResonaateDatabase`): Database for retrieving events from.
        event_scope (:class:`.EventScope`): Relevant scope to query events for.
        julian_date_lb (:class:`JulianDate`): Lower bound on Julian Date to search.
        julian_date_ub (:class:`JulianDate`): Upper bound on Julian Date to search.
        logger (:class:`.Logger`): Logger instance.
        scope_instance_id (``int``, optional): Unique ID of the object that needs to handle the events returned by
            the query.
    """
    event_types = set()
    event_count = 0
    for event in getRelevantEvents(
        database,
        event_scope,
        julian_date_lb,
        julian_date_ub,
        scope_instance_id,
    ):
        event.handleEvent(scope_instance)
        event_types.add(event.event_type)
        event_count += 1
    if event_count:
        logger.info(f"Handled {event_count} {event_scope.value!r} events of types {event_types}")
