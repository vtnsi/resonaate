"""Defines the :class:`.Observation` data table class."""
# Third Party Imports
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

# Local Imports
from . import Base, _DataMixin


class Observation(Base, _DataMixin):
    """Represents singular observation information in database."""

    __tablename__ = "observations"
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

    # Observed azimuth of target from observing sensor in radians
    azimuth_rad = Column(Float)

    # Observed elevation of target from observing sensor in radians
    elevation_rad = Column(Float)

    # Observed range of target from observing sensor in kilometers
    range_km = Column(Float, nullable=True)

    # Observed range rate of target from observing sensor in kilometers per second
    range_rate_km_p_sec = Column(Float, nullable=True)

    # South component of SEZ vector describing observation in kilometers
    sez_state_s_km = Column(Float)

    # East component of SEZ vector describing observation in kilometers
    sez_state_e_km = Column(Float)

    # Zenith component of SEZ vector describing observation in kilometers
    sez_state_z_km = Column(Float)

    # Latitude of observing sensor in radians
    position_lat_rad = Column(Float)

    # Longitude of observing sensor in radians
    position_long_rad = Column(Float)

    # Altitude of observing sensor in kilometers
    position_altitude_km = Column(Float)

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "sensor_id",
        "target_id",
        "sensor_type",
        "azimuth_rad",
        "elevation_rad",
        "range_km",
        "range_rate_km_p_sec",
        "sez_state_s_km",
        "sez_state_e_km",
        "sez_state_z_km",
        "position_lat_rad",
        "position_long_rad",
        "position_altitude_km",
    )

    @classmethod
    def fromSEZVector(cls, **kwargs):
        """Construct an :class:`.EphemerisMixin` object using a different format of keyword arguments.

        An `eci` keyword is provided as a 6x1 vector instead of the `pos[dimension]` and
        `vel[dimension]` keywords.
        """
        assert (
            kwargs.get("sez") is not None
        ), "[Ephemeris.fromSEZVector()] Missing keyword argument 'xSEZ'."

        # Parse SEZ position vector into separate columns
        kwargs["sez_state_s_km"] = kwargs["sez"][0]
        kwargs["sez_state_e_km"] = kwargs["sez"][1]
        kwargs["sez_state_z_km"] = kwargs["sez"][2]

        # Delete SEZ position vector form kwargs
        del kwargs["sez"]

        msg = "[Ephemeris.fromSEZVector()] Missing keyword argument 'sensor_position'."
        assert kwargs.get("sensor_position") is not None, msg

        # Parse SEZ position vector into separate columns
        kwargs["position_lat_rad"] = kwargs["sensor_position"][0]
        kwargs["position_long_rad"] = kwargs["sensor_position"][1]
        kwargs["position_altitude_km"] = kwargs["sensor_position"][2]

        # Delete SEZ position vector form kwargs
        del kwargs["sensor_position"]

        return cls(**kwargs)

    @property
    def sez(self):
        """``list``: Three element coordinate vector in the SEZ frame."""
        return [self.sez_state_s_km, self.sez_state_e_km, self.sez_state_z_km]

    @property
    def measurements(self):
        """``list``: Vector containing available components of [azimuth, elevation, range, rangeRate]."""
        if self.range_rate_km_p_sec and self.range_km:
            return [self.azimuth_rad, self.elevation_rad, self.range_km, self.range_rate_km_p_sec]

        return [self.azimuth_rad, self.elevation_rad]
