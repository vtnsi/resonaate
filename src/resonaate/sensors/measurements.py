"""Functions that provide different sensor measurements based on the slant range vector."""
# Standard Library Imports
from enum import IntEnum
# Third Party Imports
from numpy import arctan2, arcsin, sin, sqrt, dot, asarray, concatenate, pi
from scipy.linalg import norm
# RESONAATE Module Imports
from ..physics.math import wrapAngle2Pi, fpe_equals


class IsAngle(IntEnum):
    r"""Enum class to determine if a measurement is an angle or not."""

    NOT_ANGLE = 1
    r"""``int``: constant representing a measurement that is not an angle."""
    ANGLE_PI = 2
    r"""``int``: constant representing a measurement that is an angle and is valid :math:`[0, \pi)`."""
    ANGLE_2PI = 3
    r"""``int``: constant representing a measurement that is an angle and is valid :math:`[0, 2\pi)`."""


def getAzimuth(slant_range_sez):
    """Calculate the azimuth angle for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``np.ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the azimuth angle in radians, [0, 2pi).
    """
    if fpe_equals(getElevation(slant_range_sez), pi / 2):  # 90 degree elevation edge case
        azimuth = arctan2(slant_range_sez[4], -1.0 * slant_range_sez[3])
    else:
        azimuth = arctan2(slant_range_sez[1], -1.0 * slant_range_sez[0])
    return wrapAngle2Pi(azimuth)


def getElevation(slant_range_sez):
    """Calculate the elevation angle for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``np.ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the elevation angle in radians, [-pi/2, pi/2]
    """
    return arcsin(slant_range_sez[2] / norm(slant_range_sez[:3]))


def getRange(slant_range_sez):
    """Calculate the range (i.e. euclidean norm) for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``np.ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the range (km)
    """
    return norm(slant_range_sez[:3])


def getAzimuthRate(slant_range_sez):
    """Calculate the azimuth rate for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``np.ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the azimuth angular rate (radians/sec)
    """
    return (
        (slant_range_sez[3] * slant_range_sez[1] - slant_range_sez[4] * slant_range_sez[0])
        / (slant_range_sez[0]**2 + slant_range_sez[1]**2)
    )


def getElevationRate(slant_range_sez):
    """Calculate the elevation rate for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``np.ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the elevation angular rate (radians/sec)
    """
    return (
        (slant_range_sez[5] - getRangeRate(slant_range_sez) * sin(getElevation(slant_range_sez)))
        / sqrt(slant_range_sez[0]**2 + slant_range_sez[1]**2)
    )


def getRangeRate(slant_range_sez):
    """Calculate the range rate for an slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Algorithm 27

    Args:
        slant_range_sez (``np.ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the range rate (km/sec)
    """
    return dot(
        slant_range_sez[:3],
        slant_range_sez[3:]
    ) / getRange(slant_range_sez)


def dAzimuthDX(slant_range_sez):
    """Calculate the azimuth partial derivatives for an slant range vector.

    Args:
        slant_range_sez (``np.ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``np.ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = slant_range_sez[:3]
    r_sez_12_sq = r_sez[0]**2 + r_sez[1]**2
    return asarray([r_sez[1] / r_sez_12_sq, -r_sez[0] / r_sez_12_sq, 0, 0, 0, 0])


def dElevationDX(slant_range_sez):
    """Calculate the elevation partial derivatives for an slant range vector.

    Args:
        slant_range_sez (``np.ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``np.ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = slant_range_sez[:3]
    rho_sq = norm(r_sez)**2
    temp = sqrt(r_sez[0]**2 + r_sez[1]**2)
    return asarray(
        [
            (-r_sez[0] * r_sez[2]) / (rho_sq * temp),
            (-r_sez[1] * r_sez[2]) / (rho_sq * temp),
            (r_sez[2]**2) / (rho_sq * temp),
            0, 0, 0
        ]
    )


def dRangeDX(slant_range_sez):
    """Calculate the range partial derivatives for an slant range vector.

    Args:
        slant_range_sez (``np.ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``np.ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = slant_range_sez[:3]
    rho = norm(r_sez)
    return asarray([r_sez[0] / rho, r_sez[1] / rho, r_sez[2] / rho, 0, 0, 0])


def dRangeRateDX(slant_range_sez):
    """Calculate the range rate partial derivatives for an slant range vector.

    Args:
        slant_range_sez (``np.ndarray``): 6x1 slant range vector in SEZ frame (km; km/sec)

    Returns:
        ``np.ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = slant_range_sez[:3]
    v_sez = slant_range_sez[3:]
    rho = norm(r_sez)
    position = (1.0 / rho) * (v_sez.T) - (dot(r_sez, v_sez) / (rho**3)) * (r_sez.T)
    velocity = (1.0 / rho) * (r_sez.T)

    return concatenate((position, velocity), axis=0)
