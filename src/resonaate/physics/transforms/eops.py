"""Calculate Earth Orientation Parameters (EOPs).

This module is for calculating values of EOPs for different dates. This was split out from the
reductions.py module for later expansion/customization of how this works.
"""

from __future__ import annotations

# Standard Library Imports
import datetime
import os
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from urllib.request import urlretrieve

# Local Imports
from ...common.behavioral_config import BehavioralConfig
from ...common.utilities import loadDatFile
from .. import constants as const

EOP_MODULE: str = "resonaate.physics.data.eop"
"""``str``: defines EOP data module location."""


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
    eop_date: datetime.date,
    filename: str | Path | None = None,
) -> EarthOrientationParameter:
    """Return the :class:`.EarthOrientationParameter` based on the current calendar date.

    Args:
        eop_date (``datetime.date``): date at which to get EOP values
        filename (``str``, optional): path to EOP dat file. Default is ``None``, which results in
            the default path in the Behavioral Config being used

    Note:
        This function is cached so repeated calls shouldn't need to re-read the file.
        If enabled in the Behavioral Config, this function will also update the EOP data
        file.

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
        datafile: str = BehavioralConfig.getConfig().eop.DataPath
        res = resources.files(EOP_MODULE).joinpath(datafile)
        with resources.as_file(res) as file_resource:
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


def updateEOPData(overwrite: bool = False) -> None:
    """Updates the EOP data file defined in the :class:`BehavioralConfig` object.

    Args:
        overwrite(``bool``, optional): Check to completely overwrite existing EOP data file. Seting to False will
            instead append new EOP data to existing EOP data. Default is ``False``.
    """
    config = BehavioralConfig.getConfig()
    url: str = config.eop.RemoteURL
    eop_file: str = config.eop.DataPath
    eop_temp_name: str = "new_EOP.dat"

    parent_path = os.path.join(
        str(Path(__file__).parents[1]),
        "data/eop",
    )  # Path to the eop data dir

    eop_path = os.path.join(parent_path, eop_file)

    save_path = os.path.join(
        parent_path,
        eop_temp_name,
    )  # This is where the stuff grabbed from the url will live

    save_name, header = urlretrieve(url, save_path)  # noqa: S310

    with open(save_name) as f:
        new_eop_data: str = f.read()
        f.close()

    lines = new_eop_data.split("\n")
    new_eop_lines = []
    for line in lines:
        # Parse the first four characters and see if it's a valid year.
        try:
            year = int(line[0:4])  # noqa: F841
            new_eop_lines.append(line)
        except ValueError:  # noqa: PERF203
            pass

    # Delete the old file
    os.remove(save_name)

    # Save verified EOP content to the final destination.
    if overwrite:
        new_eop_content = "\n".join(line for line in new_eop_lines)
        with open(eop_path, "w") as f:
            f.write(new_eop_content)
            f.close()
    else:
        # Open the old file and read through line by line. Remove duplicates.
        with open(eop_path) as f:
            old_eop_text = f.read()
            f.close()
        old_eop_lines = old_eop_text.split("\n")
        new_eop_lines_first_16 = [line[0:16] for line in new_eop_lines]
        new_lines_no_dup = [
            line for line in old_eop_lines if (line[0:16] not in new_eop_lines_first_16)
        ]
        new_lines_no_dup += new_eop_lines
        new_lines_no_dup = [line for line in new_lines_no_dup if (len(line) > 0)]
        new_eop_content = "\n".join(line for line in new_lines_no_dup)
        with open(eop_path, "w") as f:
            f.write(new_eop_content)
            f.close()
