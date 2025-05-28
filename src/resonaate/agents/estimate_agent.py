"""Defines the :class:`.EstimateAgent` class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy.random import default_rng

# RESONAATE Imports
from resonaate.common.exceptions import ShapeError
from resonaate.common.utilities import getTypeString
from resonaate.data.detected_maneuver import DetectedManeuver
from resonaate.data.ephemeris import EstimateEphemeris
from resonaate.data.filter_step import FilterStep, filter_map
from resonaate.estimation import (
    adaptiveEstimationFactory,
    initialOrbitDeterminationFactory,
    sequentialFilterFactory,
)
from resonaate.estimation.particle.particle_filter import ParticleFilter
from resonaate.estimation.sequential_filter import FilterFlag, SequentialFilter
from resonaate.physics.noise import initialEstimateNoise, noiseCovarianceFactory
from resonaate.physics.transforms.methods import ecef2lla, eci2ecef

# Local Imports
from .agent_base import Agent

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import NoReturn

    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self

    # RESONAATE Imports
    from resonaate.data.ephemeris import _EphemerisMixin
    from resonaate.dynamics.dynamics_base import Dynamics
    from resonaate.dynamics.integration_events.station_keeping import StationKeeper
    from resonaate.physics.time.stardate import ScenarioTime
    from resonaate.scenario.clock import ScenarioClock
    from resonaate.scenario.config import NoiseConfig, TimeConfig
    from resonaate.scenario.config.agent_config import AgentConfig
    from resonaate.scenario.config.estimation_config import (
        AdaptiveEstimationConfig,
        EstimationConfig,
        InitialOrbitDeterminationConfig,
    )
    from resonaate.sensors.sensor_base import Observation


class EstimateAgent(Agent):  # pylint: disable=too-many-public-methods
    """Define the behavior of the **estimated** target agents in the simulation."""

    def __init__(  # noqa: PLR0913
        self,
        _id: int,
        name: str,
        agent_type: str,
        clock: ScenarioClock,
        initial_state: ndarray,
        initial_covariance: ndarray,
        _filter: SequentialFilter,
        adaptive_filter_config: AdaptiveEstimationConfig,
        initial_orbit_determination_config: InitialOrbitDeterminationConfig,
        visual_cross_section: float | int,
        mass: float | int,
        reflectivity: float,
        seed: int | None = None,
        station_keeping: list[StationKeeper] | None = None,
    ) -> None:
        R"""Construct an EstimateAgent object.

        Args:
            _id (``int``): unique identification number
            name (``str``): unique identification name
            agent_type (``str``): name signifying the type of agent `('Spacecraft', 'GroundFacility', )`
            clock (:class:`.ScenarioClock`): clock instance for retrieving proper times
            initial_state (``ndarray``): 6x1 ECI initial state vector
            initial_covariance (``ndarray``): 6x6 initial covariance or uncertainty
            _filter (:class:`.SequentialFilter`): tracks the estimate's state throughout the simulation
            adaptive_filter_config (:class:`.AdaptiveEstimationConfig`): adaptive filter configuration to be used if needed
            initial_orbit_determination_config (:class:`.InitialOrbitDeterminationConfig`): IOD configuration to be used if needed
            visual_cross_section (``float, int``): constant visual cross-section of the agent
            mass (``float, int``): constant mass of the agent
            reflectivity (``float``): constant reflectivity of the agent
            seed (``int``, optional): number to seed random number generator. Defaults to ``None``.
            station_keeping (``list``, optional): list of :class:`.StationKeeper` objects describing the station
                keeping to be performed. Defaults to ``None``.

        Raises:
            - ``TypeError`` raised on incompatible types for input params
            - ``ShapeError`` raised if process noise is not a 6x6 matrix
        """
        super().__init__(
            _id=_id,
            name=name,
            agent_type=agent_type,
            initial_state=initial_state,
            clock=clock,
            dynamics=_filter.dynamics,
            realtime=True,
            visual_cross_section=visual_cross_section,
            mass=mass,
            reflectivity=reflectivity,
            station_keeping=station_keeping,
        )

        if initial_covariance.shape != (6, 6):
            self._logger.error("Incorrect shape for initial_covariance param")
            raise ShapeError(initial_covariance.shape)

        # Properly initialize the EstimateAgent's covariance types
        self._initial_covariance = initial_covariance.copy()
        self._error_covariance = initial_covariance.copy()

        if not isinstance(seed, int) and seed is not None:
            self._logger.error("Incorrect type for seed param")
            raise TypeError(type(seed))
        # Save the random number generator for generating noise
        self._rng = default_rng(seed)

        # Properly initialize the EstimateAgent's state types
        self._state_estimate = initial_state.copy()
        self._ecef_state = eci2ecef(initial_state, self.datetime_epoch)
        self._lla_state = ecef2lla(self._ecef_state)

        # Set the EstimateAgent's filter & set itself to the filter's host
        self._filter = _filter

        self._filter_step = None
        for k, v in filter_map.items():
            if isinstance(_filter, k):
                self._filter_step = v
        if self._filter_step is None:
            raise TypeError(f"Could not find a matching filter step for {type(_filter)}")

        # Attribute to track the adaptive_filter config of this object
        self.adaptive_filter_config = adaptive_filter_config

        # Attribute to track the initial_orbit_determination config of this object
        self.initial_orbit_determination = initialOrbitDeterminationFactory(
            initial_orbit_determination_config,
            self.simulation_id,
            self.julian_date_start,
        )

        # Attribute to track the time at which IOD begins
        self.iod_start_time: ScenarioTime | None = None

        # Attribute to track the most recent _actual_ observation of this object
        self.last_observed_at = self.julian_date_start

        # Attribute which tracks maneuver detection objects
        self._detected_maneuvers = []

        # Attribute which tracks information for filter step
        self._filter_info = []

        # Apply None value to estimate station_keeping
        if self.station_keeping:
            msg = "Estimates do not perform station keeping maneuvers"
            raise ValueError(msg)

    @classmethod
    def fromConfig(
        cls,
        tgt_cfg: AgentConfig,
        clock: ScenarioClock,
        dynamics: Dynamics,
        time_cfg: TimeConfig,
        noise_cfg: NoiseConfig,
        estimation_cfg: EstimationConfig,
    ) -> Self:
        """Factory to initialize `EstimateAgent` objects based on given configuration.

        Args:
            tgt_cfg (:class:`.AgentConfig`): config from which to generate an estimate agent.
            clock (:class:`.ScenarioClock`): common clock object for the simulation.
            dynamics (:class:`.Dynamics`): dynamics that handles state propagation.
            time_cfg (:class:`.TimeConfig`): defines time configuration settings.
            noise_cfg (:class:`.NoiseConfig`): defines noise configuration settings.
            estimation_cfg (:class:`.EstimationConfig`): defines estimation configuration settings.

        Returns:
            :class:`.EstimateAgent`: properly constructed agent object.
        """
        # Create the initial state & covariance
        initial_state = tgt_cfg.state.toECI(clock.datetime_epoch)
        init_x, init_p = initialEstimateNoise(
            initial_state,
            noise_cfg.init_position_std_km,
            noise_cfg.init_velocity_std_km_p_sec,
            default_rng(noise_cfg.random_seed),
        )

        filter_noise = noiseCovarianceFactory(
            noise_cfg.filter_noise_type,
            time_cfg.physics_step_sec,
            noise_cfg.filter_noise_magnitude,
        )

        nominal_filter = None
        nominal_filter = sequentialFilterFactory(
            estimation_cfg.sequential_filter,
            tgt_cfg.id,
            clock.time,
            init_x,
            init_p,
            dynamics,
            filter_noise,
        )

        return cls(
            tgt_cfg.id,
            tgt_cfg.name,
            tgt_cfg.platform.type,
            clock,
            init_x,
            init_p,
            nominal_filter,
            estimation_cfg.adaptive_filter,
            estimation_cfg.initial_orbit_determination,
            tgt_cfg.platform.visual_cross_section,
            tgt_cfg.platform.mass,
            tgt_cfg.platform.reflectivity,
            seed=noise_cfg.random_seed,
        )

    def importState(self, ephemeris: _EphemerisMixin) -> NoReturn:
        """Set the state of this EstimateAgent based on a given :class:`.Ephemeris` object.

        Warning:
            This method is not implemented because :class:`.EstimateAgent` objects cannot load data for propagation.

        Args:
            ephemeris (:class:`._EphemerisMixin`): data object to update this SensingAgent's state with
        """
        raise NotImplementedError("Cannot load state estimates directly into simulation")

    def update(self, observations: list[Observation]) -> None:
        """Update the :attr:`nominal_filter`, state estimate, & covariance.

        Args:
            observations (``list``): :class:`.Observation` objects associated with this timestep
        """
        self.nominal_filter.update(observations)
        self._update(observations)
        self._finalizeUpdate(len(observations) > 0)

    def getCurrentEphemeris(self) -> EstimateEphemeris:
        """Returns the EstimateAgent's current ephemeris information.

        This is used for bulk-updating the output database with state information.

        Returns:
            :class:`.EstimateEphemeris`: valid data object for insertion into output database.
        """
        return EstimateEphemeris.fromCovarianceMatrix(
            agent_id=self.simulation_id,
            julian_date=self.julian_date_epoch,
            source=self.nominal_filter.source,
            eci=self.eci_state.tolist(),
            covariance=self.error_covariance.tolist(),
        )

    def getDetectedManeuvers(self) -> list[DetectedManeuver]:
        """``list``: Returns current :class:`.DetectedManeuver` objects."""
        detections = self._detected_maneuvers
        self._detected_maneuvers = []

        return detections

    def getFilterSteps(self) -> list[FilterStep]:
        """``list``: Returns current information of most recent :class:`.FilterStep` objects."""
        filter_steps = self._filter_info
        self._filter_info = []

        return filter_steps

    def _update(self, observations: list[Observation]) -> None:
        """Perform local update of :attr:`nominal_filter`, state estimate, & covariance.

        Save the *a posteriori* :attr:`state_estimate` and :attr:`error_covariance`. Also, log
        filter events if the truth is passed in, typically done locally.

        Args:
            observations (``list``): :class:`.Observation` associated with this timestep
        """
        if not observations:
            return

        if self.nominal_filter.maneuver_detected:
            self._handleManeuverDetection(observations)

        # [NOTE]: IOD & MMAE should be mutually exclusive - they should not be able to
        #   be used at the same time, so order should not matter.
        if self.initial_orbit_determination:
            self._handleIOD(observations)

        if self.adaptive_filter_config:
            self._handleMMAE(observations)

    def _finalizeUpdate(self, observed: bool) -> None:
        """Finalize the update step by saving specific attributes.

        Note:
            This logic is split into it's own method because the parallel handler
            must perform these operations after the update portion finishes.

        Args:
            observed: Flag indicating whether the target tracked by this update was observed.
        """
        self.state_estimate = self.nominal_filter.est_x
        self.error_covariance = self.nominal_filter.est_p

        if not observed:
            return

        self.last_observed_at = self.julian_date_epoch
        self._saveFilterStep()

    def _handleManeuverDetection(self, observations: list[Observation]) -> None:
        """Save :class:`.DetectedManeuver` events to insert into the DB later.

        Args:
            observations (``list``): :class:`.Observation` objects corresponding to the detected maneuver.
        """
        sensor_nums = {ob.sensor_id for ob in observations}
        msg = f"Maneuver Detected for RSO {self.simulation_id} by sensors {sensor_nums} at time {self.datetime_epoch}"
        self._logger.info(msg)

        self._detected_maneuvers.append(
            DetectedManeuver(
                julian_date=self.julian_date_epoch,
                # [FIXME]: Lazy way to implement multiple sensor IDs before moving to postgres
                sensor_ids=str(sensor_nums)[1:-1],
                target_id=self.simulation_id,
                nis=self.nominal_filter.nis,
                method=getTypeString(self.nominal_filter.maneuver_detection),
                metric=self.nominal_filter.maneuver_metric,
                threshold=self.nominal_filter.maneuver_detection.threshold,
            ),
        )

    def _saveFilterStep(self) -> None:
        """Save :class:`.FilterStep` events to insert into the DB later."""
        self._filter_info.append(
            # FilterStep.recordFilterStep(
            self._filter_step.recordFilterStep(
                julian_date=self.julian_date_epoch,
                target_id=self.simulation_id,
                filter=self.nominal_filter,
                # innovation=self.nominal_filter.innovation,
                # nis=self.nominal_filter.nis,
            ),
        )

    def _resetFilter(self, new_filter: SequentialFilter) -> None:
        """Overwrite the agent's filter object with a new filter instance.

        Args:
            new_filter (:class:`.SequentialFilter`): new filter object to replace the agent's nominal filter.

        Raises:
            ``TypeError``: raised if invalid object is passed.
        """
        if not isinstance(new_filter, (SequentialFilter, ParticleFilter)):
            msg = f"Cannot reset filter attribute with invalid type: {type(new_filter)}"
            raise TypeError(msg)

        self._filter = new_filter

    @property
    def maneuver_detected(self) -> bool:
        """``bool``: Returns whether detected maneuvers are stored for this estimate agent."""
        return bool(self._detected_maneuvers)

    @property
    def iod_active(self) -> bool:
        """Returns whether IOD is currently active."""
        return self.iod_start_time is not None and self.iod_start_time < self.time

    @property
    def eci_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECI current state estimate."""
        return self._state_estimate

    @property
    def ecef_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECEF current state estimate."""
        return self._ecef_state

    @property
    def lla_state(self) -> ndarray:
        """``ndarray``: Returns the 3x1 current position estimate in lat, lon, & alt."""
        return self._lla_state

    @property
    def process_noise_covariance(self) -> ndarray:
        """``ndarray``: Returns the 6x6 process noise matrix."""
        return self._filter.q_matrix

    @property
    def initial_covariance(self) -> ndarray:
        """``ndarray``: Returns the 6x6 original error covariance matrix."""
        return self._initial_covariance

    @property
    def error_covariance(self) -> ndarray:
        """``ndarray``: Returns the 6x6 current error covariance (uncertainty) matrix."""
        return self._error_covariance

    @error_covariance.setter
    def error_covariance(self, new_covar: ndarray) -> None:
        """Properly set the error covariance matrix.

        Args:
            new_covar (``ndarray``): updated error covariance matrix.

        Raises:
            TypeError: raised if not given a ``ndarray``
            ShapeError: raised if the matrix' shape is not ``(6,6)``
        """
        if new_covar.shape != (6, 6):
            self._logger.error("Incorrect dimensions for setting error covariance")
            raise ShapeError(new_covar.shape)
        self._error_covariance = new_covar

    @property
    def state_estimate(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECI current state estimate."""
        return self._state_estimate

    @state_estimate.setter
    def state_estimate(self, new_state) -> None:
        """Set the EstimateAgent's new 6x1 ECI state vector.

        Args:
            new_state (``ndarray``): 6x1 ECI state vector
        """
        self._state_estimate = new_state
        self._ecef_state = eci2ecef(new_state, self.datetime_epoch)
        self._lla_state = ecef2lla(self._ecef_state)

    @property
    def nominal_filter(self) -> SequentialFilter:
        """:class:`.SequentialFilter`: Returns the EstimateAgent's associated filter instance."""
        return self._filter

    @property
    def visual_cross_section(self) -> float:
        """``float``: Returns the EstimateAgent's associated visual cross section."""
        return self._visual_cross_section

    @property
    def mass(self) -> float:
        """``float``: Returns the EstimateAgent's associated mass."""
        return self._mass

    @property
    def reflectivity(self) -> float:
        """``float``: Returns the EstimateAgent's associated reflectivity."""
        return self._reflectivity

    def _handleMMAE(self, observations: list[Observation]) -> None:
        """Handle MMAE logic.

        Check for MMAE close flag and reset the filter if found. Also, if a maneuver
        is detected and MMAE

        Args:
            observations (list): :class:`.Observation` objects of this agent.
        """
        if self.maneuver_detected:
            self._beginAdaptiveEstimation(observations)

        if FilterFlag.ADAPTIVE_ESTIMATION_CLOSE in self.nominal_filter.flags:
            self.nominal_filter.flags ^= FilterFlag.ADAPTIVE_ESTIMATION_CLOSE
            self._resetFilter(self.nominal_filter.converged_filter)

    def _handleIOD(self, observations: list[Observation]) -> None:
        """Handle IOD logic.

        Try to perform a successful IOD. If successful, reset attributes accordingly
        and update the filter estimate. Otherwise, leave IOD active for next timestep.

        Args:
            observations (list): :class:`.Observation` objects of this agent.
        """
        # [NOTE]: Extra check to make sure that IOD is not currently running for this particular agent.
        if self.maneuver_detected and not self.iod_active:
            self.iod_start_time = self.time
            msg = f"Turning on IOD for RSO {self.simulation_id} at time {self.datetime_epoch}"
            self._logger.info(msg)

        if self.iod_active:
            converged, iod_state = self._attemptInitialOrbitDetermination(observations)
            if converged:
                self.iod_start_time = None
                self.nominal_filter.est_x = iod_state

    def _beginAdaptiveEstimation(self, observations: list[Observation]) -> None:
        """Try to start adaptive estimation on this RSO.

        Args:
            observations (``list``): :class:`.Observation` associated with this timestep
        """
        if FilterFlag.ADAPTIVE_ESTIMATION_START not in self.nominal_filter.flags:
            return

        self.nominal_filter.flags ^= FilterFlag.ADAPTIVE_ESTIMATION_START

        adaptive_filter = adaptiveEstimationFactory(
            self.adaptive_filter_config,
            self.nominal_filter,
            self.dt_step,
        )

        mmae_started = adaptive_filter.initialize(
            observations=observations,
            julian_date_start=self.julian_date_start,
        )

        # [NOTE]: MMAE filter started but hasn't immediately converged
        if mmae_started:
            self._resetFilter(adaptive_filter)

    def _attemptInitialOrbitDetermination(
        self,
        observations: list[Observation],
    ) -> tuple[bool, ndarray | None]:
        """Try to solve initial orbit determination on this RSO.

        Args:
            observations (``list``): :class:`.Observation` associated with this timestep.
            logging (``bool``): Bool indicating logging of estimate conops, Defaults to False.

        Returns:
            ``tuple``:

            :``bool``: whether or not IOD was success
            :``ndarray | None``: Estimate state determined from IOD
        """
        # Early Returns
        if not self.initial_orbit_determination:
            return False, None

        # [NOTE]: IOD cannot converge on the same timestep as initialization
        if self.iod_start_time is None or self.iod_start_time == self.time:
            return False, None

        if self.iod_start_time > self.time:
            raise ValueError(
                f"IOD beginning in the future: {self.iod_start_time} relative to current scenario time: {self.time}",
            )

        msg = f"Attempting IOD for RSO {self.simulation_id} at time {self.datetime_epoch}"
        self._logger.info(msg)

        iod_solution = self.initial_orbit_determination.determineNewEstimateState(
            observations,
            self.iod_start_time,
            self.time,
        )
        if iod_solution.convergence:
            msg = f"IOD successful for RSO {self.simulation_id} at time {self.datetime_epoch}"
        else:
            msg = f"IOD unsuccessful for RSO {self.simulation_id} at time {self.datetime_epoch}"

        self._logger.info(msg)

        # check if IOD failed
        if not iod_solution.convergence:
            self._logger.warning(iod_solution.message)

        return iod_solution.convergence, iod_solution.state_vector
