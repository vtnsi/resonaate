# Standard Library Imports
from logging import getLogger
from abc import ABCMeta, abstractmethod
# RESONAATE Imports
from ..decisions.decision_base import Decision
from ..rewards.reward_base import Reward


class TaskingEngine(metaclass=ABCMeta):
    """Tasking Engine abstract base class.

    This class provides the framework and behavior for the command & control node of a network or agent.
    """

    def __init__(self, sensor_nums, target_nums, reward, decision, seed=None):
        """Construct a TaskingEngine object.

        Args:
            clock (:class:`.ScenarioClock`): clock for tracking time
            sensor_nums (:class:`.List`): list of sensor agents
            target_nums (:class: `.List`): list of target agents
            reward (:class:`.Reward`): callable reward object for determining tasking priority
            decision (:class:`.Decision`): callable decision object for optimizing tasking
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

        # Save default values as None for important matrices
        self.reward_matrix = None
        self.decision_matrix = None
        self.visibility_matrix = None

        # Save class variables
        self.target_list = target_nums
        self.sensor_list = sensor_nums

    @abstractmethod
    def assess(self, julian_date):
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
    def getCurrentTasking(self, julian_date):
        """Return database information of current tasking.

        Must be overridden by implemented classes.
        """
        raise NotImplementedError

    @property
    def num_targets(self):
        """int: number of targets."""
        return len(self.target_list)

    @property
    def num_sensors(self):
        """int: number of sensors."""
        return len(self.sensor_list)
