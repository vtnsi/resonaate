"""Defines the :class:`.ScheduledFiniteManeuverEvent` data table class."""

from __future__ import annotations

# Standard Library Imports
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING

# Third Party Imports
from sqlalchemy import Boolean, Column, Float, String
from sqlalchemy.ext.declarative import declared_attr

# Local Imports
from ...dynamics.integration_events.finite_thrust import (
    ScheduledFiniteManeuver,
    planeChangeThrust,
    spiralThrust,
)
from ...physics.time.stardate import JulianDate, datetimeToJulianDate
from .base import Event, EventScope

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Callable

    # Local Imports
    from ...agents.agent_base import Agent
    from ...scenario.config.event_configs import ScheduledFiniteManeuverConfig


class ManeuverType(str, Enum):
    """Valid values for :attr:`.ScheduledFiniteManeuverEvent.maneuver_type`."""

    SPIRAL = "spiral"
    """``str``: String designation of spiral maneuver."""

    PLANE_CHANGE = "plane_change"
    """``str``: String designation of plane change maneuver."""

    @property
    def thrust(self, _mapping={  # noqa: PLR0206, B006
        SPIRAL: spiralThrust,
        PLANE_CHANGE: planeChangeThrust,
    }) -> Callable:
        """Callable: Maneuver method associated with this :class:`.ManeuverType`."""
        return _mapping[self.value]


class ScheduledFiniteManeuverEvent(Event):
    """Event data object describing a scheduled finite maneuver."""

    EVENT_TYPE: str = "finite_maneuver"
    """``str``: Name of this type of event."""

    INTENDED_SCOPE: EventScope = EventScope.AGENT_PROPAGATION
    """:class:`.EventScope`: Scope where :class:`.ScheduledImpulseEvent` objects should be handled."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    maneuver_type = Column(String(10))
    """``str``: Label for type of maneuver being applied."""

    maneuver_mag = Column(Float)
    """``float``: Magnitude of maneuver vector in km/s^2."""

    @declared_attr
    def planned(self):
        """``bool``: Flag indicating whether this task is expected by the filter or not."""
        return Event.__table__.c.get("planned", Column(Boolean))

    MUTABLE_COLUMN_NAMES = (
        *Event.MUTABLE_COLUMN_NAMES,
        "maneuver_mag",
        "maneuver_type",
        "planned",
    )

    def handleEvent(self, scope_instance: Agent) -> None:
        """Queue a :class:`.ScheduledFiniteManeuver` to take place during agent propagation.

        Args:
            scope_instance (:class:`~.agent_base.Agent`): agent instance that will be executing this finite maneuver.
        """
        start_jd = JulianDate(self.start_time_jd)
        end_jd = JulianDate(self.end_time_jd)
        start_sim_time = start_jd.convertToScenarioTime(scope_instance.julian_date_start)
        end_sim_time = end_jd.convertToScenarioTime(scope_instance.julian_date_start)

        maneuver_type = ManeuverType(self.maneuver_type)  # raises `ValueError` if not a valid maneuver type
        thrust_func = partial(maneuver_type.thrust, magnitude=self.maneuver_mag)
        finite_maneuver = ScheduledFiniteManeuver(
            start_sim_time,
            end_sim_time,
            thrust_func,
            scope_instance.simulation_id,
        )

        # if finite_burn not in scope_instance.propagate_event_queue:
        scope_instance.appendPropagateEvent(finite_maneuver)

    @classmethod
    def fromConfig(cls, config: ScheduledFiniteManeuverConfig) -> ScheduledFiniteManeuverEvent:
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
            maneuver_type=config.maneuver_type,
            maneuver_mag=config.maneuver_mag,
        )
