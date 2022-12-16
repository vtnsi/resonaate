"""Defines the capabilities and operation of different types of sensors."""
from __future__ import annotations

# Standard Library Imports
from copy import copy
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, sqrt

# Local Imports
from ..physics import constants as const
from .advanced_radar import AdvRadar
from .field_of_view import ConicFoV, FieldOfView, RectangularFoV
from .optical import Optical
from .radar import Radar
from .sensor_base import Sensor

if TYPE_CHECKING:
    # Local Imports
    from ..scenario.config.agent_configs import FieldOfViewConfig, SensingAgentConfig

OPTICAL_LABEL: str = "Optical"
"""``str``: Constant string used to describe optical sensors."""

RADAR_LABEL: str = "Radar"
"""``str``: Constant string used to describe radar sensors."""

ADV_RADAR_LABEL: str = "AdvRadar"
"""``str``: Constant string used to describe advanced radar sensors."""

CONIC_FOV_LABEL: str = "conic"
"""``str``: Constant string used to describe conic field of view."""

RECTANGULAR_FOV_LABEL: str = "rectangular"
"""str: Constant string used to describe rectangular field of view."""

VALID_SENSOR_FOV_LABELS: tuple[str] = (
    CONIC_FOV_LABEL,
    RECTANGULAR_FOV_LABEL,
)
"""``tuple``: Contains valid sensor Field of View configurations."""

SOLAR_PANEL_REFLECTIVITY: float = 0.21
"""``float``: reflectivity of a solar panel :cite:t:`montenbruck_2012_orbits`, unit-less."""

DEFAULT_VIEWING_ANGLE: float = 1.0
"""``float``: default angle for a sensor's FoV, degrees."""


def sensorFactory(sensor_config: SensingAgentConfig) -> Sensor:
    """Build a :class:`.Sensor` object for attaching to a :class:`.SensingAgent`.

    Args:
        sensor_config (:class:`.SensingAgentConfig`): describes the sensor and its capabilities

    Raises:
        ValueError: raised if invalid option is designate for `"sensor_type"`

    Returns:
        :class:`.Sensor`: properly constructed `Sensor` object
    """
    # Build generic sensor kwargs
    sensor_args = {
        "az_mask": array(sensor_config.azimuth_range) * const.RAD2DEG,  # Assumes radians
        "el_mask": array(sensor_config.elevation_range) * const.RAD2DEG,  # Assumes radians
        "r_matrix": array(sensor_config.covariance),
        "diameter": sqrt(sensor_config.aperture_area / const.PI) * 2.0,  # Assumes meters^2
        "efficiency": sensor_config.efficiency,
        "slew_rate": sensor_config.slew_rate * const.RAD2DEG,  # Assumes radians/sec
        "exemplar": array(sensor_config.exemplar),
        "field_of_view": fieldOfViewFactory(sensor_config.field_of_view),
        "background_observations": sensor_config.background_observations,
        "minimum_range": sensor_config.minimum_range,
        "maximum_range": sensor_config.maximum_range,
    }

    # Instantiate sensor object. Add extra params if needed
    if sensor_config.sensor_type == OPTICAL_LABEL:
        sensor_args["detectable_vismag"] = sensor_config.detectable_vismag
        sensor = Optical(**sensor_args)
    elif sensor_config.sensor_type == RADAR_LABEL:
        sensor_args["power_tx"] = sensor_config.tx_power
        sensor_args["frequency"] = sensor_config.tx_frequency
        sensor = Radar(**sensor_args)
    elif sensor_config.sensor_type == ADV_RADAR_LABEL:
        sensor_args["power_tx"] = sensor_config.tx_power
        sensor_args["frequency"] = sensor_config.tx_frequency
        sensor = AdvRadar(**sensor_args)
    else:
        raise ValueError(f"Invalid sensor type provided to config: {sensor_config.sensor_type}")

    return sensor


def fieldOfViewFactory(configuration: FieldOfViewConfig) -> FieldOfView:
    """Field of View factory method.

    Args:
        configuration (:class:`.FieldOfViewConfig`): field of view config

    Returns:
        :class:`.FieldOfView`
    """
    if configuration.fov_shape == CONIC_FOV_LABEL:
        return ConicFoV(configuration.cone_angle * const.DEG2RAD)

    if configuration.fov_shape == RECTANGULAR_FOV_LABEL:
        return RectangularFoV(
            azimuth_angle=configuration.azimuth_angle * const.DEG2RAD,
            elevation_angle=configuration.elevation_angle * const.DEG2RAD,
        )

    raise ValueError(f"wrong FoV shape: {configuration.fov_shape}")
