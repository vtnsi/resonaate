from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import TYPE_CHECKING

# Third Party Imports
import ray
from numpy import array, where

# Local Imports
from . import JobExecutor, Registration
from .agent_store import getEstimateStore, getSensorStore, getTargetStore

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..agents.sensing_agent import SensingAgent
    from ..data.observation import MissedObservation, Observation
    from ..tasking.engine.engine_base import TaskingEngine


@dataclass
class TaskExecutionSubmission:

    sensor_list: ndarray
    """array of sensor unique identifiers"""

    decision_row: ndarray
    """Decision matrix row corresponding to the :class:`.TargetAgent` being observed."""

    target_id: int
    """Unique identifier of the :class:`.TargetAgent` being observed."""


@dataclass
class TaskExecutionResult:

    target_id: int
    """Unique identifier of the :class:`.TargetAgent` being observed."""

    observations: list[Observation]
    """List of successful observations of target(s)."""

    missed_observations: list[MissedObservation]
    """List of missed observation objects."""

    sensor_info_list: list[dict]
    """list of dict containing updates to :class:`.SensingAgent`s that were tasked."""


@ray.remote
def asyncExecuteTasking(submission: TaskExecutionSubmission) -> dict:
    """Execute tasked observations on a :class:`.TargetAgent`.

    Args:
        submission: Encapsulation of attributes specifying task execution.

    Returns:
        Results of task execution.
    """
    tasked_sensor_indices = where(submission.decision_row)  #[0]
    if len(tasked_sensor_indices) < 1:
        return TaskExecutionResult(
            target_id=submission.target_id,
            observations=[],
            missed_observations=[],
            sensor_info_list=[],
        )
    tasked_sensor_ids = submission.sensor_list[tasked_sensor_indices]

    target_store = getTargetStore()
    target_agents = ray.get(target_store.getAllAgents.remote())
    primary_tgt = target_agents[submission.target_id]

    # Remove Primary Target from Target list
    del target_agents[submission.target_id]
    background_targets = list(target_agents.values())

    successful_obs = []
    unsuccessful_obs = []
    sensor_info_list = []
    estimate_store = getEstimateStore()
    sensor_store = getSensorStore()
    estimate_agent = ray.get(estimate_store.getAgent.remote(submission.target_id))
    for sensor_id in tasked_sensor_ids:
        sensing_agent: SensingAgent = ray.get(sensor_store.getAgent.remote(sensor_id))
        (
            made_obs,
            missed_obs,
            boresight,
            time_last_tasked,
        ) = sensing_agent.sensors.collectObservations(
            estimate_agent.eci_state,
            primary_tgt,
            background_targets,
        )
        successful_obs.extend(made_obs)
        unsuccessful_obs.extend(missed_obs)
        sensor_info_list.append(
            {
                "sensor_id": sensor_id,
                "boresight": boresight,
                "time_last_tasked": time_last_tasked,
            },
        )

    return TaskExecutionResult(
        target_id=submission.target_id,
        observations=successful_obs,
        missed_observations=unsuccessful_obs,
        sensor_info_list=sensor_info_list,
    )


class TaskExecutionRegistration(Registration):

    def __init__(self, registrant: TaskingEngine, target_id: int):
        super().__init__(registrant)
        self._target_id = target_id

    def generateSubmission(self, sensor_list: ndarray, decision_row: ndarray):
        return TaskExecutionSubmission(
            sensor_list=sensor_list,
            decision_row=decision_row,
            target_id=self._target_id
        )

    def processResults(self, results: TaskExecutionResult):
        self._registrant.saveObservations(results.observations)
        self._registrant.saveMissedObservations(results.missed_observations)
        self._registrant.updateFromAsyncTaskExecution(results.sensor_info_list)


class TaskExecutionExecutor(JobExecutor):

    def __init__(self, tasking_engine: TaskingEngine):
        super().__init__()
        self._tasking_engine = tasking_engine

    @classmethod
    def getRemoteFunc(cls):
        return asyncExecuteTasking
    
    def execute(self):
        sensor_num_array = array(self._tasking_engine.sensor_list)
        for registration in self._registrations:
            target_index = self._tasking_engine.target_indices[registration._target_id]
            submission = registration.generateSubmission(
                sensor_list=sensor_num_array,
                decision_row=self._tasking_engine.decision_matrix[target_index],
            )
            remote_ref = self.getRemoteFunc().remote(submission)
            self._unfinished_jobs.append(remote_ref)
            self._result_reg_mapping[remote_ref] = registration

        while self._unfinished_jobs:
            finished_jobs, self._unfinished_jobs = ray.wait(self._unfinished_jobs)
            result = ray.get(finished_jobs[0])
            self._result_reg_mapping[finished_jobs[0]].processResults(result)

    
