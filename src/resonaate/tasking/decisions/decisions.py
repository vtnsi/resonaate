"""Define implemented decision algorithms used to optimize tasked sensors."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import any as np_any
from numpy import argmax, where, zeros
from numpy.random import default_rng
from scipy.optimize import linear_sum_assignment

# Local Imports
from .decision_base import Decision

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


class MyopicNaiveGreedyDecision(Decision):
    """Optimizes for each sensor independently."""

    def _makeDecision(self, reward_matrix: ndarray, **kwargs) -> ndarray:
        """Select the optimal tasking for each sensor, disregarding the effect on other sensors.

        References:
            #. :cite:t:`nastasi_2018_diss`
            #. :cite:t:`krishnamurthy_2016`

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize

        Returns:
            ``ndarray``: optimal decision set
        """
        decision = zeros(reward_matrix.shape, dtype=bool)
        for sen_ind in range(reward_matrix.shape[1]):
            # Retrieve the current `Sensor` object's tasking reward_matrix
            tgt_ind = argmax(reward_matrix[:, sen_ind])
            # Ensure we have a unique max value
            if reward_matrix[tgt_ind, sen_ind] > 0.0:
                decision[tgt_ind, sen_ind] = True

        return decision


class MunkresDecision(Decision):
    """Optimizes the reward matrix as a bipartite graph using the Hungarian algorithm."""

    def _makeDecision(self, reward_matrix: ndarray, **kwargs) -> ndarray:
        """Select optimal tasking for each sensor, constrained to "perfect matching".

        References:
            :cite:t:`crouse_taes_2016_assignment`

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize

        Returns:
            ``ndarray``: optimal decision set
        """
        decision = zeros(reward_matrix.shape, dtype=bool)

        # Solve reward matrix as a bipartite graph using the Hungarian algorithm
        tgt_indices, sen_indices = linear_sum_assignment(reward_matrix, maximize=True)
        for tgt_ind, sen_ind in zip(tgt_indices, sen_indices):
            # Ensure we are only assigning capable pairs
            if reward_matrix[tgt_ind, sen_ind] > 0.0:
                decision[tgt_ind, sen_ind] = True

        return decision


class RandomDecision(Decision):
    """Completely random set decision-making."""

    def __init__(self, seed: int | None = None):
        """Create :class:`.RandomDecision` object with an RNG seed.

        Args:
            seed (``int`` | ``None``): RNG seed value.
        """
        self._seed = default_rng(seed)

    def _makeDecision(self, reward_matrix: ndarray, **kwargs) -> ndarray:
        """Select random tasking for each sensor.

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize

        Returns:
            ``ndarray``: random decision set
        """
        decision = zeros(reward_matrix.shape, dtype=bool)

        # Randomly samples over the target indices, and applies one target per sensor
        for sen_ind in range(reward_matrix.shape[1]):
            if np_any(reward_matrix[:, sen_ind]):
                tgt_ind = self._seed.choice(reward_matrix[:, sen_ind].nonzero()[0], 1)
                decision[tgt_ind, sen_ind] = True

        return decision


class AllVisibleDecision(Decision):
    """Optimizes for each sensor independently and tasks all AllVisibleDecision options."""

    def _makeDecision(self, reward_matrix: ndarray, **kwargs) -> ndarray:
        """Task each sensor to every available target.

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize

        Returns:
            ``ndarray``: decision set of all visible targets
        """
        return where(reward_matrix > 0.0, True, False)
