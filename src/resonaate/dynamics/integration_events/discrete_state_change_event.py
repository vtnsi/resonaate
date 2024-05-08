"""Defines the :class:`.DiscreteStateChangeEvent` abstract base class."""

from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod


class DiscreteStateChangeEvent(metaclass=ABCMeta):
    """Event that describes a discrete change in state that must interrupt integration to be applied.

    For more information, see `Scipy's documentation`_ for ``solve_ivp()``.

        .. _Scipy's documentation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html
    """

    terminal = True
    """bool: Whether to terminate integration if this event occurs."""

    direction = 0.0
    """float: Value of zero indicates that either direction of zero crossing should trigger this event."""

    @abstractmethod
    def __call__(self, time, state):
        """When this function returns zero during integration, it interrupts the integration process.

        Args:
            time (float): current integration time in epoch seconds
            state (numpy.ndarray): current integration state vector

        Returns:
            (float): value that the ode solver uses to root find
        """
        raise NotImplementedError

    @abstractmethod
    def getStateChange(self, time, state):
        """Return the delta between `state` and the desired end state.

        Args:
            time (float): current integration time in epoch seconds
            state (numpy.ndarray): current state vector

        Returns:
            numpy.ndarray: vector to add to `state` that results in the desired end state
        """
        raise NotImplementedError
