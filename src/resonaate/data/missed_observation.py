"""Defines the :class:`.MissedObservation` data table class."""
from __future__ import annotations

# Standard Library Imports
from enum import Enum, unique

# Third Party Imports
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

# Local Imports
from . import Base, _DataMixin


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

    # South component of SEZ vector describing observation in kilometers
    sez_state_s_km = Column(Float)

    # East component of SEZ vector describing observation in kilometers
    sez_state_e_km = Column(Float)

    # Zenith component of SEZ vector describing observation in kilometers
    sez_state_z_km = Column(Float)

    # Latitude of observing sensor in radians
    position_lat_rad = Column(Float)

    # Longitude of observing sensor in radians
    position_lon_rad = Column(Float)

    # Altitude of observing sensor in kilometers
    position_altitude_km = Column(Float)

    # True reason why observation was missed, for debugging only!
    reason = Column(String, nullable=False)

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "sensor_id",
        "target_id",
        "sensor_type",
        "sez_state_s_km",
        "sez_state_e_km",
        "sez_state_z_km",
        "position_lat_rad",
        "position_lon_rad",
        "position_altitude_km",
        "reason",
    )

    @property
    def lla(self):
        """``list``: Three element coordinate vector in the LLA frame."""
        return [self.position_lat_rad, self.position_lon_rad, self.position_altitude_km]

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
