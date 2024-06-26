"""Defines the :class:`.DetectedManeuver` data table class."""

from __future__ import annotations

# Third Party Imports
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, relationship

# Local Imports
from .table_base import Base, _DataMixin


class DetectedManeuver(Base, _DataMixin):
    """Snapshot of maneuver detection."""

    __tablename__ = "detected_maneuvers"
    id: Mapped[int] = Column(Integer, primary_key=True)
    """``int``: The id number of the detected maneuver."""

    julian_date: Mapped[float] = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    """``float``: The associated julian date."""
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)
    """Defines the epoch associated with the maneuver detection data. Many to one relation with :class:`.Epoch`."""

    # [FIXME]: Lazy way to implement multiple sensor IDs before moving to postgres
    sensor_ids: Mapped[str] = Column(String, nullable=False)
    """``str``: Defines the associated sensor agent with the observation data."""
    # sensor = relationship("AgentModel", lazy="joined", innerjoin=True)
    # Many to one relation with :class:`.AgentModel`

    target_id: Mapped[int] = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """``int``: The id number of the target."""
    target = relationship("AgentModel", lazy="joined", innerjoin=True)
    """Defines the associated target agent with the observation data. Many to one relation with :class:`.AgentModel`."""

    nis: Mapped[float] = Column(Float, nullable=False)
    """``float``: NIS at the time of the maneuver detection."""

    method: Mapped[str] = Column(String(128), nullable=False)
    """``str``: Method used to detect the maneuver. Max length of 128 characters."""

    metric: Mapped[float] = Column(Float, nullable=False)
    """``float``: Maneuver metric at the time of the maneuver detection."""

    threshold: Mapped[float] = Column(Float, nullable=False)
    """``float``: Threshold which the maneuver was tested against."""

    # [FIXME]: Lazy way to implement multiple sensor IDs before moving to postgres
    @property
    def sensor_list(self) -> list[int]:
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
