"""Defines the capabilities and operation of different types of sensors."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import asarray, sqrt

# Local Imports
from ..physics import constants as const
from .advanced_radar import AdvRadar
from .optical import Optical
from .radar import Radar

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Dict, Tuple

OPTICAL_LABEL: str = "Optical"
"""str: Constant string used to describe optical sensors."""

RADAR_LABEL: str = "Radar"
"""str: Constant string used to describe radar sensors."""

ADV_RADAR_LABEL: str = "AdvRadar"
"""str: Constant string used to describe advanced radar sensors."""

VALID_SENSOR_FOV_LABELS: Tuple[str] = (
    "conic",
    "rectangular",
)
"""list: Contains list of valid sensor Field of View configurations."""


def sensorFactory(configuration):
    """Build a :class:`.Sensor` object for attaching to a :class:`.SensingAgent`.

    Args:
        configuration (``dict``): describes the sensor and its capabilities
        fov (``bool``): Indicator whether or not this sensor should observe all objects in it's FoV

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
        "field_of_view": fieldOfViewFactory(configuration.field_of_view),
        "calculate_fov": configuration.calculate_fov,
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


def fieldOfViewFactory(configuration: Dict) -> FieldOfView:
    """Field of View factory method.

    Args:
        configuration (``Dict``): field of view config

    Returns:
        :class:`.FieldOfView`
    """
    if configuration.image_type == "conic":
        return ConicFoV(configuration)

    if configuration.image_type == "rectangular":
        return RectangularFoV(configuration)

    raise ValueError("wrong FoV type input")


class FieldOfView:
    """Field of View base class."""

    def __init__(self, config: Dict) -> None:
        """Initialize a Field of View object.

        Args:
            config (``Dict``): Field of View config object
        """
        self.image_type = config.image_type


class ConicFoV(FieldOfView):
    """Conic Field of View Subclass."""

    def __init__(self, config: Dict) -> None:
        """Initialize A ConicFoV object.

        Args:
            config (``Dict``): Field of View config object
        """
        super().__init__(config)
        self.cone_angle = config.cone_angle


class RectangularFoV(FieldOfView):
    """Rectangular Field of View Subclass."""

    def __init__(self, config: Dict) -> None:
        """Initialize A RectangularFoV object.

        Args:
            config (``Dict``): Field of View config object
        """
        super().__init__(config)
        self.x_fov = config.x_degrees
        self.y_fov = config.y_degrees
