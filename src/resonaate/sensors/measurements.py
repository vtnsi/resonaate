# Standard Library Imports
# Third Party Imports
from numpy import arctan2, arcsin, sin, sqrt, matmul, asarray, concatenate
from scipy.linalg import norm
# RESONAATE Module Imports
from ..physics import constants as const


def getAzimuth(obs_vector_sez):
    """Calculate the azimuth angle for an observation vector.

    Args:
        obs_vector_sez (``np.ndarray``): 6x1 observation vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the azimuth angle in radians, [0, 2*pi].
    """
    azimuth = arctan2(obs_vector_sez[1], -1.0 * obs_vector_sez[0])
    if azimuth < 0.0:
        return azimuth + 2 * const.PI
    else:
        return azimuth


def getElevation(obs_vector_sez):
    """Calculate the elevation angle for an observation vector.

    Args:
        obs_vector_sez (``np.ndarray``): 6x1 observation vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the elevation angle in radians, [-pi/2, pi/2]
    """
    return arcsin(obs_vector_sez[2] / norm(obs_vector_sez[:3]))


def getRange(obs_vector_sez):
    """Calculate the range (i.e. euclidean norm) for an observation vector.

    Args:
        obs_vector_sez (``np.ndarray``): 6x1 observation vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the range (km)
    """
    return norm(obs_vector_sez[:3])


def getAzimuthRate(obs_vector_sez):
    """Calculate the azimuth rate for an observation vector.

    Args:
        obs_vector_sez (``np.ndarray``): 6x1 observation vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the azimuth angular rate (radians/sec)
    """
    return (
        (obs_vector_sez[3] * obs_vector_sez[1] - obs_vector_sez[4] * obs_vector_sez[0])
        / (obs_vector_sez[0]**2 + obs_vector_sez[1]**2)
    )


def getElevationRate(obs_vector_sez):
    """Calculate the elevation rate for an observation vector.

    Args:
        obs_vector_sez (``np.ndarray``): 6x1 observation vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the elevation angular rate (radians/sec)
    """
    temp_el = getElevation(obs_vector_sez)
    return (
        (obs_vector_sez[5] - norm(obs_vector_sez[3:]) * sin(temp_el))
        / sqrt(obs_vector_sez[0]**2 + obs_vector_sez[1]**2)
    )


def getRangeRate(obs_vector_sez):
    """Calculate the range rate for an observation vector.

    Args:
        obs_vector_sez (``np.ndarray``): 6x1 observation vector in SEZ frame (km; km/sec)

    Returns:
        ``float``: scalar value for the range rate (km/sec)
    """
    return matmul(
        obs_vector_sez[:3].T,
        obs_vector_sez[3:]
    ) / norm(obs_vector_sez[:3])


def dAzimuthDX(obs_vector_sez):
    """Calculate the azimuth partial derivatives for an observation vector.

    Args:
        obs_vector_sez (``np.ndarray``): 6x1 observation vector in SEZ frame (km; km/sec)

    Returns:
        ``np.ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = obs_vector_sez[:3]
    r_sez_12_sq = r_sez[0]**2 + r_sez[1]**2
    return asarray([r_sez[1] / r_sez_12_sq, -r_sez[0] / r_sez_12_sq, 0, 0, 0, 0])


def dElevationDX(obs_vector_sez):
    """Calculate the elevation partial derivatives for an observation vector.

    Args:
        obs_vector_sez (``np.ndarray``): 6x1 observation vector in SEZ frame (km; km/sec)

    Returns:
        ``np.ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = obs_vector_sez[:3]
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


def dRangeDX(obs_vector_sez):
    """Calculate the range partial derivatives for an observation vector.

    Args:
        obs_vector_sez (``np.ndarray``): 6x1 observation vector in SEZ frame (km; km/sec)

    Returns:
        ``np.ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = obs_vector_sez[:3]
    rho = norm(r_sez)
    return asarray([r_sez[0] / rho, r_sez[1] / rho, r_sez[2] / rho, 0, 0, 0])


def dRangeRateDX(obs_vector_sez):
    """Calculate the range rate partial derivatives for an observation vector.

    Args:
        obs_vector_sez (``np.ndarray``): 6x1 observation vector in SEZ frame (km; km/sec)

    Returns:
        ``np.ndarray``: 1x6 array of partial derivatives in SEZ frame
    """
    r_sez = obs_vector_sez[:3]
    v_sez = obs_vector_sez[3:]
    rho = norm(r_sez)
    dot_rho = matmul(r_sez.T, v_sez)
    position = (1.0 / rho) * (v_sez.T) - (dot_rho / (rho**3)) * (r_sez.T)
    velocity = (1.0 / rho) * (r_sez.T)

    return concatenate((position, velocity), axis=0)
