"""Defines the :class:`.AdaptiveFilter` class to formalize an interface for adaptive filtering algorithms."""

from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import argwhere, array, ceil, concatenate, delete, dot, hstack, linspace, ones, outer
from numpy import round as np_round
from numpy import sum as np_sum
from numpy import union1d, vstack, zeros
from scipy.linalg import norm

# Local Imports
from ...data import getDBConnection
from ...data.queries import fetchEstimatesByJDInterval, fetchObservationsByJDInterval
from ...dynamics.celestial import EarthCollisionError
from ...physics.orbit_determination.lambert import determineTransferDirection
from ...physics.time.stardate import JulianDate, ScenarioTime
from ...physics.transforms.methods import radarObs2eciPosition
from ..kalman.kalman_filter import KalmanFilter
from ..results import AdaptiveForecastResult, AdaptivePredictResult, AdaptiveUpdateResult
from ..sequential_filter import FilterFlag
from .initialization import lambertInitializationFactory
from .mmae_stacking_utils import stackingFactory

if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...data.observation import Observation
    from ...data.resonaate_database import ResonaateDatabase
    from ...dynamics.integration_events import ScheduledEventType
    from ...physics.orbit_determination import OrbitDeterminationFunction
    from ...scenario.config.estimation_config import AdaptiveEstimationConfig


class AdaptiveFilter(KalmanFilter):
    r"""Describes necessary equations for state estimation using multiple model adaptive estimation.

    The Adaptive Filter Interface provides a standard method for integrating any adaptive
    estimation algorithm into a Scenario.

    See Also:
        :class:`.KalmanFilter` for definition of common class attributes

    Attributes:
        orbit_determination (``callable``): :func:`.OrbitDeterminationFunction` function by which
            models are initially generated.
        stacking_method (``callable``): :func:`.StackingFunction` function that performs estimate
            & covariance stacking/combining to get a singular _posteriori_ estimate and covariance
            of the MMAE filter.
        previous_obs_window (``int``): number of previous observations to rewind to and include in models.
        scenario_time_step (:class:`.ScenarioTime`): timestep of the scenario.
        model_interval (``float``): how many seconds between each model.
        prune_threshold (``float``): models with likelihood below this value are pruned from the considered models
        prune_percentage (``float``): if a model's likelihood is above this value, the MMAE filter is assumed to have
            "converged" to this model.
        mode_probability (``ndarray``): mode probability vector
        models (``list``): :class:`.KalmanFilter` objects representing each model
        model_likelihood (``ndarray``): likelihood of each model
        model_weights (``ndarray``): model weighting factors
        num_models (``int``): number of models
    """

    def __init__(
        self,
        nominal_filter: KalmanFilter,
        timestep: ScenarioTime,
        orbit_determination: OrbitDeterminationFunction,
        stacking_method: Callable[[list[KalmanFilter], ndarray], tuple[ndarray, ndarray]],
        previous_obs_window: int,
        model_interval: float,
        prune_threshold: float,
        prune_percentage: float,
    ):
        """Initialize a generic adaptive filter class.

        Args:
            nominal_filter (:class:`.SequentialFilter`): filter at the time MMAE initializes
            timestep (:class:`.ScenarioTime`): timestep of the scenario, for properly propagating models to current
                time
            orbit_determination (``callable``): :func:`.OrbitDeterminationFunction` function by which
                models are initially generated.
            stacking_method (``callable``): :func:`.StackingFunction` function that performs estimate
                & covariance stacking/combining to get a singular _posteriori_ estimate and covariance
                of the MMAE filter.
            previous_obs_window (``int``): number of previous observations to rewind to and include in models.
            model_interval (``float``): how many seconds between each model.
            prune_threshold (``float``): models with likelihood below this value are pruned from the considered models
            prune_percentage (``float``): if a model's likelihood is above this value, the MMAE filter is assumed to
                have "converged" to this model.
        """
        super().__init__(
            nominal_filter.target_id,
            nominal_filter.time,
            nominal_filter.est_x,
            nominal_filter.est_p,
            nominal_filter.dynamics,
            nominal_filter.q_matrix,
            nominal_filter.maneuver_detection,
            adaptive_estimation=False,
            initial_orbit_determination=False,
        )
        # MMAE initialized attributes
        self.scenario_time_step = timestep
        self.orbit_determination_method = orbit_determination
        self.stacking_method = stacking_method
        self.previous_obs_window = previous_obs_window
        self.model_interval = model_interval
        self.prune_threshold = prune_threshold
        self.prune_percentage = prune_percentage

        # Save original filter class type
        # [NOTE]: For dynamically creating copies of original filter
        self._original_filter = deepcopy(nominal_filter)
        self._filter_class = self._original_filter.__class__
        self._converged_filter = None

        # Sequential filter products
        # [NOTE]: Need to save maneuver detection information for proper logging & saving to DB
        self.maneuver_detected = True
        self.maneuver_metric = nominal_filter.maneuver_detection.metric

        # MMAE uninitialized attributes
        self.mode_probabilities: ndarray = array([])
        self.models: list[KalmanFilter] = []
        self.model_likelihoods: ndarray = array([])
        self.model_weights: ndarray = array([])
        self.num_models: int = 0
        self.mmae_antecedent_time: float = 0.0

    @classmethod
    def fromConfig(
        cls,
        mmae_config: AdaptiveEstimationConfig,
        nominal_filter: KalmanFilter,
        timestep: ScenarioTime,
    ) -> AdaptiveFilter:
        """Create adaptive estimation filter from a config object.

        Args:
            mmae_config (:class:`.AdaptiveEstimationConfig`): MMAE method associated with the filter
            nominal_filter (:class:`.SequentialFilter`): filter at the time MMAE initializes
            timestep (:class:`.ScenarioTime`): timestep of the scenario, for properly propagating models to current
                time

        Returns:
            class:`.AdaptiveEstimationConfig`: constructed adaptive estimation object
        """
        return cls(
            nominal_filter,
            timestep,
            lambertInitializationFactory(mmae_config.orbit_determination),
            stackingFactory(mmae_config.stacking_method),
            mmae_config.observation_window,
            mmae_config.model_interval,
            mmae_config.prune_threshold,
            mmae_config.prune_percentage,
        )

    def initialize(
        self,
        observations: list[Observation],
        julian_date_start: JulianDate,
    ) -> bool:
        """Initialize MMAE models.

        First the MMAE uses some method to generate "hypotheses" for how the satellite maneuvered.
        Each hypothesis is tested against physical constraints, (such as maximum delta v or not crashing into the Earth)
        and if one violates a constraint it is "pruned" or deleted. Hypotheses which satisfy the constraints are formed
        into models, which will be carried forth to perform adaptive estimation.
        Each model is propagated to the "mmae_antecedent_time", being the time one timestep prior to the maneuver
        detection.

        MMAE is **not** initialized if:

        #. number of observations is 0
        #. number of observations is not equal to or greater than the :attr:`.previous_observations` config option
        #. number of models is not greater than 1

        Args:
            observations (``list``): :class:`.Observation` objects associated with the filter step
            julian_date_start (:class:`.JulianDate`): julian date at the start of the scenario

        Returns:
            ``bool``: Whether or not enough observations and estimates were in the database to start MMAE
        """
        # load path to on-disk database for the current scenario run
        database = getDBConnection()

        current_jdate = ScenarioTime(self.time).convertToJulianDate(julian_date_start)

        observation_ephem = fetchObservationsByJDInterval(
            database,
            [self.target_id],
            jd_ub=current_jdate,
        )[-self.previous_obs_window :]

        # Check if there are enough obs to perform MMAE
        if not len(observation_ephem) >= 1:
            msg = f"Not enough observations of RSO {self.target_id} to perform MMAE {len(observation_ephem)}"
            self.logger.warning(msg)
            return False

        if self.previous_obs_window > len(observation_ephem):
            msg = f"Not enough observations of RSO {self.target_id} to perform MMAE {len(observation_ephem)}"
            self.logger.warning(msg)
            return False

        # Time of most recent observation before maneuver detection
        prior_ob_jdate = JulianDate(observation_ephem[0].julian_date)

        # Determine model timestep & number of models to generate
        prior_ob_scenario_time = prior_ob_jdate.convertToScenarioTime(julian_date_start)
        time_step, self.num_models = self._calculateTimestep(prior_ob_scenario_time)

        if self.num_models <= 1:
            msg = f"Not enough models of RSO {self.target_id} to perform MMAE {self.num_models}"
            self.logger.warning(msg)
            return False

        self.flags |= FilterFlag.ADAPTIVE_ESTIMATION_START
        msg = f"{self.__class__.__name__} beginning for {self.target_id} at {self.time} with {self.num_models} models"
        self.logger.info(msg)

        # Determine time of most recent MMAE timestep (not necessarily the most recent physics timestep)
        self.mmae_antecedent_time = self.time - time_step

        # Times of the possible maneuvers
        stack_time = linspace(
            start=round(prior_ob_scenario_time),
            stop=round(self.mmae_antecedent_time),
            num=self.num_models - 1,
        )
        ## [NOTE]: Duplicate first maneuver time for model with no maneuver
        maneuver_times = hstack((stack_time[0], stack_time))

        # Calculate the nominal states of each model at their maneuver time
        nominal_states = self._calculateNominalStates(
            database,
            julian_date_start,
            prior_ob_jdate,
            current_jdate,
            maneuver_times,
        )

        # Calculate the required impulsive maneuver for each model
        hypothesis_maneuvers = self._generateHypothesisManeuvers(
            observations,
            nominal_states,
            maneuver_times,
        )

        # Determine new states for each hypothesis at the MMAE antecedent time
        hypothesis_states = self._generateHypothesisStates(
            nominal_states,
            hypothesis_maneuvers,
            maneuver_times,
        )

        # Check after initial pruning
        if self.num_models < 1:
            msg = f"Not enough models of RSO {self.target_id} to perform MMAE {self.num_models}"
            self.logger.warning(msg)
            return False

        # Create models from valid hypotheses
        self.models = self._createModels(hypothesis_states)

        # Assign initial model probabilities
        self.model_likelihoods = ones(self.num_models)
        self.model_weights = ones(self.num_models) / self.num_models
        self.mode_probabilities = ones(self.num_models) / self.num_models

        return True

    def _calculateNominalStates(
        self,
        database: ResonaateDatabase,
        initial_jd: JulianDate,
        prior_obs_jd: JulianDate,
        current_jd: JulianDate,
        maneuver_times: ndarray,
    ) -> ndarray:
        """Create the nominal state vectors used to determine model hypotheses.

        Args:
            database (:class:`.ResonaateDatabase`): database instance from which previous estimates are fetched.
            initial_jd (:class:`.JulianDate`): julian date at the start of the scenario
            prior_obs_jd (:class:`.JulianDate`): Julian date at the most distant observation included in the
                hypotheses.
            current_jd (:class:`.JulianDate`): Julian date of the current timestep, to which all models will be
            maneuver_times (``ndarray``): Nx1 array of scenario times of each maneuver hypothesis.
                propagated.

        Returns:
            ``ndarray``: Nx6 array of nominal ECI state vectors at their maneuver times.
        """
        # Query the database for previous estimate state from last observation
        estimate_ephem = fetchEstimatesByJDInterval(
            database,
            [self.target_id],
            jd_lb=prior_obs_jd,
            jd_ub=current_jd,
        )

        # Convert Julian dates of estimate ephemerides to epoch seconds
        est_times = [
            JulianDate(est.julian_date).convertToScenarioTime(initial_jd) for est in estimate_ephem
        ]
        # [NOTE]: Add current time, for proper maneuver time checking between last physics
        # timestep and antecedent time
        est_times.append(current_jd.convertToScenarioTime(initial_jd))
        est_times = np_round(est_times)

        ## [NOTE]: First & second hypotheses start at earliest observation
        nominal_states = zeros((self.num_models, self.x_dim))
        nominal_states[0] = array(estimate_ephem[0].eci)
        nominal_states[1] = array(estimate_ephem[0].eci)

        # Map maneuver time indices to their closest estimate ephemeris, first two are always initial epoch
        maneuver_indices = array([0, 1])
        unprocessed_maneuver_times = delete(maneuver_times, maneuver_indices, axis=0)
        # Accounts for num_models == 2 case
        if not unprocessed_maneuver_times.any():
            return nominal_states

        idx = 2
        for ii, (est_time, estimate) in enumerate(zip(est_times, estimate_ephem)):
            # Get maneuver times that occur before the _next_ epoch
            maneuver_indices = argwhere(unprocessed_maneuver_times <= est_times[ii + 1]).flatten()
            current_maneuver_times = unprocessed_maneuver_times[maneuver_indices]
            n_states = len(current_maneuver_times)
            # Propagate the most recent estimate to all the maneuver times before the next estimate
            nominal_states[idx : idx + n_states] = self.dynamics.propagateBulk(
                hstack((est_time, current_maneuver_times)),
                array(estimate.eci),
            ).T
            idx += n_states

            # Remove processed maneuver times
            unprocessed_maneuver_times = delete(
                unprocessed_maneuver_times,
                maneuver_indices,
                axis=0,
            )
            # Ensures we only continue to process when there are unprocessed maneuvers
            if not unprocessed_maneuver_times.any():
                break

        return nominal_states

    def _generateHypothesisStates(
        self,
        nominal_states: ndarray,
        maneuvers: ndarray,
        maneuver_times: ndarray,
    ) -> ndarray:
        """Generate ECI state hypotheses from given maneuver hypotheses.

        Args:
            nominal_states (``ndarray``): Nx6 array of nominal ECI state vectors at their maneuver times.
            maneuvers (``ndarray``): Nx3 array of impulsive ECI maneuver vectors.
            maneuver_times (``ndarray``): Nx1 array of scenario times of each maneuver hypothesis.

        Returns:
            ``ndarray``: Nx6 array of ECI state vectors at the antecedent timestep.
        """
        # Add maneuver hypotheses
        hypothesis_states = array(
            [
                nominal_state + concatenate((zeros(3), delta_v))
                for nominal_state, delta_v in zip(nominal_states, maneuvers)
            ],
        )

        crashed_indices = []
        # Last model is not propagated because it is already at t(k+1) - dt
        for idx, maneuver_time in enumerate(maneuver_times[:-1]):
            # Occurs if num_models == 2, and both base model and first == antecedent time
            if maneuver_time == self.mmae_antecedent_time:
                continue

            # Propagate to time t(k+1) - dt, not the current time t(k+1)
            try:
                hypothesis_states[idx] = self.dynamics.propagate(
                    maneuver_time,
                    self.mmae_antecedent_time,
                    hypothesis_states[idx],
                )
            except EarthCollisionError:
                crashed_indices.append(idx)

        # Prune off hypotheses that violate constraints
        return self._initialPruning(
            maneuvers,
            array(crashed_indices, dtype=int),
            hypothesis_states,
        )

    def _calculateTimestep(self, prior_ob_scenario_time: ScenarioTime) -> tuple[float, int]:
        """Calculated the number of models and time_step between models.

        Args:
            prior_ob_scenario_time (:class:.`ScenarioTime`): Scenario Time of the previous observation

        Returns:
            ``tuple[float, int]``: the seconds between models & the number of total models
        """
        gap_time = self.time - round(prior_ob_scenario_time)
        time_step = min(self.model_interval, self.scenario_time_step)
        msg = f"Creating models at a {time_step} second time interval"
        self.logger.info(msg)
        if time_step != self.model_interval:
            msg = f"Models not instantiated at {self.model_interval} second time step"
            self.logger.warning(msg)

        return time_step, int(ceil(gap_time / time_step) + 1)

    def _generateHypothesisManeuvers(
        self,
        observations: list[Observation],
        nominal_states: ndarray,
        maneuver_times: ndarray,
    ) -> ndarray:
        """Generate deltaV hypotheses for each timestep.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the filter step
            nominal_states (``ndarray``): Nx6 array of nominal ECI state vectors.
            maneuver_times (``ndarray``): Nx1 array of scenario times of each maneuver hypothesis

        Returns:
            ``ndarray``: Nx3 array of ECI deltaV maneuver hypotheses
        """
        # [TODO]: only observed by optical sensors -- future work is range hypothesis
        tgt_eci_position = self.est_x[:3]
        for observation in observations:
            if getattr(observation, "range_km", None):
                # [TODO]: Only applies the last radar observation
                tgt_eci_position = radarObs2eciPosition(observation)

        return self._calculateDeltaV(nominal_states[1:], maneuver_times[1:], tgt_eci_position)

    def _initialPruning(
        self,
        maneuvers: ndarray,
        crashed_indices: ndarray,
        hypothesis_states: ndarray,
    ) -> ndarray:
        """Prune off physically impossible maneuver hypotheses.

        Note:
            N=number of models

        Args:
            maneuvers (``ndarray``): Nx3 array of ECI deltaV maneuver hypotheses
            crashed_indices (``ndarray``): indices of maneuver hypothesis where RSO crashed into the Earth
            hypothesis_states (``ndarray``): Nx6 array of model hypothesis ECI state vectors.

        Returns:
            ``ndarray``: Nx6 array of pruned model hypothesis ECI state vectors.
        """
        high_dv_indices = argwhere(norm(maneuvers, axis=1) > 0.981).flatten()

        # Remove crashing and infeasible models
        prune_indices = union1d(high_dv_indices, crashed_indices)
        if prune_indices.size == 0:
            return hypothesis_states

        if prune_indices.size == maneuvers.shape[1]:
            msg = "MMAE did not generate valid hypotheses, all models pruned"
            self.logger.warning(msg)

        hypothesis_states = delete(hypothesis_states, prune_indices, axis=0)
        self.num_models = hypothesis_states.shape[0]

        return hypothesis_states

    def _createModels(self, hypothesis_states: ndarray) -> list[KalmanFilter]:
        """Create All multiple models.

        Args:
            hypothesis_states (``ndarray``): Nx6 array of model hypothesis ECI state vectors.

        Returns:
            ``list``: :class:`.SequentialFilter` objects representing each model
        """
        models: list[KalmanFilter] = []
        for hypothesis_state in hypothesis_states:
            new_filter = self._filter_class(
                self.target_id,
                self.mmae_antecedent_time,
                hypothesis_state,
                self.est_p,
                self.dynamics,
                self.q_matrix,
                self.maneuver_detection,
                self._original_filter.initial_orbit_determination,
                adaptive_estimation=False,
                **self._original_filter.extra_parameters,
            )
            models.append(new_filter)

        return models

    def predict(
        self,
        final_time: ScenarioTime,
        scheduled_events: list[ScheduledEventType] | None = None,
    ):
        """Propagate the state estimate and error covariance with uncertainty.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
            scheduled_events (``list``, optional): scheduled events to apply during propagation which
                can either be implemented :class:`.ContinuousStateChangeEvent` or
                :class:`.DiscreteStateChangeEvent` objects.

        References:
            :cite:t:`nastasi_2018_diss`, Section 2.4.4, Algorithm 2.3, Eq 2.83-2.89, Pg 33
        """
        # Propagate individual models
        for model in self.models:
            model.predict(final_time)

        # Compile model predictions
        self._compilePredictStep()

        # Update time
        self.time = final_time

    def forecast(self, observations: list[Observation]):
        """Update the error covariance with observations.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the filter step

        References:
            :cite:t:`nastasi_2018_diss`, Section 2.4.4, Algorithm 2.4, Eq 2.90-2.96, Pg 34
        """
        for model in self.models:
            model.forecast(observations)

        self._compileForecastStep(observations)

    def update(self, observations: list[Observation]):
        """Update the state estimate with observations.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the filter step

        References:
            #. :cite:t:`nastasi_2018_diss`, Section 2.4.4, Algorithm 2.5, Eq 2.97-2.99, Pg 35
            #. :cite:t:`nastasi_2018_diss`, Section 4.5, Algorithm 4.3, Eq 4.9-4.14, Pg 64
            #. :cite:t:`nastasi_2018_diss`, Section 4.5, Algorithm 4.4, Pg 65
        """
        for model in self.models:
            model.update(observations)

    def _compilePredictStep(self):
        """Combine model predict step attributes into single, combined prediction."""
        # Form predicted state
        self.pred_x = zeros(self.x_dim)
        for model, weight in zip(self.models, self.model_weights):
            self.pred_x += model.pred_x * weight

        # Form predicted covariance
        self.pred_p = zeros((self.x_dim, self.x_dim))
        for model, weight in zip(self.models, self.model_weights):
            x_diff_pred = model.pred_x - self.pred_x
            self.pred_p += weight * (model.pred_p + outer(x_diff_pred, x_diff_pred))

    def _compileForecastStep(self, observations: list[Observation]):
        """Combine the filter data from each MMAE model to produce integrated filter matrices.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the filter step

        References:
            :cite:t:`nastasi_2018_diss`, Section 4.5, Algorithm 4.3, Eq 4.12-4.13, Pg 64
        """
        self._compilePredictStep()
        self.est_p = zeros((self.x_dim, self.x_dim))
        for model, weight in zip(self.models, self.model_weights):
            x_diff_est = model.est_x - self.est_x
            self.est_p += weight * (model.est_p + outer(x_diff_est, x_diff_est))

        if observations:
            self.is_angular = self.models[0].is_angular
            self.r_matrix = self.models[0].r_matrix
            self.mean_pred_y = dot(
                vstack([[x.mean_pred_y for x in self.models]]).T,
                self.model_weights,
            )
            y_dim = self.mean_pred_y.shape[0]
            self.cross_cvr = zeros((self.x_dim, y_dim))
            self.innov_cvr = zeros((y_dim, y_dim))
            self.kalman_gain = zeros((self.x_dim, y_dim))
            for model, weight in zip(self.models, self.model_weights):
                self.cross_cvr += weight * model.cross_cvr
                self.innov_cvr += weight * model.innov_cvr
                self.kalman_gain += weight * model.kalman_gain

    def _compileUpdateStep(self, observations: list[Observation]):
        """Combine the filter data from each MMAE model to produce an integrated filter estimate.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the filter step

        References:
            :cite:t:`nastasi_2018_diss`, Section 4.5, Algorithm 4.3, Eq 4.12-4.13, Pg 64
        """
        self._compileForecastStep(observations)
        self.time = self.models[0].time
        self.source = self.models[0].source
        self.pred_x, self.est_x = self.stacking_method(self.models, self.model_weights)

        self.pred_p = zeros((self.x_dim, self.x_dim))
        self.est_p = zeros((self.x_dim, self.x_dim))
        for model, weight in zip(self.models, self.model_weights):
            x_diff_pred = model.pred_x - self.pred_x
            x_diff_est = model.est_x - self.est_x
            self.pred_p += weight * (model.pred_p + outer(x_diff_pred, x_diff_pred))
            self.est_p += weight * (model.est_p + outer(x_diff_est, x_diff_est))

        if observations:
            self.true_y = self.models[0].true_y
            self.innovation = dot(
                vstack([[x.innovation for x in self.models]]).T,
                self.model_weights,
            )
            self.nis = dot([x.nis for x in self.models], self.model_weights)

    def prune(self, prune_index: ndarray, observations: list[Observation]):
        """Prune off filter candidate solutions.

        Args:
            prune_index (``ndarray``): indices of models to be pruned
            observations (``list``): :class:`.Observation` objects associated with the filter step
        """
        for index in reversed(prune_index):
            # Don't prune everything
            if len(self.models) != 1:
                self.models.pop(index)
                self.num_models -= 1
                self.model_weights = delete(self.model_weights, index)
                self.model_likelihoods = delete(self.model_likelihoods, index)
                self.mode_probabilities = delete(self.mode_probabilities, index)

        self.model_weights = self.model_weights / np_sum(self.model_weights)
        self._compileUpdateStep(observations)

    def _calculateDeltaV(
        self,
        pre_maneuver_states: ndarray,
        maneuver_times: list[float],
        tgt_eci_position: ndarray,
    ) -> ndarray:
        """Apply Universal Method Lambert Targeter to each MMAE model.

        Note:
            zeroth index MMAE model always assumes no maneuver

        Args:
            pre_maneuver_states (``ndarray``): (N-1)x6 ECI array of state vectors, N is the number of models
            maneuver_times (``list``): N-1 times where hypothesized maneuvers occurred, N is the number of models
            tgt_eci_position (``ndarray``): 3x1 ECI position to fit models

        Returns:
            ``ndarray``: (N-1)x3 ECI impulsive maneuver vectors.

        References:
            #. :cite:t:`nastasi_2018_diss`, Section 4.6, Eq 4.21-4.23, Pg 67
            #. :cite:t:`vallado_2013_astro`, Section 7.7, Algorithm 61, Pg 503
        """
        maneuvers = zeros((self.num_models, 3))
        # [NOTE]: first model has no maneuver so it is skipped
        for idx, (pre_maneuver_state, maneuver_time) in enumerate(
            zip(pre_maneuver_states, maneuver_times),
        ):
            # [NOTE]: Circular orbit assumed as first approx.
            transfer_method = determineTransferDirection(
                pre_maneuver_state,
                self.time - maneuver_time,
            )
            new_velocity, _ = self.orbit_determination_method(
                pre_maneuver_state[:3],
                tgt_eci_position[:3],
                self.time - maneuver_time,
                transfer_method,
            )
            maneuvers[idx + 1] = new_velocity - pre_maneuver_state[3:]

        return maneuvers

    def getPredictionResult(self) -> AdaptivePredictResult:
        """Compile result message for a predict step.

        Returns:
            Filter results from the 'predict' step.
        """
        return AdaptivePredictResult.fromFilter(self)

    def getForecastResult(self) -> AdaptiveForecastResult:
        """Compile result message for a forecast step.

        Returns:
            Filter results from the 'forecast' step.
        """
        return AdaptiveForecastResult.fromFilter(self)

    def getUpdateResult(self) -> AdaptiveUpdateResult:
        """Compile result message for an update step.

        Returns:
            Filter results from the 'update' step.
        """
        return AdaptiveUpdateResult.fromFilter(self)

    def _resumeSequentialFiltering(self):
        """The adaptive filter has converged, so create a nominal filter from the converged model."""
        # Reset adaptive estimation flags
        if FilterFlag.ADAPTIVE_ESTIMATION_START in self.flags:
            self.flags ^= FilterFlag.ADAPTIVE_ESTIMATION_START
        self.flags |= FilterFlag.ADAPTIVE_ESTIMATION_CLOSE

        # Set the converged filter attribute
        self._converged_filter = self._filter_class(
            tgt_id=self.target_id,
            time=self.time,
            est_x=self.est_x,
            est_p=self.est_p,
            dynamics=self.dynamics,
            q_matrix=self.q_matrix,
            maneuver_detection=self.maneuver_detection,
            initial_orbit_determination=False,
            adaptive_estimation=True,
            **self._original_filter.extra_parameters,
        )

        # [TODO]: Make a reinitialize function in the SequentialFilter
        attribute_list = [
            "pred_x",
            "pred_p",
            "is_angular",
            "innovation",
            "nis",
            "source",
            "mean_pred_y",
            "r_matrix",
            "cross_cvr",
            "innov_cvr",
            "kalman_gain",
            "maneuver_metric",
            "true_y",
            "flags",
        ]

        for attr in attribute_list:
            setattr(self._converged_filter, attr, getattr(self, attr))

    @property
    def converged_filter(self):
        """Filter that mmae has converged to."""
        return self._converged_filter
