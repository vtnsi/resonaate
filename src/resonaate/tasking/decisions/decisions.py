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

    # Local Imports
    from ...scenario.config.decision_config import DecisionConfig


class MyopicNaiveGreedyDecision(Decision):
    """Optimizes for each sensor independently.

    References:
        #. :cite:t:`nastasi_2018_diss`
        #. :cite:t:`krishnamurthy_2016`
    """

    def _calculate(self, reward_matrix: ndarray, visibility_matrix: ndarray) -> ndarray:
        """Select the optimal tasking for each sensor, disregarding the effect on other sensors.

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize
            visibility_matrix (``ndarray``): visibility matrix to optimize

        Returns:
            ``ndarray``: optimal decision set
        """
        decision_matrix = zeros(reward_matrix.shape, dtype=bool)
        for sen_ind in range(reward_matrix.shape[1]):
            # Retrieve the current `Sensor` object's tasking reward_matrix
            tgt_ind = argmax(reward_matrix[:, sen_ind])
            decision_matrix[tgt_ind, sen_ind] = True

        return decision_matrix


class MunkresDecision(Decision):
    """Optimizes the reward matrix as a bipartite graph using the Hungarian algorithm.

    References:
        :cite:t:`crouse_taes_2016_assignment`
    """

    def _calculate(self, reward_matrix: ndarray, visibility_matrix: ndarray) -> ndarray:
        """Select optimal tasking for each sensor, constrained to "perfect matching".

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize
            visibility_matrix (``ndarray``): visibility matrix to optimize

        Returns:
            ``ndarray``: optimal decision set
        """
        decision_matrix = zeros(reward_matrix.shape, dtype=bool)

        # Solve reward matrix as a bipartite graph using the Hungarian algorithm
        tgt_indices, sen_indices = linear_sum_assignment(reward_matrix, maximize=True)
        for tgt_ind, sen_ind in zip(tgt_indices, sen_indices):
            decision_matrix[tgt_ind, sen_ind] = True

        return decision_matrix


class RandomDecision(Decision):
    """Completely random set decision-making."""

    def __init__(self, seed: int | None = None):
        """Create :class:`.RandomDecision` object with an RNG seed.

        Args:
            seed (``int`` | ``None``): RNG seed value.
        """
        self._seed = default_rng(seed)

    @classmethod
    def fromConfig(cls, config: DecisionConfig) -> Decision:
        """Construct the decision-making class specified by `config`.

        Args:
            config (:class:`.DecisionConfig`): Specify configuration parameters for this decision-
                making class.

        Returns:
            (:class:`.Decision`): Decision-making class specified by `config`.
        """
        return cls(seed=config.seed)

    def _calculate(self, reward_matrix: ndarray, visibility_matrix: ndarray) -> ndarray:
        """Select random tasking for each sensor.

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize
            visibility_matrix (``ndarray``): visibility matrix to optimize

        Returns:
            ``ndarray``: random decision set
        """
        decision_matrix = zeros(visibility_matrix.shape, dtype=bool)

        # Randomly samples over the target indices, and applies one target per sensor
        for sen_ind in range(visibility_matrix.shape[1]):
            if np_any(visibility_matrix[:, sen_ind]):
                tgt_ind = self._seed.choice(visibility_matrix[:, sen_ind].nonzero()[0], 1)
                decision_matrix[tgt_ind, sen_ind] = True

        return decision_matrix


class AllVisibleDecision(Decision):
    """Optimizes for each sensor independently and tasks all AllVisibleDecision options."""

    def _calculate(self, reward_matrix: ndarray, visibility_matrix: ndarray) -> ndarray:
        """Task each sensor to every visible target.

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize
            visibility_matrix (``ndarray``): visibility matrix to optimize

        Returns:
            ``ndarray``: decision set of all visible targets
        """
        return where(visibility_matrix > 0.0, True, False)
