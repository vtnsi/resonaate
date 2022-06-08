# Standard Library Imports
from logging import getLogger
from abc import ABCMeta, abstractmethod
# Third Party Imports
from numpy.random import default_rng
# RESONAATE Imports
from ..decisions.decision_base import Decision
from ..rewards.reward_base import Reward
from ...agents.estimate_agent import EstimateAgent


class TaskingEngine(metaclass=ABCMeta):
    """Tasking Engine abstract base class.

    This class provides the framework and behavior for the command & control node of a network or agent.
    """

    def __init__(self, clock, sosi_network, filter_config, reward, decision, estimate_error, seed=None):
        """Construct a TaskingEngine object.

        Args:
            clock (:class:`.ScenarioClock`): clock for tracking time
            sosi_network (:class:`.SOSINetwork`): network of sensor agents
            filter_config (dict): config for the nominal filter object for tracking target agents
            reward (:class:`.Reward`): callable reward object for determining tasking priority
            decision (:class:`.Decision`): callable decision object for optimizing tasking
            estimate_error (float): variance used to generate uncertain initial estimate positions
            seed (int, optional): number to seed random number generator. Defaults to ``None``.

        Raises:
            TypeError: raised if invalid :class:`.Reward` object
            TypeError: raised if invalid :class:`.Decision` object
        """
        # Get logger for the class
        self.logger = getLogger("resonaate")
        if not isinstance(reward, Reward):
            raise TypeError("Engine constructor requires an instantiated `Reward` object.")
        if not isinstance(decision, Decision):
            raise TypeError("Engine constructor requires an instantiated `Decision` object.")
        self._reward = reward
        self._decision = decision

        if not isinstance(seed, int) and seed is not None:
            self.logger.error("Incorrect type for seed param")
            raise TypeError(type(seed))
        # Save the random number generator for generating noise
        self._rng = default_rng(seed)

        # Save default values as None for important matrices
        self.reward_matrix = None
        self.decision_matrix = None
        self.visibility_matrix = None

        # Save class variables
        self._target_agents = {target.simulation_id: target for target in sosi_network.tgt_list}
        self._sensor_agents = {node.name: node for node in sosi_network}
        self.num_sensors = len(self.sensor_list)
        self.num_targets = len(self.target_list)

        # Add Estimates to the CentralTaskingEngine object
        self._estimate_agents = {}
        for target in self.target_list:
            config = {
                "target": target,
                "init_estimate_error": estimate_error,
                "rng": self._rng,
                "clock": clock,
                "filter": filter_config,
                "seed": seed
            }
            self._estimate_agents[target.simulation_id] = EstimateAgent.fromConfig(config, events=[])

    @abstractmethod
    def assess(self):
        """Perform desired analysis on the current simulation state.

        Must be overridden by implemented classes.
        """
        raise NotImplementedError

    @abstractmethod
    def generateTasking(self):
        """Create tasking solution based on the current simulation state.

        Must be overridden by implemented classes.
        """
        raise NotImplementedError

    @abstractmethod
    def getCurrentTasking(self):
        """Return database information of current tasking.

        Must be overridden by implemented classes.
        """
        raise NotImplementedError

    @property
    def sensor_agents(self):
        """dict: sensor agents indexed by their unique id."""
        return self._sensor_agents

    @property
    def sensor_list(self):
        """list: current sensor agent list."""
        return list(self._sensor_agents.values())

    @property
    def target_agents(self):
        """dict: target agents indexed by their unique id."""
        return self._target_agents

    @property
    def target_list(self):
        """list: current target agent list."""
        return list(self._target_agents.values())

    @property
    def estimate_agents(self):
        """dict: estimate agents indexed by their unique id."""
        return self._estimate_agents

    @property
    def estimate_list(self):
        """list: current estimate agent list."""
        return list(self._estimate_agents.values())
