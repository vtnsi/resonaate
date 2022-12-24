"""Defines the :class:`.Observation` data table class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

# Local Imports
from ..physics.time.stardate import JulianDate, julianDateToDatetime
from ..physics.transforms.methods import ecef2lla, eci2ecef
from ..sensors.measurement import MEASUREMENT_TYPE_MAP, Measurement
from . import Base, _DataMixin
from .missed_observation import MissedObservation

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self

    # Local Imports
    from ..physics.measurement_utils import IsAngle


VALID_MEASUREMENTS = tuple(MEASUREMENT_TYPE_MAP.keys())


class Observation(Base, _DataMixin):
    r"""Represents singular observation information in database."""

    __tablename__ = "observations"
    id = Column(Integer, primary_key=True)

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

    # Type of the observing sensor (Optical, Radar, AdvRadar)
    sensor_type = Column(String(128), nullable=False)

    # Observed azimuth of target from observing sensor in radians
    azimuth_rad = Column(Float)

    # Observed elevation of target from observing sensor in radians
    elevation_rad = Column(Float)

    # Observed range of target from observing sensor in kilometers
    range_km = Column(Float, nullable=True)

    # Observed range rate of target from observing sensor in kilometers per second
    range_rate_km_p_sec = Column(Float, nullable=True)

    # Latitude of observing sensor in radians
    position_lat_rad = Column(Float)

    # Longitude of observing sensor in radians
    position_lon_rad = Column(Float)

    # Altitude of observing sensor in kilometers
    position_altitude_km = Column(Float)

    # It is visible...
    reason = MissedObservation.Explanation.VISIBLE

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "sensor_id",
        "target_id",
        "sensor_type",
        "azimuth_rad",
        "elevation_rad",
        "range_km",
        "range_rate_km_p_sec",
        "position_lat_rad",
        "position_lon_rad",
        "position_altitude_km",
    )

    def __init__(
        self,
        julian_date: JulianDate | float,
        target_id: int,
        sensor_id: int,
        sensor_type: str,
        sen_eci_state: ndarray,
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
        self.azimuth_rad = azimuth_rad
        self.elevation_rad = elevation_rad
        self.range_km = range_km
        self.range_rate_km_p_sec = range_rate_km_p_sec
        # [TODO]: Temporary solution until proper relationship columns are setup
        self._sensor_eci = sen_eci_state
        utc_datetime = julianDateToDatetime(JulianDate(julian_date))
        sensor_lla = ecef2lla(eci2ecef(sen_eci_state, utc_datetime))
        self.position_lat_rad = sensor_lla[0]
        self.position_lon_rad = sensor_lla[1]
        self.position_altitude_km = sensor_lla[2]
        self._measurement: Measurement | None = None
        self.measurement = measurement

    @classmethod
    def fromMeasurement(
        cls,
        epoch_jd: JulianDate | float,
        target_id: int,
        tgt_eci_state: ndarray,
        sensor_id: int,
        sen_eci_state: ndarray,
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
            sen_eci_state=sen_eci_state,
            measurement=measurement,
            **measurement.calculateMeasurement(
                sen_eci_state, tgt_eci_state, utc_datetime, noisy=noisy
            ),
        )

    @property
    def lla(self) -> ndarray:
        r"""``ndarray``: Three element coordinate vector in the LLA frame."""
        return array([self.position_lat_rad, self.position_lon_rad, self.position_altitude_km])

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

    @property
    def sensor_eci(self) -> ndarray:
        r"""``ndarray``: Returns the sensor's 6x1 ECI state vector at the time of observation."""
        return self._sensor_eci
