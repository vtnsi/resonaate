"""IAU-76/FK5 Reduction module.

This module handles logic pertaining to the FK5 Reduction for properly rotating ECEF (ITRF)
to/from ECI (GCRF). However, this module may later hold multiple forms of this reduction.

Author: Dylan Thomas
Date: October 5, 2018
"""
# Standard Library Imports
import datetime
from pickle import dumps, loads
# Third Party Imports
from numpy import sin, cos, matmul, asarray, fmod, dot
# RESONAATE Imports
from .nutation import get1980NutationSeries
from .eops import getEarthOrientationParameters
from .. import constants as const
from ..math import rot1, rot2, rot3
from ..time.conversions import JulianDate, utc2TerrestrialTime, greenwichApparentTime, dayOfYear
from ...parallel import getRedisConnection


REDUCTION_PARAMETER_LABELS = (
    "rot_pn", "rot_pnr", "rot_rnp", "rot_w", "rot_wt",
    "lod", "eq_equinox", "dut1", "julian_date",
)
"""list: List of keys used to construct reduction parameter dictionary."""

REDUCTION_REDIS_KEY = "reduction_params"
"""str: Redis key used to store reduction parameters."""


def updateReductionParameters(julian_date, eops=None):
    """Update the current set of FK5 data.

    Args:
        julian_date (:class:`.JulianDate`): Julian date to calculate the transformation for
        eops (:class:`.EarthOrientationParameter`, optional): Defaults to None. Specific EOPs to
            use rather than lookup, useful for tests

    """
    params = _updateFK5Parameters(julian_date, eops=eops)
    getRedisConnection().set(
        REDUCTION_REDIS_KEY,
        dumps(dict(zip(REDUCTION_PARAMETER_LABELS, params)))
    )


def getReductionParameters():
    """Retrieve current set of reduction parameters from Redis.

    Note:
        :meth:`.updateReductionParameters()` *must* be called before this function.

    Raises:
        ValueError: If :meth:`.updateReductionParameters()` hasn't been previously called to set
            the reduction parameters.
    """
    serial_obj = getRedisConnection().get(REDUCTION_REDIS_KEY)

    if serial_obj is None:
        raise ValueError("Reduction parameters have not been updated.")

    return loads(serial_obj)


def _updateFK5Parameters(julian_date, eops=None):  # pylint: disable=too-many-locals
    """Retrieve set of transformation parameters required for FK5 transformation.

    Determine the needed nutation parameters to successfully transform between
        'inertial' frames using the theory from the IAU-76 Reduction. These
        equations and constants are heavily derived from David Vallado's
        original code for his book and website.

    SeeAlso:
        Fundamentals of Astrodynamics & Applications, David Vallado, Fourth Edition, 2013.
        http://celestrak.com/software/vallado-sw.asp

    More specifically, this code follows the methodology outline in section
        3.7 of his book. Note that some major changes were made, and a few
        features were added to improve functionality.

    Args:
        julian_date (:class:`.JulianDate`): Julian date to calculate the transformation for
        eops (:class:`.EarthOrientationParameter`, optional): Defaults to None. Specific EOPs to
            use rather than lookup, useful for tests
    """
    if not isinstance(julian_date, JulianDate):
        raise TypeError("_updateFK5Parameters() requires a JulianDate input type")

    # Convert year and epoch to mdhms form. Time always in UTC
    year, month, day, hours, minutes, seconds = julian_date.calendar_date

    # Read EOPs & get terrestrial time, in Julian centuries
    if eops is None:
        eops = getEarthOrientationParameters(datetime.date(year, month, day))
    _, ttt = utc2TerrestrialTime(year, month, day, hours, minutes, seconds, eops.delta_atomic_time)

    # Get nutation params. Use all 106 terms, and 2 extra terms in the Eq. of Equinoxes. IAU-76/FK5 Reduction.
    # [NOTE] EOP corrections not added when converting to mean J2000 according to Vallado
    #           They are added here because we are rotating to GCRF instead
    delta_psi, true_eps, mean_eps, eq_equinox = _getNutationParameters(ttt, eops.d_delta_psi, eops.d_delta_eps)

    # Polar motion - Vallado 4th Ed. Eq 3-77 (full) & Eq 3-78 (simplified)
    c_x, s_x = cos(eops.x_p), sin(eops.x_p)
    c_y, s_y = cos(eops.y_p), sin(eops.y_p)

    # Complete polar motion matrix form
    rot_w = asarray(
        [
            [c_x, 0, -s_x],
            [s_x * s_y, c_y, c_x * s_y],
            [s_x * c_y, -s_y, c_x * c_y]
        ]
    )
    rot_wt = rot_w.T

    # Get seconds in UT1 & find days since Jan. 1, 0:0:0.0 (Fractional days minus 1)
    elapsed_days = dayOfYear(year, month, day, hours, minutes, seconds + eops.delta_ut1) - 1

    # Find Greenwich apparent sidereal time. [radians]
    greenwich_apparent_sidereal_time = greenwichApparentTime(year, elapsed_days, eq_equinox)

    # Get precession angles. Vallado 4th Ed. Eq 3-88
    zeta = (2306.2181 * ttt + 0.30188 * ttt**2 + 0.017998 * ttt**3) * const.ARCSEC2RAD
    theta = (2004.3109 * ttt - 0.42665 * ttt**2 - 0.041833 * ttt**3) * const.ARCSEC2RAD
    z_p = (2306.2181 * ttt + 1.09468 * ttt**2 + 0.018203 * ttt**3) * const.ARCSEC2RAD

    # Get rotation from TOD to J2000 frame (Precession, Nutation rotation matrix)
    rot_pef2tod = rot3(-1.0 * greenwich_apparent_sidereal_time)
    rot_tod2mod = matmul(rot1(-1.0 * mean_eps), matmul(rot3(delta_psi), rot1(true_eps)))
    rot_mod2eci = matmul(rot3(zeta), matmul(rot2(-1.0 * theta), rot3(z_p)))
    rot_pn = matmul(rot_mod2eci, rot_tod2mod)
    rot_pnr = matmul(rot_pn, rot_pef2tod)
    rot_rnp = rot_pnr.T

    return (
        rot_pn, rot_pnr, rot_rnp, rot_w, rot_wt,
        eops.length_of_day, eq_equinox, eops.delta_ut1, julian_date
    )


def _getNutationParameters(ttt, dd_psi, dd_eps, num=2):
    """Calculate Nutation Parameters for IAU-76/FK5 Reduction.

    Note: L suffix for Lunar, S suffix for Solar

    Args:
        ttt (``float``): terrestrial time in Julian centuries
        dd_psi (``float``): EOP correction to psi nutation parameter
        dd_eps (``float``): EOP correction to epsilon nutation parameter
        num (int, optional): whether to correct quation of equinox. Defaults to 2.

    Returns:
        ``tuple``: set of paramters defining nutation behavior
    """
    # Convenience variables
    ttt2 = ttt * ttt
    ttt3 = ttt2 * ttt

    # Find the mean obliquity of the ecliptic. Convert to between [0,2pi].
    # Vallado 4th Ed. Eqn 3-81 (could use Eqn 3-68?)
    mean_eps = 23.439291 - 0.0130042 * ttt - 1.64e-7 * ttt2 + 5.04e-7 * ttt3
    mean_eps = fmod(mean_eps, 360) * const.DEG2RAD

    # Determine coefficients for IAU-80 nutation. Convert to between [0,2pi].
    # Vallado 4th Ed. Eqn 3-82 (From Errata)
    mean_anom_l = 134.96298139 + (1325 * 360 + 198.8673981) * ttt + 0.0086972 * ttt2 + 1.78e-5 * ttt3
    mean_anom_s = 357.52772333 + (99 * 360 + 359.0503400) * ttt - 0.0001603 * ttt2 - 3.3e-6 * ttt3
    mean_arg_lat_l = 93.27191028 + (1342 * 360 + 82.0175381) * ttt - 0.0036825 * ttt2 + 3.1e-6 * ttt3
    elongation_s = 297.85036306 + (1236 * 360 + 307.1114800) * ttt - 0.0019142 * ttt2 + 5.3e-6 * ttt3
    raan_l = 125.04452222 - (5 * 360 + 134.1362608) * ttt + 0.0020708 * ttt2 + 2.2e-6 * ttt3
    corrected = fmod([mean_anom_l, mean_anom_s, mean_arg_lat_l, elongation_s, raan_l], 360) * const.DEG2RAD

    # Coefficients for longitude & obliquity correction
    rar_80, iar_80 = get1980NutationSeries()

    # Initialize & calculate nutation/obliquity corrections. Convert to between [0,2pi].
    # Vallado 4th Ed Eq 3-83
    tempval = (iar_80[::, 0] * corrected[0] + iar_80[::, 1] * corrected[1] + iar_80[::, 2] * corrected[2]
               + iar_80[::, 3] * corrected[3] + iar_80[::, 4] * corrected[4]).flatten()
    delta_psi = dot((rar_80[::, 0] + rar_80[::, 1] * ttt).flatten(), sin(tempval))
    delta_eps = dot((rar_80[::, 2] + rar_80[::, 3] * ttt).flatten(), cos(tempval))
    # Corrections for FK5 - Makes consistent with GCRF.
    delta_psi = fmod(delta_psi, const.TWOPI) + dd_psi
    delta_eps = fmod(delta_eps, const.TWOPI) + dd_eps
    # Get true obliquity of the ecliptic
    true_eps = mean_eps + delta_eps

    # Correction coefficients for equation of equinox (Eq 3-79 Vallado Ed. 4)
    equinox_c1 = 0.00264 * const.ARCSEC2RAD
    equinox_c2 = 0.000063 * const.ARCSEC2RAD
    # Determine the equation of equinoxes.
    eq_equinox = delta_psi * cos(mean_eps)
    # Before Feb 27, 1997 extra terms not used.
    if ((ttt * 36525 + 2451545) > 2450449.5) and (num > 0):
        eq_equinox += equinox_c1 * sin(corrected[4]) + equinox_c2 * sin(2.0 * corrected[4])

    return delta_psi, true_eps, mean_eps, eq_equinox
