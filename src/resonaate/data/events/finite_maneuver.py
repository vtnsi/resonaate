"""Defines the :class:`.ScheduledFiniteManeuverEvent` data table class."""

from __future__ import annotations

# Standard Library Imports
from functools import partial
from typing import TYPE_CHECKING, Tuple  # noqa: UP035

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
    # Local Imports
    from ...agents.agent_base import Agent
    from ...scenario.config.event_configs import ScheduledFiniteManeuverConfig


class ScheduledFiniteManeuverEvent(Event):
    """Event data object describing a scheduled finite maneuver."""

    EVENT_TYPE: str = "finite_maneuver"
    """``str``: Name of this type of event."""

    INTENDED_SCOPE: EventScope = EventScope.AGENT_PROPAGATION
    """:class:`.EventScope`: Scope where :class:`.ScheduledImpulseEvent` objects should be handled."""

    MANEUVER_TYPE_SPIRAL: str = "spiral"
    """``str``: Configuration string used to delineate spiral maneuver to apply this thrust."""

    MANEUVER_TYPE_PLANE_CHANGE: str = "plane_change"
    """``str``: Configuration string used to delineate plane change maneuver to apply this thrust."""

    # [NOTE]: Old-style generic type hints builtins (Tuple vs tuple) required until we either:
    #   1) Move to SQLAlchemy >= 2.0
    #   2) Move to Python >= 3.10
    VALID_MANEUVER_TYPES: Tuple[str] = (  # noqa: UP006
        MANEUVER_TYPE_SPIRAL,
        MANEUVER_TYPE_PLANE_CHANGE,
    )
    """``tuple``: Valid values for :attr:`.maneuver_type`."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    maneuver_type = Column(String(10))
    """``str``: Label for type of maneuver being applied."""

    maneuver_mag = Column(Float)
    """``float``: Magnitude of maneuver vector in km/s^2."""

    @declared_attr
    def planned(self):  # pylint: disable=invalid-name
        """``bool``: Flag indicating whether this task is expected by the filter or not."""
        return Event.__table__.c.get("planned", Column(Boolean))  # pylint: disable=no-member

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

        finite_maneuver = None
        if str(self.maneuver_type).lower() == self.MANEUVER_TYPE_SPIRAL:
            thrust_func = partial(spiralThrust, magnitude=self.maneuver_mag)
        elif str(self.maneuver_type).lower() == self.MANEUVER_TYPE_PLANE_CHANGE:
            thrust_func = partial(planeChangeThrust, magnitude=self.maneuver_mag)
        else:
            err = f"{self.maneuver_type} is not a valid thrust type."
            raise ValueError(err)
        finite_maneuver = ScheduledFiniteManeuver(
            start_sim_time, end_sim_time, thrust_func, scope_instance.simulation_id
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
