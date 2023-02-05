"""Submodule defining the 'event' configuration objects."""
from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

# Third Party Imports
from sqlalchemy.orm import Query

# Local Imports
from ...data.data_interface import AgentModel
from ...data.events import (
    AgentRemovalEvent,
    Event,
    EventScope,
    ScheduledFiniteBurnEvent,
    ScheduledFiniteManeuverEvent,
    ScheduledImpulseEvent,
    SensorAdditionEvent,
    SensorTimeBiasEvent,
    TargetAdditionEvent,
    TargetTaskPriority,
)
from .agent_config import SensingAgentConfig, TargetAgentConfig
from .base import ConfigError, ConfigObject, ConfigObjectList, ConfigTypeError, ConfigValueError
from .time_config import TIME_STAMP_FORMAT

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Type

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...data import _DataMixin

VALID_EVENT_SCOPES: tuple[str] = tuple(scope.value for scope in EventScope)
"""``tuple``: Valid event scopes."""

VALID_AGENT_TYPES: tuple[str] = tuple(_type.value for _type in AgentRemovalEvent.AgentType)
"""``tuple``: Valid agent types."""


@dataclass
class EventConfigList(ConfigObjectList):
    """Allows different types of :class:`.EventConfig` to be stored."""

    def __post_init__(self, config_type: Type[ConfigObject]) -> None:
        """Runs after the object is initialized."""
        # [NOTE]: This can't call the super class `__post_init__()` because it has DIFFERENT class types
        #   which themselves have different constructors.
        event_classes = {
            conf_class.EVENT_CLASS.EVENT_TYPE: conf_class
            for conf_class in EventConfig.__subclasses__()
        }

        config_objects = []
        for event in self._config_objects:
            if isinstance(event, dict) and event:
                if event["event_type"] not in event_classes:
                    raise ConfigValueError(
                        "event_type", event["event_type"], tuple(event_classes.keys())
                    )
                config_objects.append(event_classes[event["event_type"]](**event))

            elif isinstance(event, EventConfig):
                config_objects.append(event)
            else:
                raise ConfigTypeError("events", event, EventConfig.__subclasses__())

        self._config_objects = config_objects


class MissingDataDependency(Exception):
    """Exception raised when a data dependency is missing from the database and it cannot be created at runtime."""


class DataDependency:
    """Class describing a data dependency.

    Describes a database object that an :class:`.Event` constructed from an :class:`.EventConfig` will require to
    be present in the database.
    """

    def __init__(
        self, data_type: _DataMixin, query: Query, attributes: dict | None = None
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
            raise MissingDataDependency(err)
        return self.data_type(**self.attributes)


@dataclass
class EventConfig(ConfigObject):
    """Abstract base class defining required fields of an event configuration object."""

    EVENT_CLASS: ClassVar[Event] = Event
    """:class:`.Event`: Type of :class:`.Event` this config object corresponds to."""

    scope: str
    """``str``: scope level at which this event needs to be handled."""

    scope_instance_id: int
    """``int``: unique identifier of instance that needs to handle this event."""

    start_time: str | datetime
    """``str | datetime``: when this event needs to start being handled."""

    end_time: str | datetime | None
    """``str | datetime | None``: when this event is no longer active.

    If this attribute isn't set in the raw config, then it will default to using the value that
    :attr:`~.Event.start_time` is set to.
    """

    event_type: str
    """``str``: What type of event this config represents."""

    def __post_init__(self) -> None:
        """Runs after the constructor has finished."""
        if self.scope not in VALID_EVENT_SCOPES:
            raise ConfigValueError("scope", self.scope, VALID_EVENT_SCOPES)

        if self.event_type not in Event.eventTypes():
            raise ConfigValueError("event_type", self.event_type, Event.eventTypes())

        if isinstance(self.start_time, str):
            self.start_time = datetime.strptime(self.start_time, TIME_STAMP_FORMAT)

        if self.end_time is None:
            self.end_time = self.start_time

        if isinstance(self.end_time, str):
            self.end_time = datetime.strptime(self.end_time, TIME_STAMP_FORMAT)

        self.validateScopeEventType()

    def validateScopeEventType(self) -> None:
        """Raise a ``ConfigError`` if :attr:`~.Event.event_type` or :attr:`~.Event.scope` aren't set correctly."""
        # pylint: disable=no-member
        if self.event_type != self.EVENT_CLASS.EVENT_TYPE:
            err = f"{self.EVENT_CLASS} must have event_type set to {self.EVENT_CLASS.EVENT_TYPE}"
            raise ConfigError(self.__class__.__name__, err)

        if self.scope != self.EVENT_CLASS.INTENDED_SCOPE.value:
            err = f"{self.EVENT_CLASS} must have scope set to {self.EVENT_CLASS.INTENDED_SCOPE}"
            raise ConfigError(self.__class__.__name__, err)

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


@dataclass
class ScheduledImpulseEventConfig(EventConfig):
    """Defines the required fields of a scheduled impulse event configuration object."""

    EVENT_CLASS: ClassVar[Event] = ScheduledImpulseEvent
    """:class:`.ScheduledImpulseEvent`: Type of :class:`.Event` this config object corresponds to."""

    thrust_vector: list[float] | ndarray
    """``list``: three-element vector defining an impulsive maneuver."""

    thrust_frame: str
    """``str``: Label for frame that thrust vector should be applied in."""

    planned: bool = False
    """``bool``: Label for whether or not maneuver was planned."""

    def __post_init__(self) -> None:
        """Runs after the constructor has finished."""
        super().__post_init__()
        if len(self.thrust_vector) != 3:
            raise ConfigValueError("thrust_vector", self.thrust_vector, "3-element array")

        if self.thrust_frame not in ScheduledImpulseEvent.VALID_THRUST_FRAMES:
            raise ConfigValueError(
                "thrust_frame", self.thrust_frame, ScheduledImpulseEvent.VALID_THRUST_FRAMES
            )


@dataclass
class ScheduledFiniteBurnConfig(EventConfig):
    """Defines the required fields of a scheduled finite thrust event configuration object."""

    EVENT_CLASS: ClassVar[Event] = ScheduledFiniteBurnEvent
    """ScheduledFiniteBurnEvent: Type of :class:`.Event` this config object corresponds to."""

    acc_vector: list | ndarray
    """``list``: three-element vector defining a continuous maneuver."""

    thrust_frame: str
    """``str``: label for frame that thrust vector should be applied in."""

    planned: bool = False
    """``bool``: label for whether or not maneuver was planned."""

    def __post_init__(self) -> None:
        """Runs after the constructor has finished."""
        super().__post_init__()
        if len(self.acc_vector) != 3:
            raise ConfigValueError("acc_vector", self.acc_vector, "3-element array")

        if self.thrust_frame not in ScheduledFiniteBurnEvent.VALID_THRUST_FRAMES:
            raise ConfigValueError(
                "thrust_frame", self.thrust_frame, ScheduledFiniteBurnEvent.VALID_THRUST_FRAMES
            )


@dataclass
class ScheduledFiniteManeuverConfig(EventConfig):
    """Defines the required fields of a scheduled finite thrust event configuration object."""

    EVENT_CLASS: ClassVar[Event] = ScheduledFiniteManeuverEvent
    """:class:`.ScheduledFiniteManeuverEvent`: Type of :class:`.Event` this config object corresponds to."""

    maneuver_mag: float
    """``list``: scalar defining the magnitude of a finite thrust maneuver."""

    maneuver_type: str
    """``str``: label for maneuver type that corresponds to the thrust."""

    planned: bool = False
    """``bool``: label for whether or not maneuver was planned."""

    def __post_init__(self) -> None:
        """Runs after the constructor has finished."""
        super().__post_init__()
        if self.maneuver_type not in ScheduledFiniteManeuverEvent.VALID_MANEUVER_TYPES:
            raise ConfigValueError(
                "maneuver_type",
                self.maneuver_type,
                ScheduledFiniteManeuverEvent.VALID_MANEUVER_TYPES,
            )


@dataclass
class TargetTaskPriorityConfig(EventConfig):
    """Defines the required fields of a target task priority event configuration object."""

    EVENT_CLASS: ClassVar[Event] = TargetTaskPriority
    """:class:`.TargetTaskPriority`: Type of :class:`.Event` this config object corresponds to."""

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
            )
        )
        return dependency_list


@dataclass
class TargetAdditionEventConfig(EventConfig):
    """Defines the required fields of a target addition event configuration object."""

    EVENT_CLASS: ClassVar[Event] = TargetAdditionEvent
    """:class:`.TargetAdditionEvent`: Type of :class:`.Event` this config object corresponds to."""

    tasking_engine_id: int
    """``int``: Unique ID for the :class:`.TaskingEngine` that this target should be added to."""

    target_agent: TargetAgentConfig | dict
    """``dict``: Configuration object for the target that is being added."""

    def __post_init__(self) -> None:
        """Runs after the constructor has finished."""
        super().__post_init__()
        if isinstance(self.target_agent, dict):
            self.target_agent = TargetAgentConfig(**self.target_agent)

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
            )
        )
        return dependency_list


@dataclass
class SensorAdditionEventConfig(EventConfig):
    """Defines the required fields of a sensor addition event configuration object."""

    EVENT_CLASS: ClassVar[Event] = SensorAdditionEvent
    """:class:`.SensorAdditionEvent`: Type of :class:`.Event` this config object corresponds to."""

    tasking_engine_id: int
    """``int``: Unique ID for the :class:`.TaskingEngine` that this sensor should be added to."""

    sensor_agent: SensingAgentConfig | dict
    """``dict``: Configuration object for the sensor that is being added."""

    def __post_init__(self) -> None:
        """Runs after the constructor has finished."""
        super().__post_init__()
        if isinstance(self.sensor_agent, dict):
            self.sensor_agent = SensingAgentConfig(**self.sensor_agent)

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
            )
        )
        return dependency_list


@dataclass
class AgentRemovalEventConfig(EventConfig):
    """Defines the required fields of an agent removal event configuration object."""

    EVENT_CLASS: ClassVar[Event] = AgentRemovalEvent
    """:class:`.AgentRemovalEvent`: Type of :class:`.Event` this config object corresponds to."""

    tasking_engine_id: int
    """``int``: Unique ID for the :class:`.TaskingEngine` that this agent is being removed from."""

    agent_id: int
    """``int``: Unique ID for the agent that is being removed."""

    agent_type: str
    """``str``: Type of agent that is being removed."""

    def __post_init__(self) -> None:
        """Runs after the constructor has finished."""
        super().__post_init__()
        if self.agent_type not in VALID_AGENT_TYPES:
            raise ConfigValueError("agent_type", self.agent_type, VALID_AGENT_TYPES)

    def getDataDependencies(self) -> list[DataDependency]:
        """Return a list of database objects that :class:`.AgentRemovalEvent` relates to.

        Returns:
            list: List of :class:`.DataDependency` objects.
        """
        dependency_list = super().getDataDependencies()
        dependency_list.append(
            DataDependency(
                AgentModel, Query(AgentModel).filter(AgentModel.unique_id == self.agent_id)
            )
        )
        return dependency_list


@dataclass
class SensorTimeBiasEventConfig(EventConfig):
    """Defines the required fields of an sensor time bias event configuration object."""

    EVENT_CLASS: ClassVar[Event] = SensorTimeBiasEvent
    """:class:`.SensorTimeBiasEvent`: Type of :class:`.Event` this config object corresponds to."""

    applied_bias: float
    """``float``: time bias to be applied to the sensor."""

    def __post_init__(self) -> None:
        """Runs after the constructor has finished."""
        super().__post_init__()
        if not isinstance(self.applied_bias, float):
            raise ConfigTypeError("applied_bias", self.applied_bias, (float,))
