"""Defines the :class:`.TargetAdditionEvent` data table class."""
from __future__ import annotations

# Standard Library Imports
from json import dumps, loads
from typing import TYPE_CHECKING

# Third Party Imports
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

# Local Imports
from ...physics.orbits.elements import ClassicalElements, EquinoctialElements
from ...physics.time.stardate import datetimeToJulianDate
from .base import Event, EventScope

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...scenario.config.event_configs import TargetAdditionEventConfig
    from ...scenario.scenario import Scenario


class TargetAdditionEvent(Event):
    """Event data object describing a target that is added after scenario start."""

    EVENT_TYPE: str = "target_addition"
    """``str``: Name of this type of event."""

    INTENDED_SCOPE: EventScope = EventScope.SCENARIO_STEP
    """:class:`.EventScope`: Scope where :class:`.TargetAdditionEvent` objects should be handled."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    @declared_attr
    def agent_id(self):  # pylint: disable=invalid-name
        """``int``: Unique ID of the :class:`.Agent` being added to the scenario."""
        return Event.__table__.c.get(  # pylint: disable=no-member
            "agent_id", Column(Integer, ForeignKey("agents.unique_id"))
        )

    @declared_attr
    def tasking_engine_id(self):  # pylint: disable=invalid-name
        """``int``: Unique ID for the :class:`.TaskingEngine` that this target should be added to."""
        return Event.__table__.c.get(  # pylint: disable=no-member
            "tasking_engine_id", Column(Integer)
        )

    agent = relationship("Agent", lazy="joined", innerjoin=True)
    """:class:`~.agent.Agent`: The `Agent` object being added to the scenario."""

    @declared_attr
    def pos_x_km(self):  # pylint: disable=invalid-name
        """``float``: Cartesian x-coordinate for inertial satellite location in ECI frame."""
        return Event.__table__.c.get("pos_x_km", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def pos_y_km(self):  # pylint: disable=invalid-name
        """``float``: Cartesian y-coordinate for inertial satellite location in ECI frame."""
        return Event.__table__.c.get("pos_y_km", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def pos_z_km(self):  # pylint: disable=invalid-name
        """``float``: Cartesian z-coordinate for inertial satellite location in ECI frame."""
        return Event.__table__.c.get("pos_z_km", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def vel_x_km_p_sec(self):  # pylint: disable=invalid-name
        """``float``: Cartesian x-coordinate for inertial satellite velocity in ECI frame."""
        return Event.__table__.c.get("vel_x_km_p_sec", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def vel_y_km_p_sec(self):  # pylint: disable=invalid-name
        """``float``: Cartesian y-coordinate for inertial satellite velocity in ECI frame."""
        return Event.__table__.c.get("vel_y_km_p_sec", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def vel_z_km_p_sec(self):  # pylint: disable=invalid-name
        """``float``: Cartesian z-coordinate for inertial satellite velocity in ECI frame."""
        return Event.__table__.c.get("vel_z_km_p_sec", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def station_keeping_json(self):  # pylint: disable=invalid-name
        """``str``: JSON serialized list of station keeping key words for this target."""
        return Event.__table__.c.get(  # pylint: disable=no-member
            "station_keeping_json", Column(String(128))
        )

    MUTABLE_COLUMN_NAMES = Event.MUTABLE_COLUMN_NAMES + (
        "agent_id",
        "tasking_engine_id",
        "pos_x_km",
        "pos_y_km",
        "pos_z_km",
        "vel_x_km_p_sec",
        "vel_y_km_p_sec",
        "vel_z_km_p_sec",
        "station_keeping_json",
    )

    @property
    def eci(self) -> list[float]:
        """``list``: returns the formatted ECI state vector."""
        return [
            self.pos_x_km,
            self.pos_y_km,
            self.pos_z_km,
            self.vel_x_km_p_sec,
            self.vel_y_km_p_sec,
            self.vel_z_km_p_sec,
        ]

    @property
    def station_keeping(self) -> dict[str, list[str]]:
        """``dict``: station keeping key words for this target."""
        return loads(self.station_keeping_json)

    def handleEvent(self, scope_instance: Scenario) -> None:
        """Add the node described by this :class:`.NodeAdditionEvent` to the appropriate tasking engine.

        Args:
            scope_instance (:class:`.Scenario`): :class:`.Scenario` class that's currently executing.
        """
        target_spec = {
            "sat_num": self.agent_id,
            "sat_name": self.agent.name,
            "init_eci": self.eci,
            "station_keeping": self.station_keeping,
        }
        scope_instance.addTarget(target_spec, self.tasking_engine_id)

    @classmethod
    def fromConfig(cls, config: TargetAdditionEventConfig) -> TargetAdditionEvent:
        """Construct a :class:`.NodeAdditionEvent` from a specified `config`.

        Args:
            config (:class:`.TargetAdditionEventConfig`): object to construct a :class:`.TargetAdditionEvent` from.

        Returns:
            :class:`.TargetAdditionEvent`: object based on the specified `config`.
        """
        if config.target.eci_set:
            initial_state = config.target.init_eci
        elif config.target.coe_set:
            orbit = ClassicalElements.fromConfig(config.target.init_coe)
            initial_state = orbit.toECI()
        elif config.target.eqe_set:
            orbit = EquinoctialElements.fromConfig(config.target.init_eqe)
            initial_state = orbit.toECI()

        return cls(
            scope=config.scope,
            scope_instance_id=config.scope_instance_id,
            start_time_jd=datetimeToJulianDate(config.start_time),
            end_time_jd=datetimeToJulianDate(config.end_time),
            event_type=config.event_type,
            tasking_engine_id=config.tasking_engine_id,
            agent_id=config.target.sat_num,
            pos_x_km=initial_state[0],
            pos_y_km=initial_state[1],
            pos_z_km=initial_state[2],
            vel_x_km_p_sec=initial_state[3],
            vel_y_km_p_sec=initial_state[4],
            vel_z_km_p_sec=initial_state[5],
            station_keeping_json=dumps(config.target.station_keeping.toJSON()),
        )
