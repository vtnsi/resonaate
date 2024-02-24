"""Calculate Earth nutation parameters.

This module is for storing coefficients for different nutation series.
"""

from __future__ import annotations

# Standard Library Imports
from functools import lru_cache
from importlib import resources
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array

# Local Imports
from ...common.utilities import loadDatFile
from .. import constants as const

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


NUTATION_MODULE: str = "resonaate.physics.data.nutation"
"""``str``: defines nutation data module location."""


NUTATION_1980: str = "nut80.dat"
"""``str``: defines nutation data file for 1980 nutation model."""


@lru_cache(maxsize=5)
def get1980NutationSeries() -> tuple[ndarray, ndarray]:
    """Return the complete set of IAU 1980 Nutation Theory coefficients.

    Note:
        This function is cached so repeated calls shouldn't need to re-read the file.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 3-83, Pg. 226

    Returns:
        ``tuple``: (real coefficients, integer coefficients)
    """
    # Load nutation into numpy array
    res = resources.files(NUTATION_MODULE).joinpath(NUTATION_1980)
    with resources.as_file(res) as file_resource:
        nut_data = array(loadDatFile(file_resource))

    # Parse integer and real coefficients out.
    integers = nut_data[::, :5]
    reals = nut_data[::, 5:9] * 0.0001 * const.ARCSEC2RAD

    return array(reals), array(integers)
