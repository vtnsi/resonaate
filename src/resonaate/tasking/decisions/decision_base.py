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
    def calculate(self, reward_matrix: ndarray, **kwargs) -> ndarray:
        """Abstract function for making decisions based on the given reward matrix.

        Note:
            Must be overridden by implementors.

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize

        Returns:
            ``ndarray``: optimal decision set
        """
        raise NotImplementedError
