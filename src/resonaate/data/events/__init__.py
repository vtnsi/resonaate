"""Package describing different types of events that can take place during a resonaate scenario.

This module defines the common functions used to interact with the events data objects.
"""
# Third Party Imports
from sqlalchemy.orm import Query
from sqlalchemy.orm.util import with_polymorphic
# RESONAATE Imports
from .base import Event, EventScope
from .scheduled_impulse import ScheduledImpulseEvent
from .finite_burn import ScheduledFiniteBurnEvent
from .finite_maneuver import ScheduledFiniteManeuverEvent
from .target_task_priority import TargetTaskPriority
from .target_addition import TargetAdditionEvent
from .sensor_addition import SensorAdditionEvent
from .agent_removal import AgentRemovalEvent
from .sensor_time_bias import SensorTimeBiasEvent


def getRelevantEvents(database, event_scope, julian_date_epoch, scope_instance_id=None):
    """Return a list of :class:`.Event` objects for the current time step and scope.

    Args:
        database (:class:`.ResonaateDatabase`): Database for retreiving events from.
        event_scope (:class:`.EventScope`): Relevant scope to query events for.
        julian_date_epoch (:class:`JulianDate`): Current Julian date epoch.
        scope_instance_id (``int``, optional): Unique ID of the object that needs to handle the events returned by
            the query.

    Returns:
        ``list``: List of relevant :class:`.Event` objects.
    """
    event_alias = with_polymorphic(Event, '*')
    query = Query(event_alias).filter(
        event_alias.scope == event_scope.value,
        event_alias.start_time_jd <= julian_date_epoch,
        event_alias.end_time_jd >= julian_date_epoch
    )
    if scope_instance_id is not None:
        query.filter(event_alias.scope_instance_id == scope_instance_id)
    return database.getData(query)


def handleRelevantEvents(scope_instance, database, event_scope, julian_date_epoch, logger, scope_instance_id=None):
    """Handle events relevant for a given scope and time.

    Args:
        scope_instance (any): Scope object that will handle the relevant events.
        database (:class:`.ResonaateDatabase`): Database for retreiving events from.
        event_scope (:class:`.EventScope`): Relevant scope to query events for.
        julian_date_epoch (:class:`JulianDate`): Current Julian date epoch.
        logger (:class:`.Logger`): Logger instance.
        scope_instance_id (``int``, optional): Unique ID of the object that needs to handle the events returned by
            the query.
    """
    event_types = set()
    event_count = 0
    for event in getRelevantEvents(database, event_scope, julian_date_epoch, scope_instance_id):
        event.handleEvent(scope_instance)
        event_types.add(event.event_type)
        event_count += 1
    if event_count:
        logger.info(f"Handled {event_count} '{event_scope.value}' events of types {event_types}")
