# Standard Library Imports
# Third Party Imports
from sqlalchemy import Column, Integer, Float, String
# RESONAATE Imports
from . import Base, _DataMixin


class NodeAddition(Base, _DataMixin):
    """DB entry for adding a new node after scenario start."""

    __tablename__ = 'node_additions'

    id = Column(Integer, primary_key=True)  # noqa: A003

    # SATCAT / Simulation ID for target
    unique_id = Column(Integer)

    # Name of target agent
    name = Column(String(128))

    # Julian Date for when this prioritization should start
    start_time = Column(Float)

    ## Cartesian x-coordinate for inertial satellite location in ECI frame
    pos_x_km = Column(Float())

    ## Cartesian y-coordinate for inertial satellite location in ECI frame
    pos_y_km = Column(Float())

    ## Cartesian z-coordinate for inertial satellite location in ECI frame
    pos_z_km = Column(Float())

    ## Cartesian x-coordinate for inertial satellite velocity in ECI frame
    vel_x_km_p_sec = Column(Float())

    ## Cartesian y-coordinate for inertial satellite velocity in ECI frame
    vel_y_km_p_sec = Column(Float())

    ## Cartesian z-coordinate for inertial satellite velocity in ECI frame
    vel_z_km_p_sec = Column(Float())

    MUTABLE_COLUMN_NAMES = (
        'unique_id', 'name', 'start_time',
        'pos_x_km', 'pos_y_km', 'pos_z_km',
        'vel_x_km_p_sec', 'vel_y_km_p_sec', 'vel_z_km_p_sec'
    )

    @property
    def eci(self):
        """``list``: returns the formatted ECI state vector."""
        return [
            self.pos_x_km, self.pos_y_km, self.pos_z_km,
            self.vel_x_km_p_sec, self.vel_y_km_p_sec, self.vel_z_km_p_sec
        ]
