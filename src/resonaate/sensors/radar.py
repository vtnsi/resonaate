"""Defines the :class:`.Radar` sensor class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array

# Local Imports
from ..common.labels import Explanation, FoVLabel
from ..physics.constants import M2KM, PI, SPEED_OF_LIGHT
from ..physics.measurements import Measurement, getRange
from ..physics.sensor_utils import calculateRadarCrossSection
from .sensor_base import Sensor

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self

    # Local Imports
    from ..scenario.config.sensor_config import RadarConfig
    from .field_of_view import FieldOfView


RADAR_DEFAULT_FOV: dict[str, Any] = {
    "fov_shape": FoVLabel.RECTANGULAR,
    "cone_angle": 1.0,
}
"""``dict``: Default Field of View (conic) of a radar sensor, degrees."""


RADAR_DEFAULT_TX_POWER: float = 3e6
"""``float``: Default transmit power of a radar sensor, W."""

RADAR_DEFAULT_TX_FREQUENCY: float = 1e5
"""``float``: Default transmit frequency of a radar sensor, Hz."""


class Radar(Sensor):
    """Radar sensor class.

    The Radar sensor class provides the framework and functionality for radar sensor payloads,
    which provide azimuth, elevation, & range measurements with each observation.

    References:
        #  :cite:t:`vallado_2016_aiaa_covariance`
    """

    def __init__(  # noqa: PLR0913
        self,
        az_mask: ndarray,
        el_mask: ndarray,
        r_matrix: ndarray,
        diameter: float,
        efficiency: float,
        tx_power: float,
        tx_frequency: float,
        min_detectable_power: float,
        slew_rate: float,
        field_of_view: FieldOfView,
        background_observations: bool,
        minimum_range: float,
        maximum_range: float,
        **sensor_args: dict,
    ):
        """Construct a `Radar` sensor object.

        Args:
            az_mask (``ndarray``): azimuth mask for visibility conditions
            el_mask (``ndarray``): elevation mask for visibility conditions
            r_matrix (``ndarray``): measurement noise covariance matrix
            diameter (``float``): size of sensor (m)
            efficiency (``float``): efficiency percentage of the sensor
            tx_power (``float``): radar's transmit power (W)
            tx_frequency (``float``): radar's operating frequency (Hz)
            min_detectable_power (``float``): The smallest received power that can be detected by the radar` (W)
            slew_rate (``float``): maximum rotational speed of the sensor (deg/sec)
            field_of_view (``float``): Angular field of view of sensor (deg)
            background_observations (``bool``): whether or not to calculate serendipitous observations, default=True
            minimum_range (``float``): minimum RSO range needed for visibility
            maximum_range (``float``): maximum RSO range needed for visibility
            sensor_args (``dict``): extra key word arguments for easy extension of the `Sensor` interface
        """
        measurement = Measurement.fromMeasurementLabels(
            ["azimuth_rad", "elevation_rad", "range_km", "range_rate_km_p_sec"],
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

        # Save extra class variables
        self.tx_power = tx_power
        self.tx_frequency = tx_frequency
        self.min_detectable_power = min_detectable_power
        self.wavelength = SPEED_OF_LIGHT / tx_frequency

        # Calculate maximum auxiliary range
        self.max_range_aux = self._maximumDetectableRange(diameter, min_detectable_power)

    @classmethod
    def fromConfig(cls, sensor_config: RadarConfig, field_of_view: FieldOfView) -> Self:
        """Alternative constructor for radar sensors by using config object.

        Args:
            sensor_config (RadarConfig): radar sensor configuration object.
            field_of_view (FieldOfView): sensor field of view model.

        Returns:
            Self: constructed radar sensor object.
        """
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
            tx_power=sensor_config.tx_power,
            tx_frequency=sensor_config.tx_frequency,
            min_detectable_power=sensor_config.min_detectable_power,
        )

    def _maximumDetectableRange(self, diameter: float, min_detect_power: float) -> float:
        """Calculate the auxiliary maximum range for a detection.

        This is an intermediate calculation for simplifying when `maximumRangeTo()` is called.

        References:
            :cite:t:`nastasi_2018_diss`, Pg 46, Eqn 3.8

        Args:
            diameter (``float``): aperture diameter, m^2
            min_detect_power (``float``): minimum detectable power of the sensor, W

        Returns:
            ``float``: auxiliary maximum range, m^1/2
        """
        numerator = PI * self.tx_power * diameter**4 * self.efficiency**2
        denominator = 64 * self.wavelength**2 * min_detect_power
        return ((numerator / denominator) ** 0.25) * M2KM

    def isVisible(
        self,
        tgt_eci_state: ndarray,
        viz_cross_section: float,
        reflectivity: float,
        slant_range_sez: ndarray,
    ) -> tuple[bool, Explanation]:
        """Determine if the target is in view of the sensor.

        Args:
            tgt_eci_state (``ndarray``): 6x1 ECI state vector of the target agent
            viz_cross_section (``float``): area of the target facing the sun (m^2)
            reflectivity (``float``): Reflectivity of RSO (unitless)
            slant_range_sez (``ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)

        Returns:
            ``bool``: True if target is visible; False if target is not visible
            :class:`.Explanation`: Reason observation was visible or not
        """
        line_of_sight, explanation = super().isVisible(
            tgt_eci_state,
            viz_cross_section,
            reflectivity,
            slant_range_sez,
        )
        if not line_of_sight:
            return False, explanation

        # Early exit if target not in radar sensor's range
        if getRange(slant_range_sez) > self.maximumRangeTo(viz_cross_section):
            return False, Explanation.RADAR_SENSITIVITY

        # Passed all phenomenology-specific tests, call base class' visibility check
        return True, explanation

    def maximumRangeTo(self, viz_cross_section: float) -> float:
        """Calculate the maximum possible range based on a target's visible area.

        Args:
            viz_cross_section (``float``): area of the target facing the sun (m^2)

        Returns:
            ``float``: maximum possible range to target at which this sensor can make valid observations (km)
        """
        rcs = calculateRadarCrossSection(viz_cross_section, self.wavelength)
        return rcs**0.25 * self.max_range_aux
