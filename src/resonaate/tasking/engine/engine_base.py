# Standard Library Imports
from logging import getLogger
from abc import ABCMeta, abstractmethod
# RESONAATE Imports
from ...data.importer_database import ImporterDatabase
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

        # List of transient observations (current timestep only)
        self._observations = []
        # List of observations saved internally. Cleared on calls to `getCurrentObservations()`
        self._saved_observations = []

        # Input database object for loading `Observation` objects
        self._importer_db = None

    def assess(self, julian_date, importer_db_path=None):
        """Perform desired analysis on the current simulation state.

        First, the rewards for all possible tasks are computed, then the engine optimizes
        tasking based on the reward matrix. Finally, the optimized tasking strategy is
        applied, observations are collected, and the estimate agents are updated.

        Args:
            julian_date (:class:`.JulianDate`): epoch at which to task sensors
            importer_db_path (``str``, optional): path to external importer database for pre-canned
                data. Defaults to ``None``.
        """
        self._observations = []

        # Load importer DB if not loaded
        if importer_db_path and self._importer_db is None:
            self._importer_db = ImporterDatabase.getSharedInterface(db_url=importer_db_path)

        self.constructRewardMatrix()
        self.generateTasking()
        self.executeTasking(julian_date)

        tasked_sensors = set()
        observed_targets = set()
        for cur_ob in self._observations:
            tasked_sensors.add(cur_ob.sensor_id)
            observed_targets.add(cur_ob.target_id)

        msg = f"{self.__class__.__name__} produced {len(self._observations)} observations by tasking "
        msg += f"{len(tasked_sensors)} sensors {tasked_sensors} on {len(observed_targets)} targets {observed_targets}"
        self.logger.info(msg)

    def saveObservations(self, observations):
        """Save set of observations.

        Args:
            observations (list): List of observations to save.
        """
        self._observations.extend(observations)
        self._saved_observations.extend(observations)

    def getCurrentObservations(self):
        """Retrieve current list of observations saved internally & reset it."""
        observations = self._saved_observations
        self._saved_observations = []

        return observations

    @abstractmethod
    def constructRewardMatrix(self):
        """Determine the visibility & reward matrices for the current step k."""
        raise NotImplementedError

    @abstractmethod
    def executeTasking(self, julian_date):
        """Collect tasked observations, if they exist, based on the decision matrix.

        Collected observations are applied to each corresponding estimate agent's filter.

        Args:
            julian_date (:class:`.JulianDate`): epoch at which to task sensors
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

    @property
    def observations(self):
        """``list``: Returns the :class:`.Observation`s for the previous timestep."""
        return self._observations
