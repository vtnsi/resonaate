"""Abstract :class:`.Decision` base class defining the decision API."""
# Standard Imports
from abc import ABCMeta, abstractmethod
# Third Party Imports
# Package Imports


class Decision(metaclass=ABCMeta):
    """Abstract base class to encapsulate behavior of general decision methods."""

    REGISTRY = {}
    """Global decision object registry."""

    @classmethod
    def register(cls, name, decision):
        """Register an implemented decision class in the global registry.

        Args:
            name (str): name to store as the key in the registry
            decision (:class:`.Decision`): decision object to register

        Raises:
            TypeError: raised if not providing a valid :class:`.Decision` sub-class
        """
        if not issubclass(decision, Decision):
            raise TypeError(type(decision))

        cls.REGISTRY[name] = decision

    @property
    def is_registered(self):
        """bool: return if an implemented decision class is registered."""
        return self.__class__.__name__ in self.REGISTRY

    @abstractmethod
    def _makeDecision(self, reward_matrix, **kwargs):
        """Abstract function for making decisions based on the given reward matrix.

        Note:
            Must be overridden by implementors.

        Args:
            reward_matrix (``numpy.ndarray``): reward matrix to optimize

        Returns:
            ``numpy.ndarray``: unconstrained, optimal decision set
        """
        raise NotImplementedError

    def __call__(self, reward_matrix, **kwargs):
        """Call operator '()' for decision objects.

        Args:
            reward_matrix (``numpy.ndarray``): reward matrix to optimize

        Returns:
            ``numpy.ndarray``: constrained, optimal decision set
        """
        return self._makeDecision(reward_matrix, **kwargs)
