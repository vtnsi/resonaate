"""Abstract :class:`.Tasking` base class defining the tasking engine API."""
# Standard Library Imports
from logging import getLogger
from abc import ABCMeta, abstractmethod
# Third Party Imports
from numpy import zeros
# RESONAATE Imports
from ..decisions.decision_base import Decision
from ..rewards.reward_base import Reward
from ...data.importer_database import ImporterDatabase


class TaskingEngine(metaclass=ABCMeta):
    """Abstract base class defining common API for tasking engines.

    This class provides the framework and behavior for the command & control of a network or agent.
    """

    def __init__(self, engine_id, sensor_ids, target_ids, reward, decision, importer_db_path=None):
        """Initialize a tasking engine object.

        Args:
            engine_id (int): Unique ID for this :class:`.TaskingEngine`
            sensor_ids (``list``): list of sensor agent ID numbers
            target_ids (``list``): list of target agent ID numbers
            reward (:class:`.Reward`): callable reward object for determining tasking priority
            decision (:class:`.Decision`): callable decision object for optimizing tasking
            importer_db_path (``str``, optional): path to external importer database for pre-canned
                data. Defaults to ``None``.

        Raises:
            TypeError: raised if invalid reward parameter passed
            TypeError: raised if invalid decision parameter passed
        """
        self.logger = getLogger("resonaate")

        self._unique_id = engine_id

        if not isinstance(reward, Reward):
            raise TypeError("Engine constructor requires an instantiated `Reward` object.")
        if not isinstance(decision, Decision):
            raise TypeError("Engine constructor requires an instantiated `Decision` object.")

        self._reward = reward
        """:class:`.Reward`: callable that determines tasking priority based on various metric."""
        self._decision = decision
        """:class:`.Decision`: callable that optimizes tasking based on :attr:`.reward_matrix`."""

        self.target_list = target_ids
        """``list``: target agent ID numbers."""
        self.sensor_list = sensor_ids
        """``list``: sensor agent ID numbers."""

        self.reward_matrix = zeros((self.num_targets, self.num_sensors), dtype=float)
        """``numpy.ndarray``: NxM array defining the tasking reward for every target/sensor pair."""
        self.decision_matrix = zeros((self.num_targets, self.num_sensors), dtype=bool)
        """``numpy.ndarray``: NxM array defining the tasking decision for every target/sensor pair."""
        self.visibility_matrix = zeros((self.num_targets, self.num_sensors), dtype=bool)
        """``numpy.ndarray``: NxM array defining the visibility condition for every target/sensor pair."""

        self.target_indices = {target_id: index for index, target_id in enumerate(self.target_list)}

        # List of transient observations (current timestep only)
        self._observations = []
        """``list``: transient :class:`.Observation` tasked & saved by this engine during the current timestep."""
        self._saved_observations = []
        """``list``: transient :class:`.Observation` tasked & saved by this engine not loaded to the DB."""

        self._importer_db = None
        """:class:`.ImporterDatabase`: Input database object for loading :class:`.Observation` objects."""
        if importer_db_path:
            self._importer_db = ImporterDatabase.getSharedInterface(db_path=importer_db_path)

    def addTarget(self, target_id):
        """Add a target to this :class:`.TaskingEngine`.

        Args:
            target_id (int): Unique identifier for the target being added.
        """
        self.target_indices[target_id] = len(self.target_list)
        self.target_list.append(target_id)

    def removeTarget(self, target_id):
        """Remove a target from this :class:`.TaskingEngine`.

        Args:
            target_id (int): Unique identifier for the target being removed.
        """
        del self.target_indices[target_id]
        self.target_list.remove(target_id)

    def addSensor(self, sensor_id):
        """Add a sensor to this :class:`.TaskingEngine`.

        Args:
            sensor_id (int): Unique identifier for the sensor being added.
        """
        self.sensor_list.append(sensor_id)

    def removeSensor(self, sensor_id):
        """Remove a sensor from this :class:`.TaskingEngine`.

        Args:
            sensor_id (int): Unique identifier for the sensor being removed.
        """
        self.sensor_list.remove(sensor_id)

    def saveObservations(self, observations):
        """Save set of :class:`.Observation` objects to transient lists.

        Args:
            observations (``list``): :class:`.Observation` to save.
        """
        self._observations.extend(observations)
        self._saved_observations.extend(observations)

    def getCurrentObservations(self):
        """``list``: Returns current list of observations saved internally & resets transient list."""
        observations = self._saved_observations
        self._saved_observations = []

        return observations

    def retaskSensors(self, new_target_nums):
        """Update the set of target agents, usually after a target is added/removed.

        Args:
            new_target_nums (``list``): ID numbers of new targets to task against.
        """
        self.target_list = new_target_nums

    @abstractmethod
    def assess(self, julian_date):
        """Perform a set of analysis operations on the current simulation state.

        Must be overridden by implemented classes.

        Args:
            julian_date (:class:`.JulianDate`): epoch at which to perform analysis
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
        """Return current tasking solution.

        Must be overridden by implemented classes.

        Args:
            julian_date (:class:`.JulianDate`): epoch at which to retrieve tasking solution

        Yields:
            :class:`.Task`: tasking DB object for each target/sensor pair
        """
        raise NotImplementedError

    @property
    def reward(self):
        """:class:`.Reward`: Returns the tasking engine's reward function."""
        return self._reward

    @property
    def decision(self):
        """:class:`.Decision`: Returns the tasking engine's decision function."""
        return self._decision

    @property
    def unique_id(self):
        """int: Unique identifier for this :class:`.TaskingEngine`."""
        return self._unique_id

    @property
    def num_targets(self):
        """``int``: Returns the number of targets."""
        return len(self.target_list)

    @property
    def num_sensors(self):
        """``int``: Returns the number of sensors."""
        return len(self.sensor_list)

    @property
    def observations(self):
        """``list``: Returns the :class:`.Observation` objects for the previous timestep."""
        return self._observations
