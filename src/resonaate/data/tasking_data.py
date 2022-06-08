# Standard Library Imports
# Third Party Imports
from sqlalchemy import Column, Integer, Float, Boolean, String
# RESONAATE Imports
from . import Base, _DataMixin


class TaskingData(Base, _DataMixin):
    """Represents tasking information in database."""

    __tablename__ = 'tasking_data'

    id = Column(Integer, primary_key=True)  # noqa: A003

    # Julian date corresponding to the time the observation was made
    julian_date = Column(Float, index=True)

    # Human readable version of the `julian_date`
    timestampISO = Column(String())

    # Satellite number of the observed target
    target_id = Column(Integer)

    # Satellite number of the observing sensor
    sensor_id = Column(Integer)

    # Type of the visibility matrix value
    visibility = Column(Boolean)

    # Type of the reward matrix value
    reward = Column(Float)

    # Type of the decision matrix value
    decision = Column(Boolean)

    MUTABLE_COLUMN_NAMES = ("julian_date", "timestampISO", "target_id", "sensor_id",
                            "visibility", "reward", "decision")
