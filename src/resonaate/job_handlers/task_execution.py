""":class:`.Job` handler class that manage task execution logic."""
from __future__ import annotations

# Standard Library Imports
from pickle import loads

# Third Party Imports
from mjolnir import Job, KeyValueStore
from numpy import array, where

# Local Imports
from .base import CallbackRegistration, JobHandler


def asyncExecuteTasking(tasked_sensor_ids: list[int], target_id: int) -> dict:
    """Execute tasked observations on a :class:`.TargetAgent`.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getUpdateResult`
        implemented

    Args:
        tasked_sensor_ids (``list``): indices corresponding to sensors tasked to observe the target.
        target_id (``int``): ID of `.TargetAgent` being tasked on.

    Returns:
        ``dict``: execute result dictionary contains:
        :``"observations"``: (``list``): successful :class:`.Observation` objects of target(s).
        :``"target_id"``: (``int``): ID of the :class:`.TargetAgent` observations were made of.
        :``"missed_observations"``: (``list``): list of :class:`.MissedObservation` objects of :class:`.Target_agent`
        :``"sensor_info_list"``: (``list``): list of dict containing updates to sensing_agent.sensors
    """
    sensor_agents = loads(KeyValueStore.getValue("sensor_agents"))
    target_agents = loads(KeyValueStore.getValue("target_agents"))
    estimate_agent = loads(KeyValueStore.getValue("estimate_agents"))[target_id]

    # Remove Primary Target from Target list
    primary_tgt = target_agents[target_id]
    del target_agents[target_id]
    background_targets = list(target_agents.values())

    successful_obs = []
    unsuccessful_obs = []
    sensor_info_list = []
    if len(tasked_sensor_ids) > 0:
        for sensor_id in tasked_sensor_ids:
            sensing_agent = sensor_agents[sensor_id]
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
                }
            )

    return {
        "target_id": target_id,
        "observations": successful_obs,
        "missed_observations": unsuccessful_obs,
        "sensor_info_list": sensor_info_list,
    }


class TaskExecutionRegistration(CallbackRegistration):
    """Registration for :class:`.Task` execution jobs."""

    def jobCreateCallback(self, **kwargs):
        """Create a :func:`.asyncExecuteTasking` job.

        This relies on a common interface for for :meth:`.Sensor.collectObservations`.

        KeywordArgs:
            target_id (``int``): ID associated with the :class:`.TargetAgent`.
            tasked_sensor_ids (``list``): ID numbers of sensors tasked to this target corresponding to their columns in the
            decision matrix.

        Returns:
            :class:`.Job`: job to be processed by :class:`.QueueManager`.
        """
        return Job(asyncExecuteTasking, args=[kwargs["tasked_sensor_ids"], kwargs["target_id"]])

    def jobCompleteCallback(self, job):
        """Save :class:`.Observation` and :class:`.MissedObservation` objects of this target to be applied to it's estimate.

        Args:
            job (:class:`.Job`): job object that's returned when a job completes.
        """
        self.registrant.saveObservations(job.retval["observations"])
        self.registrant.saveMissedObservations(job.retval["missed_observations"])
        self.registrant.updateFromAsyncTaskExecution(job.retval["sensor_info_list"])


class TaskExecutionJobHandler(JobHandler):
    """Handle the parallel jobs during the :class:`.Task` execution step of the simulation."""

    callback_class = TaskExecutionRegistration
    """:class:`.TaskExecutionRegistration`: defines callback to register to the handler."""

    def generateJobs(self, **kwargs):
        """Generate list of :class:`.Task` execution jobs to submit to the :class:`.QueueManager`.

        KeywordArgs:
            decision_matrix (``ndarray``): optimized decision matrix, from which tasks are generated.

        Returns:
            ``list``: :class:`.Job` objects that will be submitted
        """
        jobs = []
        decision_matrix = kwargs["decision_matrix"]
        for registration in self.callback_registry:
            for index, target_id in enumerate(registration.registrant.target_list):
                # Retrieve all the sensors tasked to this target as a tuple, so [0] is required.
                tasked_sensor_indices = where(decision_matrix[index, :])[0]

                if len(tasked_sensor_indices) > 0:
                    sensor_num_array = array(registration.registrant.sensor_list)
                    job = registration.jobCreateCallback(
                        tasked_sensor_ids=sensor_num_array[tasked_sensor_indices].tolist(),
                        target_id=target_id,
                    )
                    self.job_id_registration_dict[job.id] = registration
                    jobs.append(job)

        return jobs

    def deregisterCallback(self, callback_id):
        """Remove a registrant's :class:`.CallbackRegistration` from this :class:`.JobHandler`.

        Note:
            The only expected registrant for a :class:`.TaskExecutionJobHandler` is the :class:`.TaskingEngine` that
            instantiated this handler. Because of this, there's no need to actually "deregister" anything. Instead, it
            should be sufficient to just remove an :attr:`.Agent.simulation_id` from the relevant
            :attr:`.TaskingEngine.target_list` or :attr:`.TaskingEngine.sensor_list`.

        Args:
            callback_id (any): Unique identifier of the :class:`.CallbackRegistration` being removed.
        """
