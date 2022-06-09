"""Defines the :class:`.ScheduledFiniteManeuverEvent` data table class."""
# Third Party Imports
from functools import partial
from sqlalchemy import Column, Float, String
from numpy import asarray
# Package
from .base import Event, EventScope
from ...physics.time.stardate import JulianDate, datetimeToJulianDate
from ...dynamics.integration_events.finite_thrust import ScheduledFiniteManeuver, spiralThrust, planeChangeThrust


class ScheduledFiniteManeuverEvent(Event):
    """Event data object describing a scheduled finite maneuver."""

    EVENT_TYPE = "finite_maneuver"
    """str: Name of this type of event."""

    INTENDED_SCOPE = EventScope.AGENT_PROPAGATION
    """EventScope: Scope where :class:`.ScheduledImpulseEvent` objects should be handled."""

    MANEUVER_TYPE_SPIRAL = "spiral"
    """str: Configuration string used to delineate spiral maneuver to apply this thrust."""

    MANEUVER_TYPE_PLANE_CHANGE = "plane_change"
    """str: Configuration string used to delineate plane change maneuver to apply this thrust."""

    VALID_MANEUVER_TYPES = (MANEUVER_TYPE_SPIRAL, MANEUVER_TYPE_PLANE_CHANGE)
    """tuple: Valid values for :attr:`.maneuver_type`."""

    __mapper_args__ = {
        'polymorphic_identity': EVENT_TYPE
    }

    maneuver_type = Column(String(10))
    """str: Label for type of maneuver being applied."""

    maneuver_mag = Column(Float)
    """float: Magnitude of maneuver vector in km/s^2."""

    MUTABLE_COLUMN_NAMES = Event.MUTABLE_COLUMN_NAMES + (
        "maneuver_mag", "maneuver_type"
    )

    def handleEvent(self, scope_instance):
        """Queue a :class:`.ScheduledFiniteManeuver` to take place during agent propagation.

        Args:
            scope_instance (:class:`~.agent_base.Agent`): agent instance that will be executing this finite maneuver.
        """
        start_jd = JulianDate(self.start_time_jd)
        end_jd = JulianDate(self.end_time_jd)
        start_sim_time = start_jd.convertToScenarioTime(scope_instance.julian_date_start)
        end_sim_time = end_jd.convertToScenarioTime(scope_instance.julian_date_start)

        time_vector = asarray([start_sim_time, end_sim_time])

        finite_maneuver = None
        if str(self.maneuver_type).lower() == self.MANEUVER_TYPE_SPIRAL:
            thrust_func = partial(spiralThrust, magnitude=self.maneuver_mag)
        elif str(self.maneuver_type).lower() == self.MANEUVER_TYPE_PLANE_CHANGE:
            thrust_func = partial(planeChangeThrust, magnitude=self.maneuver_mag)
        else:
            err = f"{self.maneuver_type} is not a valid thrust type."
            raise ValueError(err)
        finite_maneuver = ScheduledFiniteManeuver(time_vector, thrust_func)

        # if finite_burn not in scope_instance.propagate_event_queue:
        scope_instance.appendPropagateEvent(finite_maneuver)

    @classmethod
    def fromConfig(cls, config):
        """Construct a :class:`.ScheduledFiniteEvent` from a specified `config`.

        Args:
            config (ScheduledFiniteEventConfigObject): Configuration object to construct a
                :class:`.ScheduledFiniteEvent` from.

        Returns:
            ScheduledFiniteEvent: :class:`.ScheduledFiniteEvent` object based on specified `config`.
        """
        return cls(
            scope=config.scope,
            scope_instance_id=config.scope_instance_id,
            start_time_jd=datetimeToJulianDate(config.start_time),
            end_time_jd=datetimeToJulianDate(config.end_time),
            event_type=config.event_type,
            maneuver_type=config.maneuver_type,
            maneuver_mag=config.maneuver_mag
        )
