"""Defines the abstract base class :class:`.Dynamics`."""
# Standard Library Imports
from abc import abstractmethod
# Third Party Imports
# RESONAATE Imports


class Dynamics:
    """Abstract dynamics base class.

    The Dynamics class gives a general foundation for any dynamics model that describes
    how an Agent will behave within a specified scenario.
    """

    RELATIVE_TOL = 10**-10
    ABSOLUTE_TOL = 10**-12

    @abstractmethod
    def propagate(self, initial_time, final_time, initial_state, station_keeping=None, scheduled_events=None):
        """Abstract method for forwards propagation."""
        raise NotImplementedError
