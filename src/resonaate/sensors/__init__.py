"""Defines the capabilities and operation of different types of sensors."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ..common.labels import SensorLabel
from .advanced_radar import AdvRadar
from .field_of_view import FieldOfView
from .optical import Optical
from .radar import Radar

if TYPE_CHECKING:
    # Local Imports
    from ..scenario.config.sensor_config import SensorConfig
    from .sensor_base import Sensor


def sensorFactory(sensor_config: SensorConfig) -> Sensor:
    """Build a :class:`.Sensor` object for attaching to a :class:`.SensingAgent`.

    Args:
        sensor_config (:class:`.SensorConfig`): describes the sensor and its capabilities

    Raises:
        ValueError: raised if invalid option is designate for `"sensor_type"`

    Returns:
        :class:`.Sensor`: properly constructed `Sensor` object
    """
    fov = FieldOfView.fromConfig(sensor_config.field_of_view)
    if sensor_config.type == SensorLabel.OPTICAL:
        sensor = Optical.fromConfig(sensor_config, fov)
    elif sensor_config.type == SensorLabel.RADAR:
        sensor = Radar.fromConfig(sensor_config, fov)
    elif sensor_config.type == SensorLabel.ADV_RADAR:
        sensor = AdvRadar.fromConfig(sensor_config, fov)
    else:
        raise ValueError(f"Invalid sensor type provided to config: {sensor_config.type}")

    return sensor
