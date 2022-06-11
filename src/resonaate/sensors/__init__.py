"""Defines the capabilities and operation of different types of sensors."""
# Third Party Imports
from numpy import asarray, sqrt

# Local Imports
from ..physics import constants as const
from .advanced_radar import (
    ADV_RADAR_DEFAULT_FOV,
    ADV_RADAR_MAX_RANGE,
    ADV_RADAR_MIN_DETECTABLE_VISMAG,
    ADV_RADAR_MIN_RANGE,
    AdvRadar,
)
from .optical import (
    OPTICAL_DEFAULT_FOV,
    OPTICAL_MAX_RANGE,
    OPTICAL_MIN_DETECTABLE_VISMAG,
    OPTICAL_MIN_RANGE,
    Optical,
)
from .radar import (
    RADAR_DEFAULT_FOV,
    RADAR_MAX_RANGE,
    RADAR_MIN_DETECTABLE_VISMAG,
    RADAR_MIN_RANGE,
    Radar,
)

OPTICAL_LABEL = "Optical"
"""str: Constant string used to describe optical sensors."""

RADAR_LABEL = "Radar"
"""str: Constant string used to describe radar sensors."""

ADV_RADAR_LABEL = "AdvRadar"
"""str: Constant string used to describe advanced radar sensors."""

ADV_RADAR_MIN_DETECTABLE_VISMAG = 25.0  # Default minimum observable visual magnitude (unitless)
ADV_RADAR_MIN_RANGE = 0  # Default minimum range an RSO must be at to be observable (km)
ADV_RADAR_MAX_RANGE = 10000  # Default maximum range an RSO must be at to be observable (km)
ADV_RADAR_DEFAULT_FOV = 179  # Default Field of View of an advanced radar sensor (degrees)


def sensorFactory(configuration, fov=True):
    """Build a :class:`.Sensor` object for attaching to a :class:`.SensingAgent`.

    Args:
        configuration (``dict``): describes the sensor and its capabilities
        fov (``bool``): Indicator whether or not this sensor should observe all objects in it's FoV

    Raises:
        ValueError: raised if invalid option is designate for `"sensor_type"`

    Returns:
        :class:`.Sensor`: properly constructed `Sensor` object
    """
    # Local Imports
    from ..scenario.config.base import NO_SETTING, ConfigError

    if configuration.field_of_view is NO_SETTING:
        if configuration.sensor_type in OPTICAL_LABEL:
            field_of_view = OPTICAL_DEFAULT_FOV
        elif configuration.sensor_type in RADAR_LABEL:
            field_of_view = RADAR_DEFAULT_FOV
        elif configuration.sensor_type in ADV_RADAR_LABEL:
            field_of_view = ADV_RADAR_DEFAULT_FOV
        else:
            err = "Incorrect Sensor Type Setting"
            raise ConfigError(str(configuration.field_of_view), err)
    else:
        field_of_view = configuration.field_of_view

    if configuration.minimum_range is NO_SETTING:
        if configuration.sensor_type in OPTICAL_LABEL:
            minimum_range = OPTICAL_MIN_RANGE
        elif configuration.sensor_type in RADAR_LABEL:
            minimum_range = RADAR_MIN_RANGE
        elif configuration.sensor_type in ADV_RADAR_LABEL:
            minimum_range = ADV_RADAR_MIN_RANGE
        else:
            err = "Incorrect Sensor Type Setting"
            raise ConfigError(str(configuration.minimum_range), err)

    else:
        minimum_range = configuration.minimum_range

    if configuration.maximum_range is NO_SETTING:
        if configuration.sensor_type in OPTICAL_LABEL:
            maximum_range = OPTICAL_MAX_RANGE
        elif configuration.sensor_type in RADAR_LABEL:
            maximum_range = RADAR_MAX_RANGE
        elif configuration.sensor_type in ADV_RADAR_LABEL:
            maximum_range = ADV_RADAR_MAX_RANGE
        else:
            err = "Incorrect Sensor Type Setting"
            raise ConfigError(str(configuration.maximum_range), err)

    else:
        maximum_range = configuration.maximum_range

    if configuration.detectable_vismag is NO_SETTING:
        if configuration.sensor_type in OPTICAL_LABEL:
            detectable_vismag = OPTICAL_MIN_DETECTABLE_VISMAG
        elif configuration.sensor_type in RADAR_LABEL:
            detectable_vismag = RADAR_MIN_DETECTABLE_VISMAG
        elif configuration.sensor_type in ADV_RADAR_LABEL:
            detectable_vismag = ADV_RADAR_MIN_DETECTABLE_VISMAG
        else:
            err = "Incorrect Sensor Type Setting"
            raise ConfigError(str(configuration.detectable_vismag), err)

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
        "field_of_view": field_of_view,  # Assumes degrees
        "minimum_range": minimum_range,
        "maximum_range": maximum_range,
        "detectable_vismag": detectable_vismag,
        "calculate_fov": fov,
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
