r"""This module defines common noise models used throughout RESONAATE.

See Also:
    :ref:`tech-noise-top` for a more complete and detailed.

We typically define process noise for a Kalman filter as additive, zero-mean white noise.
In general, the process noise covariance is time-varying (such that the noise is a non-stationary sequence),
but we typically choose a constant process noise covariance up front.

Difficulty arises in how to design :math:`Q` for a particular dynamics (process) model.
If the system is kinematic, as is the case in astrodynamics, we can define the process noise itself as
a kinematic system.
This allows :math:`Q` to be defined via quantities derived from physics.
Process noise can be modeled as an :math:`n\mathrm{th}` order kinematic model where the :math:`n\mathrm{th}`
derivative of position is equal to white noise.
This can be done in two primary ways:

1. A discretized continuous time model (see :func:`.continuousWhiteNoise`)

2. A direct definition of the process noise in discrete time (see :func:`.discreteWhiteNoise`)
"""

from __future__ import annotations

# Standard Library Imports
from typing import Any

# Third Party Imports
from numpy import array, diagflat, ndarray

# Local Imports
from ..common.labels import NoiseLabel


def discreteWhiteNoise(dt: float, sigma: float) -> ndarray:
    r"""Return a first-order discrete process noise matrix.

    See Also:
        :ref:`tech-noise-disc`

    References:
        :cite:t:`bar-shalom_2001_estimation`, Section 6.3.2, Eqn 6.3.2-4

    Args:
        dt (``float``): discrete time step, :math:`T` (s)
        sigma (``float``): assumed standard deviation of un-modeled acceleration, :math:`\sigma` (km/s\ :sup:`2`).
            This should be roughly on the same scale as the un-modeled dynamics in your system.

    Returns:
        (``ndarray``): 6x6 process noise covariance matrix
    """
    rr_term = 0.25 * dt**4
    rv_term = 0.5 * dt**3
    vv_term = dt**2

    temp_mat = array(
        [
            [rr_term, 0.0, 0.0, rv_term, 0.0, 0.0],
            [0.0, rr_term, 0.0, 0.0, rv_term, 0.0],
            [0.0, 0.0, rr_term, 0.0, 0.0, rv_term],
            [rv_term, 0.0, 0.0, vv_term, 0.0, 0.0],
            [0.0, rv_term, 0.0, 0.0, vv_term, 0.0],
            [0.0, 0.0, rv_term, 0.0, 0.0, vv_term],
        ],
    )

    return temp_mat * sigma**2


def continuousWhiteNoise(dt: float, q: float) -> ndarray:
    r"""Return process noise matrix for a first-order, discretized continuous process noise model.

    See Also:
        :ref:`tech-noise-cont`

    References:
        :cite:t:`bar-shalom_2001_estimation`, Section 6.3.2, Eqn 6.3.2-4

    Args:
        dt (``float``): discrete time step, :math:`T` (s)
        q (``float``): assumed spectral power density of un-modeled acceleration, :math:`\tilde{q}`
            (km\ :sup:`2`/s\ :sup:`3`). This value should be scaled to satisfy
            :math:`\tilde{q}\simeq\tilde{a}^2T`

    Returns:
        (``ndarray``): 6x6 process noise covariance matrix
    """
    rr_term = (1 / 3) * dt**3
    rv_term = 0.5 * dt**2
    vv_term = dt

    temp_mat = array(
        [
            [rr_term, 0.0, 0.0, rv_term, 0.0, 0.0],
            [0.0, rr_term, 0.0, 0.0, rv_term, 0.0],
            [0.0, 0.0, rr_term, 0.0, 0.0, rv_term],
            [rv_term, 0.0, 0.0, vv_term, 0.0, 0.0],
            [0.0, rv_term, 0.0, 0.0, vv_term, 0.0],
            [0.0, 0.0, rv_term, 0.0, 0.0, vv_term],
        ],
    )

    return temp_mat * q


def simpleNoise(dt: float, std: float) -> ndarray:
    r"""Simple noise model only in acceleration.

    See Also:
        :ref:`tech-noise-cont`

    Args:
        dt (``float``): physics time step for scaling the noise (s)
        std (``float``): standard deviation of the noise covariance (km/s)

    Returns:
        (``ndarray``): 6x6 process noise covariance matrix
    """
    return dt * diagflat([0, 0, 0, std, std, std]) ** 2


def initialEstimateNoise(
    true_target_state: ndarray,
    pos_std: float,
    vel_std: float,
    rng: Any,
) -> tuple[ndarray, ndarray]:
    r"""Initialize the estimate error for a target.

    See Also:
        :ref:`tech-noise-est`

    Args:
        true_target_state (``ndarray``): true initial state of target agent, (km; km/s)
        pos_std (``float``): standard deviation of initial position error, (km)
        vel_std (``float``): standard deviation of initial position error, (km/s)
        rng (``np.random.Generator``): random number generator used to create random error

    Returns:
        tuple (``ndarray``): 6x1 initial state vector & 6x6 initial error covariance matrix
    """
    init_p = diagflat([pos_std, pos_std, pos_std, vel_std, vel_std, vel_std]) ** 2
    init_x = rng.multivariate_normal(true_target_state, init_p)

    return init_x, init_p


def noiseCovarianceFactory(method: str, time_step: int, magnitude: float) -> ndarray:
    r"""Build a dynamics propagation noise covariance matrix.

    Args:
        method (``str``): the function used to generate the noise covariance
        time_step (``int``): scales the noise covariance with the physics time step
        magnitude (``float``): the "variance" of the noise covariance

    Note:
        Valid options for `method` argument:

        - ``'continuous_white_noise'``: uses :func:`.continuousWhiteNoise` to generate noise covariance
        - ``'discrete_white_noise'``: uses :func:`.discreteWhiteNoise` to generate noise covariance
        - ``'simple_noise'``: uses :func:`.simpleNoise` to generate noise covariance

    Raises:
        `ValueError`: raised if given an invalid "method" argument

    Returns:
        ``ndarray``: 6x6 noise covariance matrix
    """
    if method.lower() == NoiseLabel.CONTINUOUS_WHITE_NOISE:
        noise = continuousWhiteNoise(time_step, magnitude)
    elif method.lower() == NoiseLabel.DISCRETE_WHITE_NOISE:
        noise = discreteWhiteNoise(time_step, magnitude)
    elif method.lower() == NoiseLabel.SIMPLE_NOISE:
        noise = simpleNoise(time_step, magnitude)
    else:
        raise ValueError(method)

    return noise
