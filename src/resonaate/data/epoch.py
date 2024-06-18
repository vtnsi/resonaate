"""Defines the :class:`.Epoch` data table class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from sqlalchemy import Column, Float, Integer, String

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped

# Local Imports
from .table_base import Base, _DataMixin


class Epoch(Base, _DataMixin):
    """Epoch time data table for tracking Julian date, timestamp tuples."""

    __tablename__ = "epochs"

    id: Mapped[int] = Column(Integer, primary_key=True)
    """Contains epoch ids, of type ``int``."""

    timestampISO: Mapped[str] = Column(String, unique=True, nullable=False)  # noqa: N815
    """ Defines the human readable version of the `julian_date`"""
    # [NOTE]: We may want to transfer this to a property or function, or to
    #   add new columns for year, day, month, hour, minute, second columns

    ## Defines the epoch associated with the given data
    # i.e. when this data is provided
    julian_date: Mapped[float] = Column(Float, index=True, unique=True, nullable=False)
    """Contains all the julian dates, which are of type ``float``."""

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "timestampISO",
    )
