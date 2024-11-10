"""Defines the :class:`.ScheduledFiniteBurnEvent` data table class."""

from __future__ import annotations

# Standard Library Imports
from functools import partial
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array
from sqlalchemy import Boolean, Column, Float, String
from sqlalchemy.ext.declarative import declared_attr

# Local Imports
from ...dynamics.integration_events.finite_thrust import ScheduledFiniteBurn
from ...physics.time.stardate import JulianDate, datetimeToJulianDate
from .base import Event, EventScope, ThrustFrame

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...agents.agent_base import Agent
    from ...scenario.config.event_configs import ScheduledFiniteBurnConfig


class ScheduledFiniteBurnEvent(Event):
    """Event data object describing a scheduled finite thrust maneuver."""

    EVENT_TYPE: str = "finite_burn"
    """``str``: Name of this type of event."""

    INTENDED_SCOPE: EventScope = EventScope.AGENT_PROPAGATION
    """`EventScope`: Scope where :class:`.ScheduledImpulseEvent` objects should be handled."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    acc_vec_0 = Column(Float)
    """``float``: First element of acceleration vector in km/s^2."""

    acc_vec_1 = Column(Float)
    """``float``: Second element of acceleration vector in km/s^2."""

    acc_vec_2 = Column(Float)
    """``float``: Third element of acceleration vector in km/s^2."""

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
        "acc_vec_0",
        "acc_vec_1",
        "acc_vec_2",
        "thrust_frame",
        "planned",
    )

    def handleEvent(self, scope_instance: Agent) -> None:
        """Queue a :class:`.ScheduledFiniteBurn` to take place during agent propagation.

        Args:
            scope_instance (:class:`~.agent_base.Agent`): agent instance that will be executing this finite thrust.
        """
        start_jd = JulianDate(self.start_time_jd)
        end_jd = JulianDate(self.end_time_jd)
        start_sim_time = start_jd.convertToScenarioTime(scope_instance.julian_date_start)
        end_sim_time = end_jd.convertToScenarioTime(scope_instance.julian_date_start)

        acc_vector = array([self.acc_vec_0, self.acc_vec_1, self.acc_vec_2])
        thrust_frame = ThrustFrame(self.thrust_frame)  # raises ValueError if frame isn't valid
        thrust_func = partial(thrust_frame.thrust, acc_vector=acc_vector)
        finite_burn = ScheduledFiniteBurn(
            start_sim_time,
            end_sim_time,
            thrust_func,
            scope_instance.simulation_id,
        )

        scope_instance.appendPropagateEvent(finite_burn)

    @classmethod
    def fromConfig(cls, config: ScheduledFiniteBurnConfig) -> ScheduledFiniteBurnEvent:
        """Construct a :class:`.ScheduledFiniteEvent` from a specified `config`.

        Args:
            config (:class:`.ScheduledFiniteEventConfig`): Configuration object to construct a
                :class:`.ScheduledFiniteEvent` from.

        Returns:
            :class:`.ScheduledFiniteEvent`: object based on specified `config`.
        """
        return cls(
            scope=config.scope,
            scope_instance_id=config.scope_instance_id,
            start_time_jd=datetimeToJulianDate(config.start_time),
            end_time_jd=datetimeToJulianDate(config.end_time),
            event_type=config.event_type,
            planned=config.planned,
            acc_vec_0=config.acc_vector[0],
            acc_vec_1=config.acc_vector[1],
            acc_vec_2=config.acc_vector[2],
            thrust_frame=config.thrust_frame,
        )
