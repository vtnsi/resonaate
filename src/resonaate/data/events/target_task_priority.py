"""Defines the :class:`.TargetTaskPriority` data table class."""
# Standard Library Imports
# Third Party Imports
from sqlalchemy import Column, Float, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr
# RESONAATE Imports
from ...physics.time.stardate import datetimeToJulianDate
from .base import Event, EventScope


class TargetTaskPriority(Event):
    """Database object representing a user-driven target tasking priority."""

    EVENT_TYPE = "task_priority"
    """str: Name of this type of event."""

    INTENDED_SCOPE = EventScope.TASK_REWARD_GENERATION
    """EventScope: Scope where :class:`.TargetTaskPriority` objects should be handled."""

    __mapper_args__ = {
        'polymorphic_identity': EVENT_TYPE
    }

    @declared_attr
    def agent_id(self):  # pylint: disable=invalid-name
        """int: Unique ID of the :class:`.Agent` with the observation priority."""
        return Event.__table__.c.get(  # pylint: disable=no-member
            'agent_id',
            Column(Integer, ForeignKey('agents.unique_id'))
        )

    agent = relationship("Agent", lazy="joined", innerjoin=True)
    """agent_base.Agent: The `Agent` that has increased observation priority."""

    priority = Column(Float)
    """float: Scalar that indicates how important it is that this target be observed."""

    is_dynamic = Column(Boolean)
    """bool: Flag indicating whether this task is pre-canned or dynamically created.

    Note:
        This facilitated logic in the service layer of resonaate.
    """

    MUTABLE_COLUMN_NAMES = Event.MUTABLE_COLUMN_NAMES + (
        "agent_id", "priority", "is_dynamic"
    )

    def handleEvent(self, scope_instance):
        """Increase the reward for tasking sensors to observe the `target`.

        Args:
            scope_instance (TaskingEngine): The tasking engine that's being given this :class:`.TargetTaskPriority`.
        """
        scope_instance.reward_matrix[scope_instance.target_indices[self.agent_id],:] *= self.priority

    @classmethod
    def fromConfig(cls, config):
        """Construct a :class:`.TargetTaskPriority` from a specified `config`.

        Args:
            config (ConfigObject): Configuration object to construct a :class:`.TargetTaskPriority` from.

        Returns:
            TargetTaskPriority: :class:`.TargetTaskPriority` object based on specified `config`.
        """
        return cls(
            scope=config.scope,
            scope_instance_id=config.scope_instance_id,
            start_time_jd=datetimeToJulianDate(config.start_time),
            end_time_jd=datetimeToJulianDate(config.end_time),
            event_type=config.event_type,
            agent_id=config.target_id,
            priority=config.priority,
            is_dynamic=config.is_dynamic
        )
