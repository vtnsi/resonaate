"""Defines the capabilities and operation of different types of sensors."""
from __future__ import annotations

# Standard Library Imports
from copy import copy
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import asarray, sqrt

# Local Imports
from ..physics import constants as const
from .advanced_radar import ADV_RADAR_DEFAULT_FOV, AdvRadar
from .optical import OPTICAL_DEFAULT_FOV, OPTICAL_DETECTABLE_VISMAG, Optical
from .radar import RADAR_DEFAULT_FOV, Radar
from .sensor_base import Sensor

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Dict, Tuple

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

VALID_SENSOR_FOV_LABELS: Tuple[str] = (
    CONIC_FOV_LABEL,
    RECTANGULAR_FOV_LABEL,
)
"""``list``: Contains list of valid sensor Field of View configurations."""

SOLAR_PANEL_REFLECTIVITY: float = 0.21
"""``float``: reflectivity of a solar panel :cite:t:`montenbruck_2012_orbits`."""

DEFAULT_VIEWING_ANGLE: float = 1.0
"""``float``: default angle for a sensor's FoV."""


def sensorFactory(
    sensor_config: SensingAgentConfig,
) -> Sensor:  # noqa: C901, # pylint: disable=too-many-branches
    """Build a :class:`.Sensor` object for attaching to a :class:`.SensingAgent`.

    Args:
        configuration (:class:`.SensingAgentConfig`): describes the sensor and its capabilities

    Raises:
        ValueError: raised if invalid option is designate for `"sensor_type"`

    Returns:
        :class:`.Sensor`: properly constructed `Sensor` object
    """
    # pylint:disable=import-outside-toplevel
    # Local Imports
    from ..scenario.config.agent_configs import FieldOfViewConfig

    # Set field of view
    if sensor_config.calculate_fov and not sensor_config.field_of_view:
        fov_dict = {
            OPTICAL_LABEL: OPTICAL_DEFAULT_FOV,
            RADAR_LABEL: RADAR_DEFAULT_FOV,
            ADV_RADAR_LABEL: ADV_RADAR_DEFAULT_FOV,
        }
        fov_config = FieldOfViewConfig(**fov_dict[sensor_config.sensor_type])
        field_of_view = copy(fov_config)
    else:
        field_of_view = sensor_config.field_of_view

    # Set detectable vismag
    if sensor_config.detectable_vismag is None and sensor_config.sensor_type == OPTICAL_LABEL:
        sensor_config.detectable_vismag = OPTICAL_DETECTABLE_VISMAG

    # Build generic sensor kwargs
    sensor_args = {
        "az_mask": asarray(sensor_config.azimuth_range) * const.RAD2DEG,  # Assumes radians
        "el_mask": asarray(sensor_config.elevation_range) * const.RAD2DEG,  # Assumes radians
        "r_matrix": asarray(sensor_config.covariance),
        "diameter": sqrt(sensor_config.aperture_area / const.PI) * 2.0,  # Assumes meters^2
        "efficiency": sensor_config.efficiency,
        "slew_rate": sensor_config.slew_rate * const.RAD2DEG,  # Assumes radians/sec
        "exemplar": asarray(sensor_config.exemplar),
        "field_of_view": fieldOfViewFactory(field_of_view),
        "calculate_fov": sensor_config.calculate_fov,
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
        raise ValueError(sensor_config.sensor_type)

    return sensor


def fieldOfViewFactory(configuration: FieldOfViewConfig) -> FieldOfView:
    """Field of View factory method.

    Args:
        configuration (:class:`.FieldOfViewConfig`): field of view config

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
