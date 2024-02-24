"""Defines the :class:`.Task` data table class."""
from __future__ import annotations

# Third Party Imports
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

# Local Imports
from .table_base import Base, _DataMixin


class Task(Base, _DataMixin):
    """Represents tasking information in database."""

    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)

    ## Defines the epoch associated with the observation data
    # Many to one relation with :class:`.Epoch`
    julian_date = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)

    ## Defines the associated sensor agent with the task data
    # Many to one relation with :class:`.AgentModel`
    sensor_id = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    sensor = relationship("AgentModel", foreign_keys=[sensor_id], lazy="joined", innerjoin=True)

    ## Defines the associated target agent with the task data
    # Many to one relation with :class:`.AgentModel`
    target_id = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    target = relationship("AgentModel", foreign_keys=[target_id], lazy="joined", innerjoin=True)

    ## Boolean visibility value
    visibility = Column(Boolean)

    ## Scalar reward matrix value
    reward = Column(Float)

    ## Boolean decision value
    decision = Column(Boolean)

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "sensor_id",
        "target_id",
        "visibility",
        "reward",
        "decision",
    )
