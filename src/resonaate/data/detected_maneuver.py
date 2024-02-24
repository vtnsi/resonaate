"""Defines the :class:`.DetectedManeuver` data table class."""

from __future__ import annotations

# Third Party Imports
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

# Local Imports
from .table_base import Base, _DataMixin


class DetectedManeuver(Base, _DataMixin):
    """Snapshot of maneuver detection."""

    __tablename__ = "detected_maneuvers"
    id = Column(Integer, primary_key=True)

    ## Defines the epoch associated with the maneuver detection data
    # Many to one relation with :class:`.Epoch`
    julian_date = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)

    ## Defines the associated sensor agent with the observation data
    # Many to one relation with :class:`.AgentModel`
    # [FIXME]: Lazy way to implement multiple sensor IDs before moving to postgres
    sensor_ids = Column(String, nullable=False)

    ## Defines the associated target agent with the observation data
    # Many to one relation with :class:`.AgentModel`
    target_id = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    target = relationship("AgentModel", lazy="joined", innerjoin=True)

    # NIS at the time of the maneuver detection
    nis = Column(Float, nullable=False)

    # Method used to detect the maneuver
    method = Column(String(128), nullable=False)

    # Maneuver metric at the time of the maneuver detection
    metric = Column(Float, nullable=False)

    # Threshold which the maneuver was tested against
    threshold = Column(Float, nullable=False)

    # [FIXME]: Lazy way to implement multiple sensor IDs before moving to postgres
    @property
    def sensor_list(self):
        """Return string of maneuver detecting sensor IDs as a list of ints."""
        string_list = self.sensor_ids.split(sep=",")
        return [int(string) for string in string_list]

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "sensor_ids",
        "target_id",
        "nis",
        "method",
        "threshold",
    )
