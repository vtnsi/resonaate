"""Defines the :class:`.Interferometer` sensor class."""

from __future__ import annotations

# Third Party Imports
from numpy import array, ndarray

# Local Imports
from ..common.labels import Explanation
from ..physics.constants import DEG2RAD
from ..physics.measurements import Measurement
from ..physics.transforms.methods import ecef2eci, getSlantRangeVector, lla2ecef
from .sensor_base import Sensor


class Interferometer(Sensor):
    """Interferometer sensor class."""

    def __init__(  # noqa: PLR0913
        self,
        az_mask,
        el_mask,
        r_matrix,
        efficiency,
        slew_rate,
        field_of_view,
        background_observations,
        minimum_range,
        maximum_range,
        azimuth_baseline_node,
        elevation_baseline_node,
        missed_obs_probability: float = 0.0,  # not defining this in the config for now since it's not clear how to parameterize it for an interferometer, but leaving it here in case we want to add it later
        downtimes=None,  # same for downtimes, not sure how to parameterize for an interferometer but leaving it here for future use
        **sensor_args,
    ):
        """Construct an 'Interferometer' sensor object."""
        measurement = Measurement.fromMeasurementLabels(
            ["azimuth_rad", "elevation_rad"],
            r_matrix,
        )
        self.azimuth_baseline_node = azimuth_baseline_node
        self.elevation_baseline_node = elevation_baseline_node
        super().__init__(
            measurement,
            az_mask,
            el_mask,
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
        """Alternative constructor using a config."""
        return cls(
            az_mask=array(sensor_config.azimuth_range),
            el_mask=array(sensor_config.elevation_range),
            r_matrix=array(sensor_config.covariance),
            efficiency=sensor_config.efficiency,
            slew_rate=sensor_config.slew_rate,
            field_of_view=field_of_view,
            background_observations=sensor_config.background_observations,
            minimum_range=sensor_config.minimum_range,
            maximum_range=sensor_config.maximum_range,
            azimuth_baseline_node=sensor_config.azimuth_baseline_node,
            elevation_baseline_node=sensor_config.elevation_baseline_node,
            min_revisit_time=sensor_config.min_revisit_time,
            missed_obs_probability=sensor_config.missed_obs_probability,
            downtimes=sensor_config.downtimes,
        )

    def isVisible(
        self,
        tgt_eci_state: ndarray,
        viz_cross_section: float,
        reflectivity: float,
        slant_range_sez: ndarray,
    ) -> tuple[bool, Explanation]:
        """Determine if the target is in view of the sensor.

        For now 'viz_cross_section' and 'reflectivity' are accepted to match the 'Sensor.isVisible' but they are irrelevant for an interferometer

        Args:
            tgt_eci_state (``ndarray``): 6x1 ECI state vector of the target agent
            slant_range_sez (``ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)
            reflectivity (''float''): unused
            viz_cross_section (''float''): unused


        Returns:
            ``bool``: True if target is visible; False if target is not visible
            :class:`.Explanation`: Reason observation was visible or not
        """
        visible, explanation = super().isVisible(
            tgt_eci_state,
            viz_cross_section,
            reflectivity,
            slant_range_sez,
        )

        if not visible:
            return visible, explanation

        utc_datetime = self.host.datetime_epoch
        for node in (self.azimuth_baseline_node, self.elevation_baseline_node):
            node_eci = self.antennaECI(node, utc_datetime)
            antenna_slant_range_sez = getSlantRangeVector(
                node_eci,
                tgt_eci_state,
                utc_datetime,
            )
            if not self.field_of_view.inFieldOfView(slant_range_sez, antenna_slant_range_sez):
                return False, Explanation.FIELD_OF_VIEW

        # TODO
        # Assume targets ar always transmitting for now. Later we may need to add a transmitting frequency, minimum signal strength and on/off state to the target and add checks for those here.
        return True, explanation

    def antennaECI(self, node, utc_datetime):
        """Compute the ECI position of a NodeConfig antenna (secondary) at a given time.

        Args:
            node (``NodeConfig``): NodeConfig of the antenna for which to compute the ECI position
            utc_datetime (``datetime``): UTC datetime at which to compute the ECI position

        Returns:
            ``ndarray``: 6x1 ECI position vector of the antenna (km)
        """
        lla_rad = array([node.latitude * DEG2RAD, node.longitude * DEG2RAD, node.altitude])

        return ecef2eci(lla2ecef(lla_rad), utc_datetime)
