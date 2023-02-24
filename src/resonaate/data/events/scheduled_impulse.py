"""Defines the :class:`.ScheduledImpulseEvent` data table class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING, Tuple

# Third Party Imports
from numpy import array
from sqlalchemy import Boolean, Column, Float, String
from sqlalchemy.ext.declarative import declared_attr

# Local Imports
from ...dynamics.integration_events.scheduled_impulse import (
    ScheduledECIImpulse,
    ScheduledNTWImpulse,
)
from ...physics.time.stardate import JulianDate, datetimeToJulianDate
from .base import Event, EventScope

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

    THRUST_FRAME_ECI: str = "eci"
    """``str``: Configuration string used to delineate using the ECI frame to apply this impulse."""

    THRUST_FRAME_NTW: str = "ntw"
    """``str``: Configuration string used to delineate using the NTW frame to apply this impulse."""

    # [NOTE]: Old-style type hints required until we either:
    #   1) Move to SQLAlchemy >= 2.0
    #   2) Move to Python >= 3.10
    # pylint: disable=deprecated-typing-alias
    VALID_THRUST_FRAMES: Tuple[str] = (THRUST_FRAME_ECI, THRUST_FRAME_NTW)
    """``tuple``: Valid values for :attr:`~.ScheduledImpulseEvent.thrust_frame`."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    thrust_vec_0 = Column(Float)
    """``float``: First element of impulse vector in km/s."""

    thrust_vec_1 = Column(Float)
    """``float``: Second element of impulse vector in km/s."""

    thrust_vec_2 = Column(Float)
    """``float``: Third element of impulse vector in km/s."""

    @declared_attr
    def thrust_frame(self):  # pylint: disable=invalid-name
        """``str``: Label for frame that thrust should be applied in."""
        return Event.__table__.c.get(  # pylint: disable=no-member
            "thrust_frame", Column(String(10))
        )

    @declared_attr
    def planned(self):  # pylint: disable=invalid-name
        """``bool``: Flag indicating whether this task is expected by the filter or not."""
        return Event.__table__.c.get("planned", Column(Boolean))  # pylint: disable=no-member

    MUTABLE_COLUMN_NAMES = Event.MUTABLE_COLUMN_NAMES + (
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
        impulse = None
        if str(self.thrust_frame).lower() == self.THRUST_FRAME_ECI:
            impulse = ScheduledECIImpulse(
                start_sim_time, burn_vector, scope_instance.simulation_id
            )
        elif str(self.thrust_frame).lower() == self.THRUST_FRAME_NTW:
            impulse = ScheduledNTWImpulse(
                start_sim_time, burn_vector, scope_instance.simulation_id
            )
        else:
            err = f"{self.thrust_frame} is not a valid coordinate frame."
            raise ValueError(err)

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
