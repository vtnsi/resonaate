"""Defines the :class:`.MissedObservation` data table class."""
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
from ..physics.transforms.methods import ecef2lla, eci2ecef
from . import Base, _DataMixin

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


class MissedObservation(Base, _DataMixin):
    """Represents singular missed observation information in the database."""

    __tablename__ = "missed_observations"
    id = Column(Integer, primary_key=True)  # noqa: A003

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

    # Latitude of observing sensor in radians
    position_lat_rad = Column(Float)

    # Longitude of observing sensor in radians
    position_lon_rad = Column(Float)

    # Altitude of observing sensor in kilometers
    position_altitude_km = Column(Float)

    # True reason why observation was missed, for debugging only!
    reason = Column(String, nullable=False)

    # [TODO]: Make this align more with new Observation API

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "sensor_id",
        "target_id",
        "sensor_type",
        "position_lat_rad",
        "position_lon_rad",
        "position_altitude_km",
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
        self.julian_date = julian_date
        self.sensor_id = sensor_id
        self.target_id = target_id
        self.sensor_type = sensor_type
        self._sensor_eci = sensor_eci
        utc_datetime = julianDateToDatetime(JulianDate(julian_date))
        sensor_lla = ecef2lla(eci2ecef(sensor_eci, utc_datetime))
        self.position_lat_rad = sensor_lla[0]
        self.position_lon_rad = sensor_lla[1]
        self.position_altitude_km = sensor_lla[2]
        self.reason = reason

    @property
    def lla(self) -> ndarray:
        """``ndarray``: Three element coordinate vector in the LLA frame."""
        return array([self.position_lat_rad, self.position_lon_rad, self.position_altitude_km])

    @property
    def sensor_eci(self) -> ndarray:
        r"""``ndarray``: Returns the sensor's 6x1 ECI state vector at the time of observation."""
        return self._sensor_eci

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
