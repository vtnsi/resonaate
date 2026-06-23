"""Defines the :class:`.Interferometer` sensor class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, ndarray
from numpy.linalg import norm

if TYPE_CHECKING:
    from resonaate.scenario.config.sensor_config import NodeConfig
    from resonaate.sensors.field_of_view import FieldOfView
    from resonaate.agents.target_agent import TargetAgent
# RESONAATE Imports
from resonaate.physics.maths import subtendedAngle

# Local Imports
from ..common.labels import Explanation
from ..physics.measurements import Measurement
from ..physics.transforms.methods import ecef2eci, getSlantRangeVector, sez2eci
from .sensor_base import Sensor


class Interferometer(Sensor):
    """Interferometer sensor class."""

    def __init__(  # noqa: PLR0913
        self,
        az_mask: ndarray,
        el_mask: ndarray,
        r_matrix: ndarray,
        efficiency: float,
        slew_rate: float,
        field_of_view: FieldOfView,
        background_observations: bool,
        minimum_range: float,
        maximum_range: float,
        a_baseline_node: NodeConfig,
        c_baseline_node: NodeConfig,
        missed_obs_probability: float = 0.0,  # not defining this in the config for now since it's not clear how to parameterize it for an interferometer, but leaving it here in case we want to add it later
        downtimes=None,  # same for downtimes, not sure how to parameterize for an interferometer but leaving it here for future use
        **sensor_args: dict,
    ):
        """Construct an 'Interferometer' sensor object."""
        measurement = Measurement.fromMeasurementLabels(
            ["azimuth_rad", "elevation_rad"],
            r_matrix,
        )
        self.a_baseline_node = a_baseline_node
        self.c_baseline_node = c_baseline_node

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
        self.node_boresights = [self.boresight.copy(), self.boresight.copy()]

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
            a_baseline_node=sensor_config.a_baseline_node,
            c_baseline_node=sensor_config.c_baseline_node,
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
        for node in (self.a_baseline_node, self.c_baseline_node):
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

    def collectObservations(
        self,
        estimate_eci: ndarray,
        target_agent: TargetAgent,
        background_agents: list[TargetAgent],
    ):
        """Collect observations on all targets within the sensor's FOV. Overrides the base class method to add additional checks for the interferometer's baseline nodes.

        Args:
            estimate_eci (``ndarray``): Estimate state vector that sensor is pointing at
            target_agent (:class:`.TargetAgent`): Target agent that sensor is pointing at
            background_agents (``list``): list of possible :class:`.TargetAgent` objects in FoV

        Returns:
            ``list``: :class:`.Observation` for each successful tasked observation
            ``list``: :class:`.MissedObservation` for each unsuccessful tasked observation
        """
        if not self.isOffline():
            utc_datetime = self.host.datetime_epoch
            primary_sez = getSlantRangeVector(self.host.eci_state, estimate_eci, utc_datetime)
            if self.canSlew(primary_sez):
                for i, node in enumerate((self.a_baseline_node, self.c_baseline_node)):
                    node_sez = getSlantRangeVector(
                        self.antennaECI(node, utc_datetime),
                        estimate_eci,
                        utc_datetime,
                    )
                    self.node_boresights[i] = node_sez[:3] / (norm(node_sez[:3]))

        return super().collectObservations(estimate_eci, target_agent, background_agents)

    def canSlew(self, slant_range_sez: ndarray) -> bool:
        """Determine if the sensor (entire array of antennas) can slew to a given slant range vector.

        Args:
            slant_range_sez (``ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)

        Returns:
            ``bool``: True if sensor can slew to the given slant range vector; False otherwise
        """
        if not super().canSlew(slant_range_sez):
            return False

        utc_datetime = self.host.datetime_epoch
        slew_range = self.slew_rate * (self.host.time - self.time_last_tasked)
        target_eci = self.host.eci_state + sez2eci(
            slant_range_sez,
            self.host.lla_state[0],
            self.host.lla_state[1],
            utc_datetime,
        )

        for node, node_boresight in zip(
            (self.a_baseline_node, self.c_baseline_node),
            self.node_boresights,
        ):
            node_sez = getSlantRangeVector(
                self.antennaECI(node, utc_datetime),
                target_eci,
                utc_datetime,
            )
            if slew_range < subtendedAngle(node_boresight, node_sez[:3], safe=True):
                return False
        return True

    def antennaECI(self, node, utc_datetime):
        """Compute the ECI position of a NodeConfig antenna (secondary) at a given time.

        Args:
            node (``NodeConfig``): The node for which to compute the ECI position
            utc_datetime (``datetime``): UTC datetime at which to compute the ECI position

        Returns:
            ``ndarray``: 6x1 ECI position vector of the antenna (km)
        """
        return ecef2eci(node.ecef, utc_datetime)
