"""Defines the :class:`~.agent.AgentModel` data table class."""

from __future__ import annotations

# Third Party Imports
from sqlalchemy import Column, Integer, String

# Local Imports
from .table_base import Base, _DataMixin


class AgentModel(Base, _DataMixin):
    """Generic agent DB table."""

    __tablename__ = "agents"

    unique_id = Column(Integer, primary_key=True, unique=True, nullable=False, index=True)
    """``int``: NORAD Catalog Number or Simulation ID."""

    name = Column(String(128), nullable=False)
    """``str``: Describes sattelite associated with NORAD number. Corresponds to a valid Space Track "SATNAME" field."""

    MUTABLE_COLUMN_NAMES = (
        "unique_id",
        "name",
    )
