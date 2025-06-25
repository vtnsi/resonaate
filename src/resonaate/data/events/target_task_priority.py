"""Defines the :class:`.TargetTaskPriority` data table class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, relationship

# Local Imports
from ...physics.time.stardate import datetimeToJulianDate
from .base import Event, EventScope

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...scenario.config.event_configs import TargetTaskPriorityConfig
    from ...tasking.engine.engine_base import TaskingEngine


class TargetTaskPriority(Event):
    """Database object representing a user-driven target tasking priority."""

    EVENT_TYPE: str = "task_priority"
    """``str``: Name of this type of event."""

    INTENDED_SCOPE: EventScope = EventScope.TASK_REWARD_GENERATION
    """:class:`.EventScope`: Scope where :class:`.TargetTaskPriority` objects should be handled."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    @declared_attr
    def agent_id(self):
        """``int``: Unique ID of the :class:`.AgentModel` with the observation priority."""
        return Event.__table__.c.get("agent_id", Column(Integer, ForeignKey("agents.unique_id")))

    agent = relationship("AgentModel", lazy="joined", innerjoin=True)
    """:class:`~.agent.AgentModel`: The `AgentModel` that has increased observation priority."""

    priority: Mapped[float] = Column(Float)
    """``float``: Scalar that indicates how important it is that this target be observed."""

    is_dynamic: Mapped[float] = Column(Boolean)
    """``bool``: Flag indicating whether this task is pre-canned or dynamically created."""

    MUTABLE_COLUMN_NAMES = (*Event.MUTABLE_COLUMN_NAMES, "agent_id", "priority", "is_dynamic")

    def handleEvent(self, scope_instance: TaskingEngine) -> None:
        """Increase the reward for tasking sensors to observe the `target`.

        Args:
            scope_instance (:class:`.TaskingEngine`): The tasking engine that's being given this
                :class:`.TargetTaskPriority`.
        """
        scope_instance.reward_matrix[
            scope_instance.target_indices[self.agent_id],
            :,
        ] *= self.priority

    @classmethod
    def fromConfig(cls, config: TargetTaskPriorityConfig) -> TargetTaskPriority:
        """Construct a :class:`.TargetTaskPriority` from a specified `config`.

        Args:
            config (:class:`.TargetTaskPriorityConfigObject`): Configuration object to construct a :class:`.TargetTaskPriority` from.

        Returns:
            :class:`.TargetTaskPriority`: object based on specified `config`.
        """
        return cls(
            scope=config.scope,
            scope_instance_id=config.scope_instance_id,
            start_time_jd=datetimeToJulianDate(config.start_time),
            end_time_jd=datetimeToJulianDate(config.end_time),
            event_type=config.event_type,
            agent_id=config.target_id,
            priority=config.priority,
            is_dynamic=config.is_dynamic,
        )
