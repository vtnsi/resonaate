"""Abstract :class:`.Tasking` base class defining the tasking engine API."""

from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from logging import getLogger
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import zeros

# Local Imports
from ...data import getDBConnection
from ...data.importer_database import ImporterDatabase
from ..decisions.decision_base import Decision
from ..rewards.reward_base import Reward

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from datetime import datetime

    # Local Imports
    from ...data.observation import MissedObservation, Observation
    from ...data.task import Task
    from ...physics.time.stardate import JulianDate


class TaskingEngine(metaclass=ABCMeta):
    """Abstract base class defining common API for tasking engines.

    This class provides the framework and behavior for the command & control of a network or agent.
    """

    def __init__(
        self,
        engine_id: int,
        sensor_ids: list[int],
        target_ids: list[int],
        reward: Reward,
        decision: Decision,
        importer_db_path: str | None = None,
    ):
        """Initialize a tasking engine object.

        Args:
            engine_id (``int``): Unique ID for this :class:`.TaskingEngine`
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

        self.sensor_list = sorted(sensor_ids)
        """``list``: sorted sensor agent ID numbers."""

        self.sensor_indices: dict[int, int] = {}
        """``dict``: mapping of sorted sensor agent ID numbers to indices in :attr:`.sensor_list`."""

        self.target_list = sorted(target_ids)
        """``list``: sorted target agent ID numbers."""

        self.target_indices: dict[int, int] = {}
        """``dict``: mapping of sorted target agent ID numbers to indices in :attr:`.target_list`."""

        self._reward = reward
        """:class:`.Reward`: callable that determines tasking priority based on various metric."""
        self._decision = decision
        """:class:`.Decision`: callable that optimizes tasking based on :attr:`.reward_matrix`."""

        # Sort sensors & targets - also creates index mappings
        self._sortSensors()
        self._sortTargets()

        self.reward_matrix = zeros((self.num_targets, self.num_sensors), dtype=float)
        """``ndarray``: NxM array defining the tasking reward for every target/sensor pair."""
        self.decision_matrix = zeros((self.num_targets, self.num_sensors), dtype=bool)
        """``ndarray``: NxM array defining the tasking decision for every target/sensor pair."""
        self.visibility_matrix = zeros((self.num_targets, self.num_sensors), dtype=bool)
        """``ndarray``: NxM array defining the visibility condition for every target/sensor pair."""
        self.metric_matrix = zeros(
            (self.num_targets, self.num_sensors, self.num_metrics),
            dtype=float,
        )
        """``ndarray``: NxMxP array defining the metrics for every target/sensor pair."""

        # List of transient observations (current timestep only)
        self._observations: list[Observation] = []
        """``list``: transient :class:`.Observation` tasked & saved by this engine during the current timestep."""
        self._saved_observations: list[Observation] = []
        """``list``: transient :class:`.Observation` tasked & saved by this engine not loaded to the DB."""
        self._missed_observations: list[MissedObservation] = []
        """``list``: transient :class:`.MissedObservation` tasked & saved by this engine during the current timestep."""
        self._saved_missed_observations: list[MissedObservation] = []
        """``list``: transient :class:`.MissedObservation` tasked & saved by this engine not loaded to the DB."""

        self.sensor_changes = {}

        self._database = getDBConnection()
        """:class:`.ResonaateDatabase`: shared instance of simulation database."""

        self._importer_db: ImporterDatabase | None = None
        """:class:`.ImporterDatabase`: Input database object for loading :class:`.Observation` objects."""
        if importer_db_path:
            self._importer_db = ImporterDatabase(db_path=importer_db_path)

        self.resetHandles()

    def resetHandles(self):
        """Clear object store agent handles."""
        self._target_store = {}
        self._sensor_store = {}
        self._estimate_store = {}

    def setHandles(self, target_store: dict, sensor_store: dict, estimate_store: dict):
        """Set the object store agent handles.

        Args:
            target_store: Dictionary mapping target identifiers to the relevant object store agent
                handle.
            sensor_store: Dictionary mapping sensor identifiers to the relevant object store agent
                handle.
            estimate_store: Dictionary mapping estimate identifiers to the relevant object store
                agent handle.
        """
        self._target_store = target_store
        self._sensor_store = sensor_store
        self._estimate_store = estimate_store

    def addTarget(self, target_id: int) -> None:
        """Add a target to this :class:`.TaskingEngine`.

        Args:
            target_id (``int``): Unique identifier for the target being added.
        """
        self.target_list.append(target_id)
        self._sortTargets()

    def removeTarget(self, target_id: int) -> None:
        """Remove a target from this :class:`.TaskingEngine`.

        Args:
            target_id (``int``): Unique identifier for the target being removed.
        """
        self.target_list.remove(target_id)
        self._sortTargets()

    def addSensor(self, sensor_id: int) -> None:
        """Add a sensor to this :class:`.TaskingEngine`.

        Args:
            sensor_id (``int``): Unique identifier for the sensor being added.
        """
        self.sensor_list.append(sensor_id)
        self._sortSensors()

    def removeSensor(self, sensor_id: int) -> None:
        """Remove a sensor from this :class:`.TaskingEngine`.

        Args:
            sensor_id (``int``): Unique identifier for the sensor being removed.
        """
        self.sensor_list.remove(sensor_id)
        self._sortSensors()

    def saveObservations(self, observations: list[Observation]) -> None:
        """Save set of :class:`.Observation` objects to transient lists.

        Args:
            observations (``list``): :class:`.Observation` to save.
        """
        self._observations.extend(observations)
        self._saved_observations.extend(observations)

    def getCurrentObservations(self) -> list[Observation]:
        """``list``: Returns current list of observations saved internally & resets transient list."""
        observations = self._saved_observations
        self._saved_observations = []

        return observations

    def saveMissedObservations(self, missed_observations: list[MissedObservation]) -> None:
        """Save set of :class:`.MissedObservation` objects to transient lists.

        Args:
            missed_observations (``list``): :class:`.MissedObservation` to save
        """
        for miss in missed_observations:
            if miss:
                self._missed_observations.extend(missed_observations)
                self._saved_missed_observations.extend(missed_observations)

    def updateFromAsyncTaskExecution(self, sensor_info_list: list) -> None:
        """Save Changes to sensor as a result of tasking.

        Args:
            sensor_info_list (list): list of dict
        """
        self.sensor_changes = {}
        for sensor_info in sensor_info_list:
            self.sensor_changes[sensor_info["sensor_id"]] = {
                "boresight": sensor_info["boresight"],
                "time_last_tasked": sensor_info["time_last_tasked"],
            }

    def getCurrentMissedObservations(self) -> list[Observation]:
        """``list``: Returns current list of :class:`.MissedObservation` saved internally & resets transient list."""
        missed_observations = self._saved_missed_observations
        self._saved_missed_observations = []

        return missed_observations

    @abstractmethod
    def assess(self, prior_datetime_epoch: datetime, datetime_epoch: datetime) -> None:
        """Perform a set of analysis operations on the current simulation state.

        Must be overridden by implemented classes.

        Args:
            prior_datetime_epoch (datetime): previous epoch
            datetime_epoch (datetime): epoch at which to perform analysis
        """
        raise NotImplementedError

    @abstractmethod
    def generateTasking(self) -> None:
        """Create tasking solution based on the current simulation state.

        Must be overridden by implemented classes.
        """
        raise NotImplementedError

    @abstractmethod
    def getCurrentTasking(self, julian_date: JulianDate) -> Task:
        """Return current tasking solution.

        Must be overridden by implemented classes.

        Args:
            julian_date (:class:`.JulianDate`): epoch at which to retrieve tasking solution

        Yields:
            :class:`.Task`: tasking DB object for each target/sensor pair
        """
        raise NotImplementedError

    def _sortTargets(self) -> None:
        """Sort target list & index mapping, for use after adding/removing target(s)."""
        self.target_list.sort()
        self.target_indices = {_id: idx for idx, _id in enumerate(self.target_list)}

    def _sortSensors(self) -> None:
        """Sort sensor list & index mapping, for use after adding/removing sensor(s)."""
        self.sensor_list.sort()
        self.sensor_indices = {_id: idx for idx, _id in enumerate(self.sensor_list)}

    @property
    def num_metrics(self):
        """``int``: Returns the number of metrics."""
        return len(self.reward.metrics)

    @property
    def reward(self) -> Reward:
        """:class:`.Reward`: Returns the tasking engine's reward function."""
        return self._reward

    @property
    def decision(self) -> Decision:
        """:class:`.Decision`: Returns the tasking engine's decision function."""
        return self._decision

    @property
    def unique_id(self) -> int:
        """int: Unique identifier for this :class:`.TaskingEngine`."""
        return self._unique_id

    @property
    def num_targets(self) -> int:
        """``int``: Returns the number of targets."""
        return len(self.target_list)

    @property
    def num_sensors(self) -> int:
        """``int``: Returns the number of sensors."""
        return len(self.sensor_list)

    @property
    def observations(self) -> list[Observation]:
        """``list``: Returns the :class:`.Observation` objects for the previous timestep."""
        return self._observations

    @property
    def missed_observations(self) -> list[MissedObservation]:
        """``list``: Returns the :class:`.MissedObservation` objects for the previous timestep."""
        return self._missed_observations
