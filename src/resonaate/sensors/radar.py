"""Defines the :class:`.Radar` sensor class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ..data.missed_observation import MissedObservation
from ..physics import constants as const
from ..physics.measurement_utils import getRange
from ..physics.sensor_utils import calculateRadarCrossSection, getWavelengthFromString
from .measurement import Measurement
from .sensor_base import Sensor

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from . import FieldOfView


RADAR_DEFAULT_FOV: dict[str, Any] = {
    "fov_shape": "conic",
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

    def __init__(
        self,
        az_mask: ndarray,
        el_mask: ndarray,
        r_matrix: ndarray,
        diameter: float,
        efficiency: float,
        exemplar: ndarray,
        power_tx: float,
        frequency: float,
        slew_rate: float,
        field_of_view: FieldOfView,
        background_observations: bool,
        minimum_range: float,
        maximum_range: float,
        **sensor_args: dict,
    ):  # noqa: E501
        """Construct a `Radar` sensor object.

        Args:
            az_mask (``ndarray``): azimuth mask for visibility conditions
            el_mask (``ndarray``): elevation mask for visibility conditions
            r_matrix (``ndarray``): measurement noise covariance matrix
            diameter (``float``): size of sensor (m)
            efficiency (``float``): efficiency percentage of the sensor
            exemplar (``ndarray``): 2x1 array of exemplar capabilities, used in min detectable power calculation [cross sectional area (m^2), range (km)]
            power_tx (``float``): radar's transmit power (W)
            frequency (``float``|``str``): radar's operating frequency (Hz)
            slew_rate (``float``): maximum rotational speed of the sensor (deg/sec)
            field_of_view (``float``): Angular field of view of sensor (deg)
            background_observations (``bool``): whether or not to calculate serendipitous observations, default=True
            minimum_range (``float``): minimum RSO range needed for visibility
            maximum_range (``float``): maximum RSO range needed for visibility
            sensor_args (``dict``): extra key word arguments for easy extension of the `Sensor` interface
        """
        measurement = Measurement.fromMeasurementLabels(
            ["azimuth_rad", "elevation_rad", "range_km", "range_rate_km_p_sec"], r_matrix
        )
        super().__init__(
            measurement,
            az_mask,
            el_mask,
            diameter,
            efficiency,
            exemplar,
            slew_rate,
            field_of_view,
            background_observations,
            minimum_range,
            maximum_range,
            **sensor_args,
        )

        # Save extra class variables
        if isinstance(frequency, str):
            self._wavelength = getWavelengthFromString(frequency)
        else:
            self._wavelength = const.SPEED_OF_LIGHT / frequency
        self.tx_power = power_tx

        # Calculate minimum detectable power & maximum auxiliary range
        min_detect = self._minimumDetectablePower(self.exemplar[0], self.exemplar[1] * 1000)
        self.max_range_aux = self._maximumDetectableRange(diameter, min_detect)

    def _minimumDetectablePower(self, exemplar_area: float, exemplar_range: float) -> float:
        """Calculate the minimum detectable power based on exemplar criterion.

        References:
            #. :cite:t:`nastasi_2018_diss`, Pg 46, Eqn 3.5 & 3.7
            #. :cite:t:`rees_2013_remote_sensing`, Pg 283

        Args:
            exemplar_area (``float``): cross-sectional area of the exemplar target, m^2
            exemplar_range (``float``): range to exemplar target, m

        Returns:
            ``float``: minimum detectable power for this sensors, W
        """
        four_pi = 4 * const.PI
        lam_sq = self.wavelength**2
        # Validated against Nastasi's equations
        return (
            four_pi
            * self.tx_power
            * (self.aperture_area * self.efficiency) ** 2
            * (four_pi * exemplar_area**2 / lam_sq)
        ) / (lam_sq * (four_pi * exemplar_range**2.0) ** 2.0)

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
        numerator = const.PI * self.tx_power * diameter**4 * self.efficiency**2
        denominator = 64 * self.wavelength**2 * min_detect_power
        return (numerator / denominator) ** 0.25

    def isVisible(
        self,
        tgt_eci_state: ndarray,
        viz_cross_section: float,
        reflectivity: float,
        slant_range_sez: ndarray,
    ) -> tuple[bool, MissedObservation.Explanation]:
        """Determine if the target is in view of the sensor.

        Args:
            tgt_eci_state (``ndarray``): 6x1 ECI state vector of the target agent
            viz_cross_section (``float``): area of the target facing the sun (m^2)
            reflectivity (``float``): Reflectivity of RSO (unitless)
            slant_range_sez (``ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)

        Returns:
            ``bool``: True if target is visible; False if target is not visible
            :class:`.MissedObservation.Explanation`: Reason observation was visible or not
        """
        # Early exit if target not in radar sensor's range
        if getRange(slant_range_sez) > self.maximumRangeTo(viz_cross_section):
            return False, MissedObservation.Explanation.RADAR_SENSITIVITY

        # Passed all phenomenology-specific tests, call base class' visibility check
        return super().isVisible(tgt_eci_state, viz_cross_section, reflectivity, slant_range_sez)

    def maximumRangeTo(self, viz_cross_section: float) -> float:
        """Calculate the maximum possible range based on a target's visible area.

        Args:
            viz_cross_section (``float``): area of the target facing the sun (m^2)

        Returns:
            ``float``: maximum possible range to target at which this sensor can make valid observations (km)
        """
        rcs = calculateRadarCrossSection(viz_cross_section, self.wavelength)
        return rcs**0.25 * self.max_range_aux / 1000.0

    @property
    def wavelength(self) -> float:
        """``float``: Returns wavelength of sensor's operating center frequency (m)."""
        return self._wavelength
