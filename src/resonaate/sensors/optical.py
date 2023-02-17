"""Defines the :class:`.Optical` sensor class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from scipy.linalg import norm

# Local Imports
from ..common.labels import Explanation, PlatformLabel
from ..physics.bodies import Sun
from ..physics.measurements import Measurement
from ..physics.sensor_utils import (
    apparentVisualMagnitude,
    calculateIncidentSolarFlux,
    calculatePhaseAngle,
    checkGalacticExclusionZone,
    checkGroundSensorLightingConditions,
    checkSpaceSensorEarthLimbObscuration,
    checkSpaceSensorLightingConditions,
    lambertianPhaseFunction,
)
from .sensor_base import Sensor

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from . import FieldOfView


OPTICAL_DETECTABLE_VISMAG: float = 25.0
"""``float``: Default minimum observable visual magnitude, unit-less"""

OPTICAL_DEFAULT_FOV: dict[str, Any] = {
    "fov_shape": "rectangular",
    "azimuth_angle": 1.0,
    "elevation_angle": 1.0,
}
"""``dict``: Default Field of View (rectangular)of an optical sensor, degrees."""


class Optical(Sensor):
    """Electro-Optical sensor class.

    The Optical sensor class provides the framework and functionality for optical sensor payloads,
    which provide azimuth and elevation measurements with each observation. The Optical sensor
    class introduces additional visibility constraints, which are dependent on the type of agent.
    Facility objects with optical sensors must be in eclipse while the target is in sunlight.
    Spacecraft objects with optical sensors must be viewing the target against empty space, and not
    the Earth.

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
        slew_rate: float,
        field_of_view: FieldOfView,
        background_observations: bool,
        detectable_vismag: float,
        minimum_range: float,
        maximum_range: float,
        **sensor_args: dict,
    ):
        """Construct a `Optical` sensor object.

        Args:
            az_mask (``ndarray``): azimuth mask for visibility conditions
            el_mask (``ndarray``): elevation mask for visibility conditions
            r_matrix (``ndarray``): measurement noise covariance matrix
            diameter (``float``): size of sensor (m)
            efficiency (``float``): efficiency percentage of the sensor
            slew_rate (``float``): maximum rotational speed of the sensor (deg/sec)
            field_of_view (``float``): Angular field of view of sensor (deg)
            background_observations (``bool``): whether or not to calculate serendipitous observations, default=True
            detectable_vismag (``float``): minimum vismag of RSO needed for visibility
            minimum_range (``float``): minimum RSO range needed for visibility
            maximum_range (``float``): maximum RSO range needed for visibility
            sensor_args (``dict``): extra key word arguments for easy extension of the `Sensor` interface
        """
        measurement = Measurement.fromMeasurementLabels(["azimuth_rad", "elevation_rad"], r_matrix)
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

        self.detectable_vismag = detectable_vismag

    def isVisible(
        self,
        tgt_eci_state: ndarray,
        viz_cross_section: float,
        reflectivity: float,
        slant_range_sez: ndarray,
    ) -> tuple[bool, Explanation]:
        """Determine if the target is in view of the sensor.

        This method specializes :class:`.Sensor`'s :meth:`~.Sensor.isVisible` for electro-optical
        sensors which includes checking sunlight conditions for targets & sensors.
        :meth:`.Sensor.isVisible` is called if the sunlight conditions are satisfied.

        References:
            :cite:t:`vallado_2013_astro`, Sections 4.1 - 4.4 and 5 - 5.3.5.

        Args:
            tgt_eci_state (``ndarray``): 6x1 ECI state vector of the target agent
            viz_cross_section (``float``): area of the target facing the sun (m^2)
            reflectivity (``float``): Reflectivity of RSO (unitless)
            slant_range_sez (``ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)

        Returns:
            ``bool``: True if target is visible; False if target is not visible
            :class:`.Explanation`: Reason observation was visible or not
        """
        # pylint:disable=too-many-return-statements
        jd = self.host.julian_date_epoch
        sun_eci_position = Sun.getPosition(jd)
        boresight_eci = tgt_eci_state - self.host.eci_state

        # Check if target is illuminated
        tgt_solar_flux = calculateIncidentSolarFlux(
            viz_cross_section, tgt_eci_state[:3], sun_eci_position
        )
        if tgt_solar_flux <= 0:
            return False, Explanation.SOLAR_FLUX

        # Check visual magnitude of RSO
        solar_phase_angle = calculatePhaseAngle(
            sun_eci_position, tgt_eci_state[:3], self.host.eci_state[:3]
        )
        rso_apparent_vismag = apparentVisualMagnitude(
            viz_cross_section,
            reflectivity,
            lambertianPhaseFunction(solar_phase_angle),
            norm(boresight_eci),
        )
        if rso_apparent_vismag > self.detectable_vismag:
            return False, Explanation.VIZ_MAG

        # Check if sensor is pointed at the galactic center
        galactic = checkGalacticExclusionZone(boresight_eci[:3])
        if not galactic:
            return False, Explanation.GALACTIC_EXCLUSION

        if self.host.agent_type == PlatformLabel.SPACECRAFT:
            # Check if sensor is pointed at the Sun
            target_sun_unit_vector_eci = (tgt_eci_state[:3] - sun_eci_position) / norm(
                tgt_eci_state[:3] - sun_eci_position
            )
            space_lighting = checkSpaceSensorLightingConditions(
                boresight_eci[:3], target_sun_unit_vector_eci
            )
            if not space_lighting:
                return False, Explanation.SPACE_ILLUMINATION

            # Check if target is in front of the Earth's limb
            # [NOTE]: The fields of regard of EO/IR space-based sensors are dynamically limited by
            #           the limb of the Earth. Therefore, they cannot observe a target if the Earth
            #           or its atmosphere is in the background.
            target_is_obscured = checkSpaceSensorEarthLimbObscuration(
                self.host.eci_state, slant_range_sez
            )

            if target_is_obscured:
                return False, Explanation.LIMB_OF_EARTH

        # Ground based require eclipse conditions
        else:
            ground_lighting = checkGroundSensorLightingConditions(
                self.host.eci_state[:3], sun_eci_position / norm(sun_eci_position)
            )
            if not ground_lighting:
                return False, Explanation.GROUND_ILLUMINATION

        # Passed all phenomenology-specific tests, call base class' visibility check
        return super().isVisible(tgt_eci_state, viz_cross_section, reflectivity, slant_range_sez)
