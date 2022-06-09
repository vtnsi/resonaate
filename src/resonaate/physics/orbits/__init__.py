"""The orbits package provides functionality to create & convert orbital elements.

This package is designed to provide an accurate, stable, well-documented, and performant
library to allow users to quickly develop effective algorithms & analyses using orbital
elements.

References:
    :cite:t:`vallado_2003_aiaa_covariance`, Pg 11
"""
# Standard Library Imports
from functools import wraps
from typing import Callable, Tuple

# Local Imports
from .. import constants as const
from ..math import wrapAngle2Pi

# Limits taken from Vallado AAS paper & verified to provide "constant" COEs across multiple orbits
ECCENTRICITY_LIMIT = 1e-7
"""``float``: Defines the limit between eccentric & circular orbits (:cite:p:`vallado_2003_aiaa_covariance`)."""
INCLINATION_LIMIT = 1e-7 * const.DEG2RAD
"""``float``: Defines the limit between inclined & equatorial orbits  (:cite:p:`vallado_2003_aiaa_covariance`)."""


class InclinationError(Exception):
    r"""Exception indicating that an invalid inclination angle was used."""


class EccentricityError(Exception):
    r"""Exception indicating that an invalid eccentricity was used."""


def fixAngleQuadrant(angle, check):
    r"""Called from within functions that require a quadrant check on the output angular value.

    If ``check`` is less than zero, :math:`\theta = 2\pi - \theta` is returned, otherwise
    :math:`\theta` is directly returned.

    This occurs due to directly using :math:`\arccos(x)` because its range is :math:`[0, \pi]`.

    References:
        :cite:t:`vallado_2013_astro`, Algorithm 9

    Args:
        angle (``float``): The angular value (in radians) that is to be (potentially) adjusted.
        check (``float``): The value used in the check.

    Returns:
        ``float``: Angular value adjusted for the proper quadrant.
    """
    if check < 0.0:
        angle = const.TWOPI - angle

    return angle


def check_ecc(func: Callable[..., float]) -> Callable[..., float]:
    r"""Checks ``ecc`` for functions that convert between anomaly types to account for circulars.

    The wrapped function's first two variables **must** be :math:`(f, e)` where :math:`f` is the
    input ``anomaly`` type and :math:`e` is the eccentricity. Also, the function must return a
    single ``float``. The special case is that if the orbit is circular, then :math:`\nu = E = M`,
    so the input :math:`f` is directly returned.

    Args:
        func (``Callable[..., float]``): `anomaly` function to be wrapped with an eccentricity check.

    Returns:
        Callable[..., float]: wrapped `anomaly` function that properly accounts for circular orbits.
    """
    # pylint: disable=invalid-name
    @wraps(func)
    def wrapper_check_ecc(anom, ecc, *args, **kwargs):
        if not isEccentric(ecc):
            new_anom = anom  # circular orbit -> f, E, M are equivalent
        else:
            new_anom = func(anom, ecc, *args, **kwargs)
        return new_anom

    return wrapper_check_ecc


def wrap_anomaly(func: Callable[..., float]) -> Callable[..., float]:
    r"""Wraps function to convert anomaly output into the range :math:`[0, 2\pi)`.

    The wrapped function must output only an `anomaly` in radians. The `anomaly` is then
    auto-converted to the valid range of :math:`[0, 2\pi)`.

    Args:
        func (``Callable[..., float]``): `anomaly` function to have its output auto-converted.

    Returns:
        Callable[..., float]: wrapped `anomaly` function that properly converts its output.
    """
    # pylint: disable=invalid-name
    @wraps(func)
    def wrapper_wrap_angle_2pi(*args, **kwargs):
        return wrapAngle2Pi(func(*args, **kwargs))

    return wrapper_wrap_angle_2pi


def isInclined(inc: float, tol: float = INCLINATION_LIMIT) -> bool:
    r"""Check whether the angle is numerically considered inclined.

    Args:
        inc (``float``): inclination angle to check, :math:`i\in[0,\pi]`, in radians.
        tol (``float``, optional): numerical limit of inclination. Defaults to :data:`.INCLINATION_LIMIT`.

    Return:
        ``bool``: whether the angle is inclined.
    """
    if inc < 0.0 or inc > const.PI:
        raise InclinationError(
            f"Invalid inclination, must be in [0, 180]. inc={inc * const.RAD2DEG:.1f} deg"
        )
    return tol <= inc <= const.PI - tol


def isEccentric(ecc: float, tol: float = ECCENTRICITY_LIMIT) -> bool:
    r"""Check whether the value is numerically considered eccentric.

    Args:
        ecc (``float``): value to check if eccentric.
        tol (``float``, optional): numerical limit of eccentricity. Defaults to :data:`.ECCENTRICITY_LIMIT`.

    Return:
        ``bool``: whether the angle is inclined.
    """
    if ecc < 0.0 or ecc > 1.0 - tol:
        raise EccentricityError(f"Invalid eccentricity, must be in [0, 1 - tol). ecc={ecc:.2f}")
    return ecc >= tol
