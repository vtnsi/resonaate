"""Defines the :class:`.Observation` data table class."""
from __future__ import annotations

# Standard Library Imports
from enum import Enum, unique
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

# Local Imports
from ..physics.time.stardate import JulianDate, julianDateToDatetime
from ..sensors.measurement import MEASUREMENT_TYPE_MAP, Measurement
from . import Base, _DataMixin

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self

    # Local Imports
    from ..physics.measurement_utils import IsAngle


VALID_MEASUREMENTS = tuple(MEASUREMENT_TYPE_MAP.keys())


@unique
class Explanation(Enum):
    """Enumeration for explanations of why an observation was missed."""

    VISIBLE = "Visible"
    MINIMUM_RANGE = "Minimum Range"
    MAXIMUM_RANGE = "Maximum Range"
    LINE_OF_SIGHT = "Line of Sight"
    AZIMUTH_MASK = "Azimuth Mask"
    ELEVATION_MASK = "Elevation Mask"
    VIZ_MAG = "Visual Magnitude"
    SOLAR_FLUX = "Solar Flux"
    LIMB_OF_EARTH = "Limb of the Earth"
    SPACE_ILLUMINATION = "Space Sensor Illumination"
    GROUND_ILLUMINATION = "Ground Sensor Illumination"
    RADAR_SENSITIVITY = "Radar Sensitivity - Max Range"
    FIELD_OF_VIEW = "Field of View"
    SLEW_DISTANCE = "Slew Rate/Distance to Target"
    GALACTIC_EXCLUSION = "Galactic Exclusion Zone"


class _ObservationMixin(_DataMixin):
    """Data Columns applicable to both Observation and Missed Observation Tables."""

    id = Column(Integer, primary_key=True)

    # Type of the observing sensor (Optical, Radar, AdvRadar)
    sensor_type = Column(String(128), nullable=False)

    ## Cartesian x-coordinate for Sensor location in ECI frame in kilometers
    pos_x_km = Column(Float, nullable=False)

    ## Cartesian y-coordinate for Sensor location in ECI frame in kilometers
    pos_y_km = Column(Float, nullable=False)

    ## Cartesian z-coordinate for Sensor location in ECI frame in kilometers
    pos_z_km = Column(Float, nullable=False)

    ## Cartesian x-coordinate for Sensor velocity in ECI frame in kilometers per second
    vel_x_km_p_sec = Column(Float, nullable=False)

    ## Cartesian y-coordinate for Sensor velocity in ECI frame in kilometers per second
    vel_y_km_p_sec = Column(Float, nullable=False)

    ## Cartesian z-coordinate for Sensor velocity in ECI frame in kilometers per second
    vel_z_km_p_sec = Column(Float, nullable=False)

    @property
    def sensor_eci(self) -> ndarray:
        r"""``ndarray``: Returns the sensor's 6x1 ECI state vector at the time of observation."""
        return array(
            [
                self.pos_x_km,
                self.pos_y_km,
                self.pos_z_km,
                self.vel_x_km_p_sec,
                self.vel_y_km_p_sec,
                self.vel_z_km_p_sec,
            ]
        )


class Observation(Base, _ObservationMixin):
    """Represents singular observation information in database."""

    __tablename__ = "observations"

    ## Defines the epoch associated with the observation data
    # Many to one relation with :class:`.Epoch`
    julian_date = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)

    ## Defines the associated sensor agent with the observation data
    # Many to one relation with :class:`.AgentModel`
    sensor_id = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    sensor = relationship("AgentModel", foreign_keys=[sensor_id], lazy="joined", innerjoin=True)

    ## Defines the associated target agent with the observation data
    # Many to one relation with :class:`.AgentModel`
    target_id = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    target = relationship("AgentModel", foreign_keys=[target_id], lazy="joined", innerjoin=True)

    # Observed azimuth of target from observing sensor in radians
    azimuth_rad = Column(Float)

    # Observed elevation of target from observing sensor in radians
    elevation_rad = Column(Float)

    # Observed range of target from observing sensor in kilometers
    range_km = Column(Float, nullable=True)

    # Observed range rate of target from observing sensor in kilometers per second
    range_rate_km_p_sec = Column(Float, nullable=True)

    # It is visible...
    reason = Explanation.VISIBLE

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "sensor_id",
        "target_id",
        "sensor_type",
        "azimuth_rad",
        "elevation_rad",
        "range_km",
        "range_rate_km_p_sec",
        "pos_x_km",
        "pos_y_km",
        "pos_z_km",
        "vel_x_km_p_sec",
        "vel_y_km_p_sec",
        "vel_z_km_p_sec",
    )

    def __init__(
        self,
        julian_date: JulianDate | float,
        target_id: int,
        sensor_id: int,
        sensor_type: str,
        sensor_eci: ndarray,
        measurement: Measurement,
        azimuth_rad: float | None = None,
        elevation_rad: float | None = None,
        range_km: float | None = None,
        range_rate_km_p_sec: float | None = None,
    ) -> None:
        r"""Explicit constructor for creating an Observation."""
        self.julian_date = float(julian_date)
        self.sensor_id = sensor_id
        self.target_id = target_id
        self.sensor_type = sensor_type
        self.pos_x_km = sensor_eci[0]
        self.pos_y_km = sensor_eci[1]
        self.pos_z_km = sensor_eci[2]
        self.vel_x_km_p_sec = sensor_eci[3]
        self.vel_y_km_p_sec = sensor_eci[4]
        self.vel_z_km_p_sec = sensor_eci[5]
        self.azimuth_rad = azimuth_rad
        self.elevation_rad = elevation_rad
        self.range_km = range_km
        self.range_rate_km_p_sec = range_rate_km_p_sec
        self._measurement: Measurement | None = None
        self.measurement = measurement

    @classmethod
    def fromMeasurement(
        cls,
        epoch_jd: JulianDate | float,
        target_id: int,
        tgt_eci_state: ndarray,
        sensor_id: int,
        sensor_eci: ndarray,
        sensor_type: str,
        measurement: Measurement,
        noisy: bool,
    ) -> Self:
        r"""Alternative constructor for creating observation objects."""
        utc_datetime = julianDateToDatetime(JulianDate(epoch_jd))
        return cls(
            julian_date=epoch_jd,
            target_id=target_id,
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            sensor_eci=sensor_eci,
            measurement=measurement,
            **measurement.calculateMeasurement(
                sensor_eci, tgt_eci_state, utc_datetime, noisy=noisy
            ),
        )

    @property
    def measurement_states(self) -> ndarray:
        r"""``ndarray``: measurement component values provided by this observation.

        Note:
            These states are not guaranteed to be in the correct order if pulled directly from the DB.
        """
        if self.measurement is not None:
            return array([self.__dict__[meas_type] for meas_type in self.measurement.labels])

        # else
        return array(
            [
                self.__dict__[meas_type]
                for meas_type in VALID_MEASUREMENTS
                if self.__dict__[meas_type] is not None
            ]
        )

    @property
    def dim(self) -> int:
        r"""``int``: Returns the measurement vector dimension."""
        return self.measurement_states.shape[0]

    @property
    def measurement(self) -> Measurement:
        r"""Returns measurement object associated with this observation, see :class:`.Measurement`."""
        return self._measurement

    @measurement.setter
    def measurement(self, new_measurement: Measurement) -> None:
        r"""Save a new measurement object to this observation, for loading from a DB query.

        Args:
            new_measurement (:class:`.Measurement`): measurement object to save to instance attribute.
        """
        if not isinstance(new_measurement, Measurement):
            raise TypeError(f"Incorrect type for 'measurement' attribute: {type(new_measurement)}")

        self._measurement = new_measurement

    @property
    def angular_values(self) -> list[IsAngle]:
        r"""Returns which measurements are angles as :class:`.IsAngle`, see :meth:`.Measurement.angular_values`."""
        return self._measurement.angular_values

    @property
    def r_matrix(self) -> ndarray:
        r"""``ndarray``: Returns the measurement noise covariance matrix, see :meth:`.Measurement.r_matrix`."""
        return self._measurement.r_matrix


class MissedObservation(Base, _ObservationMixin):
    """Represents singular missed observation information in the database."""

    __tablename__ = "missed_observations"

    ## Defines the epoch associated with the observation data
    # Many to one relation with :class:`.Epoch`
    julian_date = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)

    ## Defines the associated sensor agent with the observation data
    # Many to one relation with :class:`.AgentModel`
    sensor_id = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    sensor = relationship("AgentModel", foreign_keys=[sensor_id], lazy="joined", innerjoin=True)

    ## Defines the associated target agent with the observation data
    # Many to one relation with :class:`.AgentModel`
    target_id = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    target = relationship("AgentModel", foreign_keys=[target_id], lazy="joined", innerjoin=True)

    # True reason why observation was missed, for debugging only!
    reason = Column(String, nullable=False)

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "sensor_id",
        "target_id",
        "sensor_type",
        "pos_x_km",
        "pos_y_km",
        "pos_z_km",
        "vel_x_km_p_sec",
        "vel_y_km_p_sec",
        "vel_z_km_p_sec",
        "reason",
    )

    def __init__(
        self,
        julian_date: JulianDate | float,
        sensor_id: int,
        target_id: int,
        sensor_type: str,
        sensor_eci: ndarray,
        reason: str,
    ) -> None:
        """Explicit constructor for creating an Observation."""
        self.julian_date = float(julian_date)
        self.sensor_id = sensor_id
        self.target_id = target_id
        self.sensor_type = sensor_type
        self.pos_x_km = sensor_eci[0]
        self.pos_y_km = sensor_eci[1]
        self.pos_z_km = sensor_eci[2]
        self.vel_x_km_p_sec = sensor_eci[3]
        self.vel_y_km_p_sec = sensor_eci[4]
        self.vel_z_km_p_sec = sensor_eci[5]
        self.reason = reason
