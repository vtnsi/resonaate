"""Abstract :class:`.Sensor` base class which defines the common sensor interface."""
from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from collections import namedtuple
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, cos, diagflat, matmul, random, real, sin, squeeze, zeros_like
from scipy.linalg import norm, sqrtm

# Local Imports
from ..common.exceptions import ShapeError
from ..common.logger import resonaateLogInfo
from ..common.utilities import getTypeString
from ..data.observation import Observation
from ..physics import constants as const
from ..physics.math import isPD, subtendedAngle
from ..physics.sensor_utils import lineOfSight
from ..physics.time.stardate import ScenarioTime
from ..physics.transforms.methods import getSlantRangeVector
from .measurements import getAzimuth, getElevation, getRange

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
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


class Sensor(ABC):
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
        background_observations: bool,
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
            background_observations (``bool``): whether or not to calculate Field of View, default=True
            detectable_vismag (``float``): minimum vismag of RSO needed for visibility
            minimum_range (``float``): minimum RSO range needed for visibility
            maximum_range (``float``): maximum RSO range needed for visibility
            sensor_args (``dict``): extra key word arguments for easy extension of the `Sensor` interface
        """
        self._az_mask = zeros_like(az_mask)
        self._el_mask = zeros_like(el_mask)
        self._r_matrix = zeros_like(r_matrix)
        self._sqrt_noise_covar = zeros_like(r_matrix)
        self.az_mask = const.DEG2RAD * az_mask
        self.el_mask = const.DEG2RAD * el_mask
        self.r_matrix = r_matrix
        self.aperture_area = const.PI * ((diameter / 2.0) ** 2)
        self.efficiency = efficiency
        self.exemplar = squeeze(exemplar)
        self.slew_rate = const.DEG2RAD * slew_rate
        self.field_of_view = field_of_view
        self.calculate_background = background_observations
        self.minimum_range = minimum_range
        self.maximum_range = maximum_range

        # Derived properties initialization
        self.time_last_ob = ScenarioTime(0.0)
        self.delta_boresight = 0.0
        self.boresight = self._setInitialBoresight()
        self._host = None
        self._sensor_args = sensor_args

    @abstractmethod
    def getMeasurements(self, slant_range_sez: ndarray, noisy: bool = False) -> dict[str, float]:
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
    def angle_measurements(self) -> ndarray:
        """Returns which measurements are angles as integer values.

        The following values are valid:
            - `0` is a non-angular measurement, no special treatment is needed
            - `1` is an angular measurement valid in [-pi, pi]
            - `2` is an angular measurement valid in [0, 2pi]

        Returns:
            ``ndarray``: integer array defining angular measurements
        """
        raise NotImplementedError

    def _setInitialBoresight(self) -> ndarray:
        """Determine the initial boresight vector as the center of the field of regard."""
        if self.az_mask[0] < self.az_mask[1]:
            mid_az = self.az_mask[0] + (self.az_mask[1] - self.az_mask[0]) / 2.0
        else:
            mid_az = self.az_mask[1] + (self.az_mask[0] - self.az_mask[1]) / 2.0

        if self.el_mask[0] < self.el_mask[1]:
            mid_el = self.el_mask[0] + (self.el_mask[1] - self.el_mask[0]) / 2.0
        else:
            mid_el = self.el_mask[1] + (self.el_mask[0] - self.el_mask[1]) / 2.0

        return array([cos(mid_el) * cos(mid_az), cos(mid_el) * sin(mid_az), sin(mid_el)])

    def collectObservations(
        self,
        estimate_eci: ndarray,
        target_agent: TargetAgent,
        background_agents: list[TargetAgent],
    ) -> list[ObservationTuple]:
        """Collect observations on all targets within the sensor's FOV.

        Args:
            estimate_eci (``ndarray``): Estimate state vector that sensor is pointing at
            target_agent (:class:`.TargetAgent`): Target agent that sensor is pointing at
            background_agents (``list``): list of possible `.TargetAgent` objects in FoV

        Returns:
            obs_list (``list``): list of `.ObservationTuple`
        """
        obs_list = []
        # Check if sensor will slew to point in time
        slant_range_sez = getSlantRangeVector(self.host.ecef_state, estimate_eci)
        if self.canSlew(slant_range_sez):
            # If doing Serendipitous Observations
            if self.calculate_background:
                targets_in_fov = self.checkTargetsInView(slant_range_sez, background_agents)
                obs_list = list(
                    filter(  # pylint:disable=bad-builtin
                        lambda ob_tuple: ob_tuple.observation,
                        (self.makeNoisyObservation(tgt) for tgt in targets_in_fov),
                    )
                )  # pylint:disable=bad-builtin
            # Check if primary RSO is FoV
            elif len(self.checkTargetsInView(slant_range_sez, [target_agent])) == 1:
                observation_tuple = self.makeNoisyObservation(target_agent)
                if observation_tuple.observation:
                    obs_list.append(observation_tuple)

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
                lambda agent: self.inFOV(
                    slant_range_sez, getSlantRangeVector(self.host.ecef_state, agent.eci_state)
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
            angle = subtendedAngle(background_sez[:3], pointing_sez[:3])
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

        raise ValueError(f"Wrong FoV shape: {self.field_of_view.fov_shape}")

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

            else:
                # Forecasting an observation for reward matrix purposes
                observation = self.buildSigmaObs(tgt_id, tgt_eci_state)

        else:
            observation = None

        return ObservationTuple(observation, self.host, self.angle_measurements)

    def makeNoisyObservation(self, target_agent: TargetAgent) -> ObservationTuple:
        """Calculate the measurement data for a single observation with noisy measurements.

        Args:
            target_agent (`:class:.TargetAgent`): Target Agent being observed

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

    def getNoisyMeasurements(self, slant_range_sez: ndarray) -> dict[str, float]:
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

    def isVisible(  # pylint:disable=too-many-return-statements
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
        # Early exit if target not in sensor's minimum range
        if self.minimum_range is not None and getRange(slant_range_sez) < self.minimum_range:
            return False

        # Early exit if target not in sensor's maximum range
        if self.maximum_range is not None and getRange(slant_range_sez) > self.maximum_range:
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
        if elevation < self.el_mask[0] or elevation > self.el_mask[1]:
            return False

        # [NOTE]: Azimuth check requires two versions:
        #   - az_0 <= az_1 for normal situations
        #   - az_0 > az_1 for when mask transits the 360deg/True North line
        if self.az_mask[0] <= self.az_mask[1] and self.az_mask[0] <= azimuth <= self.az_mask[1]:
            return True

        if self.az_mask[0] > self.az_mask[1] and (
            azimuth >= self.az_mask[0] or azimuth <= self.az_mask[1]
        ):
            return True

        # Default: target satellite is not in view
        return False

    def canSlew(self, slant_range_sez: ndarray) -> bool:
        """Check if sensor can slew to target in the allotted time.

        Args:
            slant_range_sez (``ndarray``): 3x1, slant range vector, (km; km/sec)

        Returns:
            ``bool``: whether target can be slewed to in time
        """
        self.delta_boresight = subtendedAngle(slant_range_sez[:3], self.boresight)
        # Boolean if you are able to slew to the new target
        # [TODO]: We are artificially increasing a sensor's slewing ability if it is not tasked at every timestep.
        return self.slew_rate * (self.host.time - self.time_last_ob) >= self.delta_boresight

    @property
    def az_mask(self) -> ndarray:
        r"""``ndarray``: Returns the azimuth visibility mask, :math:`\in[0, 2\pi]`."""
        return self._az_mask

    @az_mask.setter
    def az_mask(self, az_mask: ndarray):
        r"""Ensure the azimuth mask is between :math:`[0, 2\pi]`.

        Args:
            az_mask (``ndarray``): azimuth mask for a particular sensor
        """
        if az_mask.shape in ((2,), (2, 1)):
            if all(az_mask >= 0) and all(az_mask <= 2 * const.PI):
                self._az_mask = az_mask.reshape(2)
            else:
                raise ValueError(f"Sensor: Invalid value [0, 2π] for az_mask: {az_mask}")
        else:
            raise ShapeError(f"Sensor: Invalid shape for az_mask: {az_mask.shape}")

    @property
    def el_mask(self) -> ndarray:
        r"""``ndarray``: Returns the elevation visibility mask, :math:`\in[-\frac{\pi}{2}, \frac{\pi}{2}]`."""
        return self._el_mask

    @el_mask.setter
    def el_mask(self, el_mask: ndarray):
        r"""Ensure the elevation mask is between :math:`[-\frac{\pi}{2}, \frac{\pi}{2}]`.

        Args:
            el_mask (``ndarray``): elevation mask for a particular sensor
        """
        if el_mask.shape in ((2,), (2, 1)):
            if all(el_mask >= -const.PI / 2) and all(el_mask <= const.PI / 2):
                self._el_mask = el_mask.reshape(2)
            else:
                raise ValueError(f"Sensor: Invalid value [-π/2, π/2] for el_mask: {el_mask}")
        else:
            raise ShapeError(f"Sensor: Invalid shape for el_mask: {el_mask.shape}")

    @property
    def r_matrix(self) -> ndarray:
        r"""``ndarray``: Returns the :math:`n_z \times n_z` measurement noise covariance matrix."""
        return self._r_matrix

    @r_matrix.setter
    def r_matrix(self, r_matrix: ndarray):
        r"""Ensure the measurement noise matrix is a square matrix.

        Args:
            r_matrix (``ndarray``): measurement noise matrix for a particular sensor
        """
        if r_matrix.ndim == 1:
            self._r_matrix = diagflat(r_matrix.ravel()) ** 2.0
        elif r_matrix.shape[0] == r_matrix.shape[1]:
            self._r_matrix = r_matrix
        else:
            raise ShapeError(f"Sensor: Invalid shape for r_matrix: {r_matrix.shape}")

        if not isPD(self._r_matrix):
            raise ValueError(f"Sensor: non-positive definite r_matrix: {r_matrix}")

        # Save the sqrt form of the R matrix to save computation time
        # [FIXME]: not initialized as `None` in `__init__` because variable not overwritten by this line...
        self._sqrt_noise_covar = real(sqrtm(self._r_matrix))

    @property
    def host(self) -> SensingAgent:
        r""":class:`.SensingAgent`: Returns reference to agent that contains this sensor."""
        return self._host

    @host.setter
    def host(self, host: SensingAgent):
        r"""Assign host to an attribute, and sets other relevant properties accordingly.

        Args:
            host (:class:`.SensingAgent`): containing `SensingAgent` object
        """
        self._host = host
        self.time_last_ob = host.time

    @property
    def measurement_noise(self) -> ndarray:
        r"""``ndarray``: Return randomly-generated measurement :math:`n_z \times 1` noise vector.

        .. math::

            v_k \simeq N(0; R)

        """
        return matmul(self._sqrt_noise_covar, random.randn(self._r_matrix.shape[0]))

    def getSensorData(self) -> dict:
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
        if self.host.agent_type == "Spacecraft":
            output_dict["init_eci"] = self.host.truth_state.tolist()
            output_dict["host_type"] = "Spacecraft"
        else:
            latlon = self.host.lla_state
            output_dict["lat"] = latlon[0]
            output_dict["lon"] = latlon[1]
            output_dict["alt"] = latlon[2]
            output_dict["host_type"] = "GroundFacility"

        return output_dict
