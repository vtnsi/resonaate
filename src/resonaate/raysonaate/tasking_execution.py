from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import TYPE_CHECKING

# Third Party Imports
import ray
from numpy import array, where

# Local Imports
from . import JobExecutor, Registration

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..agents.estimate_agent import EstimateAgent
    from ..agents.sensing_agent import SensingAgent
    from ..agents.target_agent import TargetAgent
    from ..data.observation import MissedObservation, Observation
    from ..tasking.engine.engine_base import TaskingEngine


@dataclass
class TaskExecutionSubmission:

    estimate_handle: EstimateAgent
    """Remote handle to :class:`.EstimateAgent` being tasked."""

    target_handles: dict[int, TargetAgent]
    """Dictionary of remote handles to all :class:`.TargetAgent`s."""

    sensor_handle_list: list[SensingAgent]
    """List of remote handles to :class:`.SensingAgent`s tasked to observe the target."""


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
    estimate_agent = ray.get(submission.estimate_handle)

    primary_tgt_handle = submission.target_handles[estimate_agent.simulation_id]
    del submission.target_handles[estimate_agent.simulation_id]

    primary_tgt = ray.get(primary_tgt_handle)
    background_targets = ray.get(list(submission.target_handles.values()))
    tasked_sensors = ray.get(submission.sensor_handle_list)

    successful_obs = []
    unsuccessful_obs = []
    sensor_info_list = []
    for sensing_agent in tasked_sensors:
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
                "sensor_id": sensing_agent.simulation_id,
                "boresight": boresight,
                "time_last_tasked": time_last_tasked,
            },
        )

    return TaskExecutionResult(
        target_id=primary_tgt.simulation_id,
        observations=successful_obs,
        missed_observations=unsuccessful_obs,
        sensor_info_list=sensor_info_list,
    )


class TaskExecutionRegistration(Registration):

    def __init__(self, registrant: TaskingEngine, target_id: int):
        super().__init__(registrant)
        self._target_id = target_id

    def generateSubmission(self):
        raise Exception("Don't actually call this.")

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
            tasked_sensor_indices = where(self._tasking_engine.decision_matrix[target_index, :])[0]

            if len(tasked_sensor_indices) > 0:
                tasked_sensor_ids = sensor_num_array[tasked_sensor_indices]
                submission = TaskExecutionSubmission(
                    self._tasking_engine._estimate_store[registration._target_id],
                    self._tasking_engine._target_store,
                    [self._tasking_engine._sensor_store[sensor_id] for sensor_id in tasked_sensor_ids]
                )

                remote_ref = self.getRemoteFunc().remote(submission)
                self._unfinished_jobs.append(remote_ref)
                self._result_reg_mapping[remote_ref] = registration

        while self._unfinished_jobs:
            finished_jobs, self._unfinished_jobs = ray.wait(self._unfinished_jobs)
            result = ray.get(finished_jobs[0])
            self._result_reg_mapping[finished_jobs[0]].processResults(result)

    
