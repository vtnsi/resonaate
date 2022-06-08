# Standard Library Imports
# Standard Library Imports
from functools import partial
# Third Party Imports
from numpy import concatenate, zeros
# RESONAATE Imports
from .propulsion import Propulsion
from ..physics.transforms.methods import ntw2eci
from ..physics.time.stardate import ScenarioTime


def eventHandle(inst, time, state):  # pylint: disable=unused-argument
    """Event handle for root-finding in integration steps.

    This simply stops when the start time is reached (when returned value crosses zero).

    Args:
        inst (:class:`.Impulsive`): propulsion instance object
        time (float): current integration time in epoch seconds
        state (``numpy.ndarray``): current integration state vector

    Returns:
        (float): value that the ode solver uses to root find
    """
    return time - inst.start_time


class Impulsive(Propulsion):
    """Impulsive propulsion event."""

    def __init__(self, time, deltaV, eci_flag=False):
        """Instantiates an Impulsive propulsion object.

        Args:
            time (float): time of impulsive event in epoch seconds
            deltaV (``numpy.ndarray``): 3x1 array of thrust vectors (km/sec)
            eci_flag (bool, optional): Whether the delta v is applied in the ECI frame. Defaults to False.
        """
        super(Impulsive, self).__init__()
        self.start_time = ScenarioTime(time)
        self.stop_time = ScenarioTime(time + 1)
        self.thrust = concatenate((zeros(3), deltaV))
        self.eci_flag = eci_flag

        self.event_handle = partial(eventHandle, self)

        ## [TODO] AFAIK, these have to occur after the instance method definition ~ dylant
        # Set a terminal attribute of the event function as True to force implementation to stop
        self.event_handle.terminal = True
        # Enforce that the event happens only when value goes from negative to positive
        self.event_handle.direction = 1

    def getThrust(self, state, time):
        """Calculates the thrust vector.

        Args:
            state (``numpy.ndarray``): 6x1 array of Agent's state
            time (float): time of the maneuver in epoch seconds

        Returns:
            (``numpy.ndarray``): 6x1 ECI acceleration vector
        """
        if self.eci_flag:
            thrust = self.thrust
        else:
            thrust = ntw2eci(state, self.thrust)

        return thrust
