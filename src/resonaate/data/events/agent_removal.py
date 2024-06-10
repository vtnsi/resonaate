"""Defines the :class:`.AgentRemovalEvent` data table class."""

from __future__ import annotations

# Standard Library Imports
from enum import Enum
from typing import TYPE_CHECKING

# Third Party Imports
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

# Local Imports
from ...physics.time.stardate import datetimeToJulianDate
from .base import Event, EventScope

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...scenario.config.event_configs import AgentRemovalEventConfig
    from ...scenario.scenario import Scenario


class AgentRemovalEvent(Event):
    """Event data object describing an agent that is removed after scenario start."""

    EVENT_TYPE = "agent_removal"
    """``str``: Name of this type of event."""

    INTENDED_SCOPE = EventScope.SCENARIO_STEP
    """:class:`.EventScope`: Scope where :class:`.AgentRemovalEvent` objects should be handled."""

    class AgentType(str, Enum):
        """Defines the valid types of agents for the :attr:`~.AgentRemovalEvent.agent_type` attribute."""

        TARGET = "target"
        """``str``: Label for target agents."""

        SENSOR = "sensor"
        """``str``: Label for sensor agents."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    @declared_attr
    def agent_id(self):
        """``int``: Unique ID of the :class:`~.agent_base.AgentModel` being removed from the scenario."""
        return Event.__table__.c.get("agent_id", Column(Integer, ForeignKey("agents.unique_id")))

    @declared_attr
    def tasking_engine_id(self):
        """``int``: Unique ID for the :class:`.TaskingEngine` that this agent should be removed from."""
        return Event.__table__.c.get("tasking_engine_id", Column(Integer))

    agent = relationship("AgentModel", lazy="joined", innerjoin=True)
    """:class:`~.agent.AgentModel`: The `AgentModel` object being removed from the scenario."""

    agent_type = Column(String(32))
    """``str``: Type of agent that's being removed."""

    MUTABLE_COLUMN_NAMES = (
        *Event.MUTABLE_COLUMN_NAMES,
        "agent_id",
        "tasking_engine_id",
        "agent_type",
    )

    def handleEvent(self, scope_instance: Scenario) -> None:
        """Remove the target described by this :class:`.AgentRemovalEvent` from the appropriate tasking engine.

        Args:
            scope_instance (:class:`.Scenario`): :class:`.Scenario` class that's currently executing.
        """
        if self.agent_type == self.AgentType.TARGET.value:
            scope_instance.removeTarget(self.agent_id, self.tasking_engine_id)
        elif self.agent_type == self.AgentType.SENSOR.value:
            scope_instance.removeSensor(self.agent_id, self.tasking_engine_id)
        else:
            err = f"{self.agent_type!r} is not a valid agent type."
            raise ValueError(err)

    @classmethod
    def fromConfig(cls, config: AgentRemovalEventConfig) -> AgentRemovalEvent:
        """Construct a :class:`.AgentRemovalEvent` from a specified `config`.

        Args:
            config (:class:`.AgentRemovalEventConfig`): Configuration object to construct a :class:`.AgentRemovalEvent` from.

        Returns:
            :class:`.AgentRemovalEvent`: object based on the specified `config`.
        """
        return cls(
            scope=config.scope,
            scope_instance_id=config.scope_instance_id,
            start_time_jd=datetimeToJulianDate(config.start_time),
            end_time_jd=datetimeToJulianDate(config.end_time),
            event_type=config.event_type,
            tasking_engine_id=config.tasking_engine_id,
            agent_id=config.agent_id,
            agent_type=config.agent_type,
        )
