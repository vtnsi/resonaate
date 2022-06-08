# Third Party Imports
from sqlalchemy import Column, Integer, Float, Date
# RESONAATE Imports
from . import Base, _DataMixin


class EarthOrientationParams(_DataMixin, Base):
    """EOP data table.

    Currently pulled from celestrak.com.
    """

    __tablename__ = "earth_orientation_params"

    id = Column(Integer, primary_key=True)  # noqa: A003

    # Defines the year, month, & date associated with the given data
    eop_date = Column(Date(), index=True)

    # Polar motion angles (arcseconds)
    x_p = Column(Float())
    y_p = Column(Float())

    # Nutation correction terms (arcseconds)
    #   Enforce consistency with GCRF coordinates
    d_delta_psi = Column(Float())
    d_delta_eps = Column(Float())

    # Difference between UTC and UT1 (seconds)
    delta_ut1 = Column(Float())

    # Instantaneous rate of change of UT1 w.r.t UTC (seconds)
    length_of_day = Column(Float())

    # Difference in atomice time w.r.t UTC, via leap seconds (seconds)
    delta_atomic_time = Column(Integer())

    MUTABLE_COLUMN_NAMES = (
        "eop_date", "x_p", "y_p",
        "d_delta_psi", "d_delta_eps",
        "delta_ut1", "length_of_day",
        "delta_atomic_time"
    )


class NutationParams(_DataMixin, Base):
    """Nutation correction coefficients.

    See Vallado Edition 4, Eqn 3-83
    """

    __tablename__ = "nutation_params"

    id = Column(Integer, primary_key=True)  # noqa: A003

    # Real coefficients (0.0001 arcseconds)
    a_i = Column(Float())
    b_i = Column(Float())
    c_i = Column(Float())
    d_i = Column(Float())

    # Integer coefficients (dimensionless?)
    a_n1_i = Column(Integer())
    a_n2_i = Column(Integer())
    a_n3_i = Column(Integer())
    a_n4_i = Column(Integer())
    a_n5_i = Column(Integer())

    @property
    def coefficients(self):
        """Public interface for retrieving coefficients."""
        return (
            [self.a_i, self.b_i, self.c_i, self.d_i],
            [self.a_n1_i, self.a_n2_i, self.a_n3_i, self.a_n4_i, self.a_n5_i]
        )

    MUTABLE_COLUMN_NAMES = (
        "a_i", "b_i", "c_i", "d_i", "a_n1_i", "a_n2_i", "a_n3_i", "a_n4_i", "a_n5_i"
    )
