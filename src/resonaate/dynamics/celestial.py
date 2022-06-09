"""Module defining a base :class:`.Dynamics` class for celestial :class:`.Agent`s."""
# Standard Library
from abc import ABCMeta, abstractmethod
import logging
# Third Party Imports
from scipy.integrate import solve_ivp
from numpy import ones_like, spacing
# RESONAATE Imports
from ..physics.bodies import Earth
from .constants import RK45_LABEL
from .dynamics_base import Dynamics


class EarthCollision(Exception):
    """Exception raised if a :class:`.Celestial` object crashes into the Earth."""


def checkEarthCollision(r_norm):
    """Raise an :class:`.EarthCollision` if the specified `r_norm` vector indicates a collision with the Earth.

    Args:
        r_norm (float): ``scipy.linalg.norm()`` of current state vector.

    Raises:
        EarthCollision: If the specified `r_norm` vector indicates an RSO has crashed into the Earth.
    """
    # Check if an RSO crashed into the Earth
    if r_norm <= Earth.radius:
        raise EarthCollision("An RSO has crashed into the Earth")

    if r_norm < Earth.radius + Earth.atmosphere:
        msg = "An RSO is within 100km of Earth surface"
        logger = logging.getLogger("resonaate")
        logger.warning(msg)


class Celestial(Dynamics, metaclass=ABCMeta):
    """The :class:`.Celestial` dynamics class defines the behavior of space-based :class:`.Agent`s."""

    def __init__(self, method=RK45_LABEL):
        """Instantiate a :class:`.Celestial` object.

        Args:
            method (str, optional): Which ODE integration method to use.
        """
        self._method = method

    def propagate(self, initial_time, final_time, initial_state, station_keeping=None):
        """Numerically integrate the state vector forward to the final time.

        Args:
            initial_time (:class:`.ScenarioTime`): time value when the integration will begin (seconds)
            final_time (:class:`.ScenarioTime`): time value when the integration will stop (seconds)
            initial_state (``numpy.ndarray``): (6 * K, ) initial state vector for the integration step, (km; km/sec)
            station_keeping (list, optional): list of :class:`.StationKeeper` objects describing which station keeping
                burns this RSO is capable of.

        Note: this function must take and receive 1-dimensional state vectors! Also, `K` below
            refers to the number of parallel integrations being performed

        Returns:
            ``numpy.ndarray``: (6 * K, ) final state vector after numerical integration has stopped, (km; km/sec)
        """
        if final_time <= initial_time:
            raise ValueError("final_time must be > initial_time")

        events = []
        if station_keeping:
            events.extend(station_keeping)

        # Continue integration until we reach final_time
        while initial_time < final_time:
            solution = solve_ivp(
                self._differentialEquation,
                (initial_time, final_time),
                initial_state.ravel(),
                method=self._method,
                rtol=self.RELATIVE_TOL,
                atol=self.ABSOLUTE_TOL * ones_like(initial_state.ravel()),
                events=events
            )

            initial_state = solution.y[::, -1]
            for event_index, event in enumerate(events):
                if solution.t_events[event_index]:
                    initial_state += event.getStateChange(solution.t[-1], initial_state)

            # Retrieve final time, this should auto-exit the loop if fully-integrated
            initial_time = solution.t[-1] + spacing(solution.t[-1])

        # Return final state from the solver
        return solution.y[::, -1]

    @abstractmethod
    def _differentialEquation(self, time, state):
        """Calculate the first time derivative of the state for numerical integration.

        Note: this function must take and receive 1-dimensional state vectors! Also, `K` below
            refers to the number of parallel integrations being performed

        Args:
            time (:class:`.ScenarioTime`): the current time of integration, (seconds)
            state (``numpy.ndarray``): (6 * K, ) current state vector in integration, (km, km/sec)

        Returns:
            ``numpy.ndarray``: (6 * K, ) derivative of the state vector, (km/sec; km/sec^2)
        """
        raise NotImplementedError()
