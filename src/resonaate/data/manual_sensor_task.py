# Standard Library Imports
# Third Party Imports
from sqlalchemy import Column, Integer, Float, Boolean
# RESONAATE Imports
from . import Base, _DataMixin


class ManualSensorTask(Base, _DataMixin):
    """Represent a manual sensor tasking object to insert into DB."""

    __tablename__ = 'sensor_tasks'

    id = Column(Integer, primary_key=True)  # noqa: A003

    # Satellite Number for target
    unique_id = Column(Integer)

    # Scalar that indicates how important it is that this target be observed
    priority = Column(Float)

    # Julian Date for when this prioritization should start
    start_time = Column(Float, index=True)

    # Julian Date for when this prioritization should end
    end_time = Column(Float)

    # Flag indicating whether this task is pre-canned or dynamically created
    is_dynamic = Column(Boolean)

    MUTABLE_COLUMN_NAMES = (
        'unique_id', 'priority', 'start_time', 'end_time', 'is_dynamic'
    )
