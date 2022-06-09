# Standard Library Imports
# Third Party Imports
from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
# RESONAATE Imports
from . import Base, _DataMixin


class Task(Base, _DataMixin):
    """Represents tasking information in database."""

    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)  # noqa: A003

    ## Defines the epoch associated with the observation data
    # Many to one relation with :class:`.Epoch`
    julian_date = Column(Integer, ForeignKey('epochs.julian_date'), nullable=False)
    epoch = relationship("Epoch", lazy='joined', innerjoin=True)

    ## Defines the associated sensor agent with the task data
    # Many to one relation with :class:`.Agent`
    sensor_id = Column(Integer, ForeignKey('agents.unique_id'), nullable=False)
    sensor = relationship("Agent", foreign_keys=[sensor_id], lazy='joined', innerjoin=True)

    ## Defines the associated target agent with the task data
    # Many to one relation with :class:`.Agent`
    target_id = Column(Integer, ForeignKey('agents.unique_id'), nullable=False)
    target = relationship("Agent", foreign_keys=[target_id], lazy='joined', innerjoin=True)

    ## Boolean visibility value
    visibility = Column(Boolean)

    ## Scalar reward matrix value
    reward = Column(Float)

    ## Boolean decision value
    decision = Column(Boolean)

    MUTABLE_COLUMN_NAMES = (
        "julian_date", "sensor_id", "target_id", "visibility", "reward", "decision",
    )
