"""Defines statistical functions and tests for analyzing filtering algorithms."""

from __future__ import annotations

# Standard Library Imports
from math import sqrt
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import arccos, arcsin, arcsinh, arctan2, array, cos, cosh, cross, dot, sin, sinh
from numpy.linalg import norm

# Local Imports
from ..bodies.earth import Earth
from ..constants import PI
from ..maths import _ATOL, _MAX_ITER, fpe_equals, wrapAngle2Pi
from ..orbits.kepler import keplerThirdLaw
from ..orbits.utils import universalC2C3

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


def determineTransferDirection(position_vector: float, transit_time: float) -> int:
    """Corresponds to `transfer_method` inputs in the lambert() functions.

    [NOTE]: Circular orbit assumed as first approximation.

    Note:
        "1" corresponds to short path
        "-1" corresponds to long path
        "0" corresponds to an invalid case

    Args:
        position_vector (``float``): 3x1 ECI position vector (km)
        transit_time (``float``): time between initial and final position (sec)

    Return:
        ``int``: indication of short or long pass of orbit
    """
    period = keplerThirdLaw(position_vector)
    if transit_time < period / 2:
        return 1
    if transit_time > period / 2:
        return -1

    return 0


def lambertGauss(
    initial_position: ndarray,
    current_position: ndarray,
    delta_time: float,
    transfer_method: int,
    mu: float = Earth.mu,
    tol: float = _ATOL,
    max_step: int = _MAX_ITER,
) -> ndarray:
    r"""Lambert-Gauss' algorithm.

    References:
        #. :cite:t:`vallado_2013_astro`, Algorithm 57, pg 478

    Args:
        initial_position (``ndarray``): 3x1 initial ECI position vector, km
        current_position (``ndarray``): 3x1 current ECI position vector, km
        delta_time (``float``): Difference in seconds between initial and current position
        transfer_method (``int``): Indication of either short or long arc
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.
        tol (``float``, optional): convergence criteria tolerance value. Defaults to 1.48e-8
        max_step (``int``, optional): Maximum number of iterations allowed. Defaults to 100

    Returns:
        initial_velocity (``ndarray``): 3x1 ECI velocity, km/sec
        current_velocity (``ndarray``): 3x1 ECI velocity, km/sec
    """
    r_mag = norm(current_position)
    r0_mag = norm(initial_position)

    cos_delta_nu = dot(initial_position, current_position) / (r0_mag * r_mag)
    sin_delta_nu = transfer_method * sqrt(1 - cos_delta_nu**2)

    cos_half_delta_nu = cos(wrapAngle2Pi(arctan2(sin_delta_nu, cos_delta_nu)) / 2)

    l_val = ((r0_mag + r_mag) / (4 * sqrt(r0_mag * r_mag) * cos_half_delta_nu)) - 0.5
    m_val = (mu * (delta_time**2)) / ((2 * sqrt(r0_mag * r_mag) * cos_half_delta_nu) ** 3)

    y_val = 1
    diff_y = 1
    step = 1
    while diff_y > tol and step <= max_step:
        xval_1 = (m_val / (y_val**2)) - l_val
        delta_ecc = 2 * arccos(1 - 2 * xval_1)
        xval_2 = (delta_ecc - sin(delta_ecc)) / ((sin(delta_ecc / 2)) ** 3)
        y_new = 1 + xval_2 * (l_val + xval_1)
        diff_y = abs(y_val - y_new)
        y_val = y_new
        step += 1

    xval_1 = (m_val / (y_val**2)) - l_val
    half_cos_delta_ecc = 1 - 2 * xval_1
    p_val = (r0_mag * r_mag * (1 - cos_delta_nu)) / (
        r0_mag + r_mag - 2 * sqrt(r0_mag * r_mag) * cos_half_delta_nu * half_cos_delta_ecc
    )
    gauss_f = 1 - (r_mag / p_val) * (1 - cos_delta_nu)
    gauss_g = (r0_mag * r_mag * sin_delta_nu) / sqrt(mu * p_val)
    gauss_g_dot = 1 - (r0_mag / p_val) * (1 - cos_delta_nu)
    return _calculateVelocities(
        initial_position=initial_position,
        current_position=current_position,
        gauss_f=gauss_f,
        gauss_g=gauss_g,
        gauss_g_dot=gauss_g_dot,
    )


def lambertBattin(
    initial_position: ndarray[float, float, float],
    current_position: ndarray[float, float, float],
    delta_time: float,
    transfer_method: int,
    mu: float = Earth.mu,
    tol: float = _ATOL,
    max_step: int = _MAX_ITER,
) -> tuple[ndarray, ndarray]:
    r"""Lambert's method using the solution developed by Battin, similar to Gauss' solution.

    References:
        #. :cite:t:`lambert_battin_matlab`
        #. :cite:t:`battin_1984`
        #. :cite:t:`vallado_2013_astro`, Algorithm 59, pg 494-497

    Args:
        initial_position (``ndarray``): 3x1 initial ECI position vector, km
        current_position (``ndarray``): 3x1 current ECI position vector, km
        delta_time (``float``): Difference in seconds between initial and current position
        transfer_method (``int``): Indication of either short or long arc
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.
        tol (``float``, optional): convergence criteria tolerance value. Defaults to 1.48e-8
        max_step (``int``, optional): Maximum number of iterations allowed. Defaults to 100

    Returns:
        initial_velocity (``ndarray``): 3x1 ECI velocity, km/sec
        current_velocity (``ndarray``): 3x1 ECI velocity, km/sec
    """
    if delta_time <= 0.0:
        raise ValueError("delta_time must be positive")

    r2 = norm(current_position)
    r1 = norm(initial_position)

    # Angle must be positive for the long way to work
    cos_delta_nu = dot(initial_position, current_position) / (r1 * r2)
    sin_delta_nu = transfer_method * norm(cross(current_position, initial_position)) / (r1 * r2)
    delta_nu = wrapAngle2Pi(arctan2(sin_delta_nu, cos_delta_nu))

    # Geometric terms, Pg. 331 in Battin
    c = sqrt(r1**2 + r2**2 - 2.0 * r1 * r2 * cos_delta_nu)
    s = (r1 + r2 + c) * 0.5  # Vallado Algorithm 59

    # Radius ratios
    r2_over_r1 = r2 / r1
    epsilon = r2_over_r1 - 1.0

    # Intermediate geometric terms
    # Eqn 7.57 from Battin
    tan_squared_two_omega = (epsilon**2 * 0.25) / (
        sqrt(r2_over_r1) + r2_over_r1 * (2.0 + sqrt(r2_over_r1))
    )
    # Eqn. 7.102 from Battin
    cos_delta_nu_over_2 = cos(delta_nu * 0.5)
    r_op = 0.25 * (r1 + r2 + 2 * sqrt(r1 * r2) * cos_delta_nu_over_2)

    # Determine l using Eqn. 7.101 from Battin
    if delta_nu < PI:
        numerator = sin(delta_nu * 0.25) ** 2 + tan_squared_two_omega
        l_val = numerator / (numerator + cos_delta_nu_over_2)
    else:
        denominator = cos(delta_nu * 0.25) ** 2 + tan_squared_two_omega
        l_val = (denominator - cos_delta_nu_over_2) / denominator

    # Eqn. 7.89 (third one) from Battin
    m_val = (mu * delta_time**2) / (8 * r_op**3)

    # Loop initialization
    x = l_val
    x_err = 1.0
    step = 1
    y = 0.0
    lim1 = sqrt(m_val / l_val)
    while x_err > tol and step <= max_step:
        xi_x = _battinGetXi(x)
        # Cubic evaluation
        h1 = ((l_val + x) ** 2 * (1.0 + 3.0 * x + xi_x)) / (
            (1.0 + 2.0 * x + l_val) * (4.0 * x + xi_x * (3.0 + x))
        )
        h2 = (m_val * (x - l_val + xi_x)) / (
            (1.0 + 2.0 * x + l_val) * (4.0 * x + xi_x * (3.0 + x))
        )
        xn, y = _cubicSplineBattin(y, h1, h2, m_val, l_val, lim1)

        x_err = abs(x - xn)
        x = xn
        step += 1

    # Determine SMA of transfer orbit
    sma = (mu * delta_time**2) / (16.0 * r_op**2 * x * y**2)

    # elliptical case
    if sma > 0.0:
        beta_e = 2.0 * arcsin(sqrt((s - c) / (2.0 * sma)))
        if delta_nu > PI:
            beta_e *= -1.0
        a_min = s * 0.5
        t_min = sqrt(a_min**3 / mu) * (PI - beta_e + sin(beta_e))
        alpha_e = 2.0 * arcsin(sqrt(s / (2.0 * sma)))
        if delta_time > t_min:
            alpha_e = 2.0 * PI - alpha_e
        delta_e = alpha_e - beta_e
        gauss_f = 1.0 - (sma / r1) * (1.0 - cos(delta_e))
        gauss_g = delta_time - sqrt(sma**3 / mu) * (delta_e - sin(delta_e))
        gauss_g_dot = 1.0 - (sma / r2) * (1.0 - cos(delta_e))

    # hyperbolic case
    elif sma < 0.0:
        alpha_h = 2.0 * arcsinh(sqrt(s / -2.0 * sma))
        beta_h = 2.0 * arcsinh(sqrt((s - c) / (-2.0 * sma)))
        delta_h = alpha_h - beta_h
        gauss_f = 1.0 - (sma / r1) * (1.0 - cosh(delta_h))
        gauss_g = delta_time - sqrt(-(sma**3) / mu) * (sinh(delta_h) - delta_h)
        gauss_g_dot = 1.0 - (sma / r2) * (1.0 - cosh(delta_h))

    else:
        raise NotImplementedError("Parabolic case is not implemented")

    return _calculateVelocities(initial_position, current_position, gauss_f, gauss_g, gauss_g_dot)


def lambertUniversal(
    initial_position: ndarray,
    current_position: ndarray,
    delta_time: float,
    transfer_method: int,
    mu: float = Earth.mu,
    tol: float = _ATOL,
    max_step: int = _MAX_ITER,
) -> tuple[ndarray, ndarray]:
    r"""Lambert Universal Variable algorithm.

    References:
        #. :cite:t:`vallado_2013_astro`, Algorithm 58, pg 492
        #. :cite:t:`nastasi_2018_diss`, Algorithm 4.6, Pg 71

    Args:
        initial_position (``ndarray``): 3x1 initial ECI position vector, km
        current_position (``ndarray``): 3x1 current ECI position vector, km
        delta_time (``float``): Difference in seconds between initial and current position
        transfer_method (``int``): Indication of either short or long arc
        mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to :attr:`.Earth.mu`.
        tol (``float``, optional): convergence criteria tolerance value. Defaults to 1.48e-8
        max_step (``int``, optional): Maximum number of iterations allowed. Defaults to 100

    Returns:
        initial_velocity (``ndarray``): 3x1 ECI velocity, km/sec
        current_velocity (``ndarray``): 3x1 ECI velocity, km/sec
    """
    if delta_time <= 0.0:
        raise ValueError("delta_time must be positive")

    r_mag = norm(current_position)
    r0_mag = norm(initial_position)

    cos_delta_nu = dot(initial_position, current_position) / (r0_mag * r_mag)
    a_value = transfer_method * sqrt(r_mag * r0_mag * (1.0 + cos_delta_nu))

    if fpe_equals(a_value, 0.0):
        raise ValueError("Singularity occurred, cannot use Universal Lambert")

    # Binary Search
    psi_up = 4.0 * PI**2
    psi_low = -4.0 * PI**2
    psi_n = (psi_up + psi_low) * 0.5
    c_2, c_3 = universalC2C3(psi_n)

    delta_tn = 2.0 * delta_time
    step = 1
    y_new = 0.0
    while abs(delta_tn - delta_time) >= tol and step <= max_step:
        y_new = _calcYNew(r0_mag, r_mag, a_value, psi_n, c_2, c_3)
        if a_value > 0.0:
            while y_new < 0.0:
                if psi_up == 0.0:
                    psi_up = 1.0
                psi_low = psi_low + 0.001 * psi_up
                psi_n = (psi_up + psi_low) * 0.5
                [c_2, c_3] = universalC2C3(psi_n)
                if (new_y_new := _calcYNew(r0_mag, r_mag, a_value, psi_n, c_2, c_3)) < y_new:
                    raise ValueError("Universal Lambert caught in an infinite loop")
                y_new = new_y_new

        xi_new = sqrt(y_new / c_2)

        if (delta_tn := (xi_new**3 * c_3 + a_value * sqrt(y_new)) / sqrt(mu)) <= delta_time:
            psi_low = psi_n
        else:
            psi_up = psi_n

        psi_n = (psi_up + psi_low) * 0.5
        [c_2, c_3] = universalC2C3(psi_n)
        step += 1

    gauss_f = 1.0 - y_new / r0_mag
    gauss_g = a_value * sqrt(y_new / mu)
    gauss_g_dot = 1.0 - y_new / r_mag
    return _calculateVelocities(initial_position, current_position, gauss_f, gauss_g, gauss_g_dot)


_BATTIN_SUPPORT_COEFFICIENTS_ETA: ndarray = array(
    [
        0.2,
        9.0 / 35.0,
        16.0 / 63.0,
        25.0 / 99.0,
        36.0 / 143.0,
        49.0 / 195.0,
        64.0 / 255.0,
        81.0 / 323.0,
        100.0 / 399.0,
        121.0 / 483.0,
        144.0 / 575.0,
        169.0 / 675.0,
        196.0 / 783.0,
        225.0 / 899.0,
        256.0 / 1023.0,
        289.0 / 1155.0,
        324.0 / 1295.0,
        361.0 / 1443.0,
        400.0 / 1599.0,
        441.0 / 1763.0,
        484.0 / 1935.0,
    ],
)

_BATTIN_SUPPORT_COEFFICIENTS_KAPPA: ndarray = array(
    [
        1.0 / 3.0,
        4.0 / 27.0,
        8.0 / 27.0,
        2.0 / 9.0,
        22.0 / 81.0,
        208.0 / 891.0,
        340.0 / 1287.0,
        418.0 / 1755.0,
        598.0 / 2295.0,
        700.0 / 2907.0,
        928.0 / 3591.0,
        1054.0 / 4347.0,
        1330.0 / 5175.0,
        1480.0 / 6075.0,
        1804.0 / 7047.0,
        1978.0 / 8091.0,
        2350.0 / 9207.0,
        2548.0 / 10395.0,
        2968.0 / 11655.0,
        3190.0 / 12987.0,
        3658.0 / 14391.0,
    ],
)


def _battinGetXi(x: float, tol: float = _ATOL) -> float:
    r"""Support function for :func:`.lambertBattin` to determine :math:`\xi`.

    References:
        #. :cite:t:`lambert_battin_matlab`

    Args:
        x (``float``): battin variable, :math:`x`
        tol (``float``, optional): numeric convergence tolerance. Defaults to :data:`._ATOL`.

    Returns:
        ``float``: :math:`\xi(x)`
    """
    sqrt_1_plus_x = sqrt(1.0 + x)
    eta = x / (1.0 + sqrt_1_plus_x) ** 2
    cont_frac_sum = _battinContinuedFraction(_BATTIN_SUPPORT_COEFFICIENTS_ETA, eta, tol=tol)

    return 1.0 / (
        (1.0 / (8.0 * (1.0 + sqrt_1_plus_x))) * (3.0 + cont_frac_sum / (1.0 + eta * cont_frac_sum))
    )


def _battinGetKappa(u: float, tol: float = _ATOL) -> float:
    r"""Support function for :func:`.lambertBattin` to determine :math:`\kappa`.

    References:
        #. :cite:t:`lambert_battin_matlab`

    Args:
        u (``float``): battin variable, :math:`U`
        tol (``float``, optional): numeric convergence tolerance. Defaults to :data:`._ATOL`.

    Returns:
        ``float``: :math:`\kappa(x)`
    """
    return _battinContinuedFraction(_BATTIN_SUPPORT_COEFFICIENTS_KAPPA, u, tol=tol)


def _battinContinuedFraction(coefficients: ndarray, factor: float, tol: float = _ATOL) -> float:
    r"""Continued fraction function used in :func:`.lambertBattin` to determine intermediate variables.

    References:
        #. :cite:t:`lambert_battin_matlab`

    Args:
        coefficients (``ndarray``): coefficients to use for the continued fraction terms
        factor (``float``): common multiplicative factor used in each continued fraction term
        tol (``float``, optional): numeric convergence tolerance. Defaults to :data:`._ATOL`.

    Returns:
        ``float``: continued fraction term
    """
    del_old = 1.0
    term_old = coefficients[0]
    continued_frac = term_old
    step = 0
    while abs(term_old) > tol and step < len(coefficients) - 1:
        del_new = 1.0 / (1.0 + coefficients[step + 1] * factor * del_old)
        term = term_old * (del_new - 1.0)
        continued_frac += term
        step += 1
        del_old = del_new
        term_old = term

    return continued_frac


def _cubicSplineBattin(
    y: float,
    h1: float,
    h2: float,
    m: float,
    L: float,  # noqa: N803
    lim: float,
) -> tuple[float, float]:
    r"""Cubic spline approximation used with :func:`.lambertBattin`.

    Solves the cubic spline using an approximation:

    .. math::

        y^3 - y^2 - h_1 y^2 - h_2 = 0

    References:
        #. :cite:t:`lambert_battin_matlab`
        #. :cite:t:`battin_1984`
        #. :cite:t:`vallado_2013_astro`, Algorithm 59, pg 494-497

    Args:
        y (``float``): cubic spline independent variable
        h1 (``float``): cubic spline coefficient, :math:`h_1`
        h2 (``float``): cubic spline coefficient, :math:`h_2`
        m (``float``): term used to calculate :math:`x`, :math:`m`
        L (``float``): term used to calculate coefficients :math:`h_1` and :math:`h_2`, :math:`l`
        lim (``float``): not sure, from MATLAB implementation

    Returns:
        ``tuple[float, float]``: :math:`x` from Algorithm 59 in Vallado, approx. solution of cubic spline, :math:`y`
    """
    b = (27.0 * h2) / (4.0 * (1.0 + h1) ** 3)
    x = -1.0
    # resets the initial condition
    if b < -1.0:
        x = 1.0 - 2.0 * L
    elif y > lim:
        x *= lim / y
    else:
        u = b / (2.0 * (sqrt(1.0 + b) + 1.0))
        k = _battinGetKappa(u)
        y = ((1.0 + h1) / 3.0) * (2.0 + sqrt(1.0 + b) / (1.0 + 2.0 * u * k**2))
        x = sqrt(((1.0 - L) * 0.5) ** 2 + (m / y**2)) - (1.0 + L) * 0.5
    return x, y


def _calculateVelocities(
    initial_position: ndarray,
    current_position: ndarray,
    gauss_f: float,
    gauss_g: float,
    gauss_g_dot: float,
) -> tuple[ndarray, ndarray]:
    """Apply solutions from Gauss' variables to determine velocities.

    Args:
        initial_position (``ndarray``): 3x1 initial ECI position vector, km
        current_position (``ndarray``): 3x1 current ECI position vector, km
        gauss_f (``float``): gauss f variable
        gauss_g (``float``): gauss g variable
        gauss_g_dot (``float``): derivative of gauss g variable

    Returns:
        initial_velocity (``ndarray``): 3x1 initial ECI velocity vector, km/s
        current_velocity (``ndarray``): 3x1 current ECI velocity vector, km/s
    """
    initial_velocity = (current_position - gauss_f * initial_position) / gauss_g
    current_velocity = (gauss_g_dot * current_position - initial_position) / gauss_g

    return initial_velocity, current_velocity


def _calcYNew(
    r0_mag: float,
    r_mag: float,
    a_value: float,
    psi_n: float,
    c_2: float,
    c_3: float,
) -> float:
    """Private helper function for :func:`.lambertUniversal`.

    Args:
       r0_mag (``float``): initial range (km)
       r_mag (``float``): current range (km)
       a_value (``float``): intermediate term
       psi_n (``float``): average psi value
       c_2 (``float``): first universal variable
       c_3 (``float``): second universal variable

    Returns:
        ``float``: new y value
    """
    return r0_mag + r_mag + a_value * (psi_n * c_3 - 1.0) / sqrt(c_2)
