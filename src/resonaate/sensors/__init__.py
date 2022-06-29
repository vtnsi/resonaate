"""Defines the capabilities and operation of different types of sensors."""
from __future__ import annotations

# Standard Library Imports
from copy import copy
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import asarray, sqrt

# Local Imports
from ..physics import constants as const
from .advanced_radar import (
    ADV_RADAR_DEFAULT_FOV,
    ADV_RADAR_DETECTABLE_VISMAG,
    ADV_RADAR_MAX_RANGE,
    ADV_RADAR_MIN_RANGE,
    AdvRadar,
)
from .optical import (
    OPTICAL_DEFAULT_FOV,
    OPTICAL_DETECTABLE_VISMAG,
    OPTICAL_MAX_RANGE,
    OPTICAL_MIN_RANGE,
    Optical,
)
from .radar import (
    RADAR_DEFAULT_FOV,
    RADAR_DETECTABLE_VISMAG,
    RADAR_MAX_RANGE,
    RADAR_MIN_RANGE,
    Radar,
)

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Dict, Tuple

    # Local Imports
    from ..scenario.config.agent_configs import FieldOfViewConfig

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


def sensorFactory(configuration):  # noqa: C901, # pylint: disable=too-many-branches
    """Build a :class:`.Sensor` object for attaching to a :class:`.SensingAgent`.

    Args:
        configuration (``dict``): describes the sensor and its capabilities

    Raises:
        ValueError: raised if invalid option is designate for `"sensor_type"`

    Returns:
        :class:`.Sensor`: properly constructed `Sensor` object
    """
    # pylint:disable=import-outside-toplevel
    # Local Imports
    from ..scenario.config.agent_configs import FieldOfViewConfig
    from ..scenario.config.base import NO_SETTING

    # Set field of view
    if configuration.field_of_view.fov_shape is NO_SETTING:
        fov_dict = {
            OPTICAL_LABEL: OPTICAL_DEFAULT_FOV,
            RADAR_LABEL: RADAR_DEFAULT_FOV,
            ADV_RADAR_LABEL: ADV_RADAR_DEFAULT_FOV,
        }
        fov_config = FieldOfViewConfig()
        fov_config.readConfig(fov_dict[configuration.sensor_type])
        field_of_view = copy(fov_config)
    else:
        field_of_view = configuration.field_of_view

    # Set minimum observable range
    if configuration.minimum_range is NO_SETTING:
        min_range_dict = {
            OPTICAL_LABEL: OPTICAL_MIN_RANGE,
            RADAR_LABEL: RADAR_MIN_RANGE,
            ADV_RADAR_LABEL: ADV_RADAR_MIN_RANGE,
        }
        minimum_range = min_range_dict[configuration.sensor_type]
    else:
        minimum_range = configuration.minimum_range

    # Set maximum observable range
    if configuration.maximum_range is NO_SETTING:
        max_range_dict = {
            OPTICAL_LABEL: OPTICAL_MAX_RANGE,
            RADAR_LABEL: RADAR_MAX_RANGE,
            ADV_RADAR_LABEL: ADV_RADAR_MAX_RANGE,
        }
        maximum_range = max_range_dict[configuration.sensor_type]
    else:
        maximum_range = configuration.maximum_range

    # Set detectable vismag
    if configuration.detectable_vismag is NO_SETTING:
        detectable_vismag_dict = {
            OPTICAL_LABEL: OPTICAL_DETECTABLE_VISMAG,
            RADAR_LABEL: RADAR_DETECTABLE_VISMAG,
            ADV_RADAR_LABEL: ADV_RADAR_DETECTABLE_VISMAG,
        }
        detectable_vismag = detectable_vismag_dict[configuration.sensor_type]
    else:
        detectable_vismag = configuration.detectable_vismag

    # Build generic sensor kwargs
    sensor_args = {
        "az_mask": asarray(configuration.azimuth_range) * const.RAD2DEG,  # Assumes radians
        "el_mask": asarray(configuration.elevation_range) * const.RAD2DEG,  # Assumes radians
        "r_matrix": asarray(configuration.covariance),
        "diameter": sqrt(configuration.aperture_area / const.PI) * 2.0,  # Assumes meters^2
        "efficiency": configuration.efficiency,
        "slew_rate": configuration.slew_rate * const.RAD2DEG,  # Assumes radians/sec
        "exemplar": asarray(configuration.exemplar),
        "field_of_view": fieldOfViewFactory(field_of_view),
        "calculate_fov": configuration.calculate_fov,
        "minimum_range": minimum_range,
        "maximum_range": maximum_range,
        "detectable_vismag": detectable_vismag,
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
    if configuration.fov_shape == "conic":
        return ConicFoV(configuration)

    if configuration.fov_shape == "rectangular":
        return RectangularFoV(configuration)

    raise ValueError("wrong FoV type input")


class FieldOfView:
    """Field of View base class."""

    def __init__(self, config: FieldOfViewConfig) -> None:
        """Initialize a Field of View object.

        Args:
            config (:class:`.FieldOfViewConfig`): Field of View config object
        """
        self.fov_shape = config.fov_shape


class ConicFoV(FieldOfView):
    """Conic Field of View Subclass."""

    def __init__(self, config: FieldOfViewConfig) -> None:
        """Initialize A ConicFoV object.

        Args:
            config (:class:`.FieldOfViewConfig`): Field of View config object
        """
        super().__init__(config)
        self.cone_angle = config.cone_angle * const.DEG2RAD


class RectangularFoV(FieldOfView):
    """Rectangular Field of View Subclass."""

    def __init__(self, config: FieldOfViewConfig) -> None:
        """Initialize A RectangularFoV object.

        Args:
            config (:class:`.FieldOfViewConfig`): Field of View config object
        """
        super().__init__(config)
        self.azimuth_angle = config.azimuth_angle * const.DEG2RAD
        self.elevation_angle = config.elevation_angle * const.DEG2RAD
