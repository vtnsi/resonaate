"""Calculate Earth Orientation Parameters (EOPs).

This module is for calculating values of EOPs for different dates. This was split out from the
reductions.py module for later expansion/customization of how this works.
"""
from __future__ import annotations

# Standard Library Imports
import datetime
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import TYPE_CHECKING

# Local Imports
from ...common.utilities import loadDatFile
from .. import constants as const

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from pathlib import Path


EOP_MODULE: str = "resonaate.physics.data.eop"
"""``str``: defines EOP data module location."""


DEFAULT_EOP_DATA: str = "EOPdata.dat"
"""``str``: defines default EOP data file."""


@dataclass(frozen=True)
class EarthOrientationParameter:
    """Data class to define EOP-type data used internally in RESONAATE."""

    # Defines the year, month, & date associated with the given data
    date: datetime.date

    # Polar motion angles (arcseconds)
    x_p: float
    y_p: float

    # Nutation correction terms (arcseconds)
    #   Enforce consistency with GCRF coordinates
    d_delta_psi: float
    d_delta_eps: float

    # Difference between UTC and UT1 (seconds)
    delta_ut1: float

    # Instantaneous rate of change of UT1 w.r.t UTC (seconds)
    length_of_day: float

    # Difference in atomic time w.r.t UTC, via leap seconds (seconds)
    delta_atomic_time: int

    # Catalog the source of the EOP data
    # source: str


@lru_cache(maxsize=5)
def getEarthOrientationParameters(
    eop_date: datetime.date, filename: str | Path | None = None
) -> EarthOrientationParameter:
    """Return the :class:`.EarthOrientationParameter` based on the current calendar date.

    Args:
        eop_date (``datetime.date``): date at which to get EOP values
        filename (``str``, optional): path to EOP dat file. Default is ``None``, which results in
            the physics/data/EOPdata.dat being used.

    Note:
        This function is cached so repeated calls shouldn't need to re-read the file.

    See Also:
        Default values obtained from Celestrak.com

    Returns:
        :class:`.EarthOrientationParameter`: corresponding EOP values
    """
    # Load EOPS into dictionary
    eop_dict = _readEOPFile(filename=filename)

    # Grab correct EOP set from dict
    return eop_dict[eop_date]


@lru_cache(maxsize=5)
def _readEOPFile(
    filename: str | Path | None = None,
) -> dict[datetime.date, EarthOrientationParameter]:
    """Read EOPs from a file and return them as a formatted ``dict``.

    Args:
        filename (``str``, optional): path to EOP dat file. Default is ``None``, which results in
            the physics/data/EOPdata.dat being used.

    Note:
        This function is cached so repeated calls shouldn't need to re-read the file.

    See Also:
        Default values obtained from Celestrak.com

    Returns:
        ``dict``: keys are ``datetime.date`` and values are :class:`.EarthOrientationParameter`
    """
    # Load raw data from file
    if filename is None:
        with resources.path(EOP_MODULE, DEFAULT_EOP_DATA) as file_resource:
            raw_data = loadDatFile(file_resource)
    else:
        raw_data = loadDatFile(filename)

    # Create dictionary of EOPs
    formatted_data = {}
    for eop in raw_data:
        eop_date = datetime.date(int(eop[0]), int(eop[1]), int(eop[2]))
        formatted_data[eop_date] = EarthOrientationParameter(
            date=eop_date,
            x_p=eop[4] * const.ARCSEC2RAD,
            y_p=eop[5] * const.ARCSEC2RAD,
            d_delta_psi=eop[8] * const.ARCSEC2RAD,
            d_delta_eps=eop[9] * const.ARCSEC2RAD,
            delta_ut1=eop[6],
            length_of_day=eop[7],
            delta_atomic_time=int(eop[12]),
        )

    return formatted_data
