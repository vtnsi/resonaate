"""Defines the :class:`.Task` data table class."""

from __future__ import annotations

# Third Party Imports
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

# Local Imports
from .table_base import Base, _DataMixin


class Task(Base, _DataMixin):
    """Represents and contains sensor tasking information in the database."""

    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    """An instance of :class:`sqlalchemy.Column`. Contains all the task id numbers, which are of type ``int``"""

    julian_date = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    """An instance of :class:`sqlalchemy.Column`. Contains all the julian dates, which are of type ``float``."""
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)
    """Defines the epoch associated with the observation data. Many to one relation with :class:`.Epoch`"""

    sensor_id = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """An instance of :class:`sqlalchemy.Column`. Contains all the sensor id numbers, which are of type ``int``"""
    sensor = relationship("AgentModel", foreign_keys=[sensor_id], lazy="joined", innerjoin=True)
    """Defines the associated sensor agent with the task data. Many to one relation with :class:`.AgentModel`"""

    target_id = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """An instance of :class:`sqlalchemy.Column`. Contains all the target id numbers, which are of type ``int``"""
    target = relationship("AgentModel", foreign_keys=[target_id], lazy="joined", innerjoin=True)
    """Defines the associated target agent with the task data. Many to one relation with :class:`.AgentModel`"""

    visibility = Column(Boolean)
    """An instance of :class:`sqlalchemy.Column`. Contains information regarding whether or not a target is visible to the sensor,
    elements of this column are of type ``bool``."""

    reward = Column(Float)
    """An instance of :class:`sqlalchemy.Column`. Contains the scalar reward matrix value. Elements are of type ``float``."""

    decision = Column(Boolean)
    """An instance of :class:`sqlalchemy.Column`. Contains decision data, of type ``bool``, on whether or not the sensor will observe the target"""

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "sensor_id",
        "target_id",
        "visibility",
        "reward",
        "decision",
    )
