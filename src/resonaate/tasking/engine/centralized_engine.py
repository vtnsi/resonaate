"""Defines the :class:`.CentralizedTaskingEngine` class."""
from __future__ import annotations

# Standard Library Imports
from pickle import loads
from typing import TYPE_CHECKING

# Third Party Imports
from mjolnir import KeyValueStore
from numpy import zeros
from sqlalchemy.orm import Query

# Local Imports
from ...data.epoch import Epoch
from ...data.events import EventScope, handleRelevantEvents
from ...data.observation import Observation
from ...data.resonaate_database import ResonaateDatabase
from ...data.task import Task
from ...job_handlers.base import ParallelMixin
from ...job_handlers.task_execution import TaskExecutionJobHandler
from ...job_handlers.task_prediction import TaskPredictionJobHandler
from ...physics.time.stardate import datetimeToJulianDate
from ...sensors.sensor_base import ObservationTuple
from .engine_base import TaskingEngine

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from datetime import datetime

    # Local Imports
    from ...agents.sensing_agent import SensingAgent
    from ...physics.time.stardate import JulianDate
    from ..decisions import Decision
    from ..rewards import Reward


class CentralizedTaskingEngine(ParallelMixin, TaskingEngine):
    """Centralized implementation of a tasking engine.

    This class provides methods for centralized network tasking processes. In a centralized
    scenario, a central process is used to collect & incorporate observations directly from nodes.
    The nodes themselves perform only a minimal amount of processing, if any at all.
    """

    def __init__(
        self,
        engine_id: int,
        sensor_ids: list[int],
        target_ids: list[int],
        reward: Reward,
        decision: Decision,
        importer_db_path: str | None,
        realtime_obs: bool,
    ) -> None:
        """Initialize a centralized tasking engine.

        Args:
            engine_id (``int``): Unique ID for this :class:`.TaskingEngine`
            sensor_ids (``list``): list of sensor agent ID numbers
            target_ids (``list``): list of target agent ID numbers
            reward (:class:`.Reward`): callable reward object for determining tasking priority
            decision (:class:`.Decision`): callable decision object for optimizing tasking
            importer_db_path (``str`` | ``None``): path to external importer database for pre-canned data.
            realtime_obs (``bool``): whether to execute realtime observations
        """
        super().__init__(
            engine_id, sensor_ids, target_ids, reward, decision, importer_db_path=importer_db_path
        )

        self._realtime_obs = realtime_obs
        """``bool``: whether tasking engine should task observations in realtime (during the simulation)."""

        self._predict_handler = TaskPredictionJobHandler()
        self._predict_handler.registerCallback(self)
        self._execute_handler = TaskExecutionJobHandler()
        self._execute_handler.registerCallback(self)

    def assess(self, prior_datetime_epoch: datetime, datetime_epoch: datetime) -> None:
        """Perform a set of analysis operations on the current simulation state.

        #. The rewards for all possible tasks are computed
        #. The engine optimizes tasking based on the reward matrix
        #. The optimized tasking strategy is applied and observations are collected

        Args:
            prior_datetime_epoch (datetime): previous epoch
            datetime_epoch (datetime): epoch at which to perform analysis
        """
        # Pre-conditions: reset values to ensure clean tasking state at start of every timestep
        self._observations = []
        self.visibility_matrix = zeros((self.num_targets, self.num_sensors), dtype=bool)
        self.decision_matrix = zeros((self.num_targets, self.num_sensors), dtype=bool)
        self.reward_matrix = zeros((self.num_targets, self.num_sensors), dtype=float)
        self.metric_matrix = zeros(
            (self.num_targets, self.num_sensors, self.num_metrics), dtype=float
        )

        # Only task if we say so.... :P
        if self._realtime_obs:
            self._predict_handler.executeJobs()
            handleRelevantEvents(
                self,
                ResonaateDatabase.getSharedInterface(),
                EventScope.TASK_REWARD_GENERATION,
                datetimeToJulianDate(prior_datetime_epoch),
                datetimeToJulianDate(datetime_epoch),
                self.logger,
                scope_instance_id=self.unique_id,
            )
            self.calculateRewards()
            self.generateTasking()
            self._execute_handler.executeJobs(decision_matrix=self.decision_matrix)

        # Load imported observations
        if self._importer_db:
            self.saveObservations(self.loadImportedObservations(datetime_epoch))

        tasked_sensors = set()
        observed_targets = set()
        for cur_obs_tuple in self._observations:
            tasked_sensors.add(cur_obs_tuple.observation.sensor_id)
            observed_targets.add(cur_obs_tuple.observation.target_id)

        msg = f"{self.__class__.__name__} produced {len(self._observations)} observations by tasking "
        msg += f"{len(tasked_sensors)} sensors {tasked_sensors}"
        msg += f" on {len(observed_targets)} targets {observed_targets}"
        self.logger.info(msg)

    def calculateRewards(self) -> None:
        """Calculate rewards based off of normalized metrics."""
        metrics = self.reward.normalizeMetrics(self.metric_matrix)
        rewards = self.reward.calculate(metrics)
        self.reward_matrix = rewards.reshape(self.num_targets, self.num_sensors)

    def generateTasking(self) -> None:
        """Create tasking solution based on the current simulation state."""
        self.decision_matrix = self.decision.calculate(self.reward_matrix)

    def loadImportedObservations(self, datetime_epoch: datetime) -> list[ObservationTuple]:
        """Load imported :class:`.Observation` objects from :class:`.ImporterDatabase`.

        Args:
            datetime_epoch (datetime): epoch at which to query the DB for observations

        Returns:
            ``list``: :class:`.ObservationTuple` objects constructed from imported database
        """
        query = (
            Query(Observation)
            .join(Epoch)
            .filter(Epoch.timestampISO == datetime_epoch.isoformat(timespec="microseconds"))
        )
        imported_observation_data = self._importer_db.getData(query)

        imported_observations: list[Observation] = []
        sensor_position_set = set()
        for observation in imported_observation_data:
            position_key = (
                int(observation.position_lat_rad * 1000000),
                int(observation.position_lon_rad * 1000000),
                observation.target_id,
            )
            if position_key not in sensor_position_set:
                imported_observations.append(observation)
                sensor_position_set.add(position_key)
            else:
                obs_dict = observation.makeDictionary()
                msg = f"Dropped duplicate observation: {obs_dict.sensor_id} of {obs_dict.target_id} at {obs_dict.julian_date}"  # noqa: E501
                self.logger.warning(msg)

        if imported_observations:
            msg = f"Imported {len(imported_observations)} observations"
            self.logger.debug(msg)

        sensor_agents = self._fetchSensorAgents()

        imported_obs_tuples = [
            ObservationTuple(
                observation,
                sensor_agents[observation.sensor_id],
                sensor_agents[observation.sensor_id].sensors.angle_measurements,
                "Visible",
            )
            for observation in imported_observations
        ]

        return imported_obs_tuples

    def _fetchSensorAgents(self) -> dict[int, SensingAgent]:
        return loads(KeyValueStore.getValue("sensor_agents"))

    def getCurrentTasking(self, julian_date: JulianDate) -> Task:
        """Return current tasking solution.

        Args:
            julian_date (:class:`.JulianDate`): epoch at which to retrieve tasking solution

        Yields:
            :class:`.Task`: tasking DB object for each target/sensor pair
        """
        for tgt_id, tgt_ind in self.target_indices.items():
            for sen_id, sen_ind in self.sensor_indices.items():
                yield Task(
                    julian_date=julian_date,
                    target_id=tgt_id,
                    sensor_id=sen_id,
                    visibility=self.visibility_matrix[tgt_ind, sen_ind],
                    reward=self.reward_matrix[tgt_ind, sen_ind],
                    decision=self.decision_matrix[tgt_ind, sen_ind],
                )

    def shutdown(self) -> None:
        """Perform cleanup operations for shutting down parallel processes/threads."""
        self._predict_handler.shutdown()
        self._execute_handler.shutdown()
