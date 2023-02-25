"""Defines the capabilities and operation of different types of sensors."""
from __future__ import annotations

# Standard Library Imports
from copy import copy
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array

# Local Imports
from ..common.labels import FoVLabel, SensorLabel
from ..physics import constants as const
from .field_of_view import ConicFoV, FieldOfView, RectangularFoV
from .measurement import MEASUREMENT_TYPE_MAP, Measurement

if TYPE_CHECKING:
    # Local Imports
    from ..scenario.config.sensor_config import FieldOfViewConfig, SensorConfig
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
    # pylint: disable=import-outside-toplevel
    # [FIXME]: This shouldn't be necessary. Either move Measurement to diff package or
    #   move this factory method into the base class or a fromConfig?
    # Local Imports
    from .advanced_radar import AdvRadar
    from .optical import Optical
    from .radar import Radar

    # Build generic sensor kwargs
    sensor_args = {
        "az_mask": array(sensor_config.azimuth_range),  # Assumes degrees
        "el_mask": array(sensor_config.elevation_range),  # Assumes degrees
        "r_matrix": array(sensor_config.covariance),
        "diameter": sensor_config.aperture_diameter,  # Assumes meters
        "efficiency": sensor_config.efficiency,
        "slew_rate": sensor_config.slew_rate,  # Assumes deg/sec
        "field_of_view": fieldOfViewFactory(sensor_config.field_of_view),
        "background_observations": sensor_config.background_observations,
        "minimum_range": sensor_config.minimum_range,
        "maximum_range": sensor_config.maximum_range,
    }

    # Instantiate sensor object. Add extra params if needed
    if sensor_config.type == SensorLabel.OPTICAL:
        sensor_args["detectable_vismag"] = sensor_config.detectable_vismag
        sensor = Optical(**sensor_args)
    elif sensor_config.type == SensorLabel.RADAR:
        sensor_args["tx_power"] = sensor_config.tx_power
        sensor_args["tx_frequency"] = sensor_config.tx_frequency
        sensor_args["min_detectable_power"] = sensor_config.min_detectable_power
        sensor = Radar(**sensor_args)
    elif sensor_config.type == SensorLabel.ADV_RADAR:
        sensor_args["tx_power"] = sensor_config.tx_power
        sensor_args["tx_frequency"] = sensor_config.tx_frequency
        sensor_args["min_detectable_power"] = sensor_config.min_detectable_power
        sensor = AdvRadar(**sensor_args)
    else:
        raise ValueError(f"Invalid sensor type provided to config: {sensor_config.type}")

    return sensor


def fieldOfViewFactory(configuration: FieldOfViewConfig) -> FieldOfView:
    """Field of View factory method.

    Args:
        configuration (:class:`.FieldOfViewConfig`): field of view config

    Returns:
        :class:`.FieldOfView`
    """
    if configuration.fov_shape == FoVLabel.CONIC:
        return ConicFoV(configuration.cone_angle * const.DEG2RAD)

    if configuration.fov_shape == FoVLabel.RECTANGULAR:
        return RectangularFoV(
            azimuth_angle=configuration.azimuth_angle * const.DEG2RAD,
            elevation_angle=configuration.elevation_angle * const.DEG2RAD,
        )

    raise ValueError(f"wrong FoV shape: {configuration.fov_shape}")
