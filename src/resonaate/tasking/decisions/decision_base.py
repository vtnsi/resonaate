"""Abstract :class:`.Decision` base class defining the decision API."""
from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


class Decision(metaclass=ABCMeta):
    """Abstract base class to encapsulate behavior of general decision methods."""

    REGISTRY: dict[str, Decision] = {}
    """``dict``: Global decision object registry."""

    @classmethod
    def register(cls, decision: Decision) -> None:
        """Register an implemented decision class in the global registry.

        Args:
            decision (:class:`.Decision`): decision object to register

        Raises:
            TypeError: raised if not providing a valid :class:`.Decision` sub-class
        """
        if not issubclass(decision, Decision):
            raise TypeError(type(decision))

        cls.REGISTRY[decision.__name__] = decision

    @property
    def is_registered(self) -> bool:
        """``bool``: return if an implemented decision class is registered."""
        return self.__class__.__name__ in self.REGISTRY

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
