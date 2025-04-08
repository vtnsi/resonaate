"""Module implementing distributed tasking execution processing."""

from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import TYPE_CHECKING

# Third Party Imports
import ray

# Local Imports
from . import JobExecutor, Registration

if TYPE_CHECKING:
    # Third Party Imports

    # Local Imports
    from ..agents.estimate_agent import EstimateAgent
    from ..agents.sensing_agent import SensingAgent
    from ..agents.target_agent import TargetAgent
    from ..data.observation import MissedObservation, Observation
    from ..tasking.engine.engine_base import TaskingEngine


@dataclass
class TaskExecutionSubmission:
    """Encapsulate arguments for `asyncExecuteTasking`."""

    estimate_handle: EstimateAgent
    """Remote handle to :class:`.EstimateAgent` being tasked."""

    target_handles: dict[int, TargetAgent]
    """Dictionary of remote handles to all :class:`.TargetAgent`'s."""

    sensor_handle_list: list[SensingAgent]
    """List of remote handles to :class:`.SensingAgent`'s tasked to observe the target."""


@dataclass
class TaskExecutionResult:
    """Encapsulate attributes of return value from `asyncExecuteTasking`."""

    target_id: int
    """Unique identifier of the :class:`.TargetAgent` being observed."""

    observations: list[Observation]
    """List of successful observations of target(s)."""

    missed_observations: list[MissedObservation]
    """List of missed observation objects."""

    sensor_info_list: list[dict]
    """list of dict containing updates to :class:`.SensingAgent`'s that were tasked."""


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
    """Encapsulates a tasking execution step into a :class:`.Registration`."""

    def __init__(
        self,
        registrant: TaskingEngine,
        estimate_handle: EstimateAgent,
        target_store: dict[int, TargetAgent],
        tasked_sensor_handles: list[SensingAgent],
    ):
        """Initialize a :class:`.TaskExecutionRegistration`.

        Args:
            registrant: The :class:`.TaskingEngine` requesting this tasking be executed.
            estimate_handle: Remote `ray` handle to the :class:`.EstimateAgent` object this tasking
                is executing on.
            target_store: A mapping of target IDs to their remote `ray` handles to
                :class:`.TargetAgent`'s.
            tasked_sensor_handles: List of remote `ray` handles to :class:`.SensingAgent`'s that
                have been tasked to observe the specified :class:`.EstimateAgent`.
        """
        super().__init__(registrant)
        self._estimate_handle = estimate_handle
        self._target_store = target_store
        self._tasked_sensor_handles = tasked_sensor_handles

    def generateSubmission(self) -> TaskExecutionSubmission:
        """Generate a :class:`.TaskExecutionSubmission` specifying the tasking being executed."""
        return TaskExecutionSubmission(
            self._estimate_handle,
            self._target_store,
            self._tasked_sensor_handles,
        )

    def processResults(self, results: TaskExecutionResult):
        """Queue resultant observations to be saved to the database and record sensor changes."""
        self._registrant.saveObservations(results.observations)
        self._registrant.saveMissedObservations(results.missed_observations)
        self._registrant.updateFromAsyncTaskExecution(results.sensor_info_list)


class TaskExecutionExecutor(JobExecutor):
    """Creates, executes, and processes the results of tasking reward generation jobs."""

    @classmethod
    def getRemoteFunc(cls):
        """Pointer to :meth:`.asyncExecuteTasking` function executed on remote worker."""
        return asyncExecuteTasking
