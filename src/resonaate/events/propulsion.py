# Standard Library Imports
from abc import abstractmethod
# Third Party Imports
# RESONAATE Imports
from ..physics.time.stardate import ScenarioTime


class Propulsion:
    """The Propulsion Class characterizes the maneuverability capabilities of an Agent object."""

    @abstractmethod
    def getThrust(self, state, time):
        """Abstract method that's required for all propulsion types."""
        raise NotImplementedError

    @property
    def start_time(self):
        """Returns event start time."""
        return self._start_time

    @start_time.setter
    def start_time(self, new_start_time):
        if isinstance(new_start_time, ScenarioTime):
            self._start_time = new_start_time  # pylint: disable=attribute-defined-outside-init
        else:
            raise TypeError("Propulsion: Invalid input for start_time property.")

    @property
    def stop_time(self):
        """Returns event stop time."""
        return self._stop_time

    @stop_time.setter
    def stop_time(self, new_stop_time):
        if isinstance(new_stop_time, ScenarioTime):
            self._stop_time = new_stop_time  # pylint: disable=attribute-defined-outside-init
        else:
            raise TypeError("Propulsion: Invalid input for stop_time property.")

    @property
    def thrust(self):
        """Returns propulsion thrust acceleration."""
        return self._thrust

    @thrust.setter
    def thrust(self, new_thrust):
        ## [TODO] Add checking for vector size/shape here.
        self._thrust = new_thrust  # pylint: disable=attribute-defined-outside-init
