# Standard Library Imports
import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class EarthOrientationParameter:
    """Data class to define EOP-type data used internally in RESONAATE."""

    date: datetime.date
    """datetime.date: Defines the year, month, & date associated with the given data."""

    x_p: float
    """float: Polar motion x coordinate (arcseconds)."""

    y_p: float
    """float: Polar motion y coordinate (arcseconds)."""

    d_delta_psi: float
    """float: Psi nutation correction term (arcseconds).
    
    Enforces consistency with GCRF coordinates.
    """

    d_delta_eps: float
    """float: Epsilon nutation correction term (arc seconds).
    
    Enforces consistency with GCRF coordinates.
    """

    delta_ut1: float
    """float: Difference between UTC and UT1 (seconds)."""

    length_of_day: float
    """float: Instantaneous rate of change of UT1 w.r.t UTC (seconds)."""

    delta_atomic_time: int
    """int: Difference in atomic time w.r.t UTC, via leap seconds (seconds)"""


class MissingEOP(Exception):
    """Error thrown when an EOP can't be found for a specified date."""


# Local Imports
# forward-facing API import
from .getter import getEarthOrientationParameters
