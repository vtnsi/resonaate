"""Defines the :class:`.StaticMultipleModel` class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import argwhere, exp, ones_like, sqrt
from numpy import sum as np_sum
from scipy.linalg import det

# Local Imports
from ...physics import constants as const
from ...physics.math import fpe_equals
from ...physics.statistics import oneSidedChiSquareTest
from .adaptive_filter import AdaptiveFilter

if TYPE_CHECKING:
    # Local Imports
    from ...physics.time.stardate import JulianDate
    from ...sensors.sensor_base import ObservationTuple


class StaticMultipleModel(AdaptiveFilter):
    """Static Multiple Model class.

    References:
        :cite:t:`nastasi_2018_diss`, Pg 66, Pg 68
    """

    LABELS = "smm"

    def initialize(
        self, obs_tuples: list[ObservationTuple], julian_date_start: JulianDate
    ) -> bool:
        """Initialize SMM models.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` objects associated with the filter step
            julian_date_start (:class:`.JulianDate`): julian date at the start of the scenario
            visual_cross_section (``float``): visual cross section of estimate agent, Default is 25m

        Returns:
            ``bool``: Whether or not enough observations and estimates were in the database to start MMAE
        """
        mmae_started = super().initialize(obs_tuples, julian_date_start)
        if not mmae_started:
            return False

        # Adaptive filter predict and update for each model from time t(k) -> t(k+1)
        self.predict(self.time)
        # Attempt to pre-weight if radar observations are available
        self._preWeight(obs_tuples)
        self.update(obs_tuples)

        return True

    def update(self, obs_tuples: list[ObservationTuple]):
        """Update the state estimate with observations.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` objects associated with the filter step

        References:
            #. :cite:t:`nastasi_2018_diss`, Section 2.4.4 Algorithm 2.5 eq 2.97-2.99 pg 35
            #. :cite:t:`nastasi_2018_diss`, Section 4.5 Algorithm 4.3 eq 4.9-4.14 pg 64
            #. :cite:t:`nastasi_2018_diss`, Section 4.5 Algorithm 4.4 pg 65
        """
        super().update(obs_tuples)

        if obs_tuples:
            for num, model in enumerate(self.models):
                # Nastasi, K.N. Dissertation: Section 4.5 Algorithm 4.3 eq 4.9 pg 64
                self.model_likelihoods[num] = exp(-0.5 * model.nis) / sqrt(
                    (2 * const.PI) ** self.true_y.shape[0] * det(model.innov_cvr)
                )
                # Nastasi, K.N. Dissertation: Section 4.5 Algorithm 4.3 eq 4.10 pg 64
                self.model_weights[num] = self.model_weights[num] * self.model_likelihoods[num]

            # Check for zero model likelihoods, usually if number of models is large (~100)
            if fpe_equals(0.0, np_sum(self.model_weights)):
                self.model_weights = ones_like(self.model_weights)

            # Nastasi, K.N. Dissertation: Section 4.5 Algorithm 4.3 eq 4.11 pg 64
            self.model_weights = self.model_weights / np_sum(self.model_weights)

        # Compile model data into "stacked" estimate & covariances
        self._compileUpdateStep(obs_tuples)

        # Check pruning & convergence
        if self._prunedToSingleModel(obs_tuples):
            return

        if self._convergedToSingleModel(obs_tuples):
            return

        # MMAE continues without pruning or convergeing to one model
        msg = f"Continuing SMM for {self.target_id} at {self.time} with {len(self.model_weights)} models"
        self.logger.debug(msg)

    def _prunedToSingleModel(self, obs_tuples: list[ObservationTuple]) -> bool:
        """Checks if MMAE has pruned itself to only one remaining valid model.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` objects for this filter step.

        Returns:
            ``bool``: whether the algorithm converged or not
        """
        # check if any models can be pruned
        # Nastasi, K.N. Dissertation: Section 4.5 Algorithm 4.4 pg 65
        prune_tuple = argwhere(self.model_weights < self.prune_threshold).flatten()
        if len(prune_tuple) > 0:
            self.prune(prune_tuple, obs_tuples)

        if len(self.models) == 1:
            # All, but a single model were pruned, reinitialize sequential filtering
            self._resumeSequentialFiltering()
            msg = f"SMM converged for {self.target_id} at {self.time}"
            self.logger.info(msg)
            return True

        # More than one model remains
        return False

    def _convergedToSingleModel(self, obs_tuples: list[ObservationTuple]) -> bool:
        """Checks if MMAE converged to a single model.

        More specifically it checks if a model's weight is above :attr:`.prune_percentage`. This
        occurs when the model probability mass coalesces into a single model.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` objects for this filter step.

        Returns:
            ``bool``: whether the algorithm converged or not.
        """
        # Close MMAE if likelihood of a single model is above the set percentage
        solution = argwhere(self.model_weights >= self.prune_percentage).flatten()

        if solution.size == 1:
            # Check if favored model is actually "converged" & doesn't trigger maneuver detection
            maneuver_gate = oneSidedChiSquareTest(
                self.nis, 1 - self.prune_percentage, self.true_y.shape[0]
            )
            if maneuver_gate:
                incorrect_indices = argwhere(self.model_weights < self.prune_percentage).flatten()
                self.prune(incorrect_indices, obs_tuples)
                self._resumeSequentialFiltering()
                msg = f"SMM converged for {self.target_id} at {self.time}"
                self.logger.info(msg)
                return True

        return False

    def _preWeight(self, obs_tuples: list[ObservationTuple]):
        """Weight initial models by their agreement with range rate, if possible.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` objects associated with the filter step
        """
        for obs_tuple in obs_tuples:
            sensor = obs_tuple.agent.sensors
            measured_range_rate = getattr(obs_tuple.observation, "range_rate_km_p_sec", None)
            # Attempt to predict radar observations
            if measured_range_rate:
                model_errs = []
                for model in self.models:
                    predicted_observation = sensor.buildSigmaObs(self.target_id, model.pred_x)
                    model_range_rate = predicted_observation.range_rate_km_p_sec
                    # [TODO]: Mahalanobis distance instead of direct differencing
                    model_errs.append(abs(measured_range_rate - model_range_rate))

                ## [TODO]: This overwrites model weights -> only the last obs is included
                self.model_weights = abs(1 - model_errs / sum(model_errs))
