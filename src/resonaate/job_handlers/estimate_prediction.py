""":class:`.Job` handler class that manages estimate prediction logic."""
from __future__ import annotations

# Standard Library Imports
from collections import defaultdict
from typing import TYPE_CHECKING

# Third Party Imports
from mjolnir import Job

# Local Imports
from ..data.events import EventScope, getRelevantEvents
from ..data.resonaate_database import ResonaateDatabase
from .agent_propagation import PropagationJobHandler
from .base import CallbackRegistration

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..data.events.base import Event
    from ..estimation.sequential.sequential_filter import SequentialFilter
    from ..physics.time.stardate import ScenarioTime


def asyncPredict(
    seq_filter: SequentialFilter, time: ScenarioTime, scheduled_events: list[Event] = None
) -> ndarray:
    """Wrap a filter prediction method for use with a parallel job submission module.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getPredictionResult`
        and :meth:`~.SequentialFilter.updateFromAsyncResult` methods implemented.

    Args:
        seq_filter (:class:`.SequentialFilter`): filter object used to predict state estimates
        time (:class:`.ScenarioTime`): time during the scenario to predict to
        scheduled_events (``list``, optional): :class:`.Event` objects

    Returns:
        ``ndarray``: 6x1 final state vector of the object being propagated
    """
    seq_filter.predict(time, scheduled_events=scheduled_events)

    return seq_filter.getPredictionResult()


class EstimatePredictionRegistration(CallbackRegistration):
    """Callback registration for :class:`.Estimate` prediction jobs."""

    def jobCreateCallback(self, **kwargs):
        """Create a :func:`.asyncPredict` job & update :attr:`~.Agent.time` appropriately.

        This relies on a common interface for :meth:`.SequentialFilter.predict`.

        KeywordArgs:
            new_time (:class:`.ScenarioTime`): payload indicating the current simulation time.

        Returns
            :class:`.Job`: job to be processed by :class:`.QueueManager`.
        """
        new_time = kwargs["new_time"]
        job = Job(
            asyncPredict,
            args=[self.registrant.nominal_filter, new_time],
            kwargs={
                # [NOTE][parallel-maneuver-event-handling] Step three: pass the event queue to the propagation process.
                "scheduled_events": self.registrant.propagate_event_queue
            },
        )
        self.registrant.time = new_time

        return job

    def jobCompleteCallback(self, job):
        """Save the *a priori* :attr:`.state_estimate` and :attr:`.error_covariance`.

        Also, update the :class:`.SequentialFilter` associated with the agent.

        Args:
            job (:class:`.Job`): job object that's returned when a job completes.
        """
        self.registrant.updateFromAsyncPredict(job.retval)


class EstimatePredictionJobHandler(PropagationJobHandler):
    """Handle the parallel jobs during the :class:`.Estimate` prediction step of the simulation."""

    callback_class = EstimatePredictionRegistration

    def generateJobs(self, **kwargs):
        """Generate list of propagation jobs to submit to the :class:`.QueueManager`.

        KeywordArgs:
            epoch_time (:class:`.ScenarioTime`): current simulation epoch.
            julian_date (:class:`.JulianDate`): current simulation Julian Date
            prior_julian_date (:class:`.JulianDate`): Julian Date at beginning of timestep

        Returns:
            ``list``: :class:`.Job` objects that will be submitted
        """
        # [NOTE][parallel-maneuver-event-handling] Step one: query for events and "handle" them.
        agent_propagation_events = defaultdict(list)
        relevant_events = getRelevantEvents(
            ResonaateDatabase.getSharedInterface(),
            EventScope.AGENT_PROPAGATION,
            kwargs["prior_julian_date"],
            kwargs["julian_date"],
        )
        for event in relevant_events:
            if event.planned:
                agent_propagation_events[event.scope_instance_id].append(event)

        jobs = []
        epoch_time = kwargs["epoch_time"]
        for registration in self.callback_registry:
            registrant_events = agent_propagation_events[registration.registrant.simulation_id]
            for event in registrant_events:
                event.handleEvent(registration.registrant)

            job = registration.jobCreateCallback(new_time=epoch_time)
            self.job_id_registration_dict[job.id] = registration
            jobs.append(job)

        return jobs
