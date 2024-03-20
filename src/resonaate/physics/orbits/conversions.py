"""Defines conversion functions between various orbital element models."""

from __future__ import annotations

# Third Party Imports
from numpy import arccos, arctan2, array, concatenate, cos, ndarray, sin, sqrt, tan, vdot
from scipy.linalg import norm

# Local Imports
from ..bodies import Earth
from ..maths import fpe_equals, rot1, rot3
from . import isEccentric, isInclined
from .anomaly import eccLong2MeanLong, meanLong2EccLong, meanLong2TrueAnom, trueAnom2MeanLong
from .utils import (
    getAngularMomentum,
    getArgumentLatitude,
    getArgumentPerigee,
    getEccentricity,
    getEccentricityFromEQE,
    getEquinoctialBasisVectors,
    getInclinationFromEQE,
    getLineOfNodes,
    getMeanMotion,
    getRightAscension,
    getSemiMajorAxis,
    getTrueAnomaly,
    getTrueLongitude,
    getTrueLongitudePeriapsis,
    singularityCheck,
)

# ruff: noqa: N806

OrbitalElementTuple = tuple[float, float, float, float, float, float]


def coe2eci(
    sma: float,
    ecc: float,
    inc: float,
    raan: float,
    argp: float,
    true_anom: float,
    mu: float = Earth.mu,
) -> ndarray:
    r"""Convert a set of COEs to an ECI (J2000) position and velocity vector.

    References:
        :cite:t:`vallado_2013_astro`, Sections 2-6, Pgs 116-120

    Args:
        sma (``float``): semi-major axis, :math:`a` (km).
        ecc (``float``): eccentricity, :math:`e\in[0,1)`.
        inc (``float``): inclination angle, :math:`i\in[0,\pi]` in radians.
        raan (``float``): right ascension of the ascending node, :math:`\Omega\in[0,2\pi)`, in radians.
        argp (``float``): argument of perigee, :math:`\omega\in[0,2\pi)`, in radians.
        true_anom (``float``): true  anomaly (location) angle, :math:`f\in[0,2\pi)`, in radians.
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.

    Returns:
        ``ndarray``: 6x1 ECI state vector (km; km/sec).
    """
    # Save cos(), sin() of anomaly angle, semi-parameter rectum
    cos_anom, sin_anom = cos(true_anom), sin(true_anom)
    p = sma * (1.0 - ecc**2)

    # Define PQW position, velocity vectors
    r_pqw = p / (1.0 + ecc * cos_anom) * array([cos_anom, sin_anom, 0.0])
    v_pqw = sqrt(mu / p) * array([-sin_anom, ecc + cos_anom, 0.0])

    # Define rotation matrix from PQW to ECI
    rot_pqw2eci = rot3(-raan).dot(rot1(-inc).dot(rot3(-argp)))

    return concatenate([rot_pqw2eci.dot(r_pqw), rot_pqw2eci.dot(v_pqw)], axis=0)


def eci2coe(eci_state: ndarray, mu: float = Earth.mu) -> OrbitalElementTuple:
    r"""Define a set of COEs from a ECI (J2000) position and velocity vector.

    See Also:
        :class:`.ClassicalElements` for discussion on singularities and how the COEs change.

    References:
        :cite:t:`vallado_2013_astro`, Sections 2-5, Pgs 112-116

    Args:
        eci_state (``ndarray``): 6x1 ECI state vector (km; km/sec).
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.

    Returns:
        - sma (``float``): semi-major axis, :math:`a` (km).
        - ecc (``float``): eccentricity, :math:`e\in[0,1)`.
        - inc (``float``): inclination angle, :math:`i\in[0,\pi]` in radians.
        - raan (``float``): right ascension of the ascending node, :math:`\Omega\in[0,2\pi)`, in radians.
        - argp (``float``): argument of perigee, :math:`\omega\in[0,2\pi)`, in radians.
        - true_anom (``float``): true anomaly (location) angle, :math:`f\in[0,2\pi)`, in radians.
    """
    # Get position and velocity vectors
    pos_vec, vel_vec = array(eci_state[:3], copy=True), array(eci_state[3:], copy=True)

    # Semi-major axis
    sma = getSemiMajorAxis(norm(pos_vec), norm(vel_vec), mu=mu)

    # Angular momentum (normal), eccentricity (perigee), & line of nodes vectors
    ang_momentum_vec = getAngularMomentum(pos_vec, vel_vec)
    ecc, ecc_vec = getEccentricity(pos_vec, vel_vec, mu=mu)
    node_vec = getLineOfNodes(ang_momentum_vec)

    # Normalize the line of nodes vectors if orbit is inclined
    n_unit_vec = node_vec / norm(node_vec) if not fpe_equals(norm(node_vec), 0.0) else node_vec

    # Normalize the angular momentum vector
    h_unit_vec = ang_momentum_vec / norm(ang_momentum_vec)

    # Inclination of orbital plane
    inc = arccos(h_unit_vec[2])

    # Orbital type checking
    inclined = isInclined(inc)
    eccentric = isEccentric(ecc)

    # Define parameters specific to orbit types
    if inclined and eccentric:
        raan = getRightAscension(n_unit_vec)
        argp = getArgumentPerigee(ecc_vec, n_unit_vec)
        true_anomaly = getTrueAnomaly(pos_vec, vel_vec, ecc_vec)
        return sma, ecc, inc, raan, argp, true_anomaly

    if not inclined and eccentric:
        true_long_periapsis = getTrueLongitudePeriapsis(ecc_vec)
        true_anomaly = getTrueAnomaly(pos_vec, vel_vec, ecc_vec)
        # RAAN, Ω, is undefined
        return sma, ecc, inc, 0.0, true_long_periapsis, true_anomaly

    if inclined and not eccentric:
        raan = getRightAscension(n_unit_vec)
        arg_lat = getArgumentLatitude(pos_vec, n_unit_vec)
        # Arg. Perigee, ω, is undefined
        return sma, ecc, inc, raan, 0.0, arg_lat

    # else:  # Circular and Equatorial
    true_longitude = getTrueLongitude(pos_vec)
    # RAAN, Ω, and Arg. Perigee, ω, are undefined
    return sma, ecc, inc, 0.0, 0.0, true_longitude


def coe2eqe(
    sma: float,
    ecc: float,
    inc: float,
    raan: float,
    argp: float,
    true_anom: float,
    retro: bool = False,
) -> OrbitalElementTuple:
    r"""Convert an orbit defined by a set of COEs into corresponding EQEs.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.2

    Args:
        sma (``float``): semi-major axis, :math:`a` (km).
        ecc (``float``): eccentricity, :math:`e\in[0,1)`.
        inc (``float``): inclination angle, :math:`i\in[0,\pi]` in radians.
        raan (``float``): right ascension of the ascending node, :math:`\Omega\in[0,2\pi)`, in radians.
        argp (``float``): argument of perigee, :math:`\omega\in[0,2\pi)`, in radians.
        true_anom (``float``): true anomaly (location) angle, :math:`f\in[0,2\pi)`, in radians.
        retro (``bool``, optional): whether to use the retrograde conversion equations.

    Returns:
        - sma (``float``): semi-major axis, :math:`a`, (km).
        - h (``float``): eccentricity term, :math:`h`.
        - k (``float``): eccentricity term, :math:`k`.
        - p (``float``): inclination term, :math:`p=\chi`.
        - q (``float``): inclination term, :math:`q=\psi`.
        - mean_long (``float``): mean longitude (location) angle, :math:`\lambda_M\in[0,2\pi)`, in radians.
    """
    II = 1 if not retro else -1
    h = ecc * sin(argp + II * raan)
    k = ecc * cos(argp + II * raan)
    p = tan(inc * 0.5) ** II * sin(raan)
    q = tan(inc * 0.5) ** II * cos(raan)
    mean_long = trueAnom2MeanLong(true_anom, ecc, raan, argp, retro=retro)
    return sma, h, k, p, q, mean_long


def eqe2coe(
    sma: float,
    h: float,
    k: float,
    p: float,
    q: float,
    mean_long: float,
    retro: bool = False,
) -> OrbitalElementTuple:
    r"""Convert an orbit defined by a set of EQEs into corresponding COEs.

    See Also:
        :class:`.ClassicalElements` for discussion on singularities and how the COEs change.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.3

    Args:
        sma (``float``): semi-major axis, :math:`a`, (km).
        h (``float``): eccentricity term, :math:`h`.
        k (``float``): eccentricity term, :math:`k`.
        p (``float``): inclination term, :math:`p=\chi`.
        q (``float``): inclination term, :math:`q=\psi`.
        mean_long (``float``): mean longitude (location) angle, :math:`\lambda_M\in[0,2\pi)`, in radians.
        retro (``bool``, optional): whether to use the retrograde conversion equations.

    Returns:
        - sma (``float``): semi-major axis, :math:`a` (km).
        - ecc (``float``): eccentricity, :math:`e\in[0,1)`.
        - inc (``float``): inclination angle, :math:`i\in[0,\pi]` in radians.
        - raan (``float``): right ascension of the ascending node, :math:`\Omega\in[0,2\pi)`, in radians.
        - argp (``float``): argument of perigee, :math:`\omega\in[0,2\pi)`, in radians.
        - true_anom (``float``): true anomaly (location) angle, :math:`f\in[0,2\pi)`, in radians.
    """
    II = 1 if not retro else -1
    ecc = getEccentricityFromEQE(h, k)
    inc = getInclinationFromEQE(p, q, retro=retro)
    raan = arctan2(p, q)
    argp = arctan2(h, k) - II * raan
    true_anom = meanLong2TrueAnom(mean_long, ecc, raan, argp, retro=retro)

    raan, argp, true_anom = singularityCheck(ecc, inc, raan, argp, true_anom)
    return sma, ecc, inc, raan, argp, true_anom


def eci2eqe(eci_state: ndarray, mu: float = Earth.mu, retro: bool = False) -> OrbitalElementTuple:
    r"""Define a set of COEs from a ECI (J2000) position and velocity vector.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.5

    Args:
        eci_state (``ndarray``): 6x1 ECI state vector (km; km/sec).
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.
        retro (``bool``, optional): whether to use the retrograde conversion equations.

    Returns:
        - sma (``float``): semi-major axis, :math:`a`, (km).
        - h (``float``): eccentricity term, :math:`h`.
        - k (``float``): eccentricity term, :math:`k`.
        - p (``float``): inclination term, :math:`p=\chi`.
        - q (``float``): inclination term, :math:`q=\psi`.
        - mean_long (``float``): mean longitude (location) angle, :math:`\lambda_M\in[0,2\pi)`, in radians.
    """
    II = 1 if not retro else -1
    # Get position and velocity vectors
    pos_vec, vel_vec = array(eci_state[:3], copy=True), array(eci_state[3:], copy=True)

    # Orbital energy & semi-major axis
    sma = getSemiMajorAxis(norm(pos_vec), norm(vel_vec), mu=mu)

    # Compute angular momentum unit vector
    ang_momentum_vec = getAngularMomentum(pos_vec, vel_vec)
    w_hat = ang_momentum_vec / norm(ang_momentum_vec)

    # Compute p, q equinoctial components
    p = w_hat[0] / (1 + II * w_hat[2])
    q = -w_hat[1] / (1 + II * w_hat[2])

    # Get equinoctial basis vectors using p, q. Already have w_hat
    f_hat, g_hat = getEquinoctialBasisVectors(p, q, retro=retro)

    # Eccentricity vector
    ecc, ecc_vec = getEccentricity(pos_vec, vel_vec, mu=mu)

    # Compute h, k. They use the non-unit eccentricity vector.
    h = vdot(ecc * ecc_vec, g_hat)
    k = vdot(ecc * ecc_vec, f_hat)
    h_sq, k_sq = h**2, k**2

    # Intermediate values for computing mean longitude
    X = vdot(pos_vec, f_hat)
    Y = vdot(pos_vec, g_hat)
    b = 1 / (1 + sqrt(1 - h_sq - k_sq))
    denom = sma * sqrt(1 - h_sq - k_sq)

    # Determine eccentric longitude
    F = arctan2(
        h + ((1 - h_sq * b) * Y - h * k * b * X) / denom,
        k + ((1 - k_sq * b) * X - h * k * b * Y) / denom,
    )

    # Use equinoctial form of Kepler's equation
    mean_long = eccLong2MeanLong(F, h, k)

    return sma, h, k, p, q, mean_long


def eqe2eci(
    sma: float,
    h: float,
    k: float,
    p: float,
    q: float,
    mean_long: float,
    mu: float = Earth.mu,
    retro: bool = False,
) -> ndarray:
    r"""Convert a set of EQEs to an ECI (J2000) position and velocity vector.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.4

    Args:
        sma (``float``): semi-major axis, :math:`a`, (km).
        h (``float``): eccentricity term, :math:`h`.
        k (``float``): eccentricity term, :math:`k`.
        p (``float``): inclination term, :math:`p=\chi`.
        q (``float``): inclination term, :math:`q=\psi`.
        mean_long (``float``): mean longitude (location) angle, :math:`\lambda_M\in[0,2\pi)`, in radians.
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.
        retro (``bool``, optional): whether to use the retrograde conversion equations.

    Returns:
        ``ndarray``: 6x1 ECI state vector (km; km/sec).
    """
    # Common intermediate terms
    h_sq, k_sq = h**2, k**2
    n = getMeanMotion(sma, mu=mu)
    b = 1 / (1 + sqrt(1 - h_sq - k_sq))
    hkb = h * k * b

    # Find eccentric longitude from mean longitude
    F = meanLong2EccLong(mean_long, h, k)
    sinF, cosF = sin(F), cos(F)

    # Radial distance & velocity magnitude
    r = sma * (1 - h * sinF - k * cosF)
    vel_term = n * sma**2 / r

    # Compute position & velocity components in equinoctial frame
    x = sma * ((1 - h_sq * b) * cosF + hkb * sinF - k)
    y = sma * ((1 - k_sq * b) * sinF + hkb * cosF - h)
    x_dot = vel_term * (hkb * cosF - (1 - h_sq * b) * sinF)
    y_dot = vel_term * ((1 - k_sq * b) * cosF - hkb * sinF)

    # Get equinoctial basis vectors in ECI
    f_hat, g_hat = getEquinoctialBasisVectors(p, q, retro=retro)

    # Use equinoctial basis vectors to convert position and velocity into ECI
    return concatenate(
        [
            x * f_hat + y * g_hat,  # Position vector
            x_dot * f_hat + y_dot * g_hat,  # Velocity vector
        ],
        axis=0,
    )
