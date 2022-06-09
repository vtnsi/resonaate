""":class:`.Job` handler class that manage task execution logic."""
# Third Party Imports
from numpy import where

# Local Imports
from ..async_functions import asyncExecuteTasking
from ..job import CallbackRegistration, Job
from .job_handler import JobHandler


class TaskExecutionRegistration(CallbackRegistration):
    """Registration for :class:`.Task` execution jobs."""

    def jobCreateCallback(self, **kwargs):
        """Create a :func:`.asyncExecuteTasking` job.

        This relies on a common interface for for :meth:`.Sensor.makeNoisyObservation`.

        KeywordArgs:
            target_id (``int``): ID associated with the :class:`.TargetAgent`.
            tasked_sensors (``list``): indices of sensors tasked to this target corresponding to their columns in the
            decision matrix.

        Returns:
            :class:`.Job`: job to be processed by :class:`.QueueManager`.
        """
        return Job(asyncExecuteTasking, args=[kwargs["tasked_sensors"], kwargs["target_id"]])

    def jobCompleteCallback(self, job):
        """Save successful :class:`.Observation` objects of this target to be applied to it's estimate.

        Args:
            job (:class:`.Job`): job object that's returned when a job completes.
        """
        self.registrant.saveObservations(job.retval["observations"])


class TaskExecutionJobHandler(JobHandler):
    """Handle the parallel jobs during the :class:`.Task` execution step of the simulation."""

    callback_class = TaskExecutionRegistration
    """:class:`.TaskExecutionRegistration`: defines callback to register to the handler."""

    def generateJobs(self, **kwargs):
        """Generate list of :class:`.Task` execution jobs to submit to the :class:`.QueueManager`.

        KeywordArgs:
            decision_matrix (``numpy.ndarray``): optimized decision matrix, from which tasks are generated.

        Returns:
            ``list``: :class:`.Job` objects that will be submitted
        """
        jobs = []
        decision_matrix = kwargs["decision_matrix"]
        for registration in self.callback_registry:
            for index, target_id in enumerate(registration.registrant.target_list):
                # Retrieve all the sensors tasked to this target as a tuple, so [0] is required.
                tasked_sensors = where(decision_matrix[index, :])[0]

                if len(tasked_sensors) > 0:
                    job = registration.jobCreateCallback(
                        tasked_sensors=tasked_sensors, target_id=target_id
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
