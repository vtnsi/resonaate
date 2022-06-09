"""Defines statistical functions and tests for analyzing filtering algorithms."""
from __future__ import annotations

# Standard Library Imports
from math import sqrt
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import cross, dot, sign
from numpy.linalg import norm

# Local Imports
from ..bodies.earth import Earth
from ..constants import PI
from ..orbits.conversions import eci2coe
from ..orbits.utils import universalC2C3

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


def lambertMinEnergy(
    initial_state: ndarray,
    initial_time: float,
    current_state: ndarray,
    current_time: float,
) -> ndarray:
    """Lambert's minimum energy transfer algorithm.

    References:
        #. :cite:t:`vallado_2013_astro`, Algorithm 56, pg 475

    Args:
        initial_state (``ndarray``): 6x1 initial ECI state, km; km/sec
        current_state (``ndarray``): 6x1 current ECI state, km; km/sec

    Returns:
        delta_v ``ndarray``: 3x1 change in ECI velocity, km/sec
    """
    ## [TODO]: Needs review
    # pylint: disable=unused-argument
    r_mag = norm(current_state[:3])
    r0_mag = norm(initial_state[:3])

    sign_trajectory = sign(
        dot(
            cross(initial_state[:3], initial_state[3:]),
            cross(initial_state[:3], current_state[:3]),
        )
    )
    cos_delta_nu = dot(initial_state[:3], current_state[:3]) / (r0_mag * r_mag)
    sin_delta_nu = sign_trajectory * sqrt(1 - cos_delta_nu**2)

    chord_length = sqrt(r_mag**2 + r0_mag**2 - 2 * r_mag * r0_mag * cos_delta_nu)
    p_min = (r_mag * r0_mag) / chord_length * (1 - cos_delta_nu)

    new_vel = (
        sqrt(Earth.mu * p_min)
        / (r_mag * r0_mag * sin_delta_nu)
        * (current_state[:3] - (1 - r_mag / p_min * (1 - cos_delta_nu)) * initial_state[:3])
    )
    delta_v = new_vel - initial_state[3:]

    return delta_v


def lambertGauss(
    initial_state: ndarray,
    initial_time: float,
    current_state: ndarray,
    current_time: float,
) -> ndarray:
    """Lambert-Gauss' algorithm.

    References:
        #. :cite:t:`vallado_2013_astro`, Algorithm 57, pg 478

    Args:
        initial_state (``ndarray``): 6x1 initial ECI state, km; km/sec
        initial_time (:class:`.ScenarioTime`): Initial Scenario time, sec
        current_state (``ndarray``): 6x1 current ECI state, km; km/sec
        current_time (:class:`.ScenarioTime`): Current Scenario time, sec

    Returns:
        delta_v (``ndarray``): 3x1 change in ECI velocity, km/sec
    """
    ## [TODO]: Needs review
    current_coe = eci2coe(current_state)
    delta_t = current_time - initial_time

    r_mag = norm(current_state[:3])
    r0_mag = norm(initial_state[:3])

    sign_trajectory = sign(
        dot(
            cross(initial_state[:3], initial_state[3:]),
            cross(initial_state[:3], current_state[:3]),
        )
    )
    cos_delta_nu = dot(initial_state[:3], current_state[:3]) / (r0_mag * r_mag)
    half_cos_delta_nu = sqrt((1 + cos_delta_nu) / 2)
    sin_delta_nu = sign_trajectory * sqrt(1 - cos_delta_nu**2)

    l_val = (r0_mag + r_mag) / (4 * sqrt(r0_mag * r_mag) * half_cos_delta_nu) - 0.5
    m_val = (Earth.mu * delta_t**2) / (2 * sqrt(r0_mag * r_mag) * half_cos_delta_nu) ** 3

    y_val = 1
    diff_y = 1
    step = 1
    while diff_y > 1e-6 and step <= 100:
        xval_1 = m_val / y_val**2 - l_val
        xval_2 = (4 / 3) * (1 + 6 * xval_1 / 5 + 48 * xval_1 / 35 + 410 * xval_1**3 / 315)
        y_new = 1 + xval_2 * (l_val + xval_1)
        diff_y = abs(y_val - y_new)
        y_val = y_new
        step += 1

    semi_p = current_coe[0]
    gauss_f = 1 - r_mag / semi_p * (1 - cos_delta_nu)
    gauss_g = (r0_mag * r_mag * sin_delta_nu) / sqrt(Earth.mu * semi_p)
    new_vel = (current_state[:3] - gauss_f * initial_state[:3]) / gauss_g

    delta_v = new_vel - initial_state[3:]

    return delta_v


def lambertUniversal(
    initial_state: ndarray,
    initial_time: float,
    current_state: ndarray,
    current_time: float,
) -> ndarray:
    """Lambert Universal Variable algorithm.

    References:
        #. :cite:t:`vallado_2013_astro`, Algorithm 58, pg 492
        #. :cite:t:`nastasi_2018_diss`, Algorithm 4.6, Pg 71

    Args:
        initial_state (``ndarray``): 6x1 initial ECI state, km; km/sec
        initial_time (:class:`.ScenarioTime`): Initial Scenario time, sec
        current_state (``ndarray``): 6x1 current ECI state, km; km/sec
        current_time (:class:`.ScenarioTime`): Current Scenario time, sec

    Returns:
        delta_v (``ndarray``): 3x1 change in ECI velocity, km/sec
    """
    ## [TODO]: Needs review
    r_mag = norm(current_state[:3])
    r0_mag = norm(initial_state[:3])
    delta_t = current_time - initial_time

    # if Positive, short trajectory, if negative, long trajectory
    sign_trajectory = sign(
        dot(
            cross(initial_state[:3], initial_state[3:]),
            cross(initial_state[:3], current_state[:3]),
        )
    )
    cos_delta_nu = dot(initial_state[:3], current_state[:3]) / (r0_mag * r_mag)
    a_value = sign_trajectory * sqrt(r_mag * r0_mag * (1 + cos_delta_nu))

    if a_value == 0:
        raise ValueError("Singularity occurred, cannot use Universal Lambert")

    # Binary Search
    psi_up = 4 * PI**2
    psi_low = -4 * PI**2
    psi_n = (psi_up + psi_low) / 2
    [c_two, c_three] = universalC2C3(psi_n)

    delta_tn = 2 * delta_t
    step = 1
    while abs(delta_tn - delta_t) >= 1e-6 and step <= 100:
        y_new = r0_mag + r_mag + a_value * (psi_n * c_three - 1) / sqrt(c_two)
        if a_value > 0:
            while y_new < 0:
                if psi_up == 0:
                    psi_up = 1
                psi_low = psi_low + 0.001 * psi_up
                psi_n = (psi_up + psi_low) / 2
                [c_two, c_three] = universalC2C3(psi_n)
                y_new = r0_mag + r_mag + a_value * (psi_n * c_three - 1) / sqrt(c_two)

        xi_new = sqrt(y_new / c_two)
        delta_tn = (xi_new**3 * c_three + a_value * sqrt(y_new)) / sqrt(Earth.mu)

        if delta_tn <= delta_t:
            psi_low = psi_n
        else:
            psi_up = psi_n

        psi_n = (psi_up + psi_low) / 2
        [c_two, c_three] = universalC2C3(psi_n)
        step = step + 1

    gauss_f = 1 - y_new / r0_mag
    gauss_g = a_value * sqrt(y_new / Earth.mu)
    new_vel = (current_state[:3] - gauss_f * initial_state[:3]) / gauss_g

    delta_v = new_vel - initial_state[3:]

    return delta_v
