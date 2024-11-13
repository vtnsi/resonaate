"""Defines the :class:`.ScheduledImpulseEvent` data table class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array
from sqlalchemy import Boolean, Column, Float, String
from sqlalchemy.ext.declarative import declared_attr

# Local Imports
from ...physics.time.stardate import JulianDate, datetimeToJulianDate
from .base import Event, EventScope, ThrustFrame

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...agents.agent_base import Agent
    from ...scenario.config.event_configs import ScheduledImpulseEventConfig


class ScheduledImpulseEvent(Event):
    """Event data object describing a scheduled impulsive maneuver."""

    EVENT_TYPE: str = "impulse"
    """``str``: Name of this type of event."""

    INTENDED_SCOPE: EventScope = EventScope.AGENT_PROPAGATION
    """:class:`.EventScope`: Scope where :class:`.ScheduledImpulseEvent` objects should be handled."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    thrust_vec_0 = Column(Float)
    """``float``: First element of impulse vector in km/s."""

    thrust_vec_1 = Column(Float)
    """``float``: Second element of impulse vector in km/s."""

    thrust_vec_2 = Column(Float)
    """``float``: Third element of impulse vector in km/s."""

    @declared_attr
    def thrust_frame(self):
        """``str``: Label for frame that thrust should be applied in."""
        return Event.__table__.c.get("thrust_frame", Column(String(10)))

    @declared_attr
    def planned(self):
        """``bool``: Flag indicating whether this task is expected by the filter or not."""
        return Event.__table__.c.get("planned", Column(Boolean))

    MUTABLE_COLUMN_NAMES = (
        *Event.MUTABLE_COLUMN_NAMES,
        "thrust_vec_0",
        "thrust_vec_1",
        "thrust_vec_2",
        "thrust_frame",
        "planned",
    )

    def handleEvent(self, scope_instance: Agent) -> None:
        """Queue a :class:`.ScheduledImpulse` to take place during agent propagation.

        Args:
            scope_instance (:class:`~.agent_base.Agent`): agent instance that will be executing this impulse.
        """
        start_jd = JulianDate(self.start_time_jd)
        start_sim_time = start_jd.convertToScenarioTime(scope_instance.julian_date_start)

        burn_vector = array([self.thrust_vec_0, self.thrust_vec_1, self.thrust_vec_2])
        frame = ThrustFrame(self.thrust_frame)  # raises ValueError if frame isn't valid
        impulse = frame.impulse(
            start_sim_time,
            burn_vector,
            scope_instance.simulation_id,
        )

        scope_instance.appendPropagateEvent(impulse)

    @classmethod
    def fromConfig(cls, config: ScheduledImpulseEventConfig) -> ScheduledImpulseEvent:
        """Construct a :class:`.ScheduledImpulseEvent` from a specified `config`.

        Args:
            config (:class:`.ScheduledImpulseEventConfig`): Configuration object to construct a
                :class:`.ScheduledImpulseEvent` from.

        Returns:
            :class:`.ScheduledImpulseEvent`: event object based on specified `config`.
        """
        return cls(
            scope=config.scope,
            scope_instance_id=config.scope_instance_id,
            start_time_jd=datetimeToJulianDate(config.start_time),
            end_time_jd=datetimeToJulianDate(config.end_time),
            event_type=config.event_type,
            planned=config.planned,
            thrust_vec_0=config.thrust_vector[0],
            thrust_vec_1=config.thrust_vector[1],
            thrust_vec_2=config.thrust_vector[2],
            thrust_frame=config.thrust_frame,
        )
