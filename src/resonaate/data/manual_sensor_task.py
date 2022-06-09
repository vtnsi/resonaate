# Standard Library Imports
# Third Party Imports
from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
# RESONAATE Imports
from . import Base, _DataMixin


class ManualSensorTask(Base, _DataMixin):
    """Represent a manual sensor tasking object to insert into DB."""

    __tablename__ = 'manual_sensor_tasks'
    id = Column(Integer, primary_key=True)  # noqa: A003

    ## Defines target on which to increase observation priority
    # Many to one relation with :class:`.Agent`
    target_id = Column(Integer, ForeignKey('agents.unique_id'), nullable=False)
    target = relationship("Agent", lazy='joined', innerjoin=True)

    ## Epoch for when this prioritization should start
    # Many to one relation with :class:`.Epoch`
    start_time_jd = Column(Integer, ForeignKey('epochs.julian_date'), index=True, nullable=False)
    start_time = relationship("Epoch", foreign_keys=[start_time_jd], lazy='joined', innerjoin=True)

    ## Epoch for when this prioritization should end
    # No relationship, because it might extend past current DB epoch entries
    end_time_jd = Column(Float, index=True, nullable=False)

    ## Scalar that indicates how important it is that this target be observed
    priority = Column(Float, nullable=False)

    ## Flag indicating whether this task is pre-canned or dynamically created
    is_dynamic = Column(Boolean, nullable=False)

    MUTABLE_COLUMN_NAMES = (
        'target_id', 'priority', 'start_time_jd', 'end_time_jd', 'is_dynamic'
    )
