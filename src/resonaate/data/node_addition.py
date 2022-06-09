# Standard Library Imports
# Third Party Imports
from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
# RESONAATE Imports
from . import Base, _DataMixin


class NodeAddition(Base, _DataMixin):
    """DB entry for adding a new node after scenario start."""

    __tablename__ = 'node_additions'
    id = Column(Integer, primary_key=True)  # noqa: A003

    ## Defines agent to add into the simulation
    # Many to one relation with :class:`.Agent`
    agent_id = Column(Integer, ForeignKey('agents.unique_id'), nullable=False)
    agent = relationship("Agent", lazy='joined', innerjoin=True)

    ## Epoch for when this prioritization should start
    # Many to one relation with :class:`.Epoch`
    start_time_jd = Column(Integer, ForeignKey('epochs.julian_date'), index=True)
    start_time = relationship("Epoch", lazy='joined', innerjoin=True)

    ## Cartesian x-coordinate for inertial satellite location in ECI frame
    pos_x_km = Column(Float)

    ## Cartesian y-coordinate for inertial satellite location in ECI frame
    pos_y_km = Column(Float)

    ## Cartesian z-coordinate for inertial satellite location in ECI frame
    pos_z_km = Column(Float)

    ## Cartesian x-coordinate for inertial satellite velocity in ECI frame
    vel_x_km_p_sec = Column(Float)

    ## Cartesian y-coordinate for inertial satellite velocity in ECI frame
    vel_y_km_p_sec = Column(Float)

    ## Cartesian z-coordinate for inertial satellite velocity in ECI frame
    vel_z_km_p_sec = Column(Float)

    MUTABLE_COLUMN_NAMES = (
        'agent_id', 'start_time',
        'pos_x_km', 'pos_y_km', 'pos_z_km',
        'vel_x_km_p_sec', 'vel_y_km_p_sec', 'vel_z_km_p_sec'
    )

    @classmethod
    def fromECIVector(cls, **kwargs):
        """Construct an :class:`.NodeAddition` object using a different format of keyword arguments.

        An `eci` keyword is provided as a 6x1 vector instead of the `pos[dimension]` and
        `vel[dimension]` keywords.
        """
        assert kwargs.get("eci") is not None, "[NodeAddition.fromECI()] Missing keyword argument 'eci'."

        # Parse state vector into separate columns, one for each element
        kwargs["pos_x_km"] = kwargs["eci"][0]
        kwargs["pos_y_km"] = kwargs["eci"][1]
        kwargs["pos_z_km"] = kwargs["eci"][2]
        kwargs["vel_x_km_p_sec"] = kwargs["eci"][3]
        kwargs["vel_y_km_p_sec"] = kwargs["eci"][4]
        kwargs["vel_z_km_p_sec"] = kwargs["eci"][5]

        # Remove state vector from kwargs
        del kwargs["eci"]

        return cls(**kwargs)

    @property
    def eci(self):
        """``list``: returns the formatted ECI state vector."""
        return [
            self.pos_x_km, self.pos_y_km, self.pos_z_km,
            self.vel_x_km_p_sec, self.vel_y_km_p_sec, self.vel_z_km_p_sec
        ]
