"""Define a collection of common functions used across the orbits package."""

from __future__ import annotations

# Third Party Imports
from numpy import arctan, arctan2, array, cos, cosh, cross, ndarray, sin, sinh, sqrt, vdot
from scipy.linalg import norm

# Local Imports
from ..bodies import Earth
from ..constants import PI, RAD2DEG, TWOPI
from ..maths import fpe_equals, safeArccos, wrapAngle2Pi
from . import (
    EccentricityError,
    InclinationError,
    fixAngleQuadrant,
    isEccentric,
    isInclined,
    wrap_anomaly,
)

# ruff: noqa: N806


def getTrueAnomaly(r_vec: ndarray, v_vec: ndarray, e_unit_vec: ndarray) -> float:
    r"""Calculate an orbit's true anomaly from position, velocity, & eccentricity vectors.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-86

    Args:
        r_vec (``ndarray``): 3x1 ECI position vector, :math:`\vec{r}` (km).
        v_vec (``ndarray``): 3x1 ECI velocity vector, :math:`\vec{v}` (km/s).
        e_unit_vec (``ndarray``): 3x1 eccentricity unit vector, :math:`\hat{e}`.

    Returns:
        ``float``: true anomaly, :math:`\nu\in[0,2\pi)`, in radians.
    """
    anomaly = safeArccos(vdot(e_unit_vec, r_vec) / norm(r_vec))
    return fixAngleQuadrant(anomaly, vdot(r_vec, v_vec))


def getArgumentPerigee(e_unit_vec: ndarray, n_unit_vec: ndarray) -> float:
    r"""Calculate an orbit's argument of perigee from eccentricity & nodal vectors.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-85

    Args:
        e_unit_vec (``ndarray``): 3x1 eccentricity unit vector, :math:`\hat{e}`.
        n_unit_vec (``ndarray``): 3x1 line of nodes unit vector, :math:`\hat{n}`.

    Returns:
        ``float``: argument of perigee, :math:`\omega\in[0,2\pi)`, in radians.
    """
    argp = safeArccos(vdot(n_unit_vec, e_unit_vec))
    return fixAngleQuadrant(argp, e_unit_vec[2])


def getRightAscension(n_unit_vec: ndarray) -> float:
    r"""Calculate an orbit's right ascension of ascending node from the nodal vector.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-84

    Args:
        n_unit_vec (``ndarray``): 3x1 line of nodes unit vector, :math:`\hat{n}`.

    Returns:
        ``float``: right ascension of ascending node, :math:`\Omega\in[0,2\pi)`, in radians.
    """
    raan = safeArccos(n_unit_vec[0])
    return fixAngleQuadrant(raan, n_unit_vec[1])


def getTrueLongitudePeriapsis(e_unit_vec: ndarray) -> float:
    r"""Calculate an orbit's true longitude of periapsis from the eccentricity vector.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-87

    Args:
        e_unit_vec (``ndarray``): 3x1 eccentricity unit vector, :math:`\hat{e}`.

    Returns:
        ``float``: true longitude of periapsis, :math:`\tilde{\omega}_{true}\in[0,2\pi)`, in radians.
    """
    omega_true = safeArccos(e_unit_vec[0])
    return fixAngleQuadrant(omega_true, e_unit_vec[1])


def getArgumentLatitude(r_vec: ndarray, n_unit_vec: ndarray) -> float:
    r"""Calculate an orbit's argument of latitude from position & nodal vectors.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-89

    Args:
        r_vec (``ndarray``): 3x1 ECI position vector, :math:`\vec{r}` (km).
        n_unit_vec (``ndarray``): 3x1 line of nodes unit vector, :math:`\hat{n}`.

    Returns:
        ``float``: argument of latitude, :math:`u\in[0,2\pi)`, in radians.
    """
    arg_lat = safeArccos(vdot(n_unit_vec, r_vec) / norm(r_vec))
    return fixAngleQuadrant(arg_lat, r_vec[2])


def getTrueLongitude(r_vec: ndarray) -> float:
    r"""Calculate an orbit's true longitude from the position vector.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-92

    Args:
        r_vec (``ndarray``): 3x1 ECI position vector, :math:`\vec{r}` (km).

    Returns:
        ``float``: true longitude, :math:`\lambda_{true}\in[0,2\pi)`, in radians.
    """
    # [NOTE]: Super-specific case _may_ exist for pure retrograde orbits. For
    #   some reason, the true longitude is flipped across the x-axis if
    #   inclination is 180 degrees.
    true_long = safeArccos(r_vec[0] / norm(r_vec))
    return fixAngleQuadrant(true_long, r_vec[1])


def getInclinationFromEQE(p: float, q: float, retro: bool = False) -> float:
    r"""Get the orbit inclination from EQE :math:`p` & :math:`q`.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.3, Eqn 2

    Args:
        p (``float``): inclination term, :math:`p=\chi=\tan(\frac{i}{2})\sin(\Omega)`.
        q (``float``): inclination term, :math:`q=\psi=\tan(\frac{i}{2})\cos(\Omega)`.
        retro (``bool``, optional): whether to use the retrograde conversion equations.

    Returns:
        ``float``: orbit inclination, :math:`i\in[0,\pi]`, in radians.
    """
    II = 1 if not retro else -1
    inc = 0.5 * PI * (1 - II) + 2.0 * II * arctan(sqrt(p**2 + q**2))
    if not isInclined(inc) and inc > 0.5 * PI and not retro:
        msg = f"Equatorial retrograde orbit, but retro!=True. inc={inc * RAD2DEG} deg"
        raise InclinationError(msg)
    return inc


def getEccentricityFromEQE(h: float, k: float) -> float:
    r"""Get the orbit eccentricity from EQE :math:`k` & :math:`h`.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.3, Eqn 2

    Args:
        h (``float``): EQE eccentricity term, :math:`h=e\sin(\omega + \Omega)`.
        k (``float``): EQE eccentricity term, :math:`k=e\cos(\omega + \Omega)`.

    Returns:
        ``float``: orbit eccentricity, :math:`e\in[0,1)`, in radians.
    """
    if (ecc := sqrt(h**2 + k**2)) >= 1.0:
        msg = f"Parabolic or hyperbolic orbit. ecc={ecc}"
        raise EccentricityError(msg)
    return ecc


def getEquinoctialBasisVectors(p: float, q: float, retro: bool = False) -> tuple[ndarray, ndarray]:
    r"""Get the equinoctial frame basis vectors from EQE :math:`p` & :math:`q`.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.4, Eqn 1

    Args:
        p (``float``): inclination term, :math:`p=\chi=\tan(\frac{i}{2})\sin(\Omega)`.
        q (``float``): inclination term, :math:`q=\psi=\tan(\frac{i}{2})\cos(\Omega)`.
        retro (``bool``, optional): whether to use the retrograde conversion equations.

    Returns:
        - 3x1 equinoctial basis vector, :math:`\vec{\mathbf{f}}`.
        - 3x1 equinoctial basis vector, :math:`\vec{\mathbf{g}}`.
    """
    II = 1 if not retro else -1
    p_sq, q_sq = p**2, q**2
    # Vector normalization term
    norm_term = 1 / (1 + p_sq + q_sq)

    # Get basis vectors in terms of ECI
    f_vec = norm_term * array([1 - p_sq + q_sq, 2 * p * q, -2 * II * p])
    g_vec = norm_term * array([2 * II * p * q, (1 + p_sq - q_sq) * II, 2 * q])

    return f_vec, g_vec


def getAngularMomentumFromEQE(p: float, q: float, retro: bool = False) -> ndarray:
    r"""Get the angular momentum unit vector from EQE :math:`p` & :math:`q`.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.4, Eqn 1

    Args:
        p (``float``): inclination term, :math:`p=\chi=\tan(\frac{i}{2})\sin(\Omega)`.
        q (``float``): inclination term, :math:`q=\psi=\tan(\frac{i}{2})\cos(\Omega)`.
        retro (``bool``, optional): whether to use the retrograde conversion equations.

    Returns:
        ``ndarray``: 3x1 angular momentum unit vector, :math:`\hat{h}=\hat{w}`.
    """
    II = 1 if not retro else -1
    p_sq, q_sq = p**2, q**2
    return (1 / (1 + p_sq + q_sq)) * array([2 * p, -2 * q, (1 - p_sq - q_sq) * II])


def getAngularMomentum(
    r_vec: ndarray[float, float, float],
    v_vec: ndarray[float, float, float],
) -> ndarray:
    r"""Get the angular momentum vector from position & velocity vectors.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-92

    Args:
        r_vec (``ndarray``): 3x1 ECI position vector, :math:`\vec{r}` (km).
        v_vec (``ndarray``): 3x1 ECI velocity vector, :math:`\vec{v}` (km/s).

    Returns:
        ``ndarray``: 3x1 angular momentum vector, :math:`\vec{h}=\vec{w}`.
    """
    return cross(r_vec, v_vec)


def getLineOfNodes(ang_momentum_vec: ndarray[float, float, float]) -> ndarray:
    r"""Get the line of nodes vector from the angular momentum vector.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-83

    Args:
        ang_momentum_vec (``ndarray``): 3x1 angular momentum vector, :math:`\vec{h}=\vec{w}`.

    Returns:
        ``ndarray``: 3x1 line of nodes vector, :math:`\vec{n}`.
    """
    return cross(array([0, 0, 1], dtype=float), ang_momentum_vec)


def getEccentricity(r_vec: ndarray, v_vec: ndarray, mu: float = Earth.mu) -> tuple[float, ndarray]:
    r"""Get the eccentricity magnitude & unit vector from position & velocity vectors.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-78

    Args:
        r_vec (``ndarray``): 3x1 ECI position vector, :math:`\vec{r}` (km).
        v_vec (``ndarray``): 3x1 ECI velocity vector, :math:`\vec{v}` (km/s).
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.

    Returns:
        ``tuple``: eccentricity, :math:`e`, & 3x1 eccentricity unit vector, :math:`\hat{e}`.
    """
    r, v = norm(r_vec), norm(v_vec)
    ecc_vector = ((v**2 - mu / r) * r_vec - vdot(r_vec, v_vec) * v_vec) / mu
    ecc = norm(ecc_vector)

    # Normalize the eccentricity vector if orbit is eccentric
    if not fpe_equals(ecc, 0.0):
        return ecc, ecc_vector / ecc

    # else
    return ecc, ecc_vector


def getOrbitalEnergy(r: float, v: float, mu: float = Earth.mu) -> float:
    r"""Get the orbital specific energy from orbital radius & speed.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 1-20

    Args:
        r (``float``): orbital radius, :math:`r` (km).
        v (``float``): orbital speed, :math:`v` (km/s).
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.

    Returns:
        ``float``: orbital specific energy, :math:`\xi` (km^2/s^2).
    """
    return 0.5 * v**2 - mu / r


def getSemiMajorAxis(r: float, v: float, mu: float = Earth.mu) -> float:
    r"""Get the semi-major axis from orbital radius & speed.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 1-21

    Args:
        r (``float``): orbital radius, :math:`r` (km).
        v (``float``): orbital speed, :math:`v` (km/s).
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.

    Returns:
        ``float``: semi-major axis, :math:`a` (km).
    """
    energy = getOrbitalEnergy(r, v, mu=mu)
    return -0.5 * mu / energy


def getPeriod(sma: float, mu: float = Earth.mu) -> float:
    r"""Get the orbital period from semi-major axis.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 1-27

    Args:
        sma (``float``): semi-major axis, :math:`a` (km).
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.

    Returns:
        ``float``: orbital period, :math:`P` (sec).
    """
    return TWOPI / getMeanMotion(sma, mu=mu)


def getMeanMotion(sma: float, mu: float = Earth.mu) -> float:
    r"""Get the mean motion from semi-major axis.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-5

    Args:
        sma (``float``): semi-major axis, :math:`a` (km).
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.

    Returns:
        ``float``: mean motion, :math:`n` (rad/s).
    """
    return sqrt(mu / sma**3)


def getSmaFromMeanMotion(mean_motion: float, mu: float = Earth.mu) -> float:
    r"""Get the semi-major axis from the meath motion.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-5

    Args:
        mean_motion(``float``): Mean motion, :math:`n` (rad/s).
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.

    Returns:
        ``float``: semi-major axis, in km.
    """
    return (mu / mean_motion**2) ** (1 / 3.0)


def singularityCheck(
    ecc: float,
    inc: float,
    raan: float,
    argp: float,
    anomaly: float,
) -> tuple[float, float, float]:
    r"""Check and convert angular elements, accounting for COE singularities.

    Args:
        ecc (``float``): eccentricity, :math:`e\in[0,1)`.
        inc (``float``): inclination angle, :math:`i\in[0,\pi]` in radians.
        raan (``float``): right ascension of the ascending node, :math:`\Omega\in[0,2\pi)`, in radians.
        argp (``float``): argument of perigee, :math:`\omega\in[0,2\pi)`, in radians.
        anomaly (``float``): true anomaly (location) angle, :math:`f\in[0,2\pi)`,in radians.

    Returns:
        ``tuple(float)``: adjusted right ascension (:math:`\Omega`), argument of perigee (:math:`\omega`), and
        anomaly (:math:`f`) accounting for singularities in COEs, in radians.
    """
    inclined = isInclined(inc)
    eccentric = isEccentric(ecc)
    if inclined and eccentric:
        return wrapAngle2Pi(raan), wrapAngle2Pi(argp), wrapAngle2Pi(anomaly)

    if not inclined and eccentric:
        # RAAN, Ω, is undefined
        true_long_rp = wrapAngle2Pi(raan + argp)
        return 0.0, true_long_rp, wrapAngle2Pi(anomaly)

    if inclined and not eccentric:
        # Arg. Perigee, ω, is undefined
        arg_lat = wrapAngle2Pi(anomaly + argp)
        return wrapAngle2Pi(raan), 0.0, arg_lat

    # else; Circular and Equatorial
    # RAAN, Ω, and Arg. Perigee, ω, are undefined
    true_long = wrapAngle2Pi(anomaly + argp + raan)
    return 0.0, 0.0, true_long


def retrogradeFactor(inc: float) -> float:
    r"""Determine the retrograde factor that is used in EQE equations.

    .. math::

        I=\left\{\begin{array}{l}
            +1 \\
            -1 \\
        \end{array}\right.

    where :math:`+1` is for direct orbits, and :math:`-1` is for equatorial retrograde orbits.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.2, Eqn 2

    Args:
        inc (``float``): inclination angle, :math:`i\in[0,\pi]` in radians.

    Returns:
        ``float``: retrograde factor, :math:`I`, used in EQE equations.
    """
    return 1 if isInclined(inc) or inc < PI else -1


def universalC2C3(psi: float) -> tuple[float, float]:
    r"""Calculate the Stumpff coefficients for universal variables formulation.

    The coefficients are important for solving the universal variable differential equation defined by:

    .. math::

        \dot{\chi}&=\frac{\sqrt{\mu}}{r} \\
        \psi&=\frac{\chi^2}{a}

    this new universal variable, :math:`\chi`, replaces time as the independent variable in
    equations relating time to orbit properties. This allows algorithms to be applied generically
    for all orbit classes. The other variable, :math:`\psi`, is a convenience that allows the
    Stumpff coefficients to be expressed as simple equations of :math:`\psi`.

    References:
        :cite:t:`vallado_2013_astro`, Algorithm 1

    Args:
        psi (``float``): intermediate variable, :math:`\psi`.

    Returns:
        ``tuple``: universal variable coefficients, :math:`c_2` & :math:`c_3`.
    """
    # Default values: abs(psi) <= 1e-6 ()
    c2: float = 0.5
    c3: float = 1.0 / 6.0
    if psi > 1e-6:  # Elliptical
        c2 = (1 - cos(sqrt(psi))) / psi
        c3 = (sqrt(psi) - sin(sqrt(psi))) / sqrt(psi**3)
    elif psi < -1e-6:  # Hyperbolic
        c2 = (1 - cosh(sqrt(-psi))) / psi
        c3 = (sinh(sqrt(-psi)) - sqrt(-psi)) / sqrt(-(psi**3))

    return c2, c3


@wrap_anomaly
def getFlightPathAngle(ecc: float, true_anom: float) -> float:
    r"""Return the flight path angle given the eccentricity and true anomaly.

    The flight path angle, :math:`\phi_{fpa}\in[0,2\pi)`, is the angle measured from the local horizontal of
    a satellite *to* the velocity vector of a satellite. See Figure 1-13 in
    :cite:t:`vallado_2013_astro`.

    References:
        :cite:t:`vallado_2013_astro`, Section 2.4.1, Eqn 2-95 & 2-96

    Args:
        ecc (``float``): eccentricity, :math:`e`.
        true_anom (``float``): true anomaly, :math:`\nu\in[0,2\pi)`, in radians.

    Returns:
        ``float``: flight path angle, :math:`\phi_{fpa}\in[0,2\pi)`, in radians.
    """
    return arctan2(ecc * sin(true_anom), 1 + ecc * cos(true_anom))


@wrap_anomaly
def getTrueAnomalyFromRV(eci_state: ndarray, mu: float = Earth.mu) -> float:
    """Calculate True Anomaly from an ECI state vector.

    Args:
        eci_state (``ndarray``): 6x1 ECI State Vector
        mu (``float``, optional): Gravitational Constant. Defaults to Earth.mu.

    Returns:
        ``float``: True Anomaly of state vector
    """
    position, velocity = eci_state[:3], eci_state[3:]
    _, ecc_vector = getEccentricity(r_vec=position, v_vec=velocity, mu=mu)
    return getTrueAnomaly(r_vec=position, v_vec=velocity, e_unit_vec=ecc_vector)
