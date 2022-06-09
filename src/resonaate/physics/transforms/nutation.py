"""Calculate Nutation Parameters.

This module is for storing coefficients for different nutation series.

Author: Dylan Thomas
Date: April 4, 2021
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

    SeeAlso:
        Fundamentals of Astrodynamics & Applications, David Vallado, Fourth Edition, 2013.
        Eq 3-83 (Pg 226)

    Returns:
        tuple: (real coefficients, integer coefficients)
    """
    # Load nutation into numpy array
    nut_data = np.asarray(
        loadDatFile(resource_filename('resonaate', 'physics/data/nut80.dat'))
    )

    # Parse integer and real coefficients out.
    i_coeffs = nut_data[::, :5]
    r_coeffs = nut_data[::, 5:9]

    return np.asarray(r_coeffs) * 0.0001 * const.ARCSEC2RAD, np.asarray(i_coeffs)
