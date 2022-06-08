# Standard Library Imports
# Third Party Imports
from numpy import (
    concatenate, sqrt, sin, cos, sign, arccos,
    arctan, matmul, asarray, finfo, float64, tan
)
from scipy.linalg import norm
# RESONAATE Imports
from ...physics import constants as const
from ...physics.math import rot2, rot3, cross
from ..bodies import Earth
from .reductions import getReductionParameters


def eci2ecef(x_eci):
    """Convert an ECI state vector into an ECEF state vector.

    Note:
        `updateReductionParameters()` _must_ be called before this can be used.

    Args:
        x_eci (`np.ndarray`): 6x1 ECI state vector, (km; km/sec)

    Returns:
        (`np.ndarray`): 6x1 ECEF state vector, (km; km/sec)
    """
    reduction = getReductionParameters()
    r_ecef = matmul(reduction["rot_wt"], matmul(reduction["rot_rnp"], x_eci[:3]))
    om_earth = asarray([0, 0, Earth.spin_rate * (1 - reduction["eops"]["lod"] / 86400.0)])
    v_correction = cross(om_earth, matmul(reduction["rot_w"], r_ecef))
    v_ecef = matmul(
        reduction["rot_wt"],
        matmul(reduction["rot_rnp"], x_eci[3:]) - v_correction
    )

    return concatenate((r_ecef, v_ecef), axis=0)


def ecef2eci(x_ecef):
    """Convert an ECEF state vector into an ECI state vector.

    Note:
        `updateReductionParameters()` _must_ be called before this can be used.

    Args:
        x_eci (`np.ndarray`): 6x1 ECEF state vector, (km; km/sec)

    Returns:
        (`np.ndarray`): 6x1 ECI state vector, (km; km/sec)
    """
    reduction = getReductionParameters()
    r_eci = matmul(reduction["rot_pnr"], matmul(reduction["rot_w"], x_ecef[:3]))
    om_earth = asarray([0, 0, Earth.spin_rate * (1 - reduction["eops"]["lod"] / 86400.0)])
    v_correction = cross(om_earth, matmul(reduction["rot_w"], x_ecef[:3]))
    v_eci = matmul(
        reduction["rot_pnr"],
        matmul(reduction["rot_w"], x_ecef[3:]) + v_correction
    )

    return concatenate((r_eci, v_eci), axis=0)


def sez2ecef(x_sez, lat, lon):
    """Convert an SEZ state vector into an ECEF state vector.

    Note:
        [TODO]: Unverified conversion

    Args:
        x_sez (`np.ndarray`): 6x1 SEZ state vector, (km; km/sec)
        lat (float): scalar geodetic latitude, (radians)
        lon (float): scalar longitude, (radians)

    Returns:
        (`np.ndarray`): 6x1 ECEF state vector, (km; km/sec)
    """
    sez_2_ecef_rotation = matmul(rot3(-lon), rot2(lat - const.PI / 2))
    return concatenate(
        (
            matmul(sez_2_ecef_rotation, x_sez[:3]),  # Convert position
            matmul(sez_2_ecef_rotation, x_sez[3:])  # Convert velocity
        ), axis=0
    )


def ecef2sez(x_ecef, lat, lon):
    """Convert an ECEF state vector into an SEZ state vector.

    Note:
        [TODO]: Unverified conversion

    Args:
        x_ecef (`np.ndarray`): 6x1 ECEF state vector, (km; km/sec)
        lat (float): scalar geodetic latitude, (radians)
        lon (float): scalar longitude, (radians)

    Returns:
        (`np.ndarray`): 6x1 SEZ state vector, (km; km/sec)
    """
    ecef_2_sez_rotation = matmul(rot2(const.PI / 2 - lat), rot3(lon))
    return concatenate(
        (
            matmul(ecef_2_sez_rotation, x_ecef[:3]),  # Convert position
            matmul(ecef_2_sez_rotation, x_ecef[3:])  # Convert velocity
        ), axis=0
    )


def eci2sez(x_eci, lat, lon):
    """Convert an ECI state vector into an SEZ state vector.

    Note:
        [TODO]: Unverified conversion

    Args:
        x_eci (`np.ndarray`): 6x1 ECI state vector, (km; km/sec)
        lat (float): scalar geodetic latitude, (radians)
        lon (float): scalar longitude, (radians)

    Returns:
        (`np.ndarray`): 6x1 SEZ state vector, (km; km/sec)
    """
    return ecef2sez(eci2ecef(x_eci), lat, lon)


def sez2eci(x_sez, lat, lon):
    """Convert an SEZ state vector into an ECI state vector.

    Note:
        [TODO]: Unverified conversion

    Args:
        x_sez (`np.ndarray`): 6x1 SEZ state vector, (km; km/sec)
        lat (float): scalar geodetic latitude, (radians)
        lon (float): scalar longitude, (radians)

    Returns:
        (`np.ndarray`): 6x1 ECI state vector, (km; km/sec)
    """
    return ecef2eci(sez2ecef(x_sez, lat, lon))


def lla2ecef(x_lla):
    """Convert a latitude, longitude, and altitude to a 6x1 ECEF state vector.

    The code is derived from Algorithm 51, on page 430 of Vallado, "Fundamentals of Astrodynamics
    and Applications", 4th Edition. Most of these equations come from Equation (3-7) on page 138.

    Altitude is height above ellipsoid, and latitude is geodetic latitude.

    Note:
        [TODO]: Unverified conversion

    Args:
        x_lla (`np.ndarray`): 3x1 of latitude, longitude, and altitude, (radians, radians, km)

    Returns:
        (`np.ndarray`): 6x1 ECEF state vector, (km; km/sec)
    """
    # pylint: disable=invalid-name
    lat, lon, alt = x_lla[0], x_lla[1], x_lla[2]

    # Geodesy Calculation: Radius of Curvature in Prime Vertical and Auxiliary Variables
    radius_pv = Earth.radius / sqrt(1 - Earth.eccentricity**2 * sin(lat)**2)
    radius_aux = (1 - Earth.eccentricity**2) * radius_pv

    # Horizontal component along semi-major axis & vertical component parallel to semi-minor axis
    r_delta = (radius_pv + alt) * cos(lat)
    r_k = (radius_aux + alt) * sin(lat)

    # Final ECEF Calculation relating ECEF to Geodetic Latitude, Longitude, and Altitude
    return asarray([r_delta * cos(lon), r_delta * sin(lon), r_k, 0, 0, 0])


def ecef2lla(x_ecef):
    """Convert an ECEF state vector to latitude, longitude, and altitude.

    The code is derived, with some minor modifications for coding, from Algorithm 13, on
    page 173 of Vallado, "Fundamentals of Astrodynamics and Applications", 4th Edition

    Altitude is height above ellipsoid, and latitude is geodetic latitude.

    Note:
        [TODO]: Unverified conversion

    Args:
        x_ecef (`np.ndarray`): 6x1 ECEF state vector, (km; km/sec)

    Returns:
        (`np.ndarray`): 3x1 of latitude, longitude, and altitude, (radians, radians, km)
    """
    # pylint: disable=invalid-name

    # Preliminary variables to match Vallado's implementation
    r_i, r_j, r_k = x_ecef[0], x_ecef[1], x_ecef[2]
    r_delta = sqrt(r_i**2 + r_j**2)
    a = Earth.radius  # Mean equatorial radius

    # Only occurs at exactly 0 deg, 0 deg
    if r_delta == 0:
        r_delta = finfo(float64).eps

    # Calculate the mean polar radius of Earth
    if r_k == 0:
        b = a * sqrt(1 - Earth.eccentricity**2)
    else:
        b = a * sqrt(1 - Earth.eccentricity**2) * sign(r_k)

    # Intermediate parameters
    E = (b * r_k - (a**2 - b**2)) / (a * r_delta)
    F = (b * r_k + (a**2 - b**2)) / (a * r_delta)
    P = 4.0 * (E * F + 1) / 3.0
    Q = 2.0 * (E**2 - F**2)
    D = P**3 + Q**2
    if D >= 0:
        nu = (sqrt(D) - Q)**(1.0 / 3) - (sqrt(D) + Q)**(1.0 / 3)
    else:
        nu = 2.0 * sqrt(-P) * cos(arccos(Q / (P * sqrt(-P))) / 3.0)
    G = 0.5 * (sqrt(E**2 + nu) + E)
    t = sqrt(G**2 + (F - nu * G) / (2 * G - E)) - G

    # Compute geodetic latitude, longitude, and altitude (height above ellipse)
    lat = arctan(a * (1.0 - t**2) / (2.0 * b * t))
    lon = arccos(r_i / r_delta) * sign(r_j)  # Sign(r_j) allows for [-pi, pi] range of arccos
    alt = (r_delta - a * t) * cos(lat) + (r_k - b) * sin(lat)

    return asarray([lat, lon, alt])


def rsw2eci(x_eci, x_rsw):
    """Convert a RSW relative state vector to a 6x1 ECI state vector.

    This converts the relative RSW state into an absolute ECI state relative to a given ECI state.
    `R` is the "radial" component, `W` is the "cross-track" component, and `S` is the "along-track"
    component. This should not be confused with NTW which is specifically aligned with the velocity
    vector.

    `R` points out from the satellite along the geocentric radius vector, `W` is normal to the
    orbital plane (not aligned with ECI/ECEF `K`), and `S` is normal to the other axes, positive
    in the direction of velocity.

    See Also:
        Equation (3-20) in Vallado, "Fundamentals of Astrodynamics and Applications", 4th Edition
        on page 164

    Note:
        [TODO]: Unverified conversion

    Args:
        x_eci (`np.ndarray`): 6x1 ECI reference state vector, (km; km/sec)
        x_rsw (`np.ndarray`): 6x1 RSW state vector, relative to `x_eci`, (km; km/sec)

    Returns:
        (`np.ndarray`): 6x1 ECI state vector of the relative state, (km; km/sec)
    """
    r_hat = x_eci[:3] / norm(x_eci[:3])
    w_hat = cross(x_eci[:3], x_eci[3:]) / norm(cross(x_eci[:3], x_eci[3:]))
    s_hat = cross(w_hat, r_hat)

    rsw_2_eci_rotation = asarray([r_hat, s_hat, w_hat]).T
    return concatenate(
        (
            matmul(rsw_2_eci_rotation, x_rsw[:3]),  # Convert position
            matmul(rsw_2_eci_rotation, x_rsw[3:])  # Convert velocity
        ), axis=0
    )


def ntw2eci(x_eci, x_ntw):
    """Convert a NTW relative state vector to a 6x1 ECI state vector.

    This converts the relative NTW state into an absolute ECI state relative to a given ECI state.
    `N` is the "radial" component, `T` is the "in-track", and `W` is the "cross-track" component.
    This should not be confused with RSW which is specifically aligned with the geocentric radius
    vector.

    `N` is normal to the velocity vector (not generally aligned with the radius vector), `T` is
    always parallel to the velocity vector, and `W` is normal to the orbital plane (not aligned
    with ECI/ECEF `K`).

    See Also:
        Equation (3-21) in Vallado, "Fundamentals of Astrodynamics and Applications", 4th Edition
        on page 164

    Note:
        [TODO]: Unverified conversion

    Args:
        x_eci (`np.ndarray`): 6x1 ECI reference state vector, (km; km/sec)
        x_ntw (`np.ndarray`): 6x1 NTW state vector, relative to `x_eci`, (km; km/sec)

    Returns:
        (`np.ndarray`): 6x1 ECI state vector of the relative state, (km; km/sec)
    """
    t_hat = x_eci[3:] / norm(x_eci[3:])
    w_hat = cross(x_eci[:3], x_eci[3:]) / norm(cross(x_eci[:3], x_eci[3:]))
    n_hat = cross(t_hat, w_hat)

    ntw_2_eci_rotation = asarray([n_hat, t_hat, w_hat]).T
    return concatenate(
        (
            matmul(ntw_2_eci_rotation, x_ntw[:3]),  # Convert position
            matmul(ntw_2_eci_rotation, x_ntw[3:])  # Convert velocity
        ), axis=0
    )


def convertToGeodeticLatitude(geocentric_latitude):
    """Convert a geocentric longitude into geodetic latitude.

    See Also:
        Equation (3-11) in Vallado, "Fundamentals of Astrodynamics and Applications", 4th Edition
        on page 140.

    Args:
        geocentric_latitude (float): latitude using geocentric defintion (radians).

    Returns:
        float: latitude using geodetic defintion (radians).
    """
    return arctan(tan(geocentric_latitude) / (1.0 - Earth.eccentricity**2))


def convertToGeocentricLatitude(geodetic_latitude):
    """Convert a geodetic longitude into geocentric latitude.

    See Also:
        Equation (3-11) in Vallado, "Fundamentals of Astrodynamics and Applications", 4th Edition
        on page 140.

    Args:
        geodetic_latitude (float): latitude using geodetic defintion (radians).

    Returns:
        float: latitude using geocentric defintion (radians).
    """
    return arctan((1.0 - Earth.eccentricity**2) * tan(geodetic_latitude))


def getObservationVector(sensor_ecef, tgt_state):
    """Calculate the observation vector in the SEZ frame from the observer to the target.

    Args:
        sensor_ecef (``np.ndarray``): 6x1 ECEF state vector of the :class:`.SensingAgent` (km; km/sec)
        tgt_state (``np.ndarray``): 6x1 ECI state vector of the target :class:`.Agent` (km; km/sec)

    Returns:
        ``np.ndarray``: 6x1 SEZ observation vector (km; km/sec)
    """
    obs_ecef_state = eci2ecef(tgt_state) - sensor_ecef
    lla_state = ecef2lla(sensor_ecef)

    return ecef2sez(obs_ecef_state, lla_state[0], lla_state[1])
