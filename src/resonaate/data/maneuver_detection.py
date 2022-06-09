"""Defines the :class:`.ManeuverDetection` data table class."""
# Standard Library Imports
# Third Party Imports
from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
# RESONAATE Imports
from . import Base, _DataMixin


class ManeuverDetection(Base, _DataMixin):
    """Snapshot of maneuver detection."""

    __tablename__ = 'maneuver_detection'
    id = Column(Integer, primary_key=True)  # noqa: A003

    ## Defines the epoch associated with the maneuver detection data
    # Many to one relation with :class:`.Epoch`
    julian_date = Column(Float, ForeignKey('epochs.julian_date'), nullable=False)
    epoch = relationship("Epoch", lazy='joined', innerjoin=True)

    ## Defines the associated sensor agent with the observation data
    # Many to one relation with :class:`.Agent`
    sensor_id = Column(Integer, ForeignKey('agents.unique_id'), nullable=False)

    ## Defines the associated target agent with the observation data
    # Many to one relation with :class:`.Agent`
    target_id = Column(Integer, ForeignKey('agents.unique_id'), nullable=False)

    # NIS at the time of the maneuver detection
    nis = Column(Float, nullable=False)

    # Maneuver Gate at the time of the maneuver detection
    maneuver_gate = Column(Float, nullable=False)

    MUTABLE_COLUMN_NAMES = ("julian_date", "sensor_id", "target_id", "nis", "maneuver_gate")

    @classmethod
    def recordManeuverDetection(cls, **kwargs):
        """Construct an :class:`._DataMixin` object using a different format of keyword arguments."""
        return cls(**kwargs)
