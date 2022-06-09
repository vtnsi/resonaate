# Standard Library Imports
# Third Party Imports
from sqlalchemy import Column, Integer, String
# RESONAATE Imports
from . import Base, _DataMixin


class Agent(Base, _DataMixin):
    """Generic agent DB table."""

    __tablename__ = "agents"

    ## NORAD Catalog Number or Simulation ID
    unique_id = Column(Integer, primary_key=True, unique=True, nullable=False, index=True)

    ## Describes satellite associated with NORAD number
    # Corresponds to a valid Space Track "SATNAME" field.
    name = Column(String(128), nullable=False)

    MUTABLE_COLUMN_NAMES = (
        'unique_id', 'name',
    )
