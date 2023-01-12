"""Abstract :class:`.Sensor` base class which defines the common sensor interface."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, cos, sin, zeros_like
from scipy.linalg import norm

# Local Imports
from ..common.exceptions import ShapeError
from ..common.logger import resonaateLogInfo
from ..common.utilities import getTypeString
from ..data.observation import Explanation, MissedObservation, Observation
from ..physics import constants as const
from ..physics.maths import subtendedAngle
from ..physics.measurement_utils import getAzimuth, getElevation, getRange
from ..physics.sensor_utils import lineOfSight
from ..physics.time.stardate import ScenarioTime, julianDateToDatetime
from ..physics.transforms.methods import getSlantRangeVector

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..agents.sensing_agent import SensingAgent
    from ..agents.target_agent import TargetAgent
    from .field_of_view import FieldOfView
    from .measurement import Measurement


OPTICAL_LABEL: str = "Optical"
"""``str``: Constant string used to describe optical sensors."""

RADAR_LABEL: str = "Radar"
"""``str``: Constant string used to describe radar sensors."""

ADV_RADAR_LABEL: str = "AdvRadar"
"""``str``: Constant string used to describe advanced radar sensors."""

CONIC_FOV_LABEL: str = "conic"
"""``str``: Constant string used to describe conic field of view."""

RECTANGULAR_FOV_LABEL: str = "rectangular"
"""str: Constant string used to describe rectangular field of view."""

VALID_SENSOR_FOV_LABELS: tuple[str] = (
    CONIC_FOV_LABEL,
    RECTANGULAR_FOV_LABEL,
)
"""``tuple``: Contains valid sensor Field of View configurations."""

SOLAR_PANEL_REFLECTIVITY: float = 0.21
"""``float``: reflectivity of a solar panel :cite:t:`montenbruck_2012_orbits`, unit-less."""

DEFAULT_VIEWING_ANGLE: float = 1.0
"""``float``: default angle for a sensor's FoV, degrees."""


class Sensor:
    """Abstract base class for a generic Sensor object."""

    def __init__(
        self,
        measurement: Measurement,
        az_mask: ndarray,
        el_mask: ndarray,
        diameter: float,
        efficiency: float,
        slew_rate: float,
        field_of_view: FieldOfView,
        background_observations: bool,
        minimum_range: float,
        maximum_range: float,
        **sensor_args: dict,
    ):
        """Construct a generic `Sensor` object.

        Args:
            measurement (:class:`.Measurement`): defines the measurement data produced by this sensor
            az_mask (``ndarray``): azimuth mask for visibility conditions
            el_mask (``ndarray``): elevation mask for visibility conditions
            diameter (``float``): diameter of sensor dish (m)
            efficiency (``float``): efficiency percentage of the sensor
            slew_rate (``float``): maximum rotational speed of the sensor (deg/sec)
            field_of_view (:class:`.FieldOfView`): field of view of sensor
            background_observations (``bool``): whether or not to calculate Field of View, default=True
            minimum_range (``float``): minimum RSO range needed for visibility
            maximum_range (``float``): maximum RSO range needed for visibility
            detectable_vismag (``float``): minimum vismag of RSO needed for visibility
            sensor_args (``dict``): extra key word arguments for easy extension of the `Sensor` interface
        """
        self._measurement = measurement
        self._az_mask = zeros_like(az_mask)
        self._el_mask = zeros_like(el_mask)
        self.az_mask = const.DEG2RAD * az_mask
        self.el_mask = const.DEG2RAD * el_mask
        self.aperture_area = const.PI * ((diameter / 2.0) ** 2)
        self.efficiency = efficiency
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

    @property
    def angle_measurements(self) -> ndarray:
        """Returns which measurements are angles as integer values.

        The following values are valid:
            - `0` is a non-angular measurement, no special treatment is needed
            - `1` is an angular measurement valid in [-pi, pi]
            - `2` is an angular measurement valid in [0, 2pi]

        Returns:
            ``ndarray``: integer array defining angular measurements
        """
        return self._measurement.angular_values

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
    ) -> tuple[list[Observation], list[MissedObservation]]:
        """Collect observations on all targets within the sensor's FOV.

        Args:
            estimate_eci (``ndarray``): Estimate state vector that sensor is pointing at
            target_agent (:class:`.TargetAgent`): Target agent that sensor is pointing at
            background_agents (``list``): list of possible :class:`.TargetAgent` objects in FoV

        Returns:
            ``list``: :class:`.Observation` for each successful tasked observation
            ``list``: :class:`.MissedObservation` for each unsuccessful tasked observation
        """
        obs_list = []
        missed_observation_list = []
        # Check if sensor will slew to point in time
        datetime_epoch = julianDateToDatetime(self.host.julian_date_epoch)
        slant_range_sez = getSlantRangeVector(self.host.eci_state, estimate_eci, datetime_epoch)
        if self.canSlew(slant_range_sez):
            # Check if primary RSO is FoV
            if len(self.checkTargetsInView(slant_range_sez, [target_agent])) == 1:
                observation = self.attemptNoisyObservation(target_agent)
                if observation.reason == Explanation.VISIBLE:
                    obs_list.append(observation)
                else:
                    missed_observation_list.append(observation)

            else:
                missed_observation_list.append(
                    MissedObservation(
                        julian_date=self.host.julian_date_epoch,
                        sensor_type=getTypeString(self),
                        sensor_id=self.host.simulation_id,
                        target_id=target_agent.simulation_id,
                        sensor_eci=self.host.eci_state,
                        reason=Explanation.FIELD_OF_VIEW,
                    )
                )

            # If doing Serendipitous Observations
            if self.calculate_background:
                background_targets_in_fov = self.checkTargetsInView(
                    slant_range_sez, background_agents
                )
                visible_observations = filter(  # pylint:disable=bad-builtin
                    lambda observation: isinstance(observation, Observation),
                    (self.attemptNoisyObservation(tgt) for tgt in background_targets_in_fov),
                )
                obs_list.extend(tuple(visible_observations))

            self.boresight = slant_range_sez[:3] / norm(slant_range_sez[:3])
            if obs_list:
                self.time_last_ob = self.host.time

        else:
            missed_observation_list.append(
                MissedObservation(
                    julian_date=self.host.julian_date_epoch,
                    sensor_type=getTypeString(self),
                    sensor_id=self.host.simulation_id,
                    target_id=target_agent.simulation_id,
                    sensor_eci=self.host.eci_state,
                    reason=Explanation.SLEW_DISTANCE,
                )
            )

        return obs_list, missed_observation_list

    def checkTargetsInView(
        self, slant_range_sez: float, background_agents: list[TargetAgent]
    ) -> list[TargetAgent]:
        """Perform bulk FOV check on all RSOs.

        Args:
            slant_range_sez (``ndarray``): 3x1 slant range vector that sensor is pointing towards
            background_agents (``list``): list of all background `.TargetAgents` for this observation

        Returns:
            ``list``: list of all visible background `.TargetAgents` for this observation
        """
        datetime_epoch = julianDateToDatetime(self.host.julian_date_epoch)
        # filter out targets outside of FOV
        agents_in_fov = list(
            filter(  # pylint:disable=bad-builtin
                lambda agent: self.field_of_view.inFieldOfView(
                    slant_range_sez,
                    getSlantRangeVector(self.host.eci_state, agent.eci_state, datetime_epoch),
                ),
                background_agents,
            )
        )  # pylint:disable=bad-builtin
        return agents_in_fov

    def attemptObservation(
        self,
        tgt_id: int,
        tgt_eci_state: ndarray,
        viz_cross_section: float,
        reflectivity: float,
        real_obs: bool = False,
    ) -> Observation | MissedObservation:
        """Calculate the measurement data for a single observation.

        Args:
            tgt_id (``int``): simulation ID associated with current target
            tgt_eci_state (``ndarray``): 6x1 ECI state vector of the target (km; km/sec)
            viz_cross_section (``float``): visible cross-sectional area of the target (m^2)
            reflectivity (``float``): Reflectivity of RSO (unitless)
            real_obs (``bool``, optional): whether observation should include noisy measurements. Defaults to ``False``.

        Returns:
            :class:`.Observation` | :class:`.MissedObservation`: constructed observation or a _missed_ observation and
                reason it isn't visible.
        """
        # Calculate common values
        julian_date = self.host.julian_date_epoch
        datetime_epoch = julianDateToDatetime(julian_date)
        slant_range_sez = getSlantRangeVector(self.host.eci_state, tgt_eci_state, datetime_epoch)

        # Construct observations
        visibility, reason = self.isVisible(
            tgt_eci_state, viz_cross_section, reflectivity, slant_range_sez
        )
        if visibility:
            # Make a real observation once tasked -> add noise to the measurement
            # Forecasting an observation for reward matrix purposes
            observation = Observation.fromMeasurement(
                epoch_jd=julian_date,
                target_id=tgt_id,
                tgt_eci_state=tgt_eci_state,
                sensor_id=self.host.simulation_id,
                sensor_eci=self.host.eci_state,
                sensor_type=getTypeString(self),
                measurement=self._measurement,
                noisy=real_obs,
            )

            # Also move boresight if making a real observation
            if real_obs:
                self.boresight = slant_range_sez[:3] / norm(slant_range_sez[:3])

            return observation

        # else
        return MissedObservation(
            julian_date=julian_date,
            sensor_type=getTypeString(self),
            sensor_id=self.host.simulation_id,
            target_id=tgt_id,
            sensor_eci=self.host.eci_state,
            reason=reason,
        )

    def attemptNoisyObservation(
        self, target_agent: TargetAgent
    ) -> Observation | MissedObservation:
        """Calculate the measurement data for a single observation with noisy measurements.

        Args:
            target_agent (`:class:.TargetAgent`): Target Agent being observed

        Returns:
            :class:`.Observation` | :class:`.MissedObservation`: constructed observation or a _missed_ observation and
                reason it isn't visible.
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

        return self.attemptObservation(
            target_agent.simulation_id,
            tgt_eci_state,
            target_agent.visual_cross_section,
            target_agent.reflectivity,
            real_obs=True,
        )

    def isVisible(
        self,
        tgt_eci_state: ndarray,
        viz_cross_section: float,
        reflectivity: float,
        slant_range_sez: ndarray,
    ) -> tuple[bool, Explanation]:
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
            :class:`.Explanation`: Reason observation was visible or not
        """
        # pylint:disable=unused-argument, too-many-return-statements
        # Early exit if target not in sensor's minimum range
        if self.minimum_range is not None and getRange(slant_range_sez) < self.minimum_range:
            return False, Explanation.MINIMUM_RANGE

        # Early exit if target not in sensor's maximum range
        if self.maximum_range is not None and getRange(slant_range_sez) > self.maximum_range:
            return False, Explanation.MAXIMUM_RANGE

        # Early exit if a Line of Sight doesn't exist
        if not lineOfSight(tgt_eci_state[:3], self.host.eci_state[:3]):
            return False, Explanation.LINE_OF_SIGHT

        # Get the azimuth and elevation angles
        # [NOTE]: These are assumed to always be in the following ranges:
        #           - [0, 2*pi]
        #           - [-pi/2, pi/2]
        #   This should suffice to cover all necessary/required conditions
        azimuth = getAzimuth(slant_range_sez)
        elevation = getElevation(slant_range_sez)

        # Check if the elevation is within sensor bounds
        if elevation < self.el_mask[0] or elevation > self.el_mask[1]:
            return False, Explanation.ELEVATION_MASK

        # [NOTE]: Azimuth check requires two versions:
        #   - az_0 <= az_1 for normal situations
        #   - az_0 > az_1 for when mask transits the 360deg/True North line
        if self.az_mask[0] <= self.az_mask[1] and self.az_mask[0] <= azimuth <= self.az_mask[1]:
            return True, Explanation.VISIBLE

        if self.az_mask[0] > self.az_mask[1] and (
            azimuth >= self.az_mask[0] or azimuth <= self.az_mask[1]
        ):
            return True, Explanation.VISIBLE

        # Default: target satellite is not in view
        return False, Explanation.AZIMUTH_MASK

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
        return self._measurement.r_matrix

    @property
    def measurement(self) -> Measurement:
        r""":class:`.Measurement`: Returns measurement object for this sensor."""
        return self._measurement

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
