"""Abstract :class:`.Sensor` base class which defines the common sensor interface."""
from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, cos, diagflat, dot, matmul, random, real, sin, squeeze
from scipy.linalg import norm, sqrtm

# Local Imports
from ..common.logger import resonaateLogInfo
from ..common.utilities import getTypeString
from ..data.observation import Observation
from ..physics import constants as const
from ..physics.math import safeArccos, subtendedAngle
from ..physics.sensor_utils import lineOfSight
from ..physics.time.stardate import ScenarioTime
from ..physics.transforms.methods import getSlantRangeVector
from .measurements import getAzimuth, getElevation, getRange

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..agents.estimate_agent import EstimateAgent
    from ..agents.sensing_agent import SensingAgent
    from ..agents.target_agent import TargetAgent
    from . import FieldOfView


ObservationTuple = namedtuple("ObservationTuple", ["observation", "agent", "angles"])
"""Named tuple for correlating an observation, the sensing agent, and its angular values.

Attributes:
    observation (:class:`.Observation` | ``None``): valid or invalid observation
    agent (:class:`.SensingAgent`): reference to `~.Sensor.host`
    angles (``ndarray``): array signifying which measurements are angles via :class:`.IsAngle` enum.
"""


class Sensor(metaclass=ABCMeta):
    """Abstract base class for a generic Sensor object."""

    def __init__(
        self,
        az_mask: ndarray,
        el_mask: ndarray,
        r_matrix: ndarray,
        diameter: float,
        efficiency: float,
        exemplar: ndarray,
        slew_rate: float,
        field_of_view: FieldOfView,
        calculate_fov: bool,
        detectable_vismag: float,
        minimum_range: float,
        maximum_range: float,
        **sensor_args: dict,
    ):
        """Construct a generic `Sensor` object.

        Args:
            az_mask (``ndarray``): azimuth mask for visibility conditions
            el_mask (``ndarray``): elevation mask for visibility conditions
            r_matrix (``ndarray``): measurement noise covariance matrix
            diameter (``float``): diameter of sensor dish (m)
            efficiency (``float``): efficiency percentage of the sensor
            exemplar (``ndarray``): 2x1 array of exemplar capabilities, used in min detectable power  calculation [cross sectional area (m^2), range (km)]
            slew_rate (``float``): maximum rotational speed of the sensor (deg/sec)
            field_of_view (:class:`.FieldOfView`): field of view of sensor
            calculate_fov (``bool``): whether or not to calculate Field of View, default=True
            detectable_vismag (``float``): minimum vismag of RSO needed for visibility
            minimum_range (``float``): minimum RSO range needed for visibility
            maximum_range (``float``): maximum RSO range needed for visibility
            sensor_args (``dict``): extra key word arguments for easy extension of the `Sensor` interface
        """
        self._az_mask = None
        self._el_mask = None
        self._r_matrix = None
        self.az_mask = const.DEG2RAD * az_mask
        self.el_mask = const.DEG2RAD * el_mask
        self.r_matrix = r_matrix
        self.aperture_area = const.PI * ((diameter / 2.0) ** 2)
        self.efficiency = efficiency
        self.exemplar = squeeze(exemplar)
        self.slew_rate = const.DEG2RAD * slew_rate
        self.field_of_view = field_of_view
        self.calculate_field_of_view = calculate_fov
        self.detectable_vismag = detectable_vismag
        self.minimum_range = minimum_range
        self.maximum_range = maximum_range

        # Derived properties initialization
        self.time_last_ob = ScenarioTime(0.0)
        self.delta_boresight = 0.0
        self._host = None
        self.boresight = None
        self._current_target = None
        """``float``: For tracking the current target agent and help with debugging purposes."""
        self.min_detect = None
        self.max_range_aux = None
        self._sensor_args = sensor_args

    @abstractmethod
    def maximumRangeTo(self, viz_cross_section: float, tgt_eci_state: ndarray) -> float:
        """Calculate the maximum possible range based on a target's visible area.

        Args:
            viz_cross_section (``float``): area of the target facing the sun (m^2)
            tgt_eci_state (``ndarray``): 6x1 ECI state vector of the target agent

        Returns:
            ``float``: maximum possible range to target at which this sensor can make valid observations (km)
        """
        raise NotImplementedError

    @abstractmethod
    def getMeasurements(self, slant_range_sez: ndarray, noisy=False) -> dict:
        """Return the measurement state of the measurement.

        Args:
            slant_range_sez (``ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)
            noisy (``bool``, optional): whether measurements should include sensor noise. Defaults to ``False``.

        Returns:
            ``dict``: measurements made by the sensor

            :``"azimuth_rad"``: (``float``): azimuth angle measurement (radians)
            :``"elevation_rad"``: (``float``): elevation angle measurement (radians)
            :``"range_km"``: (``float``): range measurement (km)
            :``"range_rate_km_p_sec"``: (``float``): range rate measurement (km/sec)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def angle_measurements(self):
        """Returns which measurements are angles as integer values.

        The following values are valid:
            - `0` is a non-angular measurement, no special treatment is needed
            - `1` is an angular measurement valid in [-pi, pi]
            - `2` is an angular measurement valid in [0, 2pi]

        Returns:
            ``ndarray``: integer array defining angular measurements
        """
        raise NotImplementedError

    def collectObservations(
        self, pointing_agent: EstimateAgent, background_agents: list[TargetAgent]
    ) -> list[ObservationTuple]:
        """Collect observations on all targets within the sensor's FOV.

        Args:
            pointing_agent (:class:`.EstimateAgent`): agent that sensor is pointing at
            background_agents (``list``): list of possible `.TargetAgent` objects in FoV

        Returns:
            obs_list (``list``): list of `.ObservationTuple`
        """
        obs_list = []
        # Check if sensor will slew to point in time
        slant_range_sez = getSlantRangeVector(self.host.ecef_state, pointing_agent.eci_state)
        if self.canSlew(slant_range_sez):
            if self.calculate_field_of_view:
                targets_in_fov = self.checkTargetsInView(slant_range_sez, background_agents)
                obs_list = list(
                    filter(  # pylint:disable=bad-builtin
                        lambda x: x.observation,
                        (
                            self.makeNoisyObservation(
                                tgt,
                            )
                            for tgt in targets_in_fov
                        ),
                    )
                )  # pylint:disable=bad-builtin

            else:
                obs_list.append(self.makeNoisyObservation(pointing_agent))

            self.boresight = slant_range_sez[:3] / norm(slant_range_sez[:3])
            if obs_list:  # only update time_last_ob if obs are made
                self.time_last_ob = self.host.time

        return obs_list

    def checkTargetsInView(
        self, slant_range_sez: float, background_agents: list[TargetAgent]
    ) -> list[TargetAgent]:
        """Perform bulk FOV check on all RSOs.

        Args:
            slant_range_sez (``ndarray``): 3x1 slant range vector that sensor is pointing towards
            background_agents (``list``): list of all `.TargetAgents` in scenario

        Returns:
            ``list``: list of all visible `.TargetAgents` in scenario
        """
        # filter out targets outside of FOV
        agents_in_fov = list(
            filter(  # pylint:disable=bad-builtin
                lambda x: self.inFOV(
                    slant_range_sez, getSlantRangeVector(self.host.ecef_state, x.eci_state)
                ),
                background_agents,
            )
        )  # pylint:disable=bad-builtin
        return agents_in_fov

    def inFOV(self, pointing_sez: ndarray, background_sez: ndarray) -> bool:
        """Perform bulk FOV check on all RSOs.

        Args:
            pointing_sez (``ndarray``): 3x1 slant range vector that sensor is pointing towards
            background_sez (``ndarray``): 3x1 slant range vector of possible agent in FoV

        Returns:
            ``bool``: whether or not a `.TargetAgent` object is within sensor FoV
        """
        if self.field_of_view.fov_shape == "conic":
            angle = subtendedAngle(background_sez, pointing_sez)
            return angle <= self.field_of_view.cone_angle / 2

        if self.field_of_view.fov_shape == "rectangular":
            pointing_azimuth = getAzimuth(pointing_sez)
            pointing_elevation = getElevation(pointing_sez)

            background_azimuth = getAzimuth(background_sez)
            background_elevation = getElevation(background_sez)

            azimuth_angle = abs(pointing_azimuth - background_azimuth)
            elevation_angle = abs(pointing_elevation - background_elevation)
            return (
                azimuth_angle <= self.field_of_view.azimuth_angle / 2
                and elevation_angle <= self.field_of_view.elevation_angle / 2
            )

        raise ValueError("Wrong Import for FoV Type")

    def buildSigmaObs(self, target_id: int, tgt_eci_state: ndarray) -> Observation:
        """Calculate the measurement data for a sigma point observation.

        Args:
            target_id (``int``): simulation ID associated with current target.
            tgt_eci_state (``ndarray``): 6x1 ECI state vector of the target (km; km/sec).

        Returns:
            :class:`.Observation`: observation data object.
        """
        slant_range_sez = getSlantRangeVector(self.host.ecef_state, tgt_eci_state)
        julian_date = self.host.julian_date_epoch
        return Observation.fromSEZVector(
            sensor_type=getTypeString(self),
            sensor_id=self.host.simulation_id,
            target_id=target_id,
            julian_date=julian_date,
            sez=slant_range_sez,
            sensor_position=self.host.lla_state,
            **self.getMeasurements(slant_range_sez),
        )

    def makeObservation(
        self,
        tgt_id: int,
        tgt_eci_state: ndarray,
        viz_cross_section: float,
        reflectivity: float,
        real_obs: bool = False,
    ) -> ObservationTuple:
        """Calculate the measurement data for a single observation.

        Args:
            tgt_id (``int``): simulation ID associated with current target
            tgt_eci_state (``ndarray``): 6x1 ECI state vector of the target (km; km/sec)
            viz_cross_section (``float``): visible cross-sectional area of the target (m^2)
            reflectivity (``float``): Reflectivity of RSO (unitless)
            real_obs (``bool``, optional): whether observation should include noisy measurements. Defaults to ``False``.

        Returns:
            :class:`.ObservationTuple`: observation tuple object
        """
        # Calculate common values
        slant_range_sez = getSlantRangeVector(self.host.ecef_state, tgt_eci_state)
        julian_date = self.host.julian_date_epoch

        # Construct observations
        if self.isVisible(tgt_eci_state, viz_cross_section, reflectivity, slant_range_sez):
            # Make a real observation once tasked -> add noise to the measurement
            if real_obs:
                observation = Observation.fromSEZVector(
                    sensor_type=getTypeString(self),
                    sensor_id=self.host.simulation_id,
                    target_id=tgt_id,
                    julian_date=julian_date,
                    sez=slant_range_sez,
                    sensor_position=self.host.lla_state,
                    **self.getNoisyMeasurements(slant_range_sez),
                )
                self.boresight = slant_range_sez[:3] / norm(slant_range_sez[:3])
                self._current_target = tgt_id

            else:
                # Forecasting an observation for reward matrix purposes
                observation = self.buildSigmaObs(tgt_id, tgt_eci_state)

        else:
            observation = None

        return ObservationTuple(observation, self.host, self.angle_measurements)

    def makeNoisyObservation(self, target_agent: TargetAgent) -> ObservationTuple:
        """Calculate the measurement data for a single observation with noisy measurements.

        Args:
            target_agent (`TargetAgent`): Target Agent being observed

        Returns:
            :class:`.ObservationTuple`: observation tuple object
        """
        # [NOTE][parallel-time-bias-event-handling] Step three: Check if a sensor has bias events
        tgt_eci_state = target_agent.eci_state
        if len(self.host.sensor_time_bias_event_queue):
            if abs(self.host.sensor_time_bias_event_queue[0].applied_bias) > abs(
                target_agent.dt_step
            ):
                raise ValueError("Time bias cannot be larger than the dt_step")
            tgt_eci_state = target_agent.dynamics.propagate(
                target_agent.time - target_agent.dt_step,
                target_agent.time + self.host.sensor_time_bias_event_queue[0].applied_bias,
                target_agent.previous_state,
            )
            msg = f"Sensor time bias of {self.host.sensor_time_bias_event_queue[0].applied_bias} "
            msg += f"seconds applied to sensor {self.host.simulation_id}"
            resonaateLogInfo(msg)

        return self.makeObservation(
            target_agent.simulation_id,
            tgt_eci_state,
            target_agent.visual_cross_section,
            target_agent.reflectivity,
            real_obs=True,
        )

    def getNoisyMeasurements(self, slant_range_sez: ndarray) -> dict:
        """Return noisy measurements.

        Args:
            slant_range_sez (``ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)

        Returns:
            ``dict``: noisy measurements made by the sensor

            :``"azimuth_rad"``: (``float``): azimuth angle measurement (radians)
            :``"elevation_rad"``: (``float``): elevation angle measurement (radians)
            :``"range_km"``: (``float``): range measurement (km)
            :``"range_rate_km_p_sec"``: (``float``): range rate measurement (km/sec)
        """
        return self.getMeasurements(slant_range_sez, noisy=True)

    def isVisible(
        self,
        tgt_eci_state: ndarray,
        viz_cross_section: float,
        reflectivity: float,
        slant_range_sez: ndarray,
    ) -> bool:
        """Determine if the target is in view of the sensor.

        References:
            :cite:t:`vallado_2013_astro`, Sections 4.1 - 4.4 and 5 - 5.3.5

        Args:
            tgt_eci_state (``ndarray``): 6x1 ECI state vector of the target agent
            viz_cross_section (``float``): area of the target facing the sun (m^2)
            reflectivity (``float``): Reflectivity of RSO (unitless)
            slant_range_sez (``ndarray``): 6x1 SEZ slant range vector from sensor to target (km; km/sec)

        Returns:
            ``bool``: True if target is visible; False if target is not visible
        """
        # pylint:disable=unused-argument
        # Early exit if target not in sensor's range
        if not self.minimum_range < getRange(slant_range_sez) < self.maximum_range:
            return False

        # Early exit if a Line of Sight doesn't exist
        if not lineOfSight(tgt_eci_state[:3], self.host.eci_state[:3]):
            return False

        # Get the azimuth and elevation angles
        # [NOTE]: These are assumed to always be in the following ranges:
        #           - [0, 2*pi]
        #           - [-pi/2, pi/2]
        #   This should suffice to cover all necessary/required conditions
        azimuth = getAzimuth(slant_range_sez)
        elevation = getElevation(slant_range_sez)

        # Check if the elevation is within sensor bounds
        if elevation <= self.el_mask[0] or elevation >= self.el_mask[1]:
            return False

        # [NOTE]: Azimuth check requires two versions:
        #   - az_0 <= az_1 for normal situations
        #   - az_0 > az_1 for when mask transits the 360deg/True North line
        if self.az_mask[0] <= self.az_mask[1] and self.az_mask[0] <= azimuth <= self.az_mask[1]:
            return True

        if azimuth >= self.az_mask[0] or azimuth <= self.az_mask[1]:
            return True

        # Default: target satellite is not in view
        return False

    def canSlew(self, slant_range_sez: ndarray) -> bool:
        """Check if sensor can slew to target in the allotted time.

        Args:
            slant_range_sez (``ndarray``): slant range vector

        Returns:
            ``bool``: whether target can be slewed to in time
        """
        # [NOTE]: When `slant_range_sez` and `self.boresight` are colinear, lost precision creates a value
        # __slightly__ larger than 1.0 or smaller than -1.0. This results in domain errors with `numpy::arccos()`.
        # This statement ensures to round to either 1 or -1 appropriately.
        arg = dot(slant_range_sez[:3] / norm(slant_range_sez[:3]), self.boresight)
        self.delta_boresight = safeArccos(arg)
        # Boolean if you are able to slew to the new target
        # [TODO]: We are artificially increasing a sensor's slewing ability if it is not tasked at every timestep.
        return self.slew_rate * (self.host.time - self.time_last_ob) >= self.delta_boresight

    @property
    def az_mask(self):
        """``ndarray``: Returns the azimuth visibility mask."""
        return self._az_mask

    @az_mask.setter
    def az_mask(self, new_az_mask: ndarray):
        """Ensure the azimuth mask is between [0, 2*pi].

        Args:
            new_az_mask (``ndarray``): azimuth mask for a particular sensor
        """
        if isinstance(new_az_mask[0], (float, int)):
            if new_az_mask.all() >= 0 and new_az_mask.all() <= 2 * const.PI:
                self._az_mask = new_az_mask.reshape(2)
            else:
                raise ValueError(
                    f"Sensor: Invalid shape for az_mask property: {new_az_mask.shape}"
                )
        else:
            raise TypeError(f"Sensor: Invalid type for az_mask property: {type(new_az_mask[0])}")

    @property
    def el_mask(self):
        """``ndarray``: Returns the elevation visibility mask."""
        return self._el_mask

    @el_mask.setter
    def el_mask(self, new_el_mask: ndarray):
        """Ensure the elevation mask is between [-pi, pi].

        Args:
            new_el_mask (``ndarray``): elevation mask for a particular sensor
        """
        if isinstance(new_el_mask[0], (float, int)):
            if new_el_mask.all() >= -const.PI and new_el_mask.all() <= const.PI:
                self._el_mask = new_el_mask.reshape(2)
            else:
                raise ValueError(
                    f"Sensor: Invalid shape for el_mask property: {new_el_mask.shape}"
                )
        else:
            raise TypeError(f"Sensor: Invalid type for el_mask property: {type(new_el_mask[0])}")

    @property
    def r_matrix(self):
        """``ndarray``: Returns the measurement noise covariance matrix."""
        return self._r_matrix

    @r_matrix.setter
    def r_matrix(self, new_specs: ndarray):
        """Ensure the measurement noise matrix is a square matrix.

        Args:
            new_specs (``ndarray``): measurement noise matrix for a particular sensor
        """
        if new_specs.shape[1] == 1 or new_specs.shape[0] == 1:
            self._r_matrix = diagflat(new_specs.ravel()) ** 2.0
        elif new_specs.shape[0] == new_specs.shape[1]:
            self._r_matrix = new_specs
        else:
            raise ValueError(f"Sensor: Invalid shape for r_matrix property: {new_specs.shape}")
        # Save the sqrt form of the R matrix to save computation time
        # [FIXME]: not initialized as `None` in `__init__` because variable not overwritten by this line...
        self._sqrt_noise_covar = real(
            sqrtm(self._r_matrix)
        )  # pylint: disable=attribute-defined-outside-init

    @property
    def host(self):
        """:class:`.SensingAgent`: Returns reference to agent that contains this sensor."""
        return self._host

    @host.setter
    def host(self, new_host: SensingAgent):
        """Assign host to an attribute, and sets other relevant properties accordingly.

        Args:
            new_host (:class:`.SensingAgent`): containing `SensingAgent` object
        """
        self._host = new_host
        self.time_last_ob = new_host.time

        if self.az_mask[0] < self.az_mask[1]:
            mid_az = self.az_mask[0] + (self.az_mask[1] - self.az_mask[0]) / 2.0
        else:
            mid_az = self.az_mask[1] + (self.az_mask[0] - self.az_mask[1]) / 2.0

        if self.el_mask[0] < self.el_mask[1]:
            mid_el = self.el_mask[0] + (self.el_mask[1] - self.el_mask[0]) / 2.0
        else:
            mid_el = self.el_mask[1] + (self.el_mask[0] - self.el_mask[1]) / 2.0

        self.boresight = array([cos(mid_el) * cos(mid_az), cos(mid_el) * sin(mid_az), sin(mid_el)])

    @property
    def measurement_noise(self):
        """``ndarray``: Returns randomly-generated measurement noise as v_k ~ N(0; r_matrix)."""
        return matmul(self._sqrt_noise_covar, random.randn(self._r_matrix.shape[0]))

    def getSensorData(self):
        """``dict``: Returns a this sensor's formatted information."""
        output_dict = {
            "name": self.host.name,
            "id": self.host.simulation_id,
            "covariance": self.r_matrix.tolist(),
            "slew_rate": self.slew_rate,
            "azimuth_range": self.az_mask.tolist(),
            "elevation_range": self.el_mask.tolist(),
            "efficiency": self.efficiency,
            "aperture_area": self.aperture_area,
            "sensor_type": getTypeString(self),
            "exemplar": self.exemplar.tolist(),
            "field_of_view": self.field_of_view,
        }
        if getTypeString(self.host) == "Spacecraft":
            output_dict["init_eci"] = self.host.truth_state.tolist()
            output_dict["host_type"] = "Spacecraft"
        else:
            latlon = self.host.lla_state
            output_dict["lat"] = latlon[0]
            output_dict["lon"] = latlon[1]
            output_dict["alt"] = latlon[2]
            output_dict["host_type"] = "GroundFacility"
        if getTypeString(self) == "Optical":
            pass
        else:
            output_dict["tx_power"] = self.tx_power  # pylint: disable=no-member
            output_dict["tx_frequency"] = (
                const.SPEED_OF_LIGHT / self.wavelength  # pylint: disable=no-member
            )

        return output_dict
