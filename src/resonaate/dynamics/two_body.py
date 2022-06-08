# Standard Library Imports
import logging
# Third Party Imports
from numpy import concatenate, matmul, spacing, empty_like, ones_like, eye, zeros
from scipy.linalg import norm
from scipy.integrate import solve_ivp
# RESONAATE Imports
from .dynamics_base import Dynamics
from ..physics.bodies import Earth


class TwoBody(Dynamics):
    """TwoBody class.

    Implements the Dynamics abstract class to enable propagation of the state vector (in the ECI
    reference frame) using the Two-Body equations of motion.
    """

    def __init__(self, method='RK45'):
        """Construct a TwoBody object.

        Args:
            method (``str``, optional): Defaults to ``'RK45'``. Which ODE integration method to use.
        """
        self._method = method

    def propagate(self, initial_time, final_time, initial_state):
        """Numerically integrate the state vector forward to the final time.

        Args:
            initial_time (:class:`.ScenarioTime`): time value when the integration will begin (seconds)
            final_time (:class:`.ScenarioTime`): time value when the integration will stop (seconds)
            initial_state (``numpy.ndarray``): (6 * K, ) initial state vector for the integration step, (km; km/sec)

        Note: this function must take and receive 1-dimensional state vectors! Also, `K` below
            refers to the number of parallel integrations being performed

        Returns:
            ``numpy.ndarray``: (6 * K, ) final state vector after numerical integration has stopped, (km; km/sec)
        """
        assert final_time > initial_time, "TwoBody: Invalid input. final_time must be < initial_time."

        # Continue integration until we reach final_time
        while initial_time < final_time:
            solution = solve_ivp(
                stateDerivative,
                (initial_time, final_time),
                initial_state.ravel(),
                method='RK45',
                rtol=self.RELATIVE_TOL,
                atol=self.ABSOLUTE_TOL * ones_like(initial_state.ravel())
            )

            # Get the final 'truth' state from the solver
            final_state = solution.y[::, -1]

            # Retrieve final time, this should auto-exit the loop if fully-integrated
            initial_time = solution.t[-1] + spacing(solution.t[-1])

        # Return state & covar as well for flexibility
        return final_state

    def retrogress(self, initial_time, final_time, initial_state):
        """See base class."""
        raise NotImplementedError


def stateDerivative(time, state):  # pylint: disable=unused-argument
    """Calculate the first time derivative of the state for numerical integration.

    Note: this function must take and receive 1-dimensional state vectors! Also, `K` below
        refers to the number of parallel integrations being performed

    Args:
        time (:class:`.ScenarioTime`): the current time of integration, (seconds)
        state (``numpy.ndarray``): (6 * K, ) current state vector in integration, (km, km/sec)

    Returns:
        ``numpy.ndarray``: (6 * K, ) derivative of the state vector, (km/sec; km/sec^2)
    """
    # Determine the step and halfway point for each vector
    step = int(state.shape[0] / 6)
    half = int(state.shape[0] / 2)
    derivative = empty_like(state, dtype=float)
    for jj in range(step):
        # pylint: disable=unsupported-assignment-operation

        # Parse position vector
        r_vector = state[jj:jj + half:step]
        r_norm = norm(r_vector)

        # Check if an RSO crashed into the Earth
        assert r_norm > Earth.radius, "An RSO has crashed into the Earth"
        if r_norm < Earth.radius + 100:
            msg = "An RSO is within 100km of Earth surface"
            logger = logging.getLogger("resonaate")
            logger.warning(msg)

        # Save state derivative for this state vector
        derivative[jj:jj + half:step] = state[jj + half::step]
        derivative[jj + half::step] = -1. * Earth.mu / (r_norm**3.0) * r_vector

    return derivative  # + self.host._propulsion.getThrust(state, time)


def stateMatrix(x_position):
    """Calculate the partial derivative matrix, F, for Two-Body dynamics in ECI coordinates.

    Args::
        x_position (``numpy.ndarray``): 6x1 ECI state vector (km; km/sec)

    Returns:
        (``numpy.ndarray``): 6x6 F Matrix
    """
    r_vec = x_position[0:3]
    r_norm = norm(r_vec)
    f_upper_left = zeros((3, 3))
    f_upper_right = eye(3)
    f_lower_left = 3 * Earth.mu / (r_norm**5) * (matmul(r_vec.T, r_vec)) - Earth.mu / (r_norm**3) * eye(len(r_vec))
    f_lower_right = zeros((3, 3))
    return concatenate(
        (
            concatenate((f_upper_left, f_upper_right), axis=1),
            concatenate((f_lower_left, f_lower_right), axis=1)
        ),
        axis=0
    )
