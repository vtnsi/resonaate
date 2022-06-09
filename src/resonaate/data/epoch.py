"""Defines the :class:`.Epoch` data table class."""
# Third Party Imports
from sqlalchemy import Column, Float, Integer, String

# Local Imports
from . import Base, _DataMixin


class Epoch(Base, _DataMixin):
    """Epoch time data table for tracking Julian date, timestamp tuples."""

    __tablename__ = "epochs"

    id = Column(Integer, primary_key=True)  # noqa: A003

    ## Defines the human readable version of the `julian_date`
    timestampISO = Column(String, unique=True, nullable=False)
    # [NOTE]: We may want to transfer this to a property or function, or to
    #   add new columns for year, day, month, hour, minute, second columns

    ## Defines the epoch associated with the given data
    # i.e. when this data is provided
    julian_date = Column(Float, index=True, unique=True, nullable=False)

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "timestampISO",
    )
