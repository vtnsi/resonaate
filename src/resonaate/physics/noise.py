# Standard Library Imports
# Third Party Imports
from numpy import diagflat, full, block, concatenate, ones
from scipy.linalg import norm
# RESONAATE Imports


def discreteWhiteNoise(delta_time, variance):
    """Return a first-order discrete process noise matrix.

    This assumes the noise as un-modeled constant piecewise acceleration, w, with the following
    noise gain:
                    Gamma = [0.5*(delta)^2, (deltaT)]^T
                        q_k = Gamma*sigma^2*Gamma^T

    Args:
        delta_time (float): discrete time interval (seconds)
        variance (float): assumed variance in un-modeled acceleration

    Returns:
        (``numpy.ndarray``): 6x6 discrete process noise covariance matrix
    """
    r_cov = diagflat(
        full(3, 0.25 * delta_time**4)
    )
    rv_cov = diagflat(
        full(3, 0.5 * delta_time**3)
    )
    v_cov = diagflat(
        full(3, delta_time**2)
    )

    temp_mat = block(
        [
            [r_cov, rv_cov],
            [rv_cov, v_cov]
        ]
    )

    return temp_mat * variance**2


def continuousWhiteNoise(delta_time, spectral_density):
    """Return a first-order continuous process noise matrix.

    This assumes the noise as un-modeled zero-mean constant acceleration, w(t):

                    q_k = integral(F(t)Q_c(t)F^T(t)delta_time, 0, deltaT)

    where Q_c(t) is the continuous noise

    Args:
        delta_time (float): discrete time interval (seconds)
        spectral_density (float): assumed variance in un-modeled acceleration

    Returns:
        (``numpy.ndarray``): 6x6 continuous process noise covariance matrix
    """
    r_cov = diagflat(
        full(3, (1 / 3) * delta_time**3)
    )
    rv_cov = diagflat(
        full(3, 0.5 * delta_time**2)
    )
    v_cov = diagflat(
        full(3, delta_time)
    )

    temp_mat = block(
        [
            [r_cov, rv_cov],
            [rv_cov, v_cov]
        ]
    )

    return temp_mat * spectral_density


def simpleNoise(delta_time, variance):
    """Simple noise model only in acceleration.

    Args:
        delta_time (float): physics time step for scaling the noise
        variance (float): magnitude of noise covariance

    Returns:
        (``numpy.ndarray``): 6x6 noise covariance matrix
    """
    return delta_time * diagflat([0, 0, 0, variance, variance, variance])**2


def initialEstimateNoise(true_target_state, variance, rng):
    """Initialize the estimate error for a target.

    Args:
        true_target_state (``numpy.ndarray``): true initial state of target agent
        variance (float): magnitude of the error in the initial state
        rng (`np.random.Generator`): random number generator to create random error

    Returns:
        tuple(``numpy.ndarray``): 6x1 initial state vector & 6x6 initial covariance
    """
    position = variance * norm(true_target_state[:3]) * ones((3, 1))
    velocity = variance * norm(true_target_state[3:]) * ones((3, 1))
    init_p = diagflat(concatenate((position, velocity), axis=0)**2)
    init_x = rng.multivariate_normal(true_target_state, init_p)

    return init_x, init_p


def noiseCovarianceFactory(method, time_step, magnitude):
    """Build a dynamics propagation noise covariance matrix.

    Args:
        method (``str``): the function used to generate the noise covariance
        time_step (``int``): scales the noise covariance with the physics time step
        magnitude (``float``): the "variance" of the noise covariance

    Note:
        Valid options for "method" argument:
            - "continuous_white_noise": :func:`.continuousWhiteNoise`
            - "discrete_white_noise": :func:`.discreteWhiteNoise`
            - "simple_noise": :func:`.simpleNoise`

    Raises:
        ValueError: raised if given an invalid "method" argument

    Returns:
        ``numpy.ndarray``: 6x6 noise covariance matrix
    """
    if method.lower() == "continuous_white_noise":
        noise = continuousWhiteNoise(time_step, magnitude)
    elif method.lower() == "discrete_white_noise":
        noise = discreteWhiteNoise(time_step, magnitude)
    elif method.lower() == "simple_noise":
        noise = simpleNoise(time_step, magnitude)
    else:
        raise ValueError(method)

    return noise
