# Standard Library Imports
# Third Party Imports
# RESONAATE Imports
from .network_base import Network
from ..agents.target_agent import TargetAgent


class Constellation(Network):
    """Constellation network class.

    The Constellation class provides the framework to instantiate and control networks of
    maneuvering spacecraft.
    """

    def __init__(self, nodes):
        """Construct a Constellation object.

        Args:
            nodes (list(:class:`.TargetAgent`)): objects to include in the constellation

        Raises:
            TypeError: raised if given node list isn't a set of :class:`.TargetAgent` objects
        """
        super(Constellation, self).__init__(nodes)

        for node in nodes:
            if not isinstance(node, TargetAgent):
                self._logger.error("All nodes must be a TargetAgent object")
                TypeError(type(node))
