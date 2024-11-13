"""Define :class:`.Event` abstract base class and common functionality."""

from __future__ import annotations

# Standard Library Imports
from enum import Enum
from typing import TYPE_CHECKING

# Third Party Imports
from sqlalchemy import Column, Float, Integer, String

# Local Imports
from ...dynamics.integration_events.finite_thrust import eciBurn, ntwBurn
from ...dynamics.integration_events.scheduled_impulse import (
    ScheduledECIImpulse,
    ScheduledNTWImpulse,
)
from ..table_base import Base, _DataMixin

# Type Checking Import
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Callable

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...dynamics.integration_events.scheduled_impulse import ScheduledImpulse
    from ...scenario.config.event_configs import EventConfig


class EventScope(str, Enum):
    """Enumerated possible values of the :attr:`.Event.scope` attribute."""

    AGENT_PROPAGATION: str = "agent_propagation"
    """EventScope: Scope handled by an :class:`~.agent_base.Agent` during propagation.

    An event to be handled in the scope will have it's :attr:`.Event.scope_instance_id` set to the
    :attr:`.Agent.simulation_id` of the :class:`~.agent_base.Agent` instance that needs to handle it.

    Note:
        Typically, events are handled when the "scope instance" that they correlate to calls the
        :meth:`.events.handleRelevantEvents()` function. However, in the case of the "AGENT_PROPAGATION" scope, events
        need to be handled differently. There are two primary reasons for this:

        - :class:`~.agent_base.Agent`s handle their propagation in parallel. The :meth:`.events.handleRelevantEvents()`
          function requires database access and while the default database implementation of SQLite can
          *technically* handle concurrent reads, it's not advised.
        - There are typically **many** :class:`~.agent_base.Agent`s in a :class:`.Scenario`, so having each of
          them query the database for their individual events is wildly inefficient.

        Rather than each :class:`~.agent_base.Agent` being responsible for finding and handling their own events, events
        are instead collected in :meth:`.AgentPropagationJobHandler.generateJobs()` and queued for each
        :class:`~.agent_base.Agent`.
        Each step of this process is marked with a comment tag: ``[parallel-maneuver-event-handling]``.
    """

    TASK_REWARD_GENERATION: str = "task_reward_generation"
    """EventScope: Scope handled by a :class:`.TaskingEngine` during reward generation.

    An event to be handled in this scope will have it's :attr:`.Event.scope_instance_id` set to the
    :attr:`.TaskingEngine.unique_id` of the :class:`.TaskingEngine` instance that needs to handle it.
    """

    SCENARIO_STEP: str = "scenario_step"
    """EventScope: Scope handled by the :class:`.Scenario` at the beginning of a time step.

    An event to be handled in this scope will have it's :attr:`.Event.scope_instance_id` conventionally set to `0`
    since there's only one :class:`.Scenario` object.
    """

    OBSERVATION_GENERATION: str = "observation_generation"
    """EventScope: Scope handled by an :class:`.SensorAgent` during tasking.

    Note:
        Each step of this process is marked with a comment tag: ``[parallel-time-bias-event-handling]``.
    """


class ThrustFrame(str, Enum):
    """Valid descriptors for thrust vector frames."""

    ECI = "eci"
    """``str``: The event will be applied in the ECI frame."""

    NTW = "ntw"
    """``str``: The event will be applied in the NTW frame."""

    @property
    def impulse(self, _mapping={  # noqa: PLR0206, B006
        ECI: ScheduledECIImpulse,
        NTW: ScheduledNTWImpulse,
    }) -> ScheduledImpulse:
        """ScheduledImpulse: Class associated with this :class:`.ThrustFrame`."""
        return _mapping[self.value]

    @property
    def thrust(self, _mapping={  # noqa: PLR0206, B006
        ECI: eciBurn,
        NTW: ntwBurn,
    }) -> Callable[[ndarray, ndarray], ndarray]:
        """Callable: Burn method associated with this :class:`.ThrustFrame`."""
        return _mapping[self.value]


class Event(_DataMixin, Base):
    """Base class for an event data object."""

    __tablename__ = "events"

    # [NOTE]: Old-style type hints required until we either:
    #   1) Move to SQLAlchemy >= 2.0
    #   2) Move to Python >= 3.10
    #
    # See https://github.com/sqlalchemy/sqlalchemy/issues/9110
    EVENT_REGISTRY: dict[str, Event] | None = None
    """``dict``: Correlates `event_type` values to the correct :class:`.Event` child class."""

    EVENT_TYPE: str = "event"
    """``str``: Name of this type of event."""

    id = Column(Integer, primary_key=True)
    """``int``: Primary key for the 'events' table."""

    scope = Column(String(128), nullable=False)
    """``str``: Scope level at which this event needs to be handled.

    Given the variety of events that RESONAATE needs to be able to handle, there needs to be a way
    to describe *where* in the software structure that these events need to be handled. For
    example, an impulsive maneuver only needs to be handled specifically by the
    :class:`.TargetAgent` that's performing the maneuver. Conversely, a target being added during a
    simulation would need to be handled at the :class:`.Scenario` level.
    """

    scope_instance_id = Column(Integer, nullable=False)
    """``int``: Unique identifier of instance that needs to handle this event.

    See Also:
        :class:`.EventScope` has more information on what this identifier actually points to for each defined scope.
    """

    start_time_jd = Column(Float, index=True, nullable=False)
    """``float``: Time that this event needs to be handled."""

    end_time_jd = Column(Float, nullable=False)
    """``float``: Julian date for when this event is no longer active.

    Not all events will have a time span for when they are active (e.g. impulsive manuevers or node addition/removal).
    However, because the events that _are_ active for a time span need to have their end time be query-able,
    :attr:`.end_time_jd` needs to be a parent class attribute, and not be null. Atomic events should set their
    :attr:`.end_time_jd` to be the same as their :attr:`.start_time_jd`.

    Note:
        This attribute does not have an explicit relationship to an `Epoch`, because it might extend past the end of a
        scenario.
    """

    event_type = Column(String(64), nullable=False)
    """``str``: Attribute delineating which child class this table row implements."""

    __mapper_args__ = {"polymorphic_on": event_type, "polymorphic_identity": EVENT_TYPE}

    MUTABLE_COLUMN_NAMES = (
        "scope",
        "scope_instance_id",
        "start_time_jd",
        "end_time_jd",
        "event_type",
    )

    @classmethod
    def _generateRegistry(cls) -> None:
        """Populate :attr:`.EVENT_REGISTRY` based on subclasses."""
        if cls.EVENT_REGISTRY is None:
            cls.EVENT_REGISTRY = {}
            for subclass in cls.__subclasses__():
                if subclass.EVENT_TYPE == Event.EVENT_TYPE:
                    err = f"{subclass} needs to define an 'EVENT_TYPE' class attribute."
                    raise AttributeError(err)

                if not hasattr(subclass, "handleEvent"):
                    err = f"{subclass} needs to define a 'handleEvent' method."
                    raise AttributeError(err)

                if not hasattr(subclass, "fromConfig"):
                    err = f"{subclass} needs to define a 'fromConfig' method."
                    raise AttributeError(err)

                cls.EVENT_REGISTRY[subclass.EVENT_TYPE] = subclass

    @classmethod
    def eventTypes(cls) -> list[str]:
        """``list``: Return a list of valid :attr:`.Event.event_type` values."""
        Event._generateRegistry()
        return list(Event.EVENT_REGISTRY.keys())

    @classmethod
    def concreteFromConfig(cls, config: EventConfig) -> Event:
        """Construct a concrete :class:`.Event` child object from a specified `config`.

        Args:
            config (:class:`.EventConfig`): Configuration object to construct a :class:`.Event` from.

        Returns:
            :class:`.Event`: object based on specified `config`.
        """
        Event._generateRegistry()
        child_event = Event.EVENT_REGISTRY[config.event_type]
        return child_event.fromConfig(config)
