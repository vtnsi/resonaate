"""Defines the :class:`.Interferometer` sensor class."""

from __future__ import annotations

# Standard Library Imports
from typing import Any

# Third Party Imports
from numpy import array

# Local Imports
from ..physics.measurements import Measurement
from .sensor_base import Sensor

INTERFEROMETER_DEFAULT_FOV: dict[str, Any] = {
    "fov_shape": "rectangular",
    "azimuth_angle": 1.0,
    "elevation_angle": 1.0,
}


class Interferometer(Sensor):
    """Interferometer sensor class (placeholder)."""

    def __init__(  # noqa: PLR0913
        self,
        az_mask,
        el_mask,
        r_matrix,
        diameter,
        efficiency,
        slew_rate,
        field_of_view,
        background_observations,
        minimum_range,
        maximum_range,
        **sensor_args,
    ):
        """Construct an 'Interferometer' sensor object."""
        measurement = Measurement.fromMeasurementLabels(
            ["azimuth_rad", "elevation_rad"],
            r_matrix,
        )
        super().__init__(
            measurement,
            az_mask,
            el_mask,
            diameter,
            efficiency,
            slew_rate,
            field_of_view,
            background_observations,
            minimum_range,
            maximum_range,
            **sensor_args,
        )

    @classmethod
    def fromConfig(cls, sensor_config, field_of_view):
        """Alternative cosntructor using a config."""
        return cls(
            az_mask=array(sensor_config.azimuth_range),
            el_mask=array(sensor_config.elevation_range),
            r_matrix=array(sensor_config.covariance),
            diameter=sensor_config.aperture_diameter,
            efficiency=sensor_config.efficiency,
            slew_rate=sensor_config.slew_rate,
            field_of_view=field_of_view,
            background_observations=sensor_config.background_observations,
            minimum_range=sensor_config.minimum_range,
            maximum_range=sensor_config.maximum_range,
            min_revisit_time=sensor_config.min_revisit_time,
            missed_obs_probabilty=sensor_config.missed_obs_probability, #TODO probability is spelled wrong 
            downtimes=sensor_config.downtimes,
        )
