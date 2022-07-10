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

    REGISTRY: dict[str, "Decision"] = {}
    """``dict``: Global decision object registry."""

    @classmethod
    def register(cls, name: str, decision: "Decision") -> None:
        """Register an implemented decision class in the global registry.

        Args:
            name (``str``): name to store as the key in the registry
            decision (:class:`.Decision`): decision object to register

        Raises:
            TypeError: raised if not providing a valid :class:`.Decision` sub-class
        """
        if not issubclass(decision, Decision):
            raise TypeError(type(decision))

        cls.REGISTRY[name] = decision

    @property
    def is_registered(self) -> bool:
        """``bool``: return if an implemented decision class is registered."""
        return self.__class__.__name__ in self.REGISTRY

    @abstractmethod
    def _makeDecision(self, reward_matrix: ndarray, **kwargs) -> ndarray:
        """Abstract function for making decisions based on the given reward matrix.

        Note:
            Must be overridden by implementors.

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize

        Returns:
            ``ndarray``: optimal decision set
        """
        raise NotImplementedError

    def __call__(self, reward_matrix: ndarray, **kwargs) -> ndarray:
        """Call operator '()' for decision objects.

        Args:
            reward_matrix (``ndarray``): reward matrix to optimize

        Returns:
            ``ndarray``: optimal decision set
        """
        return self._makeDecision(reward_matrix, **kwargs)
