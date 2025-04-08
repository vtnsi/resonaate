"""The orbits package provides functionality to create & convert orbital elements.

This package is designed to provide an accurate, stable, well-documented, and performant
library to allow users to quickly develop effective algorithms & analyses using orbital
elements.

References:
    :cite:t:`vallado_2003_aiaa_covariance`, Pg 11
"""

from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING

# Local Imports
from .. import constants as const
from ..bodies import Earth
from ..maths import wrapAngle2Pi

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable

# Limits taken from Vallado AAS paper & verified to provide "constant" COEs across multiple orbits
ECCENTRICITY_LIMIT = 1e-7
"""``float``: Defines the limit between eccentric & circular orbits (:cite:p:`vallado_2003_aiaa_covariance`)."""
INCLINATION_LIMIT = 1e-7 * const.DEG2RAD
"""``float``: Defines the limit between inclined & equatorial orbits  (:cite:p:`vallado_2003_aiaa_covariance`)."""


@dataclass
class _StratificationSpecification:
    """Specification of variables for a resident stratification."""

    label: str
    """str: Name associated with this resident stratification."""

    max_altitude: float
    """float: Maximum valid altitude to be considered within this resident stratification (in km)."""

    default_mass: float
    """float: Default mass of resident within this stratification (in kg)"""

    default_vis_x: float
    """float: Default visual cross section of resident within this stratification."""


class ResidentStratification:
    """Encapsulate variables associated with orbital regimes."""

    SURFACE = _StratificationSpecification(
        label="SURFACE",
        max_altitude=Earth.atmosphere,
        default_mass=10000.0,
        default_vis_x=400.0,
    )
    """_StratificationSpecification: Surface resident stratification.

    Attributes:
        label (str): Name of surface resident stratification.
        max_altitude (float): Maximum valid altitude to be considered on surface of Earth (in km).
        default_mass (float): Default mass of non-spacecraft (kg).
        default_vis_x (float): Default visual cross section of 20m by 20m building (m^2).
    """

    LEO = _StratificationSpecification(
        label="LEO",
        max_altitude=12000.0,
        default_mass=295.0,
        default_vis_x=10.0,
    )
    """_StratificationSpecification: Low Earth orbit resident stratification.

    Attributes:
        label (str): Name associated with low Earth orbit.
        max_altitude (float): Maximum valid altitude to be considered within LEO regime (in km).
        default_mass (float): Default mass of LEO RSO (kg)
        default_vis_x (float): Default visual cross section of LEO RSO (m^2)

    References:
        :cite:t:`LEO_RSO_2022_stats`
    """

    MEO = _StratificationSpecification(
        label="MEO",
        max_altitude=30000.0,
        default_mass=2861.0,
        default_vis_x=37.5,
    )
    """_StratificationSpecification: Medium Earth orbit resident stratification.

    Attributes:
        label (str): Name associated with medium Earth orbit.
        max_altitude (float): Maximum valid altitude to be considered within MEO regime (in km).
        default_mass (float): Default mass of MEO RSO (kg)
        default_vis_x (float): Default visual cross section of MEO RSO (m^2)

    References:
        :cite:t:`steigenberger_MEO_RSO_2022_stats`
    """

    GEO = _StratificationSpecification(
        label="GEO",
        max_altitude=45000.0,
        default_mass=6200.0,
        default_vis_x=90.0,
    )
    """_StratificationSpecification: Geosynchronous Earth orbit resident stratification.

    Attributes:
        label (str): Name associated with Geosynchronous Earth orbit.
        max_altitude (float): Maximum valid altitude to be considered within GEO regime (in km).
        default_mass (float): Default mass of GEO RSO (kg)
        default_vis_x (float): Default visual cross section of GEO RSO (m^2)

    References:
        :cite:t:`GEO_RSO_2022_stats`
    """

    @classmethod
    def getStratification(cls, altitude: float) -> _StratificationSpecification:
        """Return the stratification that the specified `altitude` falls within.

        Args:
            altitude (float): Altitude of resident.

        Returns:
            :class:`._StratificationSpecification`: :class:`._StratificationSpecification` that specified `altitude` falls within.
        """
        if altitude <= cls.SURFACE.max_altitude:
            return cls.SURFACE
        if altitude <= cls.LEO.max_altitude:
            return cls.LEO
        if altitude <= cls.MEO.max_altitude:
            return cls.MEO
        if altitude <= cls.GEO.max_altitude:
            return cls.GEO
        # else
        err = f"RSO altitude above GEO: {altitude}."
        raise ValueError(err)


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

    @wraps(func)
    def wrapper_check_ecc(anomaly, ecc, *args, **kwargs):
        # circular orbit -> f, E, M are equivalent
        return anomaly if not isEccentric(ecc) else func(anomaly, ecc, *args, **kwargs)

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
            f"Invalid inclination, must be in [0, 180]. inc={inc * const.RAD2DEG:.1f} deg",
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
