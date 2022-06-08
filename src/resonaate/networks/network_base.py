# Standard Library Imports
from logging import getLogger
# Third Party Imports
# RESONAATE Imports
from ..agents.agent_base import Agent


class Network:
    """Network base class.

    The Network class gives a general foundation for any type of network in the scenario
    (e.g. Constellation or SOSI Network). A network is a container for a set of similar
    :class:`.Agent` sub-classes.
    """

    def __init__(self, nodes):
        """Construct Network object with a list of nodes.

        Args:
            nodes (list(:class:`.Agent`)): nodes to add to the Network

        Raises:
            TypeError: raised if given node list isn't a set of :class:`.Agent` objects
        """
        self._logger = getLogger("resonaate")

        # Check all the nodes' types
        for node in nodes:
            if not isinstance(node, Agent):
                self._logger.error("All nodes in a network must be an `Agent` object.")
                raise TypeError(type(node))

        # Save the nodes into a class variable
        if isinstance(nodes, list):
            self._nodes = nodes
        elif isinstance(nodes, Agent):
            self._nodes = list(nodes)

    def __iter__(self):
        """Define how iterating over a network works.

        This makes it so that a user can call `for node in constellation: doStuff(node)`
        rather than have to subvert abstraction and call `for node in constellation.nodes: doStuff(node)`

        Yields:
            :class:`.Agent`: yields each Agent node in the :meth:`~.nodes` attribute
        """
        for node in self._nodes:
            yield node

    def addNodes(self, new_nodes):
        """Append the input set of Agent objects to the nodes property.

        Args:
            new_nodes (list(:class:`.Agent`)): Nx1 or 1xN array of Agent objects
        """
        if isinstance(new_nodes, list):
            for node in new_nodes:
                if not isinstance(node, Agent):
                    self._logger.error("All nodes in a network must be an `Agent` object.")
                    raise TypeError(type(node))
            self._nodes.extend(new_nodes)
        elif isinstance(new_nodes, Agent):
            self._nodes.append(new_nodes)
        else:
            self._logger.error("Network::addNodes() takes either an `Agent` object or list(`Agent`")
            raise TypeError(type(new_nodes))

    def deleteNode(self, name):
        """Delete the specified node from the list of nodes while maintaining the order.

        Args:
            name (str): Specifies the name of the node to be deleted
        """
        for agent in self._nodes:
            if agent.name == name:
                self._nodes.remove(agent)
                return True

        self._logger.warning("Could not find the node to be deleted: {0}".format(name))
        return False

    def reset(self, clock):
        """Reset all of the nodes in this network."""
        self._logger.info("Network reset to time: {0}",format(clock.julian_date_epoch))
        for node in self._nodes:
            node.reset(clock)

    @property
    def nodes(self):
        """list(:class:`.Agent`): Return the Network object's list of nodes."""
        return self._nodes
