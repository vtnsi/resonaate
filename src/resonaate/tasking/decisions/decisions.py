# Standard Library Imports
# Third Party Imports
from numpy import argmax, zeros, where, any as np_any
from numpy.random import default_rng
from munkres import Munkres, make_cost_matrix
# RESONAATE Imports
from .decision_base import Decision


class MyopicNaiveGreedyDecision(Decision):
    """Optimizes for each sensor independently."""

    def _makeDecision(self, reward_matrix, **kwargs):
        """Select the optimal tasking for each sensor, disregarding the effect on other sensors.

        Args:
            reward_matrix (``numpy.ndarray``): reward matrix to optimize

        Returns:
            ``numpy.ndarray``: unconstrained optimal decision set
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

    def _makeDecision(self, reward_matrix, **kwargs):
        """Select optimal tasking for each sensor, constrained to "perfect matching".

        Args:
            reward_matrix (``numpy.ndarray``): reward matrix to optimize

        Returns:
            ``numpy.ndarray``: unconstrained optimal decision set
        """
        mun = Munkres()
        decision = zeros(reward_matrix.shape, dtype=bool)

        # Convert reward matrix to cost matrix, and minimize via Munkres
        indices = mun.compute(make_cost_matrix(reward_matrix, lambda x: (1e6 - x)))

        # Determine the optimal decisions
        for tgt_ind, sen_ind in indices:
            if reward_matrix[tgt_ind, sen_ind] > 0.0:
                decision[tgt_ind, sen_ind] = True

        return decision


class RandomDecision(Decision):
    """Completely random set decision-making."""

    def __init__(self, seed):
        """Override init to explicitly set the seed for randomization."""
        self._seed = default_rng(seed)

    def _makeDecision(self, reward_matrix, **kwargs):
        """Select random tasking for each sensor.

        Args:
            reward_matrix (``numpy.ndarray``): reward matrix to optimize

        Returns:
            ``numpy.ndarray``: random decision set
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

    def _makeDecision(self, reward_matrix, **kwargs):
        """Task each sensor to every available target.

        Args:
            reward_matrix (``numpy.ndarray``): reward matrix to optimize

        Returns:
            ``numpy.ndarray``: unconstrained optimal decision set
        """
        return where(reward_matrix > 0.0, True, False)
