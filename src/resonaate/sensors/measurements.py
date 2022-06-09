"""Functions that provide different sensor measurements based on the slant range vector."""
from __future__ import annotations

# Standard Library Imports
from enum import IntEnum, auto
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import arcsin, arctan2, array, concatenate, dot, pi, sin, sqrt
from scipy.linalg import norm

# Local Imports
from ..physics.math import fpe_equals, wrapAngle2Pi

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Dict, Tuple

    # Third Party Imports
    from numpy import ndarray


class IsAngle(IntEnum):
    r"""Enum class to determine if a measurement is an angle or not."""

    NOT_ANGLE = auto()
    r"""``int``: constant representing a measurement that is not an angle."""
    ANGLE_0_2PI = auto()
    r"""``int``: constant representing a measurement that is an angle and is valid :math:`[0, 2\pi)`."""
    ANGLE_NEG_PI_PI = auto()
    r"""``int``: constant representing a measurement that is an angle and is valid :math:`[-\pi, \pi)`."""


VALID_ANGLE_MAP: Dict[IsAngle, Tuple[float, float]] = {
    IsAngle.ANGLE_0_2PI: (0, 2 * pi),
    IsAngle.ANGLE_NEG_PI_PI: (-pi, pi),
}
r"""``dict[:class:.`IsAngle`, tuple[float, float]]``: maps :class:`.IsAngle` enums to their associated bounds."""


VALID_ANGULAR_MEASUREMENTS: Tuple[IsAngle, ...] = tuple(VALID_ANGLE_MAP.keys())
r"""``tuple[:class:`.IsAngle`, ...]``: all valid angular measurement types categorized """


def getAzimuth(slant_range_sez: ndarray) -> float:
    r"""Calculate the azimuth angle for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the azimuth angle in radians, :math:`[0, 2\pi)`.
    """
    if fpe_equals(getElevation(slant_range_sez), pi / 2):  # 90 degree elevation edge case
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
    return dot(slant_range_sez[:3], slant_range_sez[3:]) / getRange(slant_range_sez)


def dAzimuthDX(slant_range_sez: ndarray) -> ndarray:
    r"""Calculate the azimuth partial derivatives for an slant range vector.

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = slant_range_sez[:3]
    r_sez_12_sq = r_sez[0] ** 2 + r_sez[1] ** 2
    return array([r_sez[1] / r_sez_12_sq, -r_sez[0] / r_sez_12_sq, 0, 0, 0, 0])


def dElevationDX(slant_range_sez: ndarray) -> ndarray:
    r"""Calculate the elevation partial derivatives for an slant range vector.

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = slant_range_sez[:3]
    rho_sq = norm(r_sez) ** 2
    temp = sqrt(r_sez[0] ** 2 + r_sez[1] ** 2)
    return array(
        [
            (-r_sez[0] * r_sez[2]) / (rho_sq * temp),
            (-r_sez[1] * r_sez[2]) / (rho_sq * temp),
            (r_sez[2] ** 2) / (rho_sq * temp),
            0,
            0,
            0,
        ]
    )


def dRangeDX(slant_range_sez: ndarray) -> ndarray:
    r"""Calculate the range partial derivatives for an slant range vector.

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = slant_range_sez[:3]
    rho = norm(r_sez)
    return array([r_sez[0] / rho, r_sez[1] / rho, r_sez[2] / rho, 0, 0, 0])


def dRangeRateDX(slant_range_sez: ndarray) -> ndarray:
    r"""Calculate the range rate partial derivatives for an slant range vector.

    Args:
        slant_range_sez (``ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = slant_range_sez[:3]
    v_sez = slant_range_sez[3:]
    rho = norm(r_sez)
    position = (1.0 / rho) * (v_sez.T) - (dot(r_sez, v_sez) / (rho**3)) * (r_sez.T)
    velocity = (1.0 / rho) * (r_sez.T)

    return concatenate((position, velocity), axis=0)
