"""Defines the :class:`.SensorAdditionEvent` data table class."""

from __future__ import annotations

# Standard Library Imports
from json import dumps, loads
from typing import TYPE_CHECKING

# Third Party Imports
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, relationship

# Local Imports
from ...common.labels import FoVLabel, PlatformLabel, SensorLabel
from ...physics.time.stardate import datetimeToJulianDate
from .base import Event, EventScope

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...scenario.config.event_configs import SensorAdditionEventConfig
    from ...scenario.scenario import Scenario


class SensorAdditionEvent(Event):
    """Event data object describing a sensor that is added after scenario start."""

    EVENT_TYPE: str = "sensor_addition"
    """``str``: Name of this type of event."""

    INTENDED_SCOPE: EventScope = EventScope.SCENARIO_STEP
    """:class:`.EventScope`: Scope where :class:`.SensorAdditionEvent` objects should be handled."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    @declared_attr
    def agent_id(self):
        """``int``: Unique ID of the :class:`.AgentModel` being added to the scenario."""
        return Event.__table__.c.get("agent_id", Column(Integer, ForeignKey("agents.unique_id")))

    agent = relationship("AgentModel", lazy="joined", innerjoin=True)
    """:class:`~.agent.AgentModel`: the `AgentModel` object being added to the scenario."""

    @declared_attr
    def tasking_engine_id(self):
        """``int``: Unique ID for the :class:`.TaskingEngine` that this sensor should be added to."""
        return Event.__table__.c.get("tasking_engine_id", Column(Integer))

    platform: Mapped[str] = Column(String(64))
    """``str``: Label for type of platform that this sensing agent is."""

    @declared_attr
    def pos_x_km(self):
        """``float``: Cartesian x-coordinate for inertial satellite location in ECI frame."""
        return Event.__table__.c.get("pos_x_km", Column(Float))

    @declared_attr
    def pos_y_km(self):
        """``float``: Cartesian y-coordinate for inertial satellite location in ECI frame."""
        return Event.__table__.c.get("pos_y_km", Column(Float))

    @declared_attr
    def pos_z_km(self):
        """``float``: Cartesian z-coordinate for inertial satellite location in ECI frame."""
        return Event.__table__.c.get("pos_z_km", Column(Float))

    @declared_attr
    def vel_x_km_p_sec(self):
        """``float``: Cartesian x-coordinate for inertial satellite velocity in ECI frame."""
        return Event.__table__.c.get("vel_x_km_p_sec", Column(Float))

    @declared_attr
    def vel_y_km_p_sec(self):
        """``float``: Cartesian y-coordinate for inertial satellite velocity in ECI frame."""
        return Event.__table__.c.get("vel_y_km_p_sec", Column(Float))

    @declared_attr
    def vel_z_km_p_sec(self):
        """``float``: Cartesian z-coordinate for inertial satellite velocity in ECI frame."""
        return Event.__table__.c.get("vel_z_km_p_sec", Column(Float))

    azimuth_min = Column(Float)
    """``float``: Minimum amount of motion (degrees) this sensor has in the azimuth plane."""

    azimuth_max = Column(Float)
    """``float``: Maximum amount of motion (degrees) this sensor has in the azimuth plane."""

    elevation_min = Column(Float)
    """``float``: Minimum amount of motion (degrees) this sensor has in the elevation plane."""

    elevation_max = Column(Float)
    """``float``: Maximum amount of motion (degrees) this sensor has in the elevation plane."""

    covariance_json = Column(String(128))
    """``str``: JSON serialized covariance array."""

    aperture_diameter = Column(Float)
    """``float``: Effective diameter (meters) of the sensor."""

    efficiency = Column(Float)
    """``float``: Efficiency percentage of the sensor."""

    slew_rate = Column(Float)
    """``float``: Rate (degrees/sec) at which this sensor can slew to acquire new targets."""

    sensor_type = Column(String(64))
    """``str``: Label for type of sensor this sensor is."""

    fov_shape = Column(String(64))
    """``str``: fov_shape string."""

    fov_angle_1 = Column(Float)
    """``float``: first angle (only angle for `conic`, horizontal angle for `rectangular`."""

    fov_angle_2 = Column(Float, nullable=True)
    """``float``: Second angle (vertical angle for `rectangular`."""

    background_observations = Column(Boolean, nullable=True)
    """``bool``: whether to do FoV calcs."""

    minimum_range = Column(Float, nullable=True)
    """``float``: minimum range at which this sensor can observe targets, km."""

    maximum_range = Column(Float, nullable=True)
    """``float``: maximum range at which this sensor can observe targets, km."""

    tx_power = Column(Float)
    """``float``: Transmit power of radar sensor.

    Defaults to NULL unless :attr:`.sensor_type` is `RADAR` or `ADV_RADAR`.
    """

    tx_frequency = Column(Float)
    """``float``: Transmit frequency of radar sensor.

    Defaults to NULL unless :attr:`.sensor_type` is `RADAR` or `ADV_RADAR`.
    """

    min_detectable_power = Column(Float)
    """``float``: The smallest received power that can be detected by the radar, W.

    Defaults to NULL unless :attr:`.sensor_type` is `RADAR` or `ADV_RADAR`.
    """

    detectable_vismag = Column(Float, nullable=True)
    """``float``, optional: minimum detectable visual magnitude value, used for visibility constraints, unit-less. Defaults to :data:`.OPTICAL_DETECTABLE_VISMAG`.

    Defaults to NULL unless :attr:`.sensor_type` is `OPTICAL`.
    """

    @declared_attr
    def station_keeping_json(self):
        """``str``: JSON serialized list of station keeping key words for this target."""
        return Event.__table__.c.get("station_keeping_json", Column(String(128), nullable=True))

    MUTABLE_COLUMN_NAMES = (
        *Event.MUTABLE_COLUMN_NAMES,
        "agent_id",
        "tasking_engine_id",
        "platform",
        "pos_x_km",
        "pos_y_km",
        "pos_z_km",
        "vel_x_km_p_sec",
        "vel_y_km_p_sec",
        "vel_z_km_p_sec",
        "azimuth_min",
        "azimuth_max",
        "elevation_min",
        "elevation_max",
        "covariance_json",
        "aperture_diameter",
        "efficiency",
        "slew_rate",
        "sensor_type",
        "fov_shape",
        "fov_angle_1",
        "fov_angle_2",
        "background_observations",
        "station_keeping_json",
        "minimum_range",
        "maximum_range",
        "tx_power",
        "tx_frequency",
        "min_detectable_power",
        "detectable_vismag",
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
    def azimuth_range(self) -> list[float]:
        """``list``: Range of motion (radians) that this sensor has in the azimuth plane."""
        return [self.azimuth_min, self.azimuth_max]

    @property
    def elevation_range(self) -> list[float]:
        """``list``: Range of motion (radians) that this sensor has in the elevation plane."""
        return [self.elevation_min, self.elevation_max]

    @property
    def covariance(self) -> list[list[float]]:
        """``list``: Measurement noise covariance matrix."""
        return loads(self.covariance_json)

    @property
    def station_keeping(self) -> dict:
        """``dict``: station keeping key words for this target."""
        return loads(self.station_keeping_json)

    @property
    def field_of_view(self) -> dict:
        """``dict``: Field of view dictionary object."""
        if self.fov_shape == FoVLabel.CONIC:
            return {"fov_shape": self.fov_shape, "cone_angle": self.fov_angle_1}

        if self.fov_shape == FoVLabel.RECTANGULAR:
            return {
                "fov_shape": self.fov_shape,
                "azimuth_angle": self.fov_angle_1,
                "elevation_angle": self.fov_angle_2,
            }

        raise ValueError("Incorrect field of view image type")

    def handleEvent(self, scope_instance: Scenario) -> None:
        """Add the node described by this :class:`.NodeAdditionEvent` to the appropriate tasking engine.

        Args:
            scope_instance (:class:`.Scenario`): :class:`.Scenario` class that's currently executing.
        """
        sensor_spec = {
            "id": self.agent_id,
            "name": self.agent.name,
            "platform": {
                "type": self.platform,
                "station_keeping": self.station_keeping,
            },
            "state": {
                "type": "eci",
                "position": self.eci[:3],
                "velocity": self.eci[3:],
            },
            "sensor": {
                "azimuth_range": self.azimuth_range,
                "elevation_range": self.elevation_range,
                "covariance": self.covariance,
                "aperture_diameter": self.aperture_diameter,
                "efficiency": self.efficiency,
                "slew_rate": self.slew_rate,
                "field_of_view": self.field_of_view,
                "type": self.sensor_type,
                "minimum_range": self.minimum_range,
                "maximum_range": self.maximum_range,
                "background_observations": self.background_observations,
            },
        }
        if self.sensor_type in (SensorLabel.RADAR, SensorLabel.ADV_RADAR):
            sensor_spec["sensor"]["tx_power"] = self.tx_power
            sensor_spec["sensor"]["tx_frequency"] = self.tx_frequency
            sensor_spec["sensor"]["min_detectable_power"] = self.min_detectable_power
        else:
            sensor_spec["sensor"]["detectable_vismag"] = self.detectable_vismag

        scope_instance.addSensor(sensor_spec, self.tasking_engine_id)

    @classmethod
    def fromConfig(cls, config: SensorAdditionEventConfig) -> SensorAdditionEvent:
        """Construct a :class:`.NodeAdditionEvent` from a specified `config`.

        Args:
            config (:class:`.SensorAdditionEventConfig`): Configuration object to construct a :class:`.NodeAdditionEvent` from.

        Returns:
            :class:`.SensorAdditionEvent`: object based on the specified `config`.
        """
        sensor_agent = config.sensor_agent
        sensor = sensor_agent.sensor
        initial_state = sensor_agent.state.toECI(config.start_time)

        station_keeping = ""
        if sensor_agent.platform.type == PlatformLabel.SPACECRAFT:
            station_keeping = sensor_agent.platform.station_keeping.model_dump_json()

        custom_kwargs = {}
        if sensor.type in (SensorLabel.RADAR, SensorLabel.ADV_RADAR):
            custom_kwargs["tx_power"] = sensor.tx_power
            custom_kwargs["tx_frequency"] = sensor.tx_frequency
            custom_kwargs["min_detectable_power"] = sensor.min_detectable_power

        if sensor.type == SensorLabel.OPTICAL:
            custom_kwargs["detectable_vismag"] = sensor.detectable_vismag

        if sensor.field_of_view.fov_shape == FoVLabel.CONIC:
            fov_angle_1 = sensor.field_of_view.cone_angle
            fov_angle_2 = 0.0
        elif sensor.field_of_view.fov_shape == FoVLabel.RECTANGULAR:
            fov_angle_1 = sensor.field_of_view.azimuth_angle
            fov_angle_2 = sensor.field_of_view.elevation_angle
        else:
            raise ValueError(f"Field of View config has incorrect type {sensor.field_of_view}")

        return cls(
            scope=config.scope,
            scope_instance_id=config.scope_instance_id,
            start_time_jd=datetimeToJulianDate(config.start_time),
            end_time_jd=datetimeToJulianDate(config.end_time),
            event_type=config.event_type,
            tasking_engine_id=config.tasking_engine_id,
            agent_id=sensor_agent.id,
            platform=sensor_agent.platform.type,
            pos_x_km=initial_state[0],
            pos_y_km=initial_state[1],
            pos_z_km=initial_state[2],
            vel_x_km_p_sec=initial_state[3],
            vel_y_km_p_sec=initial_state[4],
            vel_z_km_p_sec=initial_state[5],
            azimuth_min=sensor.azimuth_range[0],
            azimuth_max=sensor.azimuth_range[1],
            elevation_min=sensor.elevation_range[0],
            elevation_max=sensor.elevation_range[1],
            covariance_json=dumps(sensor.covariance),
            aperture_diameter=sensor.aperture_diameter,
            efficiency=sensor.efficiency,
            slew_rate=sensor.slew_rate,
            sensor_type=sensor.type,
            fov_shape=sensor.field_of_view.fov_shape,
            fov_angle_1=fov_angle_1,
            fov_angle_2=fov_angle_2,
            minimum_range=sensor.minimum_range,
            maximum_range=sensor.maximum_range,
            background_observations=sensor.background_observations,
            station_keeping_json=station_keeping,
            **custom_kwargs,
        )
