"""Defines methods of solving Kepler's Equation & Kepler's Problem."""

from __future__ import annotations

# Third Party Imports
from numpy import (
    arctan,
    array,
    concatenate,
    cos,
    fabs,
    isclose,
    log,
    ndarray,
    power,
    sign,
    sin,
    sqrt,
    tan,
    vdot,
)
from scipy.linalg import norm
from scipy.optimize import newton

# Local Imports
from ...common.logger import resonaateLogError
from ..bodies import Earth
from ..constants import KM2M, PI
from ..maths import _ATOL, _MAX_ITER
from .utils import getAngularMomentum, universalC2C3

# ruff: noqa: N803


class KeplerProblemError(Exception):
    r"""Exception indicating that Kepler's problem solver didn't converge."""


class KeplerEquationError(Exception):
    r"""Exception indicating that Kepler's equation solver didn't converge."""


def _keplerEquation(E: float, M: float, ecc: float) -> float:
    r"""Kepler's equation, formatted for root-finding.

    Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-51.

    Args:
        E (``float``): eccentric anomaly, :math:`E`, in radians.
        M (``float``): mean anomaly, :math:`M`, in radians.
        ecc (``float``): eccentricity, :math:`e`.

    Returns:
        ``float``: zero of Kepler's equation, :math:`E - e \sin{E} - M=0`.
    """
    return E - ecc * sin(E) - M


def _keplerEquationDerivative(E: float, M: float, ecc: float) -> float:
    r"""Derivate of Kepler's equation, formatted for root-finding.

    Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-51.

    Args:
        E (``float``): eccentric anomaly, :math:`E`, in radians.
        M (``float``): mean anomaly, :math:`M`, in radians.
        ecc (``float``): eccentricity, :math:`e`.

    Returns:
        ``float``: derivate of Kepler's equation, :math:`1 - e\cos{E}`.
    """
    return 1 - ecc * cos(E)


def _equinoctialKeplerEquation(F: float, h: float, k: float, lam: float) -> float:
    r"""Kepler's equation (equinoctial form), formatted for root-finding.

    Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`danielson_1995_sast`, Section 7.1, Eqn 1

    Args:
        F (``float``): eccentric longitude, :math:`F`, in radians.
        h (``float``): EQE eccentricity term, :math:`h=e\sin(\omega + \Omega)`.
        k (``float``): EQE eccentricity term, :math:`k=e\cos(\omega + \Omega)`.
        lam (``float``): mean longitude, :math:`\lambda=M + \omega + \Omega`, in radians.

    Returns:
        ``float``: zero of equinoctial Kepler's equation, :math:`F + h\cos{F} - k\sin{F} - \lambda=0`.
    """
    return F + h * cos(F) - k * sin(F) - lam


def _equinoctialKeplerEquationDerivative(F: float, h: float, k: float, lam: float) -> float:
    r"""Derivate of Kepler's equation (equinoctial form), formatted for root-finding.

    Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`danielson_1995_sast`, Section 7.1, Eqn 2

    Args:
        F (``float``): eccentric longitude, :math:`F`, in radians.
        h (``float``): EQE eccentricity term, :math:`h=e\sin(\omega + \Omega)`.
        k (``float``): EQE eccentricity term, :math:`k=e\cos(\omega + \Omega)`.
        lam (``float``): mean longitude, :math:`\lambda=M + \omega + \Omega`, in radians.

    Returns:
        ``float``: derivate of equinoctial Kepler's equation, :math:`1 - h\sin{F} - k\cos{F}`.
    """
    return 1 - h * sin(F) - k * cos(F)


def keplerSolveCOE(
    E_0: float,
    M: float,
    ecc: float,
    tol: float = _ATOL,
    maxiter: int = _MAX_ITER,
    raise_err: bool = True,
) -> float:
    r"""Solve Kepler's equation via Newton-Raphson.

    The mean anomaly is required to be :math:`M\in[-2\pi, 2\pi]`. Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`vallado_2013_astro`, Algorithm 2

    Args:
        E_0 (``float``): initial guess for eccentric anomaly, :math:`E_0`, in radians.
        M (``float``): mean anomaly, :math:`M`, in radians.
        ecc (``float``): eccentricity, :math:`e`.
        tol (``float``, optional): allowable error in zero value to determine convergence. Defaults to :data:`._ATOL`.
        maxiter (``int``, optional): maximum number of allowable iterations to determine
            non-convergence. Defaults to :data:`._MAX_ITER`.
        raise_err (``bool``, optional): If True, raise a RuntimeError if the algorithm didn't converge,
            with the error message containing the number of iterations and current function value.

    Returns:
        ``float``: ``np.nan`` or converged value of eccentric anomaly, :math:`E`, in radians.
    """
    return newton(
        _keplerEquation,
        E_0,
        fprime=_keplerEquationDerivative,
        args=(M, ecc),
        tol=tol,
        maxiter=maxiter,
        disp=raise_err,
    )


def keplerSolveEQE(
    F_0: float,
    h: float,
    k: float,
    lam: float,
    tol: float = _ATOL,
    maxiter: int = _MAX_ITER,
    raise_err: bool = True,
) -> float:
    r"""Solve the equinoctial form of Kepler's equation via Newton-Raphson.

    Only valid for elliptical orbits: :math:`e < 1`. The initial guess for eccentric longitude is required to
    be :math:`E\in[-2\pi, 2\pi]`.

    References:
        #. :cite:t:`vallado_2013_astro`, Algorithm 2
        #. :cite:t:`danielson_1995_sast`, Section 7.1

    Args:
        F_0 (``float``): initial guess for eccentric longitude, :math:`F_0`, in radians.
        h (``float``): EQE eccentricity term, :math:`h=e\sin(\omega + \Omega)`.
        k (``float``): EQE eccentricity term, :math:`k=e\cos(\omega + \Omega)`.
        lam (``float``): mean longitude, :math:`\lambda=M + \omega + \Omega` (radians).
        tol (``float``, optional): allowable error in zero value to determine convergence. Defaults to :data:`._ATOL`.
        maxiter (``int``, optional): maximum number of allowable iterations to determine
            non-convergence. Defaults to :data:`._MAX_ITER`.
        raise_err (``bool``, optional): If True, raise a RuntimeError if the algorithm didn't converge,
            with the error message containing the number of iterations and current function value.

    Returns:
        ``float``: ``np.nan`` or converged value of eccentric anomaly, :math:`F`,  in radians.
    """
    return newton(
        _equinoctialKeplerEquation,
        F_0,
        fprime=_equinoctialKeplerEquationDerivative,
        args=(h, k, lam),
        tol=tol,
        maxiter=maxiter,
        disp=raise_err,
    )


def solveKeplerProblemUniversal(
    init_state: ndarray,
    tof: float,
    mu: float = Earth.mu,
    tol: float = _ATOL,
    maxiter: int = _MAX_ITER,
) -> ndarray:
    r"""Solver Kepler's problem using the universal variables formulation.

    Kepler's problem is that of propagating an initial state vector forward in time given a time of flight.
    This problem assumes a Two Body (Keplerian) dynamics model.

    References:
        #. :cite:t:`vallado_2013_astro`, Algorithm 8

    Raises:
        :class:`.KeplerProblemError`: if the Newton iteration doesn't converge before ``maxiter``
            iterations or if the converged solution fails an angular momentum check.

    Args:
        init_state (``ndarray``): 6x1 ECI initial state vector (km; km/sec).
        tof (``float``): time of flight through which the state should be propagated (sec).
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.
        tol (``float``, optional): allowable error in zero value to determine convergence. Defaults to :data:`._ATOL`.
        maxiter (``int``, optional): maximum number of allowable iterations to determine
            non-convergence. Defaults to :data:`._MAX_ITER`.

    Returns:
        ``ndarray``: 6x1 ECI state vector after propagating through the time of flight (km; km/sec).
    """
    r0, v0 = array(init_state[:3], copy=True), array(init_state[3:], copy=True)
    alpha = -norm(v0) ** 2 / mu + 2.0 / norm(r0)
    sqrt_mu = sqrt(mu)
    if alpha > 1e-6:
        chi = sqrt_mu * tof * alpha
    if fabs(alpha) < 1e-6:
        p = norm(getAngularMomentum(r0, v0)) ** 2 / mu
        s = 0.5 * arctan(1 / (3 * sqrt_mu / p**3 * tof))
        chi = sqrt(p) * 2 / tan(2 * arctan(power(tan(s), 1 / 3)))
    if alpha < -1e-6:
        sqrt_a = sqrt(-1 / alpha)
        chi = (
            sign(tof)
            * sqrt_a
            * log(
                (-2 * mu * alpha * tof)
                / (vdot(r0, v0) + sign(tof) * sqrt_mu * sqrt_a * (1 - norm(r0) * alpha)),
            )
        )

    for ii in range(maxiter):  # noqa: B007
        # Get Stumpff coefficients & temporary variables
        chi_sq = chi**2
        psi = chi_sq * alpha
        c2, c3 = universalC2C3(psi)
        tmp = 1 - psi * c3
        # Perform iteration of Kepler's problem
        r = chi_sq * c2 + vdot(r0, v0) / sqrt_mu * chi * tmp + norm(r0) * (1 - psi * c2)
        chi_old = chi
        chi += (
            sqrt_mu * tof
            - chi**3 * c3
            - vdot(r0, v0) / sqrt_mu * chi_sq * c2
            - norm(r0) * chi * tmp
        ) / r
        if isclose(chi, chi_old, rtol=0.0, atol=tol):
            break

    if ii + 1 == maxiter:
        msg = f"Kepler's problem didn't converge in {ii} iterations"
        resonaateLogError(msg)
        raise KeplerProblemError(msg)

    f = 1 - chi**2 / norm(r0) * c2
    fdot = sqrt_mu / (r * norm(r0)) * chi * (psi * c3 - 1)
    g = tof - chi**3 / sqrt_mu * c3
    gdot = 1 - chi**2 / r * c2
    if not isclose(f * gdot - fdot * g, 1.0, rtol=0.0, atol=min(tol, 1e-6)):
        msg = "Kepler's problem solution failed angular momentum check"
        resonaateLogError(msg)
        raise KeplerProblemError(msg)

    return concatenate((f * r0 + g * v0, fdot * r0 + gdot * v0))


def keplerThirdLaw(position_vector: ndarray) -> float:
    """Find the Orbital Period of an RSO using Kepler's 3rd law.

    Note:
        Circular orbit assumed as first approximation.

    Args:
        position_vector (``ndarray``): 3x1 ECI RSO position vector

    Returns:
        ``float``: Orbital Period
    """
    constant = 4 * (PI**2) * (Earth.radius * KM2M) / Earth.gravity
    radius_ratio = (norm(position_vector) / Earth.radius) ** 3
    return (constant * radius_ratio) ** (1 / 2)
