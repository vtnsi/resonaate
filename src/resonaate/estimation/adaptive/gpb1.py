"""Defines the :class:`.GeneralizedPseudoBayesian1` class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import dot, exp, fill_diagonal, matmul, ones, ones_like, sqrt, zeros
from scipy.linalg import det

# Local Imports
from ...physics import constants as const
from ...physics.maths import fpe_equals
from ...physics.statistics import oneSidedChiSquareTest
from .adaptive_filter import AdaptiveFilter
from .initialization import lambertInitializationFactory
from .mmae_stacking_utils import stackingFactory

if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...data.observation import Observation
    from ...physics.orbit_determination import OrbitDeterminationFunction
    from ...physics.time.stardate import JulianDate, ScenarioTime
    from ...scenario.config.estimation_config import AdaptiveEstimationConfig
    from ..sequential.sequential_filter import SequentialFilter


class GeneralizedPseudoBayesian1(AdaptiveFilter):
    """GPB1 Multiple Model class.

    References:
        #. :cite:t:`nastasi_2018_diss`, Section 4.7, Pg 70, Figure 4.5, Pg 72
        #. :cite:t:`bar-shalom_2001_estimation`, Section 11.6., Pg 447
    """

    def __init__(  # noqa: PLR0913
        self,
        nominal_filter: SequentialFilter,
        timestep: ScenarioTime,
        orbit_determination: OrbitDeterminationFunction,
        stacking_method: Callable[[list[SequentialFilter], ndarray], tuple[ndarray, ndarray]],
        previous_obs_window: int,
        model_interval: float,
        prune_threshold: float,
        prune_percentage: float,
        mix_ratio: float = 1.5,
    ):
        """Initialize a GPB1 class.

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
            mix_ratio (``float``): ratio of diagonal to off-diagonals in transition probability matrix
        """
        super().__init__(
            nominal_filter,
            timestep,
            orbit_determination,
            stacking_method,
            previous_obs_window,
            model_interval,
            prune_threshold,
            prune_percentage,
        )
        # ratio of diagonal to off-diagonals in transition probability matrix
        self.mix_ratio = mix_ratio

    @classmethod
    def fromConfig(
        cls,
        mmae_config: AdaptiveEstimationConfig,
        nominal_filter: SequentialFilter,
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
            mix_ratio=mmae_config.mix_ratio,
        )

    def initialize(self, observations: list[Observation], julian_date_start: JulianDate) -> bool:
        """Initialize GPB1 models.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the filter step
            julian_date_start (:class:`.JulianDate`): julian date at the start of the scenario

        Returns:
            ``bool``: Whether or not enough observations and estimates were in the database to start MMAE
        """
        if not super().initialize(observations, julian_date_start):
            return False

        # Adaptive filter predict and update for each model from time t(k) -> t(k+1)
        self.predict(self.time)
        self.update(observations)
        return True

    def update(self, observations: list[Observation]):
        """Update the state estimate with observations.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the filter step

        References:
            #. :cite:t:`nastasi_2018_diss`, Section 2.4.4, Algorithm 2.5, Eq 2.97-2.99, Pg 35
            #. :cite:t:`nastasi_2018_diss`, Section 4.5, Algorithm 4.3, Eq 4.9-4.14, Pg 64
            #. :cite:t:`nastasi_2018_diss`, Section 4.5, Algorithm 4.4, Pg 65
            #. :cite:t:`bar-shalom_2001_estimation`, Section 11.6.4, Pg 447
        """
        super().update(observations)

        if observations:
            for num, model in enumerate(self.models):
                # Nastasi, K.N. Dissertation: Section 4.5 Algorithm 4.3 eq 4.9 pg 64
                self.model_likelihoods[num] = exp(-0.5 * model.nis) / sqrt(
                    (2 * const.PI) ** self.true_y.shape[0] * det(model.innov_cvr),
                )

            c = dot(self.model_likelihoods, self.mode_probabilities)
            # Check for zero model likelihoods, usually if number of models is large (~100)
            if fpe_equals(0.0, c):
                self.model_likelihoods = ones_like(self.mode_probabilities)
                c = dot(self.model_likelihoods, self.mode_probabilities)

            self.model_weights = (self.model_likelihoods * self.mode_probabilities) / c

            mix_matrix = self._constructMixMatrix()
            self.mode_probabilities = matmul(mix_matrix, self.model_weights)

        self._compileUpdateStep(observations)
        # No need to recheck maneuver detection if no obs
        if not observations:
            msg = f"Continuing GPB1 for {self.target_id} at {self.time} with {len(self.model_weights)} models"
            self.logger.debug(msg)
            return

        # Check maneuver detection to see if MMAE converged
        maneuver_gate = oneSidedChiSquareTest(
            self.nis,
            1 - self.prune_percentage,
            self.true_y.shape[0],
        )
        if maneuver_gate:
            msg = f"GPB1 converged for {self.target_id} at {self.time}"
            self.logger.info(msg)
            self._resumeSequentialFiltering()

    def _constructMixMatrix(self) -> ndarray:
        """Creating mixing Matrix."""
        mix_matrix = zeros((self.num_models, self.num_models))
        scale = 1 / (self.num_models - 1 + self.mix_ratio)
        primary = self.mix_ratio * scale

        mix_matrix = ones((self.num_models, self.num_models)) * scale
        fill_diagonal(mix_matrix, primary)

        return mix_matrix
