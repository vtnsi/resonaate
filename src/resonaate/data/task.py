"""Defines the :class:`.Task` data table class."""

from __future__ import annotations

# Third Party Imports
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, relationship

# Local Imports
from .table_base import Base, _DataMixin


class Task(Base, _DataMixin):
    """Represents and contains sensor tasking information in the database."""

    __tablename__ = "tasks"
    id: Mapped[int] = Column(Integer, primary_key=True)
    """``int``: Contains all the task id numbers."""

    julian_date: Mapped[float] = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    """``float``: Contains all the julian dates."""
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)
    """Defines the epoch associated with the observation data. Many to one relation with :class:`.Epoch`"""

    sensor_id: Mapped[int] = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """``int``: Contains the sensor id numbers."""
    sensor = relationship("AgentModel", foreign_keys=[sensor_id], lazy="joined", innerjoin=True)
    """Defines the associated sensor agent with the task data. Many to one relation with :class:`.AgentModel`"""

    target_id: Mapped[int] = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """``int``: Contains all the target id numbers."""
    target = relationship(
        "AgentModel",
        foreign_keys=[target_id],
        lazy="joined",
        innerjoin=True,
    )
    """Defines the associated target agent with the task data. Many to one relation with :class:`.AgentModel`"""

    visibility: Mapped[bool] = Column(Boolean)
    """``bool``: Contains information regarding whether or not a target is visible to the sensor."""

    reward: Mapped[float] = Column(Float)
    """``float``: Contains the scalar reward matrix value."""

    decision: Mapped[bool] = Column(Boolean)
    """``bool``: Contains decision data on whether or not the sensor will observe the target"""

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "sensor_id",
        "target_id",
        "visibility",
        "reward",
        "decision",
    )
