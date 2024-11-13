"""Abstract :class:`.Decision` base class defining the decision API."""

from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...scenario.config.decision_config import DecisionConfig


class Decision(metaclass=ABCMeta):
    """Abstract base class to encapsulate behavior of general decision methods."""

    @classmethod
    def fromConfig(cls, config: DecisionConfig) -> Decision:  # noqa: ARG003
        """Construct the decision-making class specified by `config`.

        Args:
            config (:class:`.DecisionConfig`): Specify configuration parameters for this decision-
                making class.

        Returns:
            (:class:`.Decision`): Decision-making class specified by `config`.
        """
        return cls()

    @abstractmethod
    def _calculate(self, reward_matrix: ndarray, visibility_matrix: ndarray) -> ndarray:
        """Abstract function for making decisions based on the reward and visibility matrices.

        Note:
            Must be overridden by implementers.

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize
            visibility_matrix (``ndarray``): visibility matrix to optimize

        Returns:
            ``ndarray``: decision set
        """
        raise NotImplementedError

    def calculate(self, reward_matrix: ndarray, visibility_matrix: ndarray) -> ndarray:
        """Public method for calculating the decision matrix.

        Calls the implemented :meth:`.Decision._calculate()` method, then ANDs with visibility matrix.

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize
            visibility_matrix (``ndarray``): visibility matrix to optimize

        Returns:
            ``ndarray``: decision set
        """
        decision_matrix = self._calculate(reward_matrix, visibility_matrix)
        return decision_matrix & visibility_matrix
