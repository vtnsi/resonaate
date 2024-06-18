"""Defines the :class:`.Observation` data table class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, relationship

# Local Imports
from ..common.labels import Explanation
from ..physics.measurements import MEASUREMENT_TYPE_MAP, Measurement
from ..physics.time.stardate import JulianDate, julianDateToDatetime
from .table_base import Base, _DataMixin

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self

    # Local Imports
    from ..physics.measurements import IsAngle


VALID_MEASUREMENTS = tuple(MEASUREMENT_TYPE_MAP.keys())


class _ObservationMixin(_DataMixin):
    """Data Columns applicable to both Observation and Missed Observation Tables."""

    id: Mapped[float] = Column(Integer, primary_key=True)
    """The observation id Column. Elements are of type ``int``."""

    sensor_type: Mapped[float] = Column(String(128), nullable=False)
    """Type of the observing sensor (Optical, Radar, AdvRadar). Elements are of type ``str`` with a max length of 128."""

    pos_x_km: Mapped[float] = Column(Float, nullable=False)
    """Cartesian x-coordinate for Sensor location in ECI frame in kilometers. Elements are of type ``float``."""

    pos_y_km: Mapped[float] = Column(Float, nullable=False)
    """Cartesian y-coordinate for Sensor location in ECI frame in kilometers. Elements are of type ``float``."""

    pos_z_km: Mapped[float] = Column(Float, nullable=False)
    """Cartesian z-coordinate for Sensor location in ECI frame in kilometers. Elements are of type ``float``."""

    vel_x_km_p_sec: Mapped[float] = Column(Float, nullable=False)
    """Cartesian x-coordinate for Sensor velocity in ECI frame in kilometers per second. Elements are of type ``float``."""

    vel_y_km_p_sec: Mapped[float] = Column(Float, nullable=False)
    """Cartesian y-coordinate for Sensor velocity in ECI frame in kilometers per second. Elements are of type ``float``."""

    vel_z_km_p_sec: Mapped[float] = Column(Float, nullable=False)
    """Cartesian z-coordinate for Sensor velocity in ECI frame in kilometers per second. Elements are of type ``float``."""

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
            ],
        )


class Observation(Base, _ObservationMixin):
    """Represents singular observation information in database."""

    __tablename__ = "observations"

    julian_date: Mapped[float] = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    """Contains all the julian dates, which are of type ``float``."""
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)
    """Defines the epoch associated with the observation data. Many to one relation with :class:`.Epoch`"""

    sensor_id: Mapped[int] = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """Contains all the sensor id numbers, which are of type ``int``"""
    sensor = relationship("AgentModel", foreign_keys=[sensor_id], lazy="joined", innerjoin=True)
    """Defines the associated sensor agent with the task data. Many to one relation with :class:`.AgentModel`"""

    target_id: Mapped[int] = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """Contains all the target id numbers, which are of type ``int``"""
    target = relationship("AgentModel", foreign_keys=[target_id], lazy="joined", innerjoin=True)
    """Defines the associated target agent with the task data. Many to one relation with :class:`.AgentModel`"""

    azimuth_rad: Mapped[float] = Column(Float)
    """Observed azimuth of target from observing sensor in radians. Elements are of type ``float``."""

    elevation_rad: Mapped[float] = Column(Float)
    """Observed elevation of target from observing sensor in radians. Elements are of type ``float``."""

    range_km: Mapped[float] = Column(Float, nullable=True)
    """Observed range of target from observing sensor in kilometers. Elements are of type ``float`` and are nullable."""

    range_rate_km_p_sec: Mapped = Column(Float, nullable=True)
    """Observed range rate of target from observing sensor in kilometers per second. Elements are of type ``float`` and are nullable."""

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

    def __init__(  # noqa: PLR0913
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
        self.julian_date: float = float(julian_date)
        """The Julian Date of the observation."""
        self.sensor_id: int = sensor_id
        """The id number of the sensor."""
        self.target_id: int = target_id
        """The id number of the target."""
        self.sensor_type: str = (
            sensor_type  # Will likely need to check at some point that len(sensor_type) is shorther than 128...
        )
        """The sensor type. Must be shorter than 128 characters"""
        self.pos_x_km: float = sensor_eci[0]
        """The x-coordinate in cartesian space in the ECI frame. Measured in km."""
        self.pos_y_km: float = sensor_eci[1]
        """The y-coordinate in cartesian space in the ECI frame. Measured in km."""
        self.pos_z_km: float = sensor_eci[2]
        """The z-coordinate in cartesian space in the ECI frame. Measured in km."""
        self.vel_x_km_p_sec: float = sensor_eci[3]
        """The x-component of the cartesian velocity vectory in the ECI frame. Measured in km/sec."""
        self.vel_y_km_p_sec: float = sensor_eci[4]
        """The y-component of the cartesian velocity vectory in the ECI frame. Measured in km/sec."""
        self.vel_z_km_p_sec: float = sensor_eci[5]
        """The z-component of the cartesian velocity vectory in the ECI frame. Measured in km/sec."""
        self.azimuth_rad: float = azimuth_rad
        """The azimuth of the observation in radians. Measured clockwise from due North. Ranges from 0 to 2pi"""
        self.elevation_rad: float = elevation_rad
        """The angular elevation of the observation in radians. Measured from the horizon to the zenith. -pi/4=nadir, 0=horizon, pi/4=zenith."""
        self.range_km: float = range_km
        """Distance between the spacecraft and the observer at the time of observation. Measured in km."""
        self.range_rate_km_p_sec: float = range_rate_km_p_sec
        """The change in range over time dr/dt. Measured in km/sec."""
        self._measurement: Measurement | None = None
        self.measurement = measurement
        """The measurement associated with the observation, of type :class:`.Measurement`"""

    @classmethod
    def fromMeasurement(  # noqa: PLR0913
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
        r"""Alternative constructor for creating observation objects. Builds an instance of :class:`.Observation` from an instance of :class:`.Measurement`."""
        utc_datetime = julianDateToDatetime(JulianDate(epoch_jd))
        return cls(
            julian_date=epoch_jd,
            target_id=target_id,
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            sensor_eci=sensor_eci,
            measurement=measurement,
            **measurement.calculateMeasurement(
                sensor_eci,
                tgt_eci_state,
                utc_datetime,
                noisy=noisy,
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
            ],
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

    julian_date: Mapped[float] = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    """Contains all the julian dates, which are of type ``float``."""
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)
    """ Defines the epoch associated with the observation data. Many to one relation with :class:`.Epoch`"""

    sensor_id: Mapped[int] = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """Contains all the sensor id numbers, which are of type ``int``"""
    sensor = relationship("AgentModel", foreign_keys=[sensor_id], lazy="joined", innerjoin=True)
    """ Defines the associated sensor agent with the observation data. Many to one relation with :class:`.AgentModel`"""

    target_id: Mapped[int] = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """Contains all the target id numbers, which are of type ``int``"""
    target = relationship(
        "AgentModel",
        foreign_keys=[target_id],
        lazy="joined",
        innerjoin=True,
    )
    """ Defines the associated target agent with the observation data. Many to one relation with :class:`.AgentModel`."""

    reason: Mapped[str] = Column(String, nullable=False)
    """True reason why observation was missed, for debugging only!"""

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
        self.julian_date: float = float(julian_date)
        """The Julian Date of the observation."""
        self.sensor_id: int = sensor_id
        """The id number of the sensor."""
        self.target_id: int = target_id
        """The id number of the target."""
        self.sensor_type: str = (
            sensor_type  # Will likely need to check at some point that len(sensor_type) is shorther than 128...
        )
        """The sensor type. Must be shorter than 128 characters"""
        self.pos_x_km: float = sensor_eci[0]
        """The x-coordinate in cartesian space in the ECI frame. Measured in km."""
        self.pos_y_km: float = sensor_eci[1]
        """The y-coordinate in cartesian space in the ECI frame. Measured in km."""
        self.pos_z_km: float = sensor_eci[2]
        """The z-coordinate in cartesian space in the ECI frame. Measured in km."""
        self.vel_x_km_p_sec: float = sensor_eci[3]
        """The x-component of the cartesian velocity vectory in the ECI frame. Measured in km/sec."""
        self.vel_y_km_p_sec: float = sensor_eci[4]
        """The y-component of the cartesian velocity vectory in the ECI frame. Measured in km/sec."""
        self.vel_z_km_p_sec: float = sensor_eci[5]
        """The z-component of the cartesian velocity vectory in the ECI frame. Measured in km/sec."""
        self.reason: str = reason
        """ The reason why the observation was missed. Used for debug reasons."""
