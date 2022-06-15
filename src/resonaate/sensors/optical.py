"""Defines the :class:`.Optical` sensor class."""
# Third Party Imports
from numpy import array, sqrt, squeeze
from scipy.linalg import norm

# Local Imports
from ..physics import constants as const
from ..physics.bodies import Sun
from ..physics.sensor_utils import (
    calculateIncidentSolarFlux,
    checkGroundSensorLightingConditions,
    checkSpaceSensorLightingConditions,
    getEarthLimbConeAngle,
)
from .measurements import IsAngle, getAzimuth, getElevation
from .sensor_base import Sensor


class Optical(Sensor):
    """Electro-Optical sensor class.

    The Optical sensor class provides the framework and functionality for optical sensor payloads,
    which provide azimuth and elevation measurements with each observation. The Optical sensor
    class introduces additional visibility constraints, which are dependent on the type of agent.
    Facility objects with optical sensors must be in eclipse while the target is in sunlight.
    Spacecraft objects with optical sensors must be viewing the target against empty space, and not
    the Earth.
    """

    def __init__(
        self,
        az_mask,
        el_mask,
        r_matrix,
        diameter,
        efficiency,
        exemplar,
        slew_rate,
        field_of_view,
        calculate_fov,
        **sensor_args,
    ):
        """Construct a `Optical` sensor object.

        Args:
            az_mask (``list``): azimuth mask for visibility conditions
            el_mask (``list``): elevation mask for visibility conditions
            r_matrix (``np.ndarray``): measurement noise covariance matrix
            diameter (``float``): size of sensor (m)
            efficiency (``float``): efficiency percentage of the sensor
            exemplar (``np.ndarray``): 2x1 array of exemplar capabilities, used in min detectable power calculation
                    [cross sectional area (m^2), range (km)]
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
            calculate_fov,
            **sensor_args,
        )

        # Calculate minimum detectable power & maximum auxiliary range
        self.exemplar = squeeze(exemplar)
        self.min_detect = self._minPowerFromExemplar(
            diameter, self.exemplar[0], self.exemplar[1] * 1000
        )
        self.max_range_aux = self._maxRangeFromExemplar(diameter, self.min_detect)

    def _minPowerFromExemplar(self, diameter, exemplar_area, exemplar_range):
        """Calculate the minimum detectable power based on exemplar criterion.

        References:
            :cite:t:`nastasi_2018_diss`, Pg 48, Eqn 3.10

        Args:
            diameter (``float``): aperture diameter, m^2
            exemplar_area (``float``): cross-sectional area of the exemplar target, m^2
            exemplar_range (``float``): range to exemplar target, m

        Returns:
            ``float``: minimum detectable power for this sensors, W
        """
        return (const.SOLAR_FLUX * exemplar_area * diameter**2 * self.efficiency) / (
            16 * exemplar_range**2
        )

    def _maxRangeFromExemplar(self, diameter, min_detect_power):
        """Calculate the auxiliary maximum range for a detection.

        This is an intermediate calculation for simplifying when `maximumRangeTo()` is called.

        References:
            :cite:t:`nastasi_2018_diss`, Pg 48, Eqn 3.11

        Args:
            diameter (``float``): aperture diameter, m^2
            min_detect_power (``float``): minimum detectable power of the sensor, W

        Returns:
            ``float``: auxiliary maximum range, (mW-1)^1/2
        """
        return sqrt((diameter**2 * self.efficiency) / (16 * min_detect_power))

    @property
    def angle_measurements(self):
        """``np.ndarray``: Returns 2x1 integer array of which measurements are angles."""
        return array([IsAngle.ANGLE_0_2PI, IsAngle.ANGLE_NEG_PI_PI], dtype=int)

    def getMeasurements(self, slant_range_sez, noisy=False):
        """Return the measurement state of the measurement.

        Args:
            slant_range_sez (``np.ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)
            noisy (``bool``, optional): whether measurements should include sensor noise. Defaults to ``False``.

        Returns:
            ``dict``: measurements made by the sensor

            :``"azimuth_rad"``: (``float``): azimuth angle measurement (radians)
            :``"elevation_rad"``: (``float``): elevation angle measurement (radians)
        """
        measurements = {
            "azimuth_rad": getAzimuth(slant_range_sez),
            "elevation_rad": getElevation(slant_range_sez),
        }
        if noisy:
            measurements["azimuth_rad"] += self.measurement_noise[0]
            measurements["elevation_rad"] += self.measurement_noise[1]

        return measurements

    def isVisible(self, tgt_eci_state, viz_cross_section, slant_range_sez):
        """Determine if the target is in view of the sensor.

        This method specializes :class:`.Sensor`'s :meth:`~.Sensor.isVisible` for electro-optical
        sensors which includes checking sunlight conditions for targets & sensors.
        :meth:`.Sensor.isVisible` is called if the sunlight conditions are satisfied.

        References:
            :cite:t:`vallado_2013_astro`, Sections 4.1 - 4.4 and 5 - 5.3.5.

        Args:
            tgt_eci_state (``np.ndarray``): 6x1 ECI state vector of the target agent
            viz_cross_section (``float``): area of the target facing the sun (m^2)
            slant_range_sez (``np.ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)

        Returns:
            ``bool``: True if target is visible; False if target is not visible
        """
        jd = self.host.julian_date_epoch
        sun_eci_position = Sun.getPosition(jd)

        # Calculate the illumination of the target object
        tgt_solar_flux = calculateIncidentSolarFlux(
            viz_cross_section, tgt_eci_state[:3], sun_eci_position
        )

        if self.host.agent_type == "Spacecraft":
            # Check if sensor is pointed at the Sun
            boresight_eci = tgt_eci_state - self.host.eci_state
            lighting = checkSpaceSensorLightingConditions(
                boresight_eci[:3], sun_eci_position / norm(sun_eci_position)
            )

            # Check if target is in front of the Earth's limb
            elevation = getElevation(slant_range_sez)
            limb_angle = getEarthLimbConeAngle(self.host.eci_state)

            # Combine the two conditions
            # [NOTE]: The fields of regard of EO/IR space-based sensors are dynamically limited by
            #           the limb of the Earth. Therefore, they cannot observe a target if the Earth
            #           or its atmosphere is in the background.
            can_observe = lighting and limb_angle <= elevation

        else:
            # Ground based require eclipse conditions
            can_observe = checkGroundSensorLightingConditions(
                self.host.eci_state[:3], sun_eci_position / norm(sun_eci_position)
            )

        # Check if target is illuminated & if sensor has good lighting conditions
        if tgt_solar_flux > 0 and can_observe:
            # Call base class' visibility check
            return super().isVisible(tgt_eci_state, viz_cross_section, slant_range_sez)

        return False

    def maximumRangeTo(self, viz_cross_section, tgt_eci_state):
        """Calculate the maximum possible range based on a target's visible area.

        Args:
            viz_cross_section (``float``): area of the target facing the sun (m^2)
            tgt_eci_state (``np.ndarray``): 6x1 ECI state vector of the target agent

        Returns:
            ``float``: maximum possible range to target at which this sensor can make valid observations (km)
        """
        jd = self.host.julian_date_epoch
        sun_eci_position = Sun.getPosition(jd)
        solar_flux = calculateIncidentSolarFlux(
            viz_cross_section, tgt_eci_state[:3], sun_eci_position
        )
        return sqrt(solar_flux) * self.max_range_aux / 1000.0
