"""Defines the :class:`.Radar` sensor class."""
# Third Party Imports
from numpy import array, squeeze

# Local Imports
from ..physics import constants as const
from ..physics.sensor_utils import calculateRadarCrossSection, getWavelengthFromString
from .measurements import IsAngle, getAzimuth, getElevation, getRange, getRangeRate
from .sensor_base import Sensor


class Radar(Sensor):
    """Radar sensor class.

    The Radar sensor class provides the framework and functionality for radar sensor payloads,
    which provide azimuth, elevation, & range measurements with each observation.
    """

    def __init__(
        self,
        az_mask,
        el_mask,
        r_matrix,
        diameter,
        efficiency,
        exemplar,
        power_tx,
        frequency,
        slew_rate,
        field_of_view,
        **sensor_args,
    ):  # noqa: E501
        """Construct a `Radar` sensor object.

        Args:
            az_mask (``list``): azimuth mask for visibility conditions
            el_mask (``list``): elevation mask for visibility conditions
            r_matrix (``np.ndarray``): measurement noise covariance matrix
            diameter (``float``): size of sensor (m)
            efficiency (``float``): efficiency percentage of the sensor
            exemplar (``np.ndarray``): 2x1 array of exemplar capabilities, used in min detectable power calculation
                    [cross sectional area (m^2), range (km)]
            power_tx (``float``): radar's transmit power (W)
            frequency (``float``|``str``): radar's operating frequency (Hz)
            slew_rate (``float``): maximum rotational speed of the sensor (deg/sec)
            field_of_view (``float``): Angular field of view of sensor (deg)
            sensor_args (``dict``): extra key word arguments for easy extension of the `Sensor` interface
        """
        super().__init__(
            az_mask,
            el_mask,
            r_matrix,
            diameter,
            efficiency,
            slew_rate,
            field_of_view,
            **sensor_args,
        )

        # Save extra class variables
        if isinstance(frequency, str):
            self._wavelength = getWavelengthFromString(frequency)
        else:
            self._wavelength = const.SPEED_OF_LIGHT / frequency
        self.tx_power = power_tx

        # Calculate minimum detectable power & maximum auxiliary range
        self.exemplar = squeeze(exemplar)
        self.min_detect = self._minPowerFromExemplar(self.exemplar[0], self.exemplar[1] * 1000)
        self.max_range_aux = self._maxRangeFromExemplar(diameter, self.min_detect)

    def _minPowerFromExemplar(self, exemplar_area, exemplar_range):
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

    def _maxRangeFromExemplar(self, diameter, min_detect_power):
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

    @property
    def angle_measurements(self):
        """``np.ndarray``: Returns 4x1 integer array of which measurements are angles."""
        return array(
            [IsAngle.ANGLE_0_2PI, IsAngle.ANGLE_NEG_PI_PI, IsAngle.NOT_ANGLE, IsAngle.NOT_ANGLE],
            dtype=int,
        )

    def getMeasurements(self, slant_range_sez, noisy=False):
        """Return the measurement state of the measurement.

        Args:
            slant_range_sez (``np.ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)
            noisy (``bool``, optional): whether measurements should include sensor noise. Defaults to ``False``.

        Returns:
            ``dict``: measurements made by the sensor

            :``"azimuth_rad"``: (``float``): azimuth angle measurement (radians)
            :``"elevation_rad"``: (``float``): elevation angle measurement (radians)
            :``"range_km"``: (``float``): range measurement (km)
            :``"range_rate_km_p_sec"``: (``float``): range rate measurement (km/sec)
        """
        measurements = {
            "azimuth_rad": getAzimuth(slant_range_sez),
            "elevation_rad": getElevation(slant_range_sez),
            "range_km": getRange(slant_range_sez),
            "range_rate_km_p_sec": getRangeRate(slant_range_sez),
        }
        if noisy:
            measurements["azimuth_rad"] += self.measurement_noise[0]
            measurements["elevation_rad"] += self.measurement_noise[1]
            measurements["range_km"] += self.measurement_noise[2]
            measurements["range_rate_km_p_sec"] += self.measurement_noise[3]

        return measurements

    def maximumRangeTo(self, viz_cross_section, tgt_eci_state):
        """Calculate the maximum possible range based on a target's visible area.

        Args:
            viz_cross_section (``float``): area of the target facing the sun (m^2)
            tgt_eci_state (``np.ndarray``): 6x1 ECI state vector of the target agent

        Returns:
            ``float``: maximum possible range to target at which this sensor can make valid observations (km)
        """
        rcs = calculateRadarCrossSection(viz_cross_section, self.wavelength)
        return rcs**0.25 * self.max_range_aux / 1000.0

    @property
    def wavelength(self):
        """``float``: Returns wavelength of sensor's operating center frequency (m)."""
        return self._wavelength
