"""Functions that define physics related to sensors."""
from __future__ import annotations

# Standard Library Imports
from enum import IntEnum, auto
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import arcsin, arctan2, sin, sqrt, vdot
from scipy.linalg import norm

# Local Imports
from .constants import PI, TWOPI
from .maths import fpe_equals, wrapAngle2Pi

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


def getAzimuth(slant_range_sez: ndarray) -> float:
    r"""Calculate the azimuth angle for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the azimuth angle in radians, :math:`[0, 2\pi)`.
    """
    if fpe_equals(getElevation(slant_range_sez), PI / 2):  # 90 degree elevation edge case
        azimuth = arctan2(slant_range_sez[4], -1.0 * slant_range_sez[3])
    else:
        azimuth = arctan2(slant_range_sez[1], -1.0 * slant_range_sez[0])
    return wrapAngle2Pi(azimuth)


def getElevation(slant_range_sez: ndarray) -> float:
    r"""Calculate the elevation angle for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the elevation angle in radians, :math:`[\frac{-\pi}{2}, \frac{\pi}{2})`
    """
    return arcsin(slant_range_sez[2] / norm(slant_range_sez[:3]))


def getRange(slant_range_sez: ndarray) -> float:
    r"""Calculate the range (i.e. euclidean norm) for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the range (km)
    """
    return norm(slant_range_sez[:3])


def getAzimuthRate(slant_range_sez: ndarray) -> float:
    r"""Calculate the azimuth rate for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the azimuth angular rate (radians/sec)
    """
    return (slant_range_sez[3] * slant_range_sez[1] - slant_range_sez[4] * slant_range_sez[0]) / (
        slant_range_sez[0] ** 2 + slant_range_sez[1] ** 2
    )


def getElevationRate(slant_range_sez: ndarray) -> float:
    r"""Calculate the elevation rate for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the elevation angular rate (radians/sec)
    """
    return (
        slant_range_sez[5] - getRangeRate(slant_range_sez) * sin(getElevation(slant_range_sez))
    ) / sqrt(slant_range_sez[0] ** 2 + slant_range_sez[1] ** 2)


def getRangeRate(slant_range_sez: ndarray) -> float:
    r"""Calculate the range rate for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the range rate (km/sec)
    """
    return vdot(slant_range_sez[:3], slant_range_sez[3:]) / getRange(slant_range_sez)


class IsAngle(IntEnum):
    r"""Enum class to determine if a measurement is an angle or not."""

    NOT_ANGLE = auto()
    r"""``int``: constant representing a measurement that is not an angle."""
    ANGLE_0_2PI = auto()
    r"""``int``: constant representing a measurement that is an angle and is valid :math:`[0, 2\pi)`."""
    ANGLE_NEG_PI_PI = auto()
    r"""``int``: constant representing a measurement that is an angle and is valid :math:`[-\pi, \pi)`."""


VALID_ANGLE_MAP: dict[IsAngle, tuple[float, float]] = {
    IsAngle.ANGLE_0_2PI: (0.0, TWOPI),
    IsAngle.ANGLE_NEG_PI_PI: (-PI, PI),
}
r"""``dict[:class:.`IsAngle`, tuple[float, float]]``: maps :class:`.IsAngle` enums to their associated bounds."""


VALID_ANGULAR_MEASUREMENTS: tuple[IsAngle, ...] = tuple(VALID_ANGLE_MAP.keys())
r"""``tuple[:class:`.IsAngle`, ...]``: all valid angular measurement types categorized """
