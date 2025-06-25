"""Defines the :class:`.TwoBody` class defining Keplerian motion."""

from __future__ import annotations

# Third Party Imports
from numpy import empty_like
from scipy.linalg import norm

# Local Imports
from ..physics.bodies import Earth
from .celestial import Celestial, checkEarthCollision


class TwoBody(Celestial):
    """TwoBody class.

    Implements the Dynamics abstract class to enable propagation of the state vector (in the ECI
    reference frame) using the Two-Body equations of motion.
    """

    def _differentialEquation(self, time, state, check_collision: bool = True):
        """Calculate the first time derivative of the state for numerical integration.

        References:
            #. :cite:t:`vallado_2013_astro`, Section 1.3, Eqn 1-14
            #. :cite:t:`wiesel_1997_spaceflight`, Section 2.3, Eqn 2.10

        Note: this function must take and receive 1-dimensional state vectors! Also, `K` below
            refers to the number of parallel integrations being performed

        Args:
            time (:class:`.ScenarioTime`): the current time of integration, (seconds)
            state (``numpy.ndarray``): (6 * K, ) current state vector in integration, (km, km/sec)
            check_collision (``bool``): whether to error on collision with the primary body

        Returns:
            ``numpy.ndarray``: (6 * K, ) derivative of the state vector, (km/sec; km/sec^2)
        """
        # Determine the step and halfway point for each vector
        step = int(state.shape[0] / 6)
        half = int(state.shape[0] / 2)
        derivative = empty_like(state, dtype=float)
        for jj in range(step):
            # Parse position vector
            r_vector = state[jj : jj + half : step]
            r_norm = norm(r_vector)

            if check_collision:
                # Check if an RSO crashed into the Earth
                checkEarthCollision(r_norm)

            # Save state derivative for this state vector
            derivative[jj : jj + half : step] = state[jj + half :: step]
            derivative[jj + half :: step] = -1.0 * Earth.mu / (r_norm**3.0) * r_vector

        return derivative
