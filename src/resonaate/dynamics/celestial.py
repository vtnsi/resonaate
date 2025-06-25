"""Defines the abstract base class :class:`.Celestial`."""

from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from functools import partial
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array
from numpy import max as np_max
from numpy import ones_like, spacing, zeros
from scipy.integrate import solve_ivp

# Local Imports
from ..common.labels import IntegratorLabel
from ..common.logger import resonaateLogError, resonaateLogWarning
from ..physics.bodies import Earth
from .dynamics_base import Dynamics, DynamicsErrorFlag
from .integration_events.finite_thrust import ScheduledFiniteThrust

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..physics.time.stardate import ScenarioTime
    from .integration_events import ScheduledEventType
    from .integration_events.station_keeping import StationKeeper


class EarthCollisionError(Exception):
    """Exception raised if a :class:`.Celestial` object crashes into the Earth."""


def checkEarthCollision(r_norm: float):
    r"""Raise an :class:`.EarthCollision` if the specified `r_norm` vector indicates a collision with the Earth.

    Args:
        r_norm (``float``): ``scipy.linalg.norm()`` of current state vector.

    Raises:
        :exc:`.EarthCollision`: If the specified `r_norm` vector indicates an RSO has crashed into
            the Earth.
    """
    # Check if an RSO crashed into the Earth
    if r_norm <= Earth.radius:
        raise EarthCollisionError("An RSO has crashed into the Earth")

    if r_norm < Earth.radius + Earth.atmosphere:
        msg = "An RSO is within 100km of Earth surface"
        resonaateLogWarning(msg)


class Celestial(Dynamics, metaclass=ABCMeta):
    r"""The :class:`.Celestial` dynamics class defines the behavior of space-based :class:`agent_base.Agent` objects."""

    def __init__(self, method: str = IntegratorLabel.RK45):
        r"""Instantiate a :class:`.Celestial` object.

        Args:
            method (``str``, optional): Which ODE integration method to use.
        """
        self._method = method
        self.finite_thrust = None

    def _prepEvents(
        self,
        initial_time: ScenarioTime | float,
        station_keeping: list[StationKeeper] | None = None,
        scheduled_events: list[ScheduledEventType] | None = None,
    ) -> list[Callable[[float, ndarray], float]]:
        r"""Prep events before propagation starts, to add to `solve_ivp` events parameter.

        Args:
            initial_time (:class:`.ScenarioTime`): initial time when propagation starts, sec.
            station_keeping (``list``): :class:`.StationKeeper` objects describing which station keeping
                burns this RSO is capable of.
            scheduled_events (``list``): scheduled events to apply during propagation which can either
                be implemented :class:`.ContinuousStateChangeEvent` or :class:`.DiscreteStateChangeEvent`
                objects.

        Returns:
            ``list``: event functions that are ``Callable`` objects of the form :math:`g(t, y) = 0`.
        """
        events = []
        self.finite_thrust = None
        if station_keeping:
            events.extend(station_keeping)
        if scheduled_events:
            # [NOTE][parallel-maneuver-event-handling] Step four:
            #  Add the event queue to the list of events to be handled by the integration solver.
            events.extend(scheduled_events)
            for event in scheduled_events:
                # Grab finite thrust events that should already be active
                if (
                    isinstance(event, ScheduledFiniteThrust)
                    and event.start_time < initial_time < event.end_time
                ):
                    self.finite_thrust = event.getStateChangeCallback(initial_time)

        return events

    def _applyEvents(
        self,
        t_events: ndarray,
        events: list[ScheduledEventType],
        current_state: ndarray,
    ) -> ndarray:
        r"""Apply any events that stopped integration.

        Args:
            t_events (``ndarray``): times of events that occurred during integration.
            events (``list``): event functions that are ``Callable`` of the form :math:`g(t, y) = 0`.
            current_state (``ndarray``): current state after integration has stopped.

        Returns:
            ``ndarray``: updated state vector after applying any events.
        """
        # Save original shape of the input state
        for event_index, event in enumerate(events):
            if t_events[event_index].size > 0:
                current_time = t_events[event_index][-1]
                if isinstance(event, ScheduledFiniteThrust):
                    self.finite_thrust = event.getStateChangeCallback(current_time)
                else:
                    current_state += event.getStateChange(current_time, current_state[:, 0])[
                        :,
                        None,
                    ]

        return current_state

    def propagate(
        self,
        initial_time: ScenarioTime | float,
        final_time: ScenarioTime | float,
        initial_state: ndarray,
        station_keeping: list[StationKeeper] | None = None,
        scheduled_events: list[ScheduledEventType] | None = None,
        error_flags: DynamicsErrorFlag = DynamicsErrorFlag.COLLISION,
    ) -> ndarray:
        r"""Numerically integrate the state vector forward to the final time.

        Args:
            initial_time (:class:`.ScenarioTime`): time value when the integration will begin, sec.
            final_time (:class:`.ScenarioTime`): time value when the integration will stop, sec.
            initial_state (``ndarray``): (6, K) initial ECI state vector for the integration step, km; km/sec.
            station_keeping (``list``, optional): :class:`.StationKeeper` objects describing which station keeping
                burns this RSO is capable of.
            scheduled_events (``list``, optional): scheduled events to apply during propagation which
                can either be implemented :class:`.ContinuousStateChangeEvent` or
                :class:`.DiscreteStateChangeEvent` objects.
            error_flags (:class:`.DynamicsErrorFlag`): flags marking which errors will halt propagation

        Note:
            :math:`K` refers to the number of parallel integrations being performed

        Returns:
            ``ndarray``: (6, K) final state vector after numerical integration has stopped, km; km/sec.
        """
        if final_time <= initial_time:
            raise ValueError("final_time must be > initial_time")

        # Enforce 2D array
        if len(initial_state.shape) == 1:
            initial_state = initial_state[:, None]
        # Save original shape of the input state
        state_shape = initial_state.shape

        events = self._prepEvents(
            initial_time=initial_time,
            station_keeping=station_keeping,
            scheduled_events=scheduled_events,
        )

        # Continue integration until we reach final_time
        check_collision = bool(DynamicsErrorFlag.COLLISION & error_flags)
        while initial_time < final_time:
            solution = solve_ivp(
                partial(self._differentialEquation, check_collision=check_collision),
                (initial_time, final_time),
                initial_state.ravel(),
                method=self._method,
                rtol=self.RELATIVE_TOL,
                atol=self.ABSOLUTE_TOL * ones_like(initial_state.ravel()),
                events=events,
            )

            initial_state = solution.y[::, -1].reshape(state_shape)
            initial_state = self._applyEvents(
                solution.t_events,
                events,
                initial_state,
            )

            # Retrieve final time, this should auto-exit the loop if fully-integrated
            initial_time = solution.t[-1] + spacing(solution.t[-1])

        # Return final state from the solver
        return (
            initial_state.flatten() if state_shape[1] == 1 else initial_state.reshape(state_shape)
        )

    def propagateBulk(
        self,
        times: list[ScenarioTime | float],
        current_state: ndarray,
        station_keeping: list[StationKeeper] | None = None,
        scheduled_events: list[ScheduledEventType] | None = None,
        error_flags: DynamicsErrorFlag = DynamicsErrorFlag.COLLISION,
    ) -> ndarray:
        r"""Numerically integrate the state vector forward to the final time.

        Args:
            times (``list``): :class:`.ScenarioTime` or ``float`` times to propagate over, where the first entry is
                the initial time, the last entry is the final time, and the times in between are
                passed to ``solve_ivp`` as the ``t_eval`` parameter. Therefore, the returned
                propagated states will be the ODE solution where
                :math:`t = t_i \quad i = 1,...,T` where :math:`T` is one less than the length
                of ``times``.
            current_state (``ndarray``): (6, K) initial ECI state vector for the integration step, km; km/sec.
            station_keeping (``list``, optional): :class:`.StationKeeper` objects describing which station keeping
                burns this RSO is capable of.
            scheduled_events (``list``, optional): scheduled events to apply during propagation which
                can either be implemented :class:`.ContinuousStateChangeEvent` or
                :class:`.DiscreteStateChangeEvent` objects.
            error_flags (:class:`.DynamicsErrorFlag`): flags marking which errors will halt propagation

        Note:
            :math:`K` refers to the number of parallel integrations being performed

        Returns:
            ``ndarray``: (6, K, T) final state vector after numerical integration has stopped, km; km/sec.
                Each (6, K) state vector refers to a time in the ``times`` list.
        """
        if len(times) < 2:
            raise ValueError("Must provide at least two times to integrate between")
        if (current_time := times[0]) > (final_time := times[-1]):
            raise ValueError("final_time must be > initial_time")

        # Save original shape of the input state
        state_shape = current_state.shape

        events = self._prepEvents(
            initial_time=current_time,
            station_keeping=station_keeping,
            scheduled_events=scheduled_events,
        )

        final_states = zeros((*state_shape, len(times)))
        # Continue integration until we reach final_time
        num_times = 0
        atol = self.ABSOLUTE_TOL * ones_like(current_state.ravel())
        check_collision = bool(DynamicsErrorFlag.COLLISION & error_flags)
        while current_time < final_time:
            solution = solve_ivp(
                partial(self._differentialEquation, check_collision=check_collision),
                (current_time, final_time),
                current_state.ravel(),
                method=self._method,
                rtol=self.RELATIVE_TOL,
                atol=atol,
                events=events,
                t_eval=times,
            )

            # Integration failed for some reason
            if not solution.success:
                resonaateLogError(solution.message)
                raise ValueError(solution.message)

            # Pull out solved states at each `times`
            n_t = len(solution.t)
            states = solution.y

            # Integration completed, check if event occurred between last two `times`
            if solution.status == 0 and len(times) == 0:
                n_t = 1
                states = states[..., -1]

            # Properly reshape states
            states = states.reshape((*state_shape, n_t)).copy()

            # Retrieve time when integration stopped, should auto-exit the loop if fully-integrated
            if array(solution.t_events).size == 0:
                current_time = solution.t[-1]
                # print(states.shape, states[...,-1].shape, states[::,-1].shape)
                current_state = states[..., -1]  # .reshape(state_shape)
            else:
                # Retrieve the current state & update the initial state for next loop
                current_time = np_max(solution.t_events)
                current_state = self._applyEvents(
                    t_events=solution.t_events,
                    events=events,
                    # [TODO]: Make this more robust. What about multiple events?
                    current_state=solution.y_events[0].reshape(state_shape),
                )

                # Properly copies updated state back into full state vector for when
                # an event occurs on a `times`
                if current_time == solution.t[-1]:
                    states[..., -1] = current_state.copy()

            # [TODO]: This may not be needed?
            # The reshape should give a _view_ into `states`, but this is just in case
            # and it needs to be verified if it's necessary
            # states[::, -1] = current_state

            # [NOTE]: Need to increment time a tiny bit, so events don't re-trigger.
            # This also protects events that occur on a timestep. The event is applied
            # at the end of the previous timestep, rather than the beginning of current
            current_time += spacing(current_time)

            # Save states to output variable, checks for case where event occurs before times[1]
            final_states[..., num_times : num_times + n_t] = states
            # Update information for next loop
            times = times[n_t:]
            num_times += n_t

        # Return final state from the solver
        return final_states[..., 1:]

    @abstractmethod
    def _differentialEquation(self, time: ScenarioTime | float, state: ndarray) -> ndarray:
        """Calculate the first time derivative of the state for numerical integration.

        Note: this function must take and receive 1-dimensional state vectors! Also, `K` below
            refers to the number of parallel integrations being performed

        Args:
            time (:class:`.ScenarioTime`): the current time of integration, (seconds)
            state (``numpy.ndarray``): (6 * K, ) current state vector in integration, (km, km/sec)

        Returns:
            ``numpy.ndarray``: (6 * K, ) derivative of the state vector, (km/sec; km/sec^2)
        """
        raise NotImplementedError
