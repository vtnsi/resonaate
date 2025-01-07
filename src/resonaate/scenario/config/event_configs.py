"""Submodule defining the 'event' configuration objects."""

# ruff: noqa: TCH001, TCH003

from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Literal, Union

# Third Party Imports
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Query

# Local Imports
from ...data.data_interface import AgentModel
from ...data.events import (
    AgentRemovalEvent,
    Event,
    EventScope,
    ScheduledFiniteBurnEvent,
    SensorAdditionEvent,
    SensorTimeBiasEvent,
    TargetAdditionEvent,
    TargetTaskPriority,
)
from ...data.events.finite_maneuver import ManeuverType, ScheduledFiniteManeuverEvent
from ...data.events.scheduled_impulse import ScheduledImpulseEvent, ThrustFrame
from .agent_config import AgentConfig, SensingAgentConfig

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from typing_extensions import Self

    # Local Imports
    from ...data import _DataMixin


Vector3 = Annotated[list[float], Field(..., min_length=3, max_length=3)]
"""Type annotation denoting a 3-element vector."""


class MissingDataDependencyError(Exception):
    """Exception raised when a data dependency is missing from the database and it cannot be created at runtime."""


class DataDependency:
    """Class describing a data dependency.

    Describes a database object that an :class:`.Event` constructed from an :class:`.EventConfig` will require to
    be present in the database.
    """

    def __init__(
        self,
        data_type: _DataMixin,
        query: Query,
        attributes: dict | None = None,
    ) -> None:
        """Construct an instance of a :class:`.DataDependency`.

        Args:
            data_type (:class:`._DataMixin`): Data object type for this dependency.
            query (``Query``): SQLAlchemy query that would return this object if it exists in the database already.
            attributes (``dict``, optional): Dictionary that could be passed to the `data_type` constructor to make the
                data dependency if it doesn't already exist in the database. Leaving this unpopulated will result in an
                exception being thrown if the dependency doesn't already exist in the database.
        """
        self.data_type = data_type
        self.query = query
        self.attributes = attributes

    def createDependency(self) -> _DataMixin:
        """Returns the database object that the :class:`.Event` depends on."""
        if self.attributes is None:
            err = f"Cannot create missing {self.data_type} dependency"
            raise MissingDataDependencyError(err)
        return self.data_type(**self.attributes)



class EventConfigBase(BaseModel, ABC, extra="allow"):
    """Abstract base class defining required fields of an event configuration object."""

    @classmethod
    @abstractmethod
    def getEventClass(cls) -> Event:
        """Return the :class:`.Event` class associated with this ``EventConfig``."""
        raise NotImplementedError

    scope: EventScope
    """``str``: scope level at which this event needs to be handled."""

    @field_validator("scope")
    @classmethod
    def check_scope(cls, v):
        """Validate that the scope field matches the intended scope."""
        event_class = cls.getEventClass()
        if v != event_class.INTENDED_SCOPE.value:
            err = f"{event_class} must have scope set to {event_class.INTENDED_SCOPE}"
            raise ValueError(err)
        return v

    scope_instance_id: int
    """``int``: unique identifier of instance that needs to handle this event."""

    start_time: datetime
    """``str | datetime``: when this event needs to start being handled."""

    end_time: Union[datetime, None] = None  # noqa: UP007
    """``str | datetime | None``: when this event is no longer active.

    If this attribute isn't set in the raw config, then it will default to using the value that
    :attr:`~.Event.start_time` is set to.
    """

    @model_validator(mode="after")
    def default_end_time(self) -> Self:
        """If no end time is specified, set it to start time."""
        if self.end_time is None:
            self.end_time = self.start_time
        return self

    def getDataDependencies(self) -> list[DataDependency]:
        """Return a list of database objects that the :attr:`.EVENT_CLASS` relates to.

        This list is then used to verify that the data dependencies already exist in the database so no SQL errors are
        thrown.

        [TODO]: this method is now kind of legacy, because not every event config object has a data dependency anymore.
                There is probably a more elegant way to handle data dependencies, but it will require
                significant changes.

        Returns:
            ``list``: :class:`.DataDependency` objects.
        """
        return []


class ScheduledImpulseEventConfig(EventConfigBase):
    """Defines the required fields of a scheduled impulse event configuration object."""

    @classmethod
    def getEventClass(cls) -> Event:
        """:class:`.ScheduledImpulseEvent`: Type of :class:`.Event` this config object corresponds to."""
        return ScheduledImpulseEvent

    event_type: Literal["impulse"]
    """``str``: What type of event this config represents."""

    thrust_vector: Vector3
    """``list``: three-element vector defining an impulsive maneuver."""

    thrust_frame: ThrustFrame
    """``str``: Label for frame that thrust vector should be applied in."""

    planned: bool = False
    """``bool``: Label for whether or not maneuver was planned."""


class ScheduledFiniteBurnConfig(EventConfigBase):
    """Defines the required fields of a scheduled finite thrust event configuration object."""

    @classmethod
    def getEventClass(cls) -> Event:
        """ScheduledFiniteBurnEvent: Type of :class:`.Event` this config object corresponds to."""
        return ScheduledFiniteBurnEvent

    event_type: Literal["finite_burn"]
    """``str``: What type of event this config represents."""

    acc_vector: Vector3
    """``list``: three-element vector defining a continuous maneuver."""

    thrust_frame: ThrustFrame
    """``str``: label for frame that thrust vector should be applied in."""

    planned: bool = False
    """``bool``: label for whether or not maneuver was planned."""


class ScheduledFiniteManeuverConfig(EventConfigBase):
    """Defines the required fields of a scheduled finite thrust event configuration object."""

    @classmethod
    def getEventClass(cls) -> Event:
        """:class:`.ScheduledFiniteManeuverEvent`: Type of :class:`.Event` this config object corresponds to."""
        return ScheduledFiniteManeuverEvent

    event_type: Literal["finite_maneuver"]
    """``str``: What type of event this config represents."""

    maneuver_mag: float
    """``list``: scalar defining the magnitude of a finite thrust maneuver."""

    maneuver_type: ManeuverType
    """``str``: label for maneuver type that corresponds to the thrust."""

    planned: bool = False
    """``bool``: label for whether or not maneuver was planned."""


class TargetTaskPriorityConfig(EventConfigBase):
    """Defines the required fields of a target task priority event configuration object."""

    @classmethod
    def getEventClass(cls) -> Event:
        """:class:`.TargetTaskPriority`: Type of :class:`.Event` this config object corresponds to."""
        return TargetTaskPriority

    event_type: Literal["task_priority"]
    """``str``: What type of event this config represents."""

    target_id: int
    """``int``: Unique ID of the :class:`~.agent_base.Agent` that has increased observation priority."""

    target_name: str
    """``str``: Name of the :class:`~.agent_base.Agent` that has increased observation priority."""

    priority: float
    """``float``: Scalar that indicates how important it is that this target be observed."""

    is_dynamic: bool = False
    """``bool``: Flag indicating whether this task is pre-canned or dynamically created."""

    def getDataDependencies(self) -> list[DataDependency]:
        """Return a list of database objects that :class:`.TargetTaskPriorityEvent` relates to.

        Returns:
            list: List of :class:`.DataDependency` objects.
        """
        dependency_list = super().getDataDependencies()
        dependency_list.append(
            DataDependency(
                AgentModel,
                Query(AgentModel).filter(AgentModel.unique_id == self.target_id),
                {"unique_id": self.target_id, "name": self.target_name},
            ),
        )
        return dependency_list


class TargetAdditionEventConfig(EventConfigBase):
    """Defines the required fields of a target addition event configuration object."""

    @classmethod
    def getEventClass(cls) -> Event:
        """:class:`.TargetAdditionEvent`: Type of :class:`.Event` this config object corresponds to."""
        return TargetAdditionEvent

    event_type: Literal["target_addition"]
    """``str``: What type of event this config represents."""

    tasking_engine_id: int
    """``int``: Unique ID for the :class:`.TaskingEngine` that this target should be added to."""

    target_agent: AgentConfig
    """``dict``: Configuration object for the target that is being added."""

    def getDataDependencies(self) -> list[DataDependency]:
        """Return a list of database objects that :class:`.TargetAdditionEvent` relates to.

        Returns:
            list: List of :class:`.DataDependency` objects.
        """
        dependency_list = super().getDataDependencies()
        dependency_list.append(
            DataDependency(
                AgentModel,
                Query(AgentModel).filter(AgentModel.unique_id == self.target_agent.id),
                {"unique_id": self.target_agent.id, "name": self.target_agent.name},
            ),
        )
        return dependency_list


class SensorAdditionEventConfig(EventConfigBase):
    """Defines the required fields of a sensor addition event configuration object."""

    @classmethod
    def getEventClass(cls) -> Event:
        """:class:`.SensorAdditionEvent`: Type of :class:`.Event` this config object corresponds to."""
        return SensorAdditionEvent

    event_type: Literal["sensor_addition"]
    """``str``: What type of event this config represents."""

    tasking_engine_id: int
    """``int``: Unique ID for the :class:`.TaskingEngine` that this sensor should be added to."""

    sensor_agent: SensingAgentConfig
    """``dict``: Configuration object for the sensor that is being added."""

    def getDataDependencies(self) -> list[DataDependency]:
        """Return a list of database objects that :class:`.SensorAdditionEvent` relates to.

        Returns:
            list: List of :class:`.DataDependency` objects.
        """
        dependency_list = super().getDataDependencies()
        dependency_list.append(
            DataDependency(
                AgentModel,
                Query(AgentModel).filter(AgentModel.unique_id == self.sensor_agent.id),
                {"unique_id": self.sensor_agent.id, "name": self.sensor_agent.name},
            ),
        )
        return dependency_list


class AgentRemovalEventConfig(EventConfigBase):
    """Defines the required fields of an agent removal event configuration object."""

    @classmethod
    def getEventClass(cls) -> Event:
        """:class:`.AgentRemovalEvent`: Type of :class:`.Event` this config object corresponds to."""
        return AgentRemovalEvent

    event_type: Literal["agent_removal"]
    """``str``: What type of event this config represents."""

    tasking_engine_id: int
    """``int``: Unique ID for the :class:`.TaskingEngine` that this agent is being removed from."""

    agent_id: int
    """``int``: Unique ID for the agent that is being removed."""

    agent_type: AgentRemovalEvent.AgentType
    """``str``: Type of agent that is being removed."""

    def getDataDependencies(self) -> list[DataDependency]:
        """Return a list of database objects that :class:`.AgentRemovalEvent` relates to.

        Returns:
            list: List of :class:`.DataDependency` objects.
        """
        dependency_list = super().getDataDependencies()
        dependency_list.append(
            DataDependency(
                AgentModel,
                Query(AgentModel).filter(AgentModel.unique_id == self.agent_id),
            ),
        )
        return dependency_list


class SensorTimeBiasEventConfig(EventConfigBase):
    """Defines the required fields of an sensor time bias event configuration object."""

    @classmethod
    def getEventClass(cls) -> Event:
        """:class:`.SensorTimeBiasEvent`: Type of :class:`.Event` this config object corresponds to."""
        return SensorTimeBiasEvent

    event_type: Literal["sensor_time_bias"]
    """``str``: What type of event this config represents."""

    applied_bias: float
    """``float``: time bias to be applied to the sensor."""


EventConfig = Annotated[Union[
        ScheduledImpulseEventConfig,
        ScheduledFiniteBurnConfig,
        ScheduledFiniteManeuverConfig,
        TargetTaskPriorityConfig,
        TargetAdditionEventConfig,
        SensorAdditionEventConfig,
        AgentRemovalEventConfig,
        SensorTimeBiasEventConfig,
    ],
    Field(..., discriminator="event_type"),
]
