"""Calculate Earth nutation parameters.

This module is for storing coefficients for different nutation series.
"""
# Standard Library Imports
from functools import lru_cache
from pkg_resources import resource_filename
# Third Party Imports
import numpy as np
# RESONAATE Imports
import resonaate.physics.constants as const
from ...common.utilities import loadDatFile


@lru_cache(maxsize=5)
def get1980NutationSeries():
    """Return the complete set of IAU 1980 Nutation Theory coefficients.

    Note:
        This function is cached so repeated calls shouldn't need to re-read the file.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 3-83, Pg. 226

    Returns:
        tuple: (real coefficients, integer coefficients)
    """
    # Load nutation into numpy array
    nut_data = np.asarray(
        loadDatFile(resource_filename('resonaate', 'physics/data/eop/nut80.dat'))
    )

    # Parse integer and real coefficients out.
    i_coeffs = nut_data[::, :5]
    r_coeffs = nut_data[::, 5:9]

    return np.asarray(r_coeffs) * 0.0001 * const.ARCSEC2RAD, np.asarray(i_coeffs)
