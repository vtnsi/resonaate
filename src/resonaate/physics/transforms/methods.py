"""Defines reference frame & coordinate system conversion functions."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import (
    arccos,
    arcsin,
    arctan,
    arctan2,
    asarray,
    concatenate,
    cos,
    cross,
    diagflat,
    dot,
    finfo,
    float64,
    matmul,
    sign,
    sin,
    sqrt,
    tan,
)
from scipy.linalg import norm

# Local Imports
from .. import constants as const
from ..bodies import Earth
from ..math import rot2, rot3, wrapAngle2Pi
from .reductions import getReductionParameters

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...sensors.sensor_base import ObservationTuple


def eci2ecef(x_eci):
    """Convert an ECI state vector into an ECEF state vector.

    References:
        :cite:t:`vallado_2013_astro`, Sections 3.7 - 3.7.2

    Note:
        `updateReductionParameters()` **must** be called before this can be used.

    Args:
        x_eci (``np.ndarray``): 6x1 ECI state vector, (km; km/sec)

    Returns:
        (``np.ndarray``): 6x1 ECEF state vector, (km; km/sec)
    """
    reduction = getReductionParameters()
    r_ecef = matmul(reduction["rot_wt"], matmul(reduction["rot_rnp"], x_eci[:3]))
    om_earth = asarray([0, 0, Earth.spin_rate * (1 - reduction["lod"] / 86400.0)])
    v_correction = cross(om_earth, matmul(reduction["rot_w"], r_ecef))
    v_ecef = matmul(reduction["rot_wt"], matmul(reduction["rot_rnp"], x_eci[3:]) - v_correction)

    return concatenate((r_ecef, v_ecef), axis=0)


def ecef2eci(x_ecef):
    """Convert an ECEF state vector into an ECI state vector.

    References:
        :cite:t:`vallado_2013_astro`, Sections 3.7 - 3.7.2

    Note:
        `updateReductionParameters()` **must** be called before this can be used.

    Args:
        x_eci (``np.ndarray``): 6x1 ECEF state vector, (km; km/sec)

    Returns:
        (``np.ndarray``): 6x1 ECI state vector, (km; km/sec)
    """
    reduction = getReductionParameters()
    r_eci = matmul(reduction["rot_pnr"], matmul(reduction["rot_w"], x_ecef[:3]))
    om_earth = asarray([0, 0, Earth.spin_rate * (1 - reduction["lod"] / 86400.0)])
    v_correction = cross(om_earth, matmul(reduction["rot_w"], x_ecef[:3]))
    v_eci = matmul(reduction["rot_pnr"], matmul(reduction["rot_w"], x_ecef[3:]) + v_correction)

    return concatenate((r_eci, v_eci), axis=0)


def sez2ecef(x_sez, lat, lon):
    """Convert an SEZ state vector into an ECEF state vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.4.3, Eqn 3-28

    Note:
        This assumes the ECEF state vector is **relative** to the observer.

    Args:
        x_sez (``np.ndarray``): 6x1 SEZ state vector, (km; km/sec)
        lat (``float``): scalar geodetic latitude, (radians)
        lon (``float``): scalar longitude, (radians)

    Returns:
        (``np.ndarray``): 6x1 ECEF state vector, (km; km/sec)
    """
    sez_2_ecef_rotation = matmul(rot3(-lon), rot2(lat - const.PI / 2))
    return concatenate(
        (
            matmul(sez_2_ecef_rotation, x_sez[:3]),  # Convert position
            matmul(sez_2_ecef_rotation, x_sez[3:]),  # Convert velocity
        ),
        axis=0,
    )


def ecef2sez(x_ecef, lat, lon):
    """Convert an ECEF state vector into an SEZ state vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.4.3, Eqn 3-28

    Note:
        This assumes the ECEF state vector is **relative** to the observer.

    Args:
        x_ecef (``np.ndarray``): 6x1 ECEF state vector, (km; km/sec)
        lat (``float``): scalar geodetic latitude, (radians)
        lon (``float``): scalar longitude, (radians)

    Returns:
        (``np.ndarray``): 6x1 SEZ state vector, (km; km/sec)
    """
    ecef_2_sez_rotation = matmul(rot2(const.PI / 2 - lat), rot3(lon))
    return concatenate(
        (
            matmul(ecef_2_sez_rotation, x_ecef[:3]),  # Convert position
            matmul(ecef_2_sez_rotation, x_ecef[3:]),  # Convert velocity
        ),
        axis=0,
    )


def eci2sez(x_eci, lat, lon):
    """Convert an ECI state vector into an SEZ state vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.4.3, Eqn 3-28

    Note:
        This assumes the ECI state vector is **relative** to the observer.

    Args:
        x_eci (``np.ndarray``): 6x1 ECI state vector, (km; km/sec)
        lat (``float``): scalar geodetic latitude, (radians)
        lon (``float``): scalar longitude, (radians)

    Returns:
        (``np.ndarray``): 6x1 SEZ state vector, (km; km/sec)
    """
    return ecef2sez(eci2ecef(x_eci), lat, lon)


def sez2eci(x_sez, lat, lon):
    """Convert an SEZ state vector into an ECI state vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.4.3, Eqn 3-28

    Note:
        This assumes the ECI state vector is **relative** to the observer.

    Args:
        x_sez (``np.ndarray``): 6x1 SEZ state vector, (km; km/sec)
        lat (``float``): scalar geodetic latitude, (radians)
        lon (``float``): scalar longitude, (radians)

    Returns:
        (``np.ndarray``): 6x1 ECI state vector, (km; km/sec)
    """
    return ecef2eci(sez2ecef(x_sez, lat, lon))


def lla2ecef(x_lla):
    """Convert a latitude, longitude, and altitude to a 6x1 ECEF state vector.

    References:
        #. :cite:t:`vallado_2013_astro`, Section 7.2.1, Algorithm 51
        #. :cite:t:`vallado_2013_astro`, Section 3.2.2, Eqn 3-7

    Altitude is height above ellipsoid, and latitude is geodetic latitude.

    Args:
        x_lla (``np.ndarray``): 3x1 of latitude, longitude, and altitude, (radians, radians, km)

    Returns:
        (``np.ndarray``): 6x1 ECEF state vector, (km; km/sec)
    """
    lat, lon, alt = x_lla[0], x_lla[1], x_lla[2]

    # Geodesy Calculation: Radius of Curvature in Prime Vertical and Auxiliary Variables
    radius_pv = Earth.radius / sqrt(1 - Earth.eccentricity**2 * sin(lat) ** 2)
    radius_aux = (1 - Earth.eccentricity**2) * radius_pv

    # Horizontal component along semi-major axis & vertical component parallel to semi-minor axis
    r_delta = (radius_pv + alt) * cos(lat)
    r_k = (radius_aux + alt) * sin(lat)

    # Final ECEF Calculation relating ECEF to Geodetic Latitude, Longitude, and Altitude
    return asarray([r_delta * cos(lon), r_delta * sin(lon), r_k, 0, 0, 0])


def ecef2lla(x_ecef):
    """Convert an ECEF state vector to latitude, longitude, and altitude.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.4.4, Algorithm 13

    Altitude is height above ellipsoid, and latitude is geodetic latitude.

    Args:
        x_ecef (``np.ndarray``): 6x1 ECEF state vector, (km; km/sec)

    Returns:
        (``np.ndarray``): 3x1 of latitude, longitude, and altitude, (radians, radians, km)
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
    b = a * sqrt(1 - Earth.eccentricity**2)
    if r_k != 0:
        b *= sign(r_k)

    # Intermediate parameters
    E = (b * r_k - (a**2 - b**2)) / (a * r_delta)
    F = (b * r_k + (a**2 - b**2)) / (a * r_delta)
    P = 4.0 * (E * F + 1) / 3.0
    Q = 2.0 * (E**2 - F**2)
    D = P**3 + Q**2
    if D >= 0:
        nu = (sqrt(D) - Q) ** (1.0 / 3) - (sqrt(D) + Q) ** (1.0 / 3)
    else:
        nu = 2.0 * sqrt(-P) * cos(arccos(Q / (P * sqrt(-P))) / 3.0)
    G = 0.5 * (sqrt(E**2 + nu) + E)
    t = sqrt(G**2 + (F - nu * G) / (2 * G - E)) - G

    # Compute geodetic latitude, longitude, and altitude (height above ellipse)
    lat = arctan(a * (1.0 - t**2) / (2.0 * b * t))
    lon = arctan2(r_j, r_i)
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

    References:
        :cite:t:`vallado_2013_astro`, Section 3.4.1, Eqn 3-20

    Args:
        x_eci (``np.ndarray``): 6x1 ECI reference state vector, (km; km/sec)
        x_rsw (``np.ndarray``): 6x1 RSW state vector, relative to `x_eci`, (km; km/sec)

    Returns:
        (``np.ndarray``): 6x1 ECI state vector of the relative state, (km; km/sec)
    """
    r_hat = x_eci[:3] / norm(x_eci[:3])
    w_hat = cross(x_eci[:3], x_eci[3:]) / norm(cross(x_eci[:3], x_eci[3:]))
    s_hat = cross(w_hat, r_hat)

    rsw_2_eci_rotation = asarray([r_hat, s_hat, w_hat]).T
    return concatenate(
        (
            matmul(rsw_2_eci_rotation, x_rsw[:3]),  # Convert position
            matmul(rsw_2_eci_rotation, x_rsw[3:]),  # Convert velocity
        ),
        axis=0,
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

    References:
        :cite:t:`vallado_2013_astro`, Section 3.4.1, Eqn 3-21

    Args:
        x_eci (``np.ndarray``): 6x1 ECI reference state vector, (km; km/sec)
        x_ntw (``np.ndarray``): 6x1 NTW state vector, relative to `x_eci`, (km; km/sec)

    Returns:
        (``np.ndarray``): 6x1 ECI state vector of the relative state, (km; km/sec)
    """
    t_hat = x_eci[3:] / norm(x_eci[3:])
    w_hat = cross(x_eci[:3], x_eci[3:]) / norm(cross(x_eci[:3], x_eci[3:]))
    n_hat = cross(t_hat, w_hat)

    ntw_2_eci_rotation = asarray([n_hat, t_hat, w_hat]).T
    return concatenate(
        (
            matmul(ntw_2_eci_rotation, x_ntw[:3]),  # Convert position
            matmul(ntw_2_eci_rotation, x_ntw[3:]),  # Convert velocity
        ),
        axis=0,
    )


def radarObs2eciPosition(obs_tuple: ObservationTuple) -> ndarray:
    """Convert Radar observation from RAZEL to ECI position vector.

    Args:
        obs_tuple (:class:`.ObservationTuple`): `ObservationTuple` associated with observation

    Returns:
        ``ndarray``: 3x1 ECI Position State based on radar observation
    """
    range_ = obs_tuple.observation.range_km
    azimuth = obs_tuple.observation.azimuth_rad
    elevation = obs_tuple.observation.elevation_rad
    x_j2000_relative = sez2eci(
        x_sez=razel2sez(range_, elevation, azimuth, 0, 0, 0),
        lat=obs_tuple.observation.position_lat_rad,
        lon=obs_tuple.observation.position_long_rad,
    )
    # [NOTE]: Only valid for positions
    return x_j2000_relative[:3] + obs_tuple.agent.eci_state[:3]


def spherical2cartesian(rho, theta, phi, rho_dot, theta_dot, phi_dot):
    """Conversion of spherical coordinates to cartesian coordinates.

    This will convert spherical coordinates to cartesian coordinates in the same reference frame.
    This does **not** convert reference frames.

    References:
        :cite:t:`vallado_2015_aiaa_transformations`

    Note:
        This uses the physics form of spherical coordinates:
        - `rho` is the radial distance, measured from origin
        - `theta` is the elevation angle, measured positive north from the reference plane
        - `phi` is the azimuthal angle, measured positive from the initial meridian plane

    Args:
        rho (``float``): radial distance >=0 (km)
        theta (``float``): elevation angle [-pi/2, pi/2] (radians)
        phi (``float``): azimuthal angle [0, 2pi] (radians)
        rho_dot (`float`): radial distance rate (km/sec)
        theta_dot (``float``): polar angular rate (rad/sec)
        phi_dot (``float``): azimuthal angular rate (rad/sec)

    Returns:
        ``np.ndarray``: 6x1 cartesian state vector in corresponding reference frame.
    """
    c_phi, c_th, s_phi, s_th = cos(phi), cos(theta), sin(phi), sin(theta)
    return asarray(
        [
            rho * c_th * c_phi,
            rho * c_th * s_phi,
            rho * s_th,
            rho_dot * c_th * c_phi - rho * s_th * c_phi * theta_dot - rho * c_th * s_phi * phi_dot,
            rho_dot * c_th * s_phi - rho * s_th * s_phi * theta_dot + rho * c_th * c_phi * phi_dot,
            rho_dot * s_th + rho * c_th * theta_dot,
        ]
    )


def cartesian2spherical(state):
    """Conversion of cartesian coordinates to spherical coordinates.

    This will convert cartesian coordinates to spherical coordinates in the same reference frame.
    This does **not** convert reference frames.

    References:
        :cite:t:`vallado_2015_aiaa_transformations`

    Note:
        This uses the physics form of spherical coordinates:
        - `rho` is the radial distance, measured from origin
        - `theta` is the elevation angle, measured positive north from the reference plane
        - `phi` is the azimuthal angle, measured positive from the initial meridian plane

    Args:
        state (``np.ndarray``): 6x1 cartesian state vector in corresponding reference frame.

    Returns:
        rho (``float``): radial distance >=0 (km)
        theta (``float``): elevation angle [-pi/2, pi/2] (radians)
        phi (``float``): azimuthal angle [0, 2pi] (radians)
        rho_dot (`float`): radial distance rate (km/sec)
        theta_dot (``float``): polar angular rate (rad/sec)
        phi_dot (``float``): azimuthal angular rate (rad/sec)
    """
    r_i, r_j, r_k = state[0], state[1], state[2]
    v_i, v_j, v_k = state[3], state[4], state[5]

    rng = norm(state[:3])
    temp1 = sqrt(r_i**2 + r_j**2)
    temp2 = sqrt(v_i**2 + v_j**2)
    temp3 = r_k / rng
    theta = arcsin(temp3)
    rng_dot = dot(state[:3], state[3:]) / rng
    if temp1 != 0:
        phi = arctan2(r_j / temp1, r_i / temp1)
        theta_dot = (v_k - rng_dot * temp3) / temp1
        phi_dot = (v_i * r_j - v_j * r_i) / (-(r_j**2) - r_i**2)
    else:
        phi = arctan2(v_j / temp2, v_i / temp2)
        theta_dot = 0  # In-determinant without accelerations
        phi_dot = 0  # In-determinant without accelerations

    return rng, theta, wrapAngle2Pi(phi), rng_dot, theta_dot, phi_dot


def razel2sez(rng, el, az, rng_rate, el_rate, az_rate):
    """Convert az, el, rng, & rates to a topocentric horizon slant range vector.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Eqn 4-4 & 4-5

    Args:
        rng (``float``): topocentric horizon range to target (km)
        el (``float``): topocentric horizon elevation angle [-pi/2, pi/2] (radians)
        az (``float``): topocentric horizon azimuth angle [0, 2pi] (radians)
        rng_rate (``float``): topocentric horizon range rate of target (km/sec)
        el_rate (``float``): topocentric horizon elevation angular rate (radians/sec)
        az_rate (``float``): topocentric horizon azimuth angular rate (radians/sec)

    Returns:
        ``np.ndarray``: 6x1 topocentric horizon slant range vector, SEZ (km; km/sec).
    """
    # pylint: disable=invalid-name
    return spherical2cartesian(rng, el, az, rng_rate, el_rate, az_rate).dot(
        diagflat([-1, 1, 1, -1, 1, 1])
    )


def razel2radec(rng, el, az, rng_rate, el_rate, az_rate, observer_eci):
    """Convert az, el, rng, & rates to topocentric ra, dec, rng, & rates.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.4

    Args:
        rng (``float``): topocentric horizon range to target (km)
        el (``float``): topocentric horizon elevation angle [-pi/2, pi/2] (radians)
        az (``float``): topocentric horizon azimuth angle [0, 2pi] (radians)
        rng_rate (``float``): topocentric horizon range rate of target (km/sec)
        el_rate (``float``): topocentric horizon elevation angular rate (radians/sec)
        az_rate (``float``): topocentric horizon azimuth angular rate (radians/sec)
        observer_eci (``np.ndarray``): 6x1 ECI state vector of observer (km; km/sec)

    Returns:
        rng (``float``): topocentric equatorial range to target (km)
        dec (``float``): topocentric equatorial declination angle [-pi/2, pi/2] (radians)
        ra (``float``): topocentric equatorial right ascension angle [0, 2pi] (radians)
        rng_rate (``float``): topocentric equatorial range rate of target (km/sec)
        dec_rate (``float``): topocentric equatorial declination angular rate (radians/sec)
        ra_rate (``float``): topocentric equatorial right ascension angular rate (radians/sec)
    """
    # pylint: disable=invalid-name
    observer_ecef = eci2ecef(observer_eci)
    observer_lla = ecef2lla(observer_ecef)
    tgt_ecef = observer_ecef + sez2ecef(
        razel2sez(rng, el, az, rng_rate, el_rate, az_rate), observer_lla[0], observer_lla[1]
    )
    return cartesian2spherical(ecef2eci(tgt_ecef) - observer_eci)


def radec2razel(rng, dec, ra, rng_rt, dec_rt, ra_rt, observer_eci):
    """Convert topocentric ra, dec, rng, & rates to az, el, rng, & rates.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 4-1 & 4-2

    Args:
        rng (``float``): topocentric equatorial range to target (km)
        dec (``float``): topocentric equatorial declination angle [-pi/2, pi/2] (radians)
        ra (``float``): topocentric equatorial right ascension angle [0, 2pi] (radians)
        rng_rate (``float``): topocentric equatorial range rate of target (km/sec)
        dec_rate (``float``): topocentric equatorial declination angular rate (radians/sec)
        ra_rate (``float``): topocentric equatorial right ascension angular rate (radians/sec)
        observer_eci (``np.ndarray``): 6x1 ECI state vector of observer (km; km/sec)

    Returns:
        rng (``float``): topocentric horizon range to target (km)
        el (``float``): topocentric horizon elevation angle [-pi/2, pi/2] (radians)
        az (``float``): topocentric horizon azimuth angle [0, 2pi] (radians)
        rng_rate (``float``): topocentric horizon range rate of target (km/sec)
        el_rate (``float``): topocentric horizon elevation angular rate (radians/sec)
        az_rate (``float``): topocentric horizon azimuth angular rate (radians/sec)
    """
    # pylint: disable=invalid-name
    target_eci = spherical2cartesian(rng, dec, ra, rng_rt, dec_rt, ra_rt) + observer_eci
    return eci2razel(target_eci, observer_eci)


def eci2razel(target_eci, observer_eci):
    """Convert target and observer ECI states into az, el, rng, & rates.

    References:
        :cite:t:`vallado_2013_astro`, Algorithm 27

    Args:
        target_eci (``np.ndarray``): 6x1 ECI state vector of target
        observer_eci (``np.ndarray``): 6x1 ECI state vector of observer

    Returns:
        rng (``float``): topocentric horizon range to target (km)
        el (``float``): topocentric horizon elevation angle [-pi/2, pi/2] (radians)
        az (``float``): topocentric horizon azimuth angle [0, 2pi] (radians)
        rng_rate (``float``): topocentric horizon range rate of target (km/sec)
        el_rate (``float``): topocentric horizon elevation angular rate (radians/sec)
        az_rate (``float``): topocentric horizon azimuth angular rate (radians/sec)
    """
    return sez2razel(getSlantRangeVector(eci2ecef(observer_eci), target_eci))


def sez2razel(slant_range_sez):
    """Convert topocentric horizon slant range vector into az, el, rng, & rates.

    References:
        :cite:t:`vallado_2013_astro`, Algorithm 27

    Args:
        slant_range_sez (``np.ndarray``): 6x1 topocentric horizon slant range vector, SEZ (km; km/sec).

    Returns:
        rng (``float``): topocentric horizon range to target (km)
        el (``float``): topocentric horizon elevation angle [-pi/2, pi/2] (radians)
        az (``float``): topocentric horizon azimuth angle [0, 2pi] (radians)
        rng_rate (``float``): topocentric horizon range rate of target (km/sec)
        el_rate (``float``): topocentric horizon elevation angular rate (radians/sec)
        az_rate (``float``): topocentric horizon azimuth angular rate (radians/sec)
    """
    return cartesian2spherical(slant_range_sez.dot(diagflat([-1, 1, 1, -1, 1, 1])))


def geocentric2geodetic(geocentric_latitude):
    """Convert a geocentric longitude into geodetic latitude.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.2.2, Eqn 3-11

    Args:
        geocentric_latitude (``float``): latitude using geocentric definition [-pi/2, pi/2] (radians).

    Returns:
        ``float``: latitude using geodetic definition [-pi/2, pi/2] (radians).
    """
    return arctan(tan(geocentric_latitude) / (1.0 - Earth.eccentricity**2))


def geodetic2geocentric(geodetic_latitude):
    """Convert a geodetic longitude into geocentric latitude.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.2.2, Eqn 3-11

    Args:
        geodetic_latitude (``float``): latitude using geodetic definition [-pi/2, pi/2] (radians).

    Returns:
        ``float``: latitude using geocentric definition [-pi/2, pi/2] (radians).
    """
    return arctan((1.0 - Earth.eccentricity**2) * tan(geodetic_latitude))


def getSlantRangeVector(sensor_ecef, tgt_state):
    """Calculate the slant range vector in the SEZ frame from the observer to the target.

    References:
        :cite:t:`vallado_2013_astro`, Section 4.4.3, Eqn 4-6

    Args:
        sensor_ecef (``np.ndarray``): 6x1 ECEF state vector of the :class:`.SensingAgent` (km; km/sec)
        tgt_state (``np.ndarray``): 6x1 ECI state vector of the :class:`TargetAgent` (km; km/sec)

    Returns:
        ``np.ndarray``: 6x1 SEZ slant range vector (km; km/sec)
    """
    lla_state = ecef2lla(sensor_ecef)
    return ecef2sez(eci2ecef(tgt_state) - sensor_ecef, lla_state[0], lla_state[1])
