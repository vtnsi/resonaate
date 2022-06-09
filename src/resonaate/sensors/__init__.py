"""Defines the capabilities and operation of different types of sensors."""
# Third Party Imports
from numpy import asarray, sqrt

# Local Imports
from ..physics import constants as const
from .advanced_radar import AdvRadar
from .optical import Optical
from .radar import Radar

OPTICAL_LABEL = "Optical"
"""str: Constant string used to describe optical sensors."""

RADAR_LABEL = "Radar"
"""str: Constant string used to describe radar sensors."""

ADV_RADAR_LABEL = "AdvRadar"
"""str: Constant string used to describe advanced radar sensors."""


def sensorFactory(configuration):
    """Build a :class:`.Sensor` object for attaching to a :class:`.SensingAgent`.

    Args:
        configuration (``dict``): describes the sensor and its capabilities

    Raises:
        ValueError: raised if invalid option is designate for `"sensor_type"`

    Returns:
        :class:`.Sensor`: properly constructed `Sensor` object
    """
    # Build generic sensor kwargs
    sensor_args = {
        "az_mask": asarray(configuration.azimuth_range) * const.RAD2DEG,  # Assumes radians
        "el_mask": asarray(configuration.elevation_range) * const.RAD2DEG,  # Assumes radians
        "r_matrix": asarray(configuration.covariance),
        "diameter": sqrt(configuration.aperture_area / const.PI) * 2.0,  # Assumes meters^2
        "efficiency": configuration.efficiency,
        "slew_rate": configuration.slew_rate * const.RAD2DEG,  # Assumes radians/sec
        "exemplar": asarray(configuration.exemplar),
    }

    # Instantiate sensor object. Add extra params if needed
    sensor_type = configuration.sensor_type
    if sensor_type == OPTICAL_LABEL:
        sensor = Optical(**sensor_args)
    elif sensor_type == RADAR_LABEL:
        sensor_args["power_tx"] = configuration.tx_power
        sensor_args["frequency"] = configuration.tx_frequency
        sensor = Radar(**sensor_args)
    elif sensor_type == ADV_RADAR_LABEL:
        sensor_args["power_tx"] = configuration.tx_power
        sensor_args["frequency"] = configuration.tx_frequency
        sensor = AdvRadar(**sensor_args)
    else:
        raise ValueError(sensor_type)

    return sensor
