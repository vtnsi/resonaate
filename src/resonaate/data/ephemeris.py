"""Defines `Ephemeris` data table classes."""

from __future__ import annotations

# Third Party Imports
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, relationship

# Local Imports
from .table_base import Base, _DataMixin


class _EphemerisMixin(_DataMixin):
    """Data Columns applicable to both Truth and Estimate Ephemeris Tables."""

    id: Mapped[int] = Column(Integer, primary_key=True)
    """``int``: The Epheremis id number."""

    pos_x_km: Mapped[float] = Column(Float)
    """``float``: Cartesian x-coordinate for inertial satellite location in ECI frame in kilometers."""

    pos_y_km: Mapped[float] = Column(Float)
    """``float``: Cartesian y-coordinate for inertial satellite location in ECI frame in kilometers."""

    pos_z_km: Mapped[float] = Column(Float)
    """``float``: Cartesian z-coordinate for inertial satellite location in ECI frame in kilometers."""

    vel_x_km_p_sec: Mapped[float] = Column(Float)
    """``float``: Cartesian x-coordinate for inertial satellite velocity in ECI frame in kilometers per second."""

    vel_y_km_p_sec: Mapped[float] = Column(Float)
    """``float``: Cartesian y-coordinate for inertial satellite velocity in ECI frame in kilometers per second."""

    vel_z_km_p_sec: Mapped[float] = Column(Float)
    """``float``: Cartesian z-coordinate for inertial satellite velocity in ECI frame in kilometers per second."""

    @property
    def eci(self) -> list:
        """``list``: returns formatted ECI state vector. First three elements are position (x, y z), last three are velocity (vx, vy, vz). All are measured in km, or km/s, respectively."""
        return [
            self.pos_x_km,
            self.pos_y_km,
            self.pos_z_km,
            self.vel_x_km_p_sec,
            self.vel_y_km_p_sec,
            self.vel_z_km_p_sec,
        ]


class TruthEphemeris(Base, _EphemerisMixin):
    """Snapshot of truth ephemeris in time."""

    __tablename__ = "truth_ephemerides"

    julian_date: Mapped[float] = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    """``float``: Julian date associated with the epheremis."""
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)
    """Defines the epoch associated with the given data. Many to one relation with :class:`.Epoch`."""

    agent_id: Mapped[int] = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """``int``: The agent id number."""
    agent = relationship("AgentModel", lazy="joined", innerjoin=True)
    """Many to one relation with :class:`.AgentModel`."""

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "agent_id",
        "pos_x_km",
        "pos_y_km",
        "pos_z_km",
        "vel_x_km_p_sec",
        "vel_y_km_p_sec",
        "vel_z_km_p_sec",
    )

    @classmethod
    def fromECIVector(cls, **kwargs):
        """Construct an :class:`.EphemerisMixin` object using a different format of keyword arguments.

        An `eci` keyword is provided as a 6x1 vector instead of the `pos[dimension]` and
        `vel[dimension]` keywords.
        """
        if kwargs.get("eci") is None:
            raise KeyError("[Ephemeris.fromECIArray()] Missing keyword argument 'eci'.")

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


class EstimateEphemeris(Base, _EphemerisMixin):
    """Snapshot of estimate ephemeris in time."""

    __tablename__ = "estimate_ephemerides"

    julian_date: Mapped[float] = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    """``float``: The asscoiated julian date."""
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)
    """Defines the epoch associated with the given data. Many to one relation with :class:`.Epoch`"""

    agent_id: Mapped[int] = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """``int``: The agent id number."""
    agent = relationship("AgentModel", lazy="joined", innerjoin=True)
    """Many to one relation with :class:`.AgentModel`."""

    source: Mapped[str] = Column(String, nullable=False)
    """``str``: Source of Estimate (Observation or Propagation)."""

    # 6x6 Covariance Matrix
    # Row 0
    covar_00 = Column(Float)
    covar_01 = Column(Float)
    covar_02 = Column(Float)
    covar_03 = Column(Float)
    covar_04 = Column(Float)
    covar_05 = Column(Float)
    # Row 1
    covar_10 = Column(Float)
    covar_11 = Column(Float)
    covar_12 = Column(Float)
    covar_13 = Column(Float)
    covar_14 = Column(Float)
    covar_15 = Column(Float)
    # Row 2
    covar_20 = Column(Float)
    covar_21 = Column(Float)
    covar_22 = Column(Float)
    covar_23 = Column(Float)
    covar_24 = Column(Float)
    covar_25 = Column(Float)
    # Row 3
    covar_30 = Column(Float)
    covar_31 = Column(Float)
    covar_32 = Column(Float)
    covar_33 = Column(Float)
    covar_34 = Column(Float)
    covar_35 = Column(Float)
    # Row 4
    covar_40 = Column(Float)
    covar_41 = Column(Float)
    covar_42 = Column(Float)
    covar_43 = Column(Float)
    covar_44 = Column(Float)
    covar_45 = Column(Float)
    # Row 5
    covar_50 = Column(Float)
    covar_51 = Column(Float)
    covar_52 = Column(Float)
    covar_53 = Column(Float)
    covar_54 = Column(Float)
    covar_55 = Column(Float)

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "agent_id",
        "source",
        "pos_x_km",
        "pos_y_km",
        "pos_z_km",
        "vel_x_km_p_sec",
        "vel_y_km_p_sec",
        "vel_z_km_p_sec",
        "covar_00",
        "covar_01",
        "covar_02",
        "covar_03",
        "covar_04",
        "covar_05",
        "covar_10",
        "covar_11",
        "covar_12",
        "covar_13",
        "covar_14",
        "covar_15",
        "covar_20",
        "covar_21",
        "covar_22",
        "covar_23",
        "covar_24",
        "covar_25",
        "covar_30",
        "covar_31",
        "covar_32",
        "covar_33",
        "covar_34",
        "covar_35",
        "covar_40",
        "covar_41",
        "covar_42",
        "covar_43",
        "covar_44",
        "covar_45",
        "covar_50",
        "covar_51",
        "covar_52",
        "covar_53",
        "covar_54",
        "covar_55",
    )

    @classmethod
    def fromCovarianceMatrix(cls, **kwargs):
        """Construct an :class:`.EstimateEphemeris` object using a different format of keyword arguments.

        A `covariance` keyword is provided as a 6x6 matrix instead of the `covar_[]` keywords.
        """
        if kwargs.get("covariance") is None:
            raise KeyError(
                "[Ephemeris.fromCovarianceMatrix()] Missing keyword argument 'covariance'.",
            )

        # Parse covariance matrix into separate columns, one for each matrix element
        kwargs["covar_00"] = kwargs["covariance"][0][0]
        kwargs["covar_01"] = kwargs["covariance"][0][1]
        kwargs["covar_02"] = kwargs["covariance"][0][2]
        kwargs["covar_03"] = kwargs["covariance"][0][3]
        kwargs["covar_04"] = kwargs["covariance"][0][4]
        kwargs["covar_05"] = kwargs["covariance"][0][5]
        kwargs["covar_10"] = kwargs["covariance"][1][0]
        kwargs["covar_11"] = kwargs["covariance"][1][1]
        kwargs["covar_12"] = kwargs["covariance"][1][2]
        kwargs["covar_13"] = kwargs["covariance"][1][3]
        kwargs["covar_14"] = kwargs["covariance"][1][4]
        kwargs["covar_15"] = kwargs["covariance"][1][5]
        kwargs["covar_20"] = kwargs["covariance"][2][0]
        kwargs["covar_21"] = kwargs["covariance"][2][1]
        kwargs["covar_22"] = kwargs["covariance"][2][2]
        kwargs["covar_23"] = kwargs["covariance"][2][3]
        kwargs["covar_24"] = kwargs["covariance"][2][4]
        kwargs["covar_25"] = kwargs["covariance"][2][5]
        kwargs["covar_30"] = kwargs["covariance"][3][0]
        kwargs["covar_31"] = kwargs["covariance"][3][1]
        kwargs["covar_32"] = kwargs["covariance"][3][2]
        kwargs["covar_33"] = kwargs["covariance"][3][3]
        kwargs["covar_34"] = kwargs["covariance"][3][4]
        kwargs["covar_35"] = kwargs["covariance"][3][5]
        kwargs["covar_40"] = kwargs["covariance"][4][0]
        kwargs["covar_41"] = kwargs["covariance"][4][1]
        kwargs["covar_42"] = kwargs["covariance"][4][2]
        kwargs["covar_43"] = kwargs["covariance"][4][3]
        kwargs["covar_44"] = kwargs["covariance"][4][4]
        kwargs["covar_45"] = kwargs["covariance"][4][5]
        kwargs["covar_50"] = kwargs["covariance"][5][0]
        kwargs["covar_51"] = kwargs["covariance"][5][1]
        kwargs["covar_52"] = kwargs["covariance"][5][2]
        kwargs["covar_53"] = kwargs["covariance"][5][3]
        kwargs["covar_54"] = kwargs["covariance"][5][4]
        kwargs["covar_55"] = kwargs["covariance"][5][5]

        # Remove covariance from kwargs
        del kwargs["covariance"]

        # Parse state vector into separate columns, one for each element
        if kwargs.get("eci") is None:
            raise KeyError("[Ephemeris.fromCovarianceMatrix()] Missing keyword argument 'eci'.")

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
    def covariance(self):
        """``list``: returns formatted covariance matrix."""
        return [
            [
                self.covar_00,
                self.covar_01,
                self.covar_02,
                self.covar_03,
                self.covar_04,
                self.covar_05,
            ],
            [
                self.covar_10,
                self.covar_11,
                self.covar_12,
                self.covar_13,
                self.covar_14,
                self.covar_15,
            ],
            [
                self.covar_20,
                self.covar_21,
                self.covar_22,
                self.covar_23,
                self.covar_24,
                self.covar_25,
            ],
            [
                self.covar_30,
                self.covar_31,
                self.covar_32,
                self.covar_33,
                self.covar_34,
                self.covar_35,
            ],
            [
                self.covar_40,
                self.covar_41,
                self.covar_42,
                self.covar_43,
                self.covar_44,
                self.covar_45,
            ],
            [
                self.covar_50,
                self.covar_51,
                self.covar_52,
                self.covar_53,
                self.covar_54,
                self.covar_55,
            ],
        ]
