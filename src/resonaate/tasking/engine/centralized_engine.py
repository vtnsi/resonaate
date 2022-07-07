"""Defines the :class:`.CentralizedTaskingEngine` class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import zeros
from sqlalchemy.orm import Query

# Local Imports
from ...data.data_interface import Observation
from ...data.events import EventScope, handleRelevantEvents
from ...data.query_util import addAlmostEqualFilter
from ...data.resonaate_database import ResonaateDatabase
from ...data.task import Task
from ...parallel.handlers.task_execution import TaskExecutionJobHandler
from ...parallel.handlers.task_prediction import TaskPredictionJobHandler
from .engine_base import TaskingEngine

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...physics.time.stardate import JulianDate
    from ..decisions import Decision
    from ..rewards import Reward


class CentralizedTaskingEngine(TaskingEngine):
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
    ):
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

    def assess(self, prior_julian_date: JulianDate, julian_date: JulianDate) -> None:
        """Perform a set of analysis operations on the current simulation state.

        #. The rewards for all possible tasks are computed
        #. The engine optimizes tasking based on the reward matrix
        #. The optimized tasking strategy is applied and observations are collected

        Args:
            prior_julian_date (:class:`.JulianDate`): previous epoch
            julian_date (:class:`.JulianDate`): epoch at which to perform analysis
        """
        # Pre-conditions: reset values to ensure clean tasking state at start of every timestep
        self._observations = []
        self.visibility_matrix = zeros((self.num_targets, self.num_sensors), dtype=bool)
        self.decision_matrix = zeros((self.num_targets, self.num_sensors), dtype=bool)
        self.reward_matrix = zeros((self.num_targets, self.num_sensors), dtype=float)

        # Only task if we say so.... :P
        if self._realtime_obs:
            self._predict_handler.executeJobs()
            handleRelevantEvents(
                self,
                ResonaateDatabase.getSharedInterface(),
                EventScope.TASK_REWARD_GENERATION,
                prior_julian_date,
                julian_date,
                self.logger,
                scope_instance_id=self.unique_id,
            )
            self.generateTasking()
            self._execute_handler.executeJobs(decision_matrix=self.decision_matrix)

        # Load imported observations
        if self._importer_db:
            self.saveObservations(self.loadImportedObservations(julian_date))

        tasked_sensors = set()
        observed_targets = set()
        for cur_obs_tuple in self._observations:
            tasked_sensors.add(cur_obs_tuple.observation.sensor_id)
            observed_targets.add(cur_obs_tuple.observation.target_id)

        msg = f"{self.__class__.__name__} produced {len(self._observations)} observations by tasking "
        msg += f"{len(tasked_sensors)} sensors {tasked_sensors}"
        msg += f" on {len(observed_targets)} targets {observed_targets}"
        self.logger.info(msg)

    def generateTasking(self) -> None:
        """Create tasking solution based on the current simulation state."""
        self.decision_matrix = self._decision(self.reward_matrix)

    def loadImportedObservations(self, epoch: JulianDate) -> list[Observation]:
        """Load imported :class:`.Observation` objects from :class:`.ImporterDatabase`.

        Args:
            epoch (:class:`.JulianDate`): epoch at which to query the DB for observations

        Returns:
            ``list``: :class:`.Observation` objects imported from database
        """
        query = addAlmostEqualFilter(Query(Observation), Observation, "julian_date", epoch)
        imported_observation_data = self._importer_db.getData(query)

        imported_observations = []
        sensor_position_set = set()
        for observation in imported_observation_data:
            position_key = (
                int(observation.position_lat_rad * 1000000),
                int(observation.position_long_rad * 1000000),
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

        return imported_observations

    def getCurrentTasking(self, julian_date: JulianDate) -> Task:
        """Return current tasking solution.

        Args:
            julian_date (:class:`.JulianDate`): epoch at which to retrieve tasking solution

        Yields:
            :class:`.Task`: tasking DB object for each target/sensor pair
        """
        for tgt_ind, target in enumerate(self.target_list):
            for sen_ind, sensor_agent in enumerate(self.sensor_list):
                yield Task(
                    julian_date=julian_date,
                    target_id=target,
                    sensor_id=sensor_agent,
                    visibility=self.visibility_matrix[tgt_ind, sen_ind],
                    reward=self.reward_matrix[tgt_ind, sen_ind],
                    decision=self.decision_matrix[tgt_ind, sen_ind],
                )
