# Standard Library Imports
# Third PArty Imports
# RESONAATE Imports
from .constellation import Constellation
from .network_base import Network
from ..agents.sensing_agent import SensingAgent


class SOSINetwork(Network):
    """SOSI Network class.

    The SOSI Network Class, which inherits/uses the Network interface superclass, defines and
    controls a network of Agent objects used to track the constellation network and estimate each
    spacecraft's state.
    """

    def __init__(self, agents):
        """Construct a SOSINetwork object.

        Args:
            agents (``list``): :class:`SensingAgent` associated with this SOSI network

        Raises:
            TypeError: raised if given node list isn't a set of :class:`.SensingAgent` objects
        """
        super(SOSINetwork, self).__init__(agents)

        # Ensure that we are only use sensing agents here
        for node in self._nodes:
            if not isinstance(node, SensingAgent):
                self._logger.error("All nodes must be a SensingAgent object")
                TypeError(type(node))

        self._tgt_list = []

    def assignTo(self, constellation):
        """Assign a target set to the SOSINetwork for estimation and tracking.

        Args:
            constellation (:class:`.Constellation`): set of :class:`.TargetAgent` to task on
        """
        if isinstance(constellation, Constellation):
            self._tgt_list = constellation.nodes
        else:
            raise TypeError('SOSINetwork: Invalid input for tgtConstellation property.')

    @property
    def tgt_list(self):
        """list(:class:`.TargetAgent`): Return the list of this SOSINetwork object's targets."""
        return self._tgt_list

    @classmethod
    def fromDict(cls, clock, ssn_dict, rso_dynamics, realtime=False):
        """Instantiate a SSN object from a dictionary.

        Args:
            clock (:class:`.ScenarioClock`): common clock object
            ssn_dict (``dict``): describes the SOSI network specification
            rso_dynamics (:class:`.Dynamics`): baseline satellite dynamics used for space-based
                :class:`.SensingAgent`
            realtime (``bool``, optional): whether to propagate or import space-based
                :class:`.SensingAgent` objects dynamics. Defaults to `False`.

        Returns:
            :class:`.SOSINetwork`: constructed SOSI Network from the dictionary specification
        """
        sensor_agent_list = []
        for agent in ssn_dict:
            config = {
                "agent": agent,
                "clock": clock,
                "satellite_dynamics": rso_dynamics,
                "realtime": realtime
            }

            sensor_agent_list.append(
                SensingAgent.fromConfig(config, events=[])
            )

        return cls(sensor_agent_list)
