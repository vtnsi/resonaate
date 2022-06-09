"""Module containing functions to fetch targets in a sensor's FOV."""
# Standard Library Imports
from typing import List

# Third Party Imports
from numpy import arccos, array, ndarray, vdot
from scipy.linalg import norm

# Local Imports
from ..agents.estimate_agent import EstimateAgent
from ..agents.target_agent import TargetAgent
from ..physics.constants import RAD2DEG
from ..physics.sensor_utils import lineOfSight
from ..sensors.sensor_base import Sensor


def checkOpticalFOV(
    sensor: Sensor, tasked_agent: EstimateAgent, all_target_agents: List[TargetAgent]
):
    """Perform bulk FOV check on all RSOs.

    Args:
        sensor (:class:`.Sensor`): sensor to check FOV
        tasked_agent (:class:`.EstimateAgent`): estimate that sensor is looking for
        all_target_agents (``list``): list of target agents truth

    Returns:
        targets_in_fov (``list``): `.TargetAgent` objects in sensor FOV
    """
    boresight_vector = array(tasked_agent.eci_state[:3] - sensor.host.eci_state[:3])
    sensor_position = array(
        [
            sensor.host.eci_position_x_km,
            sensor.host.eci_position_y_km,
            sensor.host.eci_position_z_km,
        ]
    )

    # filter out targets that are not in line of sight of the sensor
    targets_in_los = filter(  # pylint:disable=bad-builtin
        lambda x: lineOfSight(sensor_position, x.eci_state[:3]), all_target_agents
    )  # pylint:disable=bad-builtin

    # filter out targets outside of FOV
    targets_in_fov = filter(  # pylint:disable=bad-builtin
        lambda x: getOffBoresightAngle(sensor_position, boresight_vector, x.eci_state[:3])
        <= sensor.FOV_ANGLE,
        targets_in_los,
    )  # pylint:disable=bad-builtin

    return targets_in_fov


def getOffBoresightAngle(sensor_position: ndarray, boresight: ndarray, target_position: ndarray):
    """Calculates the angle of the target off-boresight.

    Args:
        sensor_position (``np.ndarray``): ECI position of the sensor
        boresight (``np.ndarray``): ECI boresight vector of the sensor
        target (``np.ndarray``): ECI position of the target

    Returns:
        ``bool``: whether target is in the sensor FOV cone
    """
    topos_eci = array(target_position - sensor_position)
    return arccos(vdot(topos_eci, boresight) / (norm(topos_eci) * norm(boresight))) * RAD2DEG
