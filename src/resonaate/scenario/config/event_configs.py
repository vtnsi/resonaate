"""Submodule defining the 'event' configuration objects."""
# Standard Library Imports
from abc import ABCMeta
from datetime import datetime

# Third Party Imports
from sqlalchemy.orm import Query

# Local Imports
from ...data.data_interface import Agent
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
from .agent_configs import SensorConfigObject, TargetConfigObject
from .base import (
    NO_SETTING,
    BaseConfigError,
    ConfigError,
    ConfigObject,
    ConfigObjectList,
    ConfigOption,
    ConfigValueError,
)


class EventConfigObjectList(ConfigObjectList):
    """Extension of the :class:`.ConfigObjectList` that allows different types of event config objects to be stored."""

    def __init__(self):
        """Call the super class' constructor with event-specific arguments."""
        super().__init__("events", EventConfigObject, default_empty=True)

    def readConfig(self, raw_config):
        """Parse of list of object dictionaries and store them as :class:`.ConfigObject` objects.

        Args:
            raw_config (list): List of dictionaries that correspond to :attr:`.obj_type`.
        """
        self._validateRawConfig(raw_config)

        event_classes = {
            conf_class.EVENT_CLASS.EVENT_TYPE: conf_class
            for conf_class in EventConfigObject.__subclasses__()
        }

        for config_dict in raw_config:
            if config_dict["event_type"] not in event_classes:
                raise ConfigValueError(
                    "event_type", config_dict["event_type"], list(event_classes.keys())
                )

            obj_type = event_classes[config_dict["event_type"]]
            try:
                read_obj = obj_type(config_dict)
            except BaseConfigError as inner_err:
                raise ConfigError(self.config_label, str(inner_err)) from inner_err
            else:
                self._list.append(read_obj)


class MissingDataDependency(Exception):
    """Exception raised when a data dependency is missing from the database and it cannot be created at runtime."""


class DataDependency:
    """Class describing a data dependency.

    Describes a database object that an :class:`.Event` constructed from an :class:`.EventConfigObject` will require to
    be present in the database.
    """

    def __init__(self, data_type, query, attributes=None):
        """Construct an instance of a :class:`.DataDependency`.

        Args:
            data_type (_DataMixin): Data object type for this dependency.
            query (Query): SQLAlchemy query that would return this object if it exists in the database already.
            attributes (dict, optional): Dictionary that could be passed to the `data_type` constructor to make the
                data dependency if it doesn't already exist in the database. Leaving this unpopulated will result in an
                exception being thrown if the dependency doesn't already exist in the database.
        """
        self.data_type = data_type
        self.query = query
        self.attributes = attributes

    def createDependency(self):
        """Returns the database object that the :class:`.Event` depends on."""
        if self.attributes is None:
            err = f"Cannot create missing {self.data_type} dependency"
            raise MissingDataDependency(err)
        return self.data_type(**self.attributes)


class EventConfigObject(ConfigObject, metaclass=ABCMeta):
    """Abstract base class defining required fields of an event configuration object."""

    EVENT_CLASS = Event
    """Event: Type of :class:`.Event` this config object corresponds to."""

    @staticmethod
    def getFields():
        """Return a tuple of defining required :class:`.ConfigOption` objects for a :class:`.EventConfigObject`."""
        return (
            ConfigOption("scope", (str,), valid_settings=[scope.value for scope in EventScope]),
            ConfigOption("scope_instance_id", (int,)),
            ConfigOption(
                "start_time",
                (
                    str,
                    datetime,
                ),
            ),
            ConfigOption(
                "end_time",
                (
                    str,
                    datetime,
                ),
                default=NO_SETTING,
            ),
            ConfigOption("event_type", (str,), valid_settings=Event.eventTypes()),
        )

    def validateScopeEventType(self):
        """Raise a ``ConfigError`` if :attr:`~.Event.event_type` or :attr:`~.Event.scope` aren't set correctly."""
        # pylint: disable=no-member
        if self.event_type != self.EVENT_CLASS.EVENT_TYPE:
            err = f"{self.EVENT_CLASS} must have event_type set to {self.EVENT_CLASS.EVENT_TYPE}"
            raise ConfigError(self.__class__.__name__, err)

        if self.scope != self.EVENT_CLASS.INTENDED_SCOPE.value:
            err = f"{self.EVENT_CLASS} must have scope set to {self.EVENT_CLASS.INTENDED_SCOPE}"
            raise ConfigError(self.__class__.__name__, err)

    def getDataDependencies(self):
        """Return a list of database objects that the :attr:`.EVENT_CLASS` relates to.

        This list is then used to verify that the data dependencies already exist in the database so no SQL errors are
        thrown.

        [TODO]: this method is now kind of legacy, because not every event config object has a data dependency anymore.
                There is probably a more elegant way to handle data dependencies, but it will require
                significant changes.

        Returns:
            list: List of :class:`.DataDependency` objects.
        """
        return []

    @property
    def scope(self):
        """str: Scope level at which this event needs to be handled."""
        return self._scope.setting  # pylint: disable=no-member

    @property
    def scope_instance_id(self):
        """int:  Unique identifier of instance that needs to handle this event."""
        return self._scope_instance_id.setting  # pylint: disable=no-member

    @property
    def start_time(self):
        """datetime: Time for when this event needs to start being handled."""
        # pylint: disable=no-member
        if isinstance(self._start_time.setting, str):
            self._start_time.readConfig(
                datetime.strptime(self._start_time.setting, "%Y-%m-%dT%H:%M:%S.%fZ")
            )
        return self._start_time.setting

    @property
    def end_time(self):
        """datetime: When this event is no longer active.

        If this attribute isn't set in the raw config, then it will default to using the value that
        :attr:`~.Event.start_time` is set to.
        """
        # pylint: disable=no-member
        if self._end_time.setting == NO_SETTING:
            self._end_time.readConfig(self.start_time)
        if isinstance(self._end_time.setting, str):
            self._end_time.readConfig(
                datetime.strptime(self._end_time.setting, "%Y-%m-%dT%H:%M:%S.%fZ")
            )
        return self._end_time.setting

    @property
    def event_type(self):
        """str: What type of event this config represents."""
        return self._event_type.setting  # pylint: disable=no-member


class ScheduledImpulseEventConfigObject(EventConfigObject):
    """Defines the required fields of a scheduled impulse event configuration object."""

    EVENT_CLASS = ScheduledImpulseEvent
    """ScheduledImpulseEvent: Type of :class:`.Event` this config object corresponds to."""

    @staticmethod
    def getFields():
        """Return a tuple of required :class:`.ConfigOption` objects for a :class:`.ScheduledImpulseEventConfigObject`."""  # noqa: E501
        return EventConfigObject.getFields() + (
            ConfigOption("thrust_vector", (list,)),
            ConfigOption(
                "thrust_frame", (str,), valid_settings=ScheduledImpulseEvent.VALID_THRUST_FRAMES
            ),
            ConfigOption("planned", (bool,), default=False),
        )

    def __init__(self, object_config):
        """Extend the inherited constructor.

        See Also:
            :meth:`.ConfigObject.__init__()`.
        """
        super().__init__(object_config)
        self.validateScopeEventType()

        vector_size = len(self.thrust_vector)
        if vector_size != 3:
            err = f"Delta vector defining an impulsive maneuver should be 3 dimensional, not {vector_size}"
            raise ConfigError(self.__class__.__name__, err)

    @property
    def thrust_vector(self):
        """list: Three-element vector defining an impulsive maneuver."""
        return self._thrust_vector.setting  # pylint: disable=no-member

    @property
    def thrust_frame(self):
        """str: Label for frame that thrust vector should be applied in."""
        return self._thrust_frame.setting  # pylint: disable=no-member

    @property
    def planned(self):
        """bool: Label for whether or not maneuver was planned."""
        return self._planned.setting  # pylint: disable=no-member


class ScheduledFiniteBurnConfigObject(EventConfigObject):
    """Defines the required fields of a scheduled finite thrust event configuration object."""

    EVENT_CLASS = ScheduledFiniteBurnEvent
    """ScheduledFiniteBurnEvent: Type of :class:`.Event` this config object corresponds to."""

    @staticmethod
    def getFields():
        """Return a tuple of required :class:`.ConfigOption` objects for a :class:`.ScheduledFiniteManeuverConfigObject`."""  # noqa: E501
        return EventConfigObject.getFields() + (
            ConfigOption("acc_vector", (list,)),
            ConfigOption(
                "thrust_frame", (str,), valid_settings=ScheduledFiniteBurnEvent.VALID_THRUST_FRAMES
            ),
            ConfigOption("planned", (bool,), default=False),
        )

    def __init__(self, object_config):
        """Extend the inherited constructor.

        See Also:
            :meth:`.ConfigObject.__init__()`.
        """
        super().__init__(object_config)
        self.validateScopeEventType()

        vector_size = len(self.acc_vector)
        if vector_size != 3:
            err = f"Delta vector defining a finite burn should be 3 dimensional, not {vector_size}"
            raise ConfigError(self.__class__.__name__, err)

    @property
    def acc_vector(self):
        """list: Three-element vector defining a continuous maneuver."""
        return self._acc_vector.setting  # pylint: disable=no-member

    @property
    def thrust_frame(self):
        """str: Label for frame that thrust vector should be applied in."""
        return self._thrust_frame.setting  # pylint: disable=no-member

    @property
    def planned(self):
        """bool: Label for whether or not maneuver was planned."""
        return self._planned.setting  # pylint: disable=no-member


class ScheduledFiniteManeuverConfigObject(EventConfigObject):
    """Defines the required fields of a scheduled finite thrust event configuration object."""

    EVENT_CLASS = ScheduledFiniteManeuverEvent
    """ScheduledFiniteManeuverEvent: Type of :class:`.Event` this config object corresponds to."""

    @staticmethod
    def getFields():
        """Return a tuple of required :class:`.ConfigOption` objects for a :class:`.ScheduledFiniteManeuverConfigObject`."""  # noqa: E501
        return EventConfigObject.getFields() + (
            ConfigOption("maneuver_mag", (int, float)),
            ConfigOption(
                "maneuver_type",
                (str,),
                valid_settings=ScheduledFiniteManeuverEvent.VALID_MANEUVER_TYPES,
            ),
            ConfigOption("planned", (bool,), default=False),
        )

    def __init__(self, object_config):
        """Extend the inherited constructor.

        See Also:
            :meth:`.ConfigObject.__init__()`.
        """
        super().__init__(object_config)
        self.validateScopeEventType()

    @property
    def maneuver_mag(self):
        """list: Scalar defining the magnitude of a finite thrust maneuver."""
        return self._maneuver_mag.setting  # pylint: disable=no-member

    @property
    def maneuver_type(self):
        """str: Label for maneuver type that corresponds to the thrust."""
        return self._maneuver_type.setting  # pylint: disable=no-member

    @property
    def planned(self):
        """bool: Label for whether or not maneuver was planned."""
        return self._planned.setting  # pylint: disable=no-member


class TargetTaskPriorityConfigObject(EventConfigObject):
    """Defines the required fields of a target task priority event configuration object."""

    EVENT_CLASS = TargetTaskPriority
    """TargetTaskPriority: Type of :class:`.Event` this config object corresponds to."""

    @staticmethod
    def getFields():
        """Return required :class:`.ConfigOption` objects for a :class:`.TargetTaskPriorityConfigObject`."""
        return EventConfigObject.getFields() + (
            ConfigOption("target_id", (int,)),
            ConfigOption("target_name", (str,)),
            ConfigOption("priority", (float,)),
            ConfigOption("is_dynamic", (bool,), default=False),
        )

    def __init__(self, object_config):
        """Extend the inherited constructor.

        See Also:
            :meth:`.ConfigObject.__init__()`.
        """
        super().__init__(object_config)
        self.validateScopeEventType()

    def getDataDependencies(self):
        """Return a list of database objects that :class:`.TargetTaskPriorityEvent` relates to.

        Returns:
            list: List of :class:`.DataDependency` objects.
        """
        dependency_list = super().getDataDependencies()
        dependency_list.append(
            DataDependency(
                Agent,
                Query(Agent).filter(Agent.unique_id == self.target_id),
                {"unique_id": self.target_id, "name": self.target_name},
            )
        )
        return dependency_list

    @property
    def target_id(self):
        """int: Unique ID of the :class:`~.agent_base.Agent` that has increased observation priority."""
        return self._target_id.setting  # pylint: disable=no-member

    @property
    def target_name(self):
        """str: Name of the :class:`~.agent_base.Agent` that has increased observation priority."""
        return self._target_name.setting  # pylint: disable=no-member

    @property
    def priority(self):
        """float: Scalar that indicates how important it is that this target be observed."""
        return self._priority.setting  # pylint: disable=no-member

    @property
    def is_dynamic(self):
        """bool: Flag indicating whether this task is pre-canned or dynamically created."""
        return self._is_dynamic.setting  # pylint: disable=no-member


class TargetAdditionEventConfigObject(TargetConfigObject, EventConfigObject):
    """Defines the required fields of a target addition event configuration object."""

    EVENT_CLASS = TargetAdditionEvent
    """TargetAdditionEvent: Type of :class:`.Event` this config object corresponds to."""

    @staticmethod
    def getFields():
        """Return required :class:`.ConfigOption` objects for a :class:`.TargetAdditionEventConfigObject`."""
        return (
            EventConfigObject.getFields()
            + TargetConfigObject.getFields()
            + (ConfigOption("tasking_engine_id", (int,)),)
        )

    def __init__(self, object_config):
        """Extend the inherited constructor.

        See Also:
            :meth:`.ConfigObject.__init__()`.
        """
        super().__init__(object_config)
        self.validateScopeEventType()

    def getDataDependencies(self):
        """Return a list of database objects that :class:`.TargetAdditionEvent` relates to.

        Returns:
            list: List of :class:`.DataDependency` objects.
        """
        dependency_list = super().getDataDependencies()
        dependency_list.append(
            DataDependency(
                Agent,
                Query(Agent).filter(Agent.unique_id == self.sat_num),
                {"unique_id": self.sat_num, "name": self.sat_name},
            )
        )
        return dependency_list

    @property
    def tasking_engine_id(self):
        """int: Unique ID for the :class:`.TaskingEngine` that this target should be added to."""
        return self._tasking_engine_id.setting  # pylint: disable=no-member


class SensorAdditionEventConfigObject(SensorConfigObject, EventConfigObject):
    """Defines the required fields of a sensor addition event configuration object."""

    EVENT_CLASS = SensorAdditionEvent
    """SensorAdditionEvent: Type of :class:`.Event` this config object corresponds to."""

    @staticmethod
    def getFields():
        """Return required :class:`.ConfigOption` objects for a :class:`.SensorAdditionEventConfigObject`."""
        return (
            EventConfigObject.getFields()
            + SensorConfigObject.getFields()
            + (ConfigOption("tasking_engine_id", (int,)),)
        )

    def __init__(self, object_config):
        """Extend the inherited constructor.

        See Also:
            :meth:`.ConfigObject.__init__()`.
        """
        super().__init__(object_config)
        self.validateScopeEventType()

    def getDataDependencies(self):
        """Return a list of database objects that :class:`.SensorAdditionEvent` relates to.

        Returns:
            list: List of :class:`.DataDependency` objects.
        """
        dependency_list = super().getDataDependencies()
        dependency_list.append(
            DataDependency(
                Agent,
                Query(Agent).filter(Agent.unique_id == self.id),
                {"unique_id": self.id, "name": self.name},
            )
        )
        return dependency_list

    @property
    def tasking_engine_id(self):
        """int: Unique ID for the :class:`.TaskingEngine` that this sensor should be added to."""
        return self._tasking_engine_id.setting  # pylint: disable=no-member


class AgentRemovalEventConfigObject(EventConfigObject):
    """Defines the required fields of an agent removal event configuration object."""

    EVENT_CLASS = AgentRemovalEvent
    """AgentRemovalEvent: Type of :class:`.Event` this config object corresponds to."""

    @staticmethod
    def getFields():
        """Return required :class:`.ConfigOption` objects for a :class:`.AgentRemovalEventConfigObject`."""
        return EventConfigObject.getFields() + (
            ConfigOption("tasking_engine_id", (int,)),
            ConfigOption("agent_id", (int,)),
            ConfigOption(
                "agent_type",
                (str,),
                valid_settings=[_type.value for _type in AgentRemovalEvent.AgentType],
            ),
        )

    def __init__(self, object_config):
        """Extend the inherited constructor.

        See Also:
            :meth:`.ConfigObject.__init__()`.
        """
        super().__init__(object_config)
        self.validateScopeEventType()

    def getDataDependencies(self):
        """Return a list of database objects that :class:`.AgentRemovalEvent` relates to.

        Returns:
            list: List of :class:`.DataDependency` objects.
        """
        dependency_list = super().getDataDependencies()
        dependency_list.append(
            DataDependency(Agent, Query(Agent).filter(Agent.unique_id == self.agent_id))
        )
        return dependency_list

    @property
    def tasking_engine_id(self):
        """int: Unique ID for the :class:`.TaskingEngine` that this agent is being removed from."""
        return self._tasking_engine_id.setting  # pylint: disable=no-member

    @property
    def agent_id(self):
        """int: Unique ID for the agent that is being removed."""
        return self._agent_id.setting  # pylint: disable=no-member

    @property
    def agent_type(self):
        """str: Type of agent that's being removed."""
        return self._agent_type.setting  # pylint: disable=no-member


class SensorTimeBiasEventConfigObject(EventConfigObject):
    """Defines the required fields of an agent removal event configuration object."""

    EVENT_CLASS = SensorTimeBiasEvent
    """SensorTimeBiasEvent: Type of :class:`.Event` this config object corresponds to."""

    @staticmethod
    def getFields():
        """Return a tuple of required :class:`.ConfigOption` objects for a :class:`.SensorTimeBiasEventConfigObject`."""
        return EventConfigObject.getFields() + (ConfigOption("applied_bias", (float,)),)

    def __init__(self, object_config):
        """Extend the inherited constructor.

        See Also:
            :meth:`.ConfigObject.__init__()`.
        """
        super().__init__(object_config)
        self.validateScopeEventType()

    @property
    def applied_bias(self):
        """float: applied_bias."""
        return self._applied_bias.setting  # pylint: disable=no-member
