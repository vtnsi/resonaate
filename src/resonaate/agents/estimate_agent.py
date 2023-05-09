"""Defines the :class:`.EstimateAgent` class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy.random import default_rng

# Local Imports
from ..common.exceptions import ShapeError
from ..common.utilities import getTypeString
from ..data.detected_maneuver import DetectedManeuver
from ..data.ephemeris import EstimateEphemeris
from ..data.filter_step import FilterStep
from ..estimation import (
    adaptiveEstimationFactory,
    initialOrbitDeterminationFactory,
    sequentialFilterFactory,
)
from ..estimation.sequential.sequential_filter import FilterFlag, SequentialFilter
from ..physics.noise import initialEstimateNoise, noiseCovarianceFactory
from ..physics.transforms.methods import ecef2lla, eci2ecef
from .agent_base import Agent

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any, NoReturn

    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self

    # Local Imports
    from ..data.ephemeris import _EphemerisMixin
    from ..dynamics.dynamics_base import Dynamics
    from ..dynamics.integration_events.station_keeping import StationKeeper
    from ..physics.time.stardate import ScenarioTime
    from ..scenario.clock import ScenarioClock
    from ..scenario.config import NoiseConfig, PropagationConfig, TimeConfig
    from ..scenario.config.agent_config import TargetAgentConfig
    from ..scenario.config.estimation_config import (
        AdaptiveEstimationConfig,
        EstimationConfig,
        InitialOrbitDeterminationConfig,
    )
    from ..sensors.sensor_base import Observation


class EstimateAgent(Agent):  # pylint: disable=too-many-public-methods
    """Define the behavior of the **estimated** target agents in the simulation."""

    def __init__(
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
            adaptive_filter_config (:class:`.ConfigOption`): adaptive filter configuration to be used if needed
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
        if isinstance(_filter, SequentialFilter):
            self._filter = _filter
        else:
            self._logger.error("Invalid input type for _filter param")
            raise TypeError(type(_filter))

        # Attribute to track the adaptive_filter config of this object
        self.adaptive_filter_config = adaptive_filter_config

        # Attribute to track the initial_orbit_determination config of this object
        self.initial_orbit_determination = initialOrbitDeterminationFactory(
            initial_orbit_determination_config, self.simulation_id, self.julian_date_start
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
        assert not self.station_keeping, "Estimates do not perform station keeping maneuvers"

    @classmethod
    def fromConfig(
        cls,
        tgt_cfg: TargetAgentConfig,
        clock: ScenarioClock,
        dynamics: Dynamics,
        time_cfg: TimeConfig,
        noise_cfg: NoiseConfig,
        estimation_cfg: EstimationConfig,
    ) -> Self:
        """Factory to initialize `EstimateAgent` objects based on given configuration.

        Args:
            tgt_cfg (:class:`.TargetAgentConfig`): config from which to generate an estimate agent.
            clock (:class:`.ScenarioClock`): common clock object for the simulation.
            dynamics (:class:`.Dynamics`): dynamics that handles state propagation.
            time_cfg (:class:`.TimeConfig`): defines time configuration settings.
            noise_cfg (:class:`.NoiseConfig`): defines noise configuration settings.
            estimation_cfg (:class:`.EstimationConfig`): defines estimation configuration settings.

        Returns:
            :class:`.EstimateAgent`: properly constructed agent object.
        """
        # pylint: disable=unused-argument
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

    def updateEstimate(self, observations: list[Observation]) -> None:
        """Update the :attr:`nominal_filter`, state estimate, & covariance.

        This is the local update function. See :meth:`.updateFromAsyncUpdateEstimate` for details
        on how to update from a parallel job result.

        See Also:
            :func:`.asyncExecuteTasking` to see how the result is computed

        Args:
            observations (``list``): :class:`.Observation` objects associated with this timestep
        """
        self.nominal_filter.update(observations)
        self._update(observations)

    def updateFromAsyncPredict(self, async_result: dict[str, Any]) -> None:
        """Perform predict using EstimateAgent's :attr:`nominal_filter`'s async result.

        Save the *a priori* :attr:`.state_estimate` and :attr:`.error_covariance`. This occurs
        **after** execution of a job on a :class:`.Worker`. The job result is handled by the
        :class:`.QueueManager` to update the :attr:`nominal_filter`.

        See Also:
            :meth:`~.JobHandler.handleProcessedJob` to see how the result is handled

        Args:
            async_result (``dict``): Result from parallel :attr:`nominal_filter` predict.
        """
        self.nominal_filter.updateFromAsyncResult(async_result)

        self.state_estimate = self.nominal_filter.pred_x
        self.error_covariance = self.nominal_filter.pred_p

    def updateFromAsyncUpdateEstimate(self, async_result: dict[str, Any]) -> None:
        """Update the :attr:`nominal_filter`, state estimate, & covariance from an async result.

        This is the parallel result update function. See :meth:`.updateEstimate` for details
        on how to update in a local way.

        See Also:
            :meth:`~.JobHandler.handleProcessedJob` to see how the result is handled

        Args:
            async_result (``dict``): Result from parallel :attr:`nominal_filter` update.
        """
        self.nominal_filter.updateFromAsyncResult(async_result["filter_update"])
        self._update(async_result["observations"])

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

    def _saveDetectedManeuver(self, observations: list[Observation]) -> None:
        """Save :class:`.DetectedManeuver` events to insert into the DB later.

        Args:
            observations (``list``): :class:`.Observation` objects corresponding to the detected maneuver.
        """
        sensor_nums = {ob.sensor_id for ob in observations}
        # [FIXME]: Lazy way to implement multiple sensor IDs before moving to postgres
        self._detected_maneuvers.append(
            DetectedManeuver(
                julian_date=self.julian_date_epoch,
                sensor_ids=str(sensor_nums)[1:-1],
                target_id=self.simulation_id,
                nis=self.nominal_filter.nis,
                method=getTypeString(self.nominal_filter.maneuver_detection),
                metric=self.nominal_filter.maneuver_metric,
                threshold=self.nominal_filter.maneuver_detection.threshold,
            )
        )

    def getDetectedManeuvers(self) -> list[DetectedManeuver]:
        """``list``: Returns current :class:`.DetectedManeuver` objects."""
        detections = self._detected_maneuvers
        self._detected_maneuvers = []

        return detections

    def _saveFilterStep(self) -> None:
        """Save :class:`.FilterStep` events to insert into the DB later."""
        self._filter_info.append(
            FilterStep.recordFilterStep(
                julian_date=self.julian_date_epoch,
                target_id=self.simulation_id,
                innovation=self.nominal_filter.innovation,
                nis=self.nominal_filter.nis,
            )
        )

    def getFilterSteps(self) -> list[FilterStep]:
        """``list``: Returns current information of most recent :class:`.FilterStep` objects."""
        filter_steps = self._filter_info
        self._filter_info = []

        return filter_steps

    @property
    def maneuver_detected(self) -> bool:
        """``bool``: Returns whether detected maneuvers are stored for this estimate agent."""
        return bool(self._detected_maneuvers)

    def _logFilterEvents(self, observations: list[Observation]) -> None:
        """Log filter events and perform debugging steps.

        Args:
            observations (``list``): :class:`.Observation` made of the agent during the timestep.
        """
        # Check if a maneuver was detected
        if FilterFlag.MANEUVER_DETECTION in self.nominal_filter.flags:
            sensor_nums = {ob.sensor_id for ob in observations}
            tgt = self.simulation_id
            jd = self.julian_date_epoch
            msg = f"Maneuver Detected for RSO {tgt} by sensors {sensor_nums} at time {jd}"
            self._logger.info(msg)

    def _update(self, observations: list[Observation]) -> None:
        """Perform update of :attr:`nominal_filter`, state estimate, & covariance.

        Save the *a posteriori* :attr:`state_estimate` and :attr:`error_covariance`. Also, log
        filter events if the truth is passed in, typically done locally.

        Args:
            observations (``list``): :class:`.Observation` associated with this timestep
        """
        self._logFilterEvents(observations)

        if observations:
            self.last_observed_at = self.julian_date_epoch
            self._saveFilterStep()
            self._attemptInitialOrbitDetermination(observations)
            if self.nominal_filter.maneuver_detected:
                self._saveDetectedManeuver(observations)
                if FilterFlag.ADAPTIVE_ESTIMATION_CLOSE in self.nominal_filter.flags:
                    self.resetFilter(self.nominal_filter.converged_filter)
                self._attemptAdaptiveEstimation(observations)
                self._attemptInitialOrbitDetermination(observations)

        self.state_estimate = self.nominal_filter.est_x
        self.error_covariance = self.nominal_filter.est_p

    def importState(self, ephemeris: _EphemerisMixin) -> NoReturn:
        """Set the state of this EstimateAgent based on a given :class:`.Ephemeris` object.

        Warning:
            This method is not implemented because EstimateAgent's cannot load data for propagation.

        Args:
            ephemeris (:class:`._EphemerisMixin`): data object to update this SensingAgent's state with
        """
        raise NotImplementedError("Cannot load state estimates directly into simulation")

    def _attemptAdaptiveEstimation(self, observations: list[Observation]) -> None:
        """Try to start adaptive estimation on this RSO.

        Args:
            observations (``list``): :class:`.Observation` associated with this timestep
        """
        # MMAE initialization checks
        if FilterFlag.ADAPTIVE_ESTIMATION_START in self.nominal_filter.flags:
            self.nominal_filter.flags ^= FilterFlag.ADAPTIVE_ESTIMATION_START
            adaptive_filter = adaptiveEstimationFactory(
                self.adaptive_filter_config, self.nominal_filter, self.dt_step
            )

            # Create a multiple_model_filter
            mmae_started = adaptive_filter.initialize(
                observations=observations,
                julian_date_start=self.julian_date_start,
            )

            if mmae_started:
                self.resetFilter(adaptive_filter)

    def _attemptInitialOrbitDetermination(self, observations: list[Observation]):
        """Try to start initial orbit determination on this RSO.

        Args:
            observations (``list``): :class:`.Observation` associated with this timestep
        """
        if not self.initial_orbit_determination:
            return

        if self.iod_start_time is None and self.nominal_filter.maneuver_detected:
            self.iod_start_time = self.time
            msg = f"Turning on IOD for RSO {self.simulation_id} at time {self.julian_date_epoch}"
            self._logger.info(msg)

        # [NOTE]: IOD cannot converge on the same timestep as initialization
        if self.iod_start_time is not None and self.iod_start_time < self.time:
            msg = f"Attempting IOD for RSO {self.simulation_id} at time {self.julian_date_epoch}"
            self._logger.info(msg)
            iod_est_x, success = self.initial_orbit_determination.determineNewEstimateState(
                observations, self.iod_start_time, self.time
            )
            if success:
                self.iod_start_time = None
                self.nominal_filter.est_x = iod_est_x
                msg = f"IOD successful for RSO {self.simulation_id}"
            else:
                msg = f"IOD unsuccessful for RSO {self.simulation_id}"
            self._logger.debug(msg)

    def resetFilter(self, new_filter: SequentialFilter) -> None:
        """Overwrite the agent's filter object with a new filter instance.

        Args:
            new_filter (:class:`.SequentialFilter`): new filter object to replace the agent's nominal filter.

        Raises:
            ``TypeError``: raised if invalid object is passed.
        """
        if not isinstance(new_filter, SequentialFilter):
            msg = f"Cannot reset filter attribute with invalid type: {type(new_filter)}"
            raise TypeError(msg)

        self._filter = new_filter

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
