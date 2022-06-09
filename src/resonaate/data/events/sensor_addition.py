"""Defines the :class:`.SensorAdditionEvent` data table class."""
# Standard Library Imports
from json import dumps, loads

# Third Party Imports
from numpy import array
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

# Local Imports
from ...physics.orbits.elements import ClassicalElements, EquinoctialElements
from ...physics.time.stardate import datetimeToJulianDate
from ...physics.transforms.methods import ecef2eci, lla2ecef
from ...sensors import ADV_RADAR_LABEL, RADAR_LABEL
from .base import Event, EventScope


class SensorAdditionEvent(Event):
    """Event data object describing a sensor that is added after scenario start."""

    EVENT_TYPE = "sensor_addition"
    """str: Name of this type of event."""

    INTENDED_SCOPE = EventScope.SCENARIO_STEP
    """EventScope: Scope where :class:`.SensorAdditionEvent` objects should be handled."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    @declared_attr
    def agent_id(self):  # pylint: disable=invalid-name
        """int: Unique ID of the :class:`.Agent` being added to the scenario."""
        return Event.__table__.c.get(  # pylint: disable=no-member
            "agent_id", Column(Integer, ForeignKey("agents.unique_id"))
        )

    agent = relationship("Agent", lazy="joined", innerjoin=True)
    """agent_base.Agent: the `Agent` object being added to the scenario."""

    @declared_attr
    def tasking_engine_id(self):  # pylint: disable=invalid-name
        """int: Unique ID for the :class:`.TaskingEngine` that this sensor should be added to."""
        return Event.__table__.c.get(  # pylint: disable=no-member
            "tasking_engine_id", Column(Integer)
        )

    host_type = Column(String(64))
    """str: Label for type of sensing agent this sensor is."""

    @declared_attr
    def pos_x_km(self):  # pylint: disable=invalid-name
        """float: Cartesian x-coordinate for inertial satellite location in ECI frame."""
        return Event.__table__.c.get("pos_x_km", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def pos_y_km(self):  # pylint: disable=invalid-name
        """float: Cartesian y-coordinate for inertial satellite location in ECI frame."""
        return Event.__table__.c.get("pos_y_km", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def pos_z_km(self):  # pylint: disable=invalid-name
        """float: Cartesian z-coordinate for inertial satellite location in ECI frame."""
        return Event.__table__.c.get("pos_z_km", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def vel_x_km_p_sec(self):  # pylint: disable=invalid-name
        """float: Cartesian x-coordinate for inertial satellite velocity in ECI frame."""
        return Event.__table__.c.get("vel_x_km_p_sec", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def vel_y_km_p_sec(self):  # pylint: disable=invalid-name
        """float: Cartesian y-coordinate for inertial satellite velocity in ECI frame."""
        return Event.__table__.c.get("vel_y_km_p_sec", Column(Float))  # pylint: disable=no-member

    @declared_attr
    def vel_z_km_p_sec(self):  # pylint: disable=invalid-name
        """float: Cartesian z-coordinate for inertial satellite velocity in ECI frame."""
        return Event.__table__.c.get("vel_z_km_p_sec", Column(Float))  # pylint: disable=no-member

    azimuth_min = Column(Float)
    """float: Minimum amount of motion (radians) this sensor has in the azimuth plane."""

    azimuth_max = Column(Float)
    """float: Maximum amount of motion (radians) this sensor has in the azimuth plane."""

    elevation_min = Column(Float)
    """float: Minimum amount of motion (radians) this sensor has in the elevation plane."""

    elevation_max = Column(Float)
    """float: Maximum amount of motion (radians) this sensor has in the elevation plane."""

    covariance_json = Column(String(128))
    """str: JSON serialized covariance array."""

    aperture_area = Column(Float)
    """float: Size (meters^2) of the sensor."""

    efficiency = Column(Float)
    """float: Efficiency percentage of the sensor."""

    slew_rate = Column(Float)
    """float: Rate (radians/sec) at which this sensor can slew to acquire new targets."""

    sensor_type = Column(String(64))
    """str: Label for type of sensor this sensor is."""

    exemplar_cross_section = Column(Float)
    """float: Cross sectional area (m^2) exemplar capability."""

    exemplar_range = Column(Float)
    """float: Range (km) exemplar capability."""

    field_of_view = Column(Float)
    """float: Field of View (degrees)."""

    tx_power = Column(Float)
    """float: Transmit power of radar sensor.

    Defaults to 0.0 unless :attr:`.sensor_type` is `RADAR_LABEL` or `ADV_RADAR_LABEL`.
    """

    tx_frequency = Column(Float)
    """float: Transmit frequency of radar sensor.

    Defaults to 0.0 unless :attr:`.sensor_type` is `RADAR_LABEL` or `ADV_RADAR_LABEL`.
    """

    @declared_attr
    def station_keeping_json(self):  # pylint: disable=invalid-name
        """str: JSON serialized list of station keeping key words for this target."""
        return Event.__table__.c.get(  # pylint: disable=no-member
            "station_keeping_json", Column(String(128))
        )

    MUTABLE_COLUMN_NAMES = Event.MUTABLE_COLUMN_NAMES + (
        "agent_id",
        "tasking_engine_id",
        "host_type",
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
        "aperture_area",
        "efficiency",
        "slew_rate",
        "sensor_type",
        "exemplar_cross_section",
        "exemplar_range",
        "field_of_view",
        "tx_power",
        "tx_frequency",
        "station_keeping_json",
    )

    @property
    def eci(self):
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
    def azimuth_range(self):
        """list: Range of motion (radians) that this sensor has in the azimuth plane."""
        return [self.azimuth_min, self.azimuth_max]

    @property
    def elevation_range(self):
        """list: Range of motion (radians) that this sensor has in the elevation plane."""
        return [self.elevation_min, self.elevation_max]

    @property
    def covariance(self):
        """list: Measurement noise covariance matrix."""
        return loads(self.covariance_json)

    @property
    def exemplar(self):
        """list: Two element list of exemplar capabilities, used in min detectable power calculation."""
        return [self.exemplar_cross_section, self.exemplar_range]

    @property
    def station_keeping(self):
        """list: List of station keeping key words for this target."""
        return loads(self.station_keeping_json)

    def handleEvent(self, scope_instance):
        """Add the node described by this :class:`.NodeAdditionEvent` to the appropriate tasking engine.

        Args:
            scope_instance (Scenario): :class:`.Scenario` class that's currently executing.
        """
        sensor_spec = {
            "id": self.agent_id,
            "name": self.agent.name,
            "host_type": self.host_type,
            "init_eci": self.eci,
            "azimuth_range": self.azimuth_range,
            "elevation_range": self.elevation_range,
            "covariance": self.covariance,
            "aperture_area": self.aperture_area,
            "efficiency": self.efficiency,
            "slew_rate": self.slew_rate,
            "exemplar": self.exemplar,
            "field_of_view": self.field_of_view,
            "sensor_type": self.sensor_type,
            "tx_power": self.tx_power,
            "tx_frequency": self.tx_frequency,
            "station_keeping": self.station_keeping,
        }
        scope_instance.addSensor(sensor_spec, self.tasking_engine_id)

    @classmethod
    def fromConfig(cls, config):
        """Construct a :class:`.NodeAdditionEvent` from a specified `config`.

        Args:
            config (SensorAdditionEventConfig): Configuration object to construct a :class:`.NodeAdditionEvent` from.

        Returns:
            NodeAdditionEvent: :class:`.NodeAdditionEvent` object based on the specified `config`.
        """
        if config.lla_set:
            ecef_state = lla2ecef(
                array([config.lat, config.lon, config.alt])  # radians, radians, km
            )
            initial_state = ecef2eci(ecef_state)
        elif config.eci_set:
            initial_state = array(config.init_eci)
        elif config.coe_set:
            orbit = ClassicalElements.fromConfig(config.init_coe)
            initial_state = orbit.toECI()
        elif config.eqe_set:
            orbit = EquinoctialElements.fromConfig(config.init_eqe)
            initial_state = orbit.toECI()
        else:
            raise ValueError(f"Sensor config doesn't contain initial state information: {config}")

        if config.sensor_type in (RADAR_LABEL, ADV_RADAR_LABEL):
            tx_power = config.tx_power
            tx_frequency = config.tx_frequency
        else:
            tx_power = 0.0
            tx_frequency = 0.0

        return cls(
            scope=config.scope,
            scope_instance_id=config.scope_instance_id,
            start_time_jd=datetimeToJulianDate(config.start_time),
            end_time_jd=datetimeToJulianDate(config.end_time),
            event_type=config.event_type,
            tasking_engine_id=config.tasking_engine_id,
            agent_id=config.id,
            host_type=config.host_type,
            pos_x_km=initial_state[0],
            pos_y_km=initial_state[1],
            pos_z_km=initial_state[2],
            vel_x_km_p_sec=initial_state[3],
            vel_y_km_p_sec=initial_state[4],
            vel_z_km_p_sec=initial_state[5],
            azimuth_min=config.azimuth_range[0],
            azimuth_max=config.azimuth_range[1],
            elevation_min=config.elevation_range[0],
            elevation_max=config.elevation_range[1],
            covariance_json=dumps(config.covariance),
            aperture_area=config.aperture_area,
            efficiency=config.efficiency,
            slew_rate=config.slew_rate,
            sensor_type=config.sensor_type,
            exemplar_cross_section=config.exemplar[0],
            exemplar_range=config.exemplar[1],
            field_of_view=config.field_of_view,
            tx_power=tx_power,
            tx_frequency=tx_frequency,
            station_keeping_json=dumps(config.station_keeping.toJSON()),
        )
