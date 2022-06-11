"""Defines the :class:`.EstimateAgent` class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import fabs
from numpy.random import default_rng
from scipy.linalg import norm

# Local Imports
from ..common.exceptions import ShapeError
from ..common.utilities import getTypeString
from ..data.detected_maneuver import DetectedManeuver
from ..data.ephemeris import EstimateEphemeris
from ..data.filter_step import FilterStep
from ..estimation import adaptiveEstimationFactory, sequentialFilterFactory
from ..estimation.debug_utils import checkThreeSigmaObs, logFilterStep
from ..estimation.sequential.sequential_filter import FilterDebugFlag, SequentialFilter
from ..physics.noise import initialEstimateNoise
from ..physics.transforms.methods import ecef2lla, eci2ecef
from .agent_base import Agent

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any, Optional

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..dynamics.integration_events.station_keeping import StationKeeper
    from ..scenario.clock import ScenarioClock
    from ..scenario.config.estimation_config import AdaptiveEstimationConfig
    from ..sensors.sensor_base import ObservationTuple


class EstimateAgent(Agent):
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
        seed: Optional[int] = None,
        station_keeping: Optional[list[StationKeeper]] = None,
    ):
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
            seed (``int``, optional): number to seed random number generator. Defaults to ``None``.
            station_keeping (``list``, optional): list of :class:`.StationKeeper` objects describing the station
                keeping to be performed. Defaults to ``None``.

        Raises:
            - ``TypeError`` raised on incompatible types for input params
            - ``ShapeError`` raised if process noise is not a 6x6 matrix
        """
        super().__init__(
            _id,
            name,
            agent_type,
            initial_state,
            clock,
            _filter.dynamics,
            True,
            DEFAULT_VIS_X_SECTION,
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
        self._ecef_state = eci2ecef(initial_state)
        self._lla_state = ecef2lla(self._ecef_state)

        # Set the EstimateAgent's filter & set itself to the filter's host
        if isinstance(_filter, SequentialFilter):
            self._filter = _filter
        else:
            self._logger.error("Invalid input type for _filter param")
            raise TypeError(type(_filter))

        self.adaptive_filter = adaptive_filter_config

        # Attribute to track the most recent _actual_ observation of this object
        self.last_observed_at = self.julian_date_start

        # Attribute which tracks maneuver detection objects
        self._detected_maneuvers = []

        # Attribute which tracks information for filter step
        self._filter_info = []

        # Apply None value to estimate station_keeping
        assert not self.station_keeping, "Estimates do not perform station keeping maneuvers"

    def updateEstimate(self, obs_tuples: list[ObservationTuple], truth: ndarray):
        """Update the :attr:`nominal_filter`, state estimate, & covariance.

        This is the local update function. See :meth:`.updateFromAsyncUpdateEstimate` for details
        on how to update from a parallel job result.

        See Also:
            :func:`.asyncExecuteTasking` to see how the result is computed

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` objects associated with this timestep
            truth (``ndarray``): 6x1 ECI state vector for the true target agent
        """
        self.nominal_filter.update(obs_tuples)
        self._update(obs_tuples, truth=truth)

    def updateFromAsyncPredict(self, async_result: dict[str, Any]):
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

        if FilterDebugFlag.NEAREST_PD in self.nominal_filter.flags:
            msg = f"`nearestPD()` function was used in predict: {self.name}"
            self._logger.warning(msg)

        self.state_estimate = self.nominal_filter.pred_x
        self.error_covariance = self.nominal_filter.pred_p

    def updateFromAsyncUpdateEstimate(self, async_result: dict[str, Any]):
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

    def _saveDetectedManeuver(self, obs_tuples: list[ObservationTuple]):
        """Save :class:`.DetectedManeuver` events to insert into the DB later.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` objects corresponding to the detected maneuver.
        """
        sensor_nums = {obs_tuple.agent.simulation_id for obs_tuple in obs_tuples}
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

    def _saveFilterStep(self):
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
    def maneuver_detected(self):
        """``bool``: Returns whether detected maneuvers are stored for this estimate agent."""
        return bool(self._detected_maneuvers)

    def _logFilterEvents(self, obs_tuples: list[ObservationTuple], truth: ndarray):
        """Log filter events and perform debugging steps.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` made of the agent during the timestep.
            truth (``ndarray``): 6x1, ECI truth_state of the target
        """
        # Check if error inflation is too large
        if FilterDebugFlag.ERROR_INFLATION in self.nominal_filter.flags:
            tol_km = 5  # Estimate inflation error tolerance (km)
            pred_error = fabs(norm(truth[:3] - self.nominal_filter.pred_x[:3]))
            est_error = fabs(norm(truth[:3] - self.nominal_filter.est_x[:3]))

            # If error increase is larger than desired log the debug information
            if est_error > pred_error + tol_km:
                file_name = logFilterStep(self.nominal_filter, obs_tuples, truth)
                msg = f"EstimateAgent error inflation occurred:\n\t{file_name}"
                self._logger.warning(msg)

        # Check if nearestPD() was called on the filter
        if FilterDebugFlag.NEAREST_PD in self.nominal_filter.flags:
            msg = f"`nearestPD()` function was used on {self.name} EstimateAgent"
            self._logger.warning(msg)

        # Check the three sigma distance of observations & log if needed
        if FilterDebugFlag.THREE_SIGMA_OBS in self.nominal_filter.flags:
            filenames = checkThreeSigmaObs(obs_tuples, sigma=3)
            msg = "Made bad observation, debugging info:\n\t"
            for filename in filenames:
                self._logger.warning(msg + f"{filename}")

        # Check if a maneuver was detected
        if FilterDebugFlag.MANEUVER_DETECTION in self.nominal_filter.flags:
            sensor_nums = {ob.agent.simulation_id for ob in obs_tuples}
            tgt = self.simulation_id
            jd = self.julian_date_epoch
            msg = f"Maneuver Detected for RSO {tgt} by sensors {sensor_nums} at time {jd}"
            self._logger.info(msg)

    def _update(self, obs_tuples: list[ObservationTuple], truth: Optional[ndarray] = None):
        """Perform update of :attr:`nominal_filter`, state estimate, & covariance.

        Save the *a posteriori* :attr:`state_estimate` and :attr:`error_covariance`. Also, log
        filter events if the truth is passed in, typically done locally.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` associated with this timestep
            truth (``ndarray``, optional): 6x1 ECI state vector for the true target agent
        """
        if truth is not None:
            self._logFilterEvents(obs_tuples, truth)

        if obs_tuples:
            self.last_observed_at = self.julian_date_epoch
            self._saveFilterStep()
            if self.nominal_filter.maneuver_detected:
                self._saveDetectedManeuver(obs_tuples)
                if (
                    FilterDebugFlag.ADAPTIVE_ESTIMATION_CLOSE
                    in self.nominal_filter.flags
                ):
                    self.resetFilter(self.nominal_filter.converged_filter)
                self._attemptAdaptiveEstimation(obs_tuples)

        self.state_estimate = self.nominal_filter.est_x
        self.error_covariance = self.nominal_filter.est_p

    def importState(self, ephemeris):
        """Set the state of this EstimateAgent based on a given :class:`.Ephemeris` object.

        Warning:
            This method is not implemented because EstimateAgent's cannot load data for propagation.

        Args:
            ephemeris (:class:`.Ephemeris`): data object to update this SensingAgent's state with
        """
        raise NotImplementedError("Cannot load state estimates directly into simulation")

    def _attemptAdaptiveEstimation(self, obs_tuples: list[ObservationTuple]):
        """Try to start adaptive estimation on this RSO.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` associated with this timestep
        """
        # MMAE initialization checks
        if FilterDebugFlag.ADAPTIVE_ESTIMATION_START in self.nominal_filter.flags:
            self.nominal_filter.flags ^= FilterDebugFlag.ADAPTIVE_ESTIMATION_START
            adaptive_filter = adaptiveEstimationFactory(
                self.adaptive_filter, self.nominal_filter, self.dt_step
            )

            # Create a multiple_model_filter
            mmae_started = adaptive_filter.initialize(
                obs_tuples=obs_tuples,
                julian_date_start=self.julian_date_start,
            )

            if mmae_started:
                self.resetFilter(adaptive_filter)

    @classmethod
    def fromConfig(cls, config: dict[str, Any], events: dict[str, Any]):
        """Factory to initialize :class:`.EstimateAgent` objects based on given configuration.

        Args:
            config (``dict``): formatted configuration parameters
            events (``dict``): corresponding formatted events

        Returns:
            :class:`.EstimateAgent`: properly constructed `EstimateAgent` object
        """
        # Grab multiple objects required for creating estimate agents
        tgt = config["target"]
        clock = config["clock"]
        # Create the initial state & covariance
        init_x, init_p = initialEstimateNoise(
            tgt.eci_state, config["position_std"], config["velocity_std"], config["rng"]
        )

        nominal_filter = sequentialFilterFactory(
            config["sequential_filter"],
            tgt.simulation_id,
            clock.time,
            init_x,
            init_p,
            config["dynamics"],
            config["q_matrix"],
        )

        # Create the `EstimateAgent` and initialize its filter object
        est = cls(
            tgt.simulation_id,
            tgt.name,
            tgt.agent_type,
            clock,
            init_x,
            init_p,
            nominal_filter,
            config["adaptive_filter"],
            config["seed"],
        )

        # Return properly initialized `EstimateAgent`
        return est

    def resetFilter(self, new_filter: SequentialFilter):
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
    def eci_state(self):
        """``ndarray``: Returns the 6x1 ECI current state estimate."""
        return self._state_estimate

    @property
    def ecef_state(self):
        """``ndarray``: Returns the 6x1 ECEF current state estimate."""
        return self._ecef_state

    @property
    def lla_state(self):
        """``ndarray``: Returns the 3x1 current position estimate in lat, lon, & alt."""
        return self._lla_state

    @property
    def process_noise_covariance(self):
        """``ndarray``: Returns the 6x6 process noise matrix."""
        return self._filter.q_matrix

    @property
    def initial_covariance(self):
        """``ndarray``: Returns the 6x6 original error covariance matrix."""
        return self._initial_covariance

    @property
    def error_covariance(self):
        """``ndarray``: Returns the 6x6 current error covariance (uncertainty) matrix."""
        return self._error_covariance

    @error_covariance.setter
    def error_covariance(self, new_covar: ndarray):
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
    def state_estimate(self):
        """``ndarray``: Returns the 6x1 ECI current state estimate."""
        return self._state_estimate

    @state_estimate.setter
    def state_estimate(self, new_state):
        """Set the EstimateAgent's new 6x1 ECI state vector.

        Args:
            new_state (``ndarray``): 6x1 ECI state vector
        """
        self._state_estimate = new_state
        self._ecef_state = eci2ecef(new_state)
        self._lla_state = ecef2lla(self._ecef_state)

    @property
    def nominal_filter(self):
        """:class:`.SequentialFilter`: Returns the EstimateAgent's associated filter instance."""
        return self._filter
