""":class:`.Job` handler class that manages estimate updating logic."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from mjolnir import Job

# Local Imports
from ..estimation.sequential.sequential_filter import FilterFlag
from .base import CallbackRegistration, JobHandler

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ..agents.estimate_agent import EstimateAgent
    from ..data.observation import Observation


def asyncUpdateEstimate(estimate_agent: EstimateAgent, successful_obs: list[Observation]) -> dict:
    """Update the state estimate for a :class:`.EstimateAgent`.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getUpdateResult`
        and :meth:`~.SequentialFilter.updateFromAsyncResult` methods implemented.

    Args:
        estimate_agent (:class:`.EstimateAgent`): estimate object corresponding to the target.
        successful_obs (``list``): :class:`.Observation` objects to be incorporated in the filter update

    Returns:
        ``dict``: execute result dictionary contains:

        :``"filter_update"``: (``dict``): filter update results to be applied.
        :``"observations'``: (:class:`.Observation`): successful_obs
        :``"observed"``: (``bool``): whether there were successful observations of this target.
        :``"estimate_id"``: (``int``): ID of the :class:`.EstimateAgent` to calculate metrics for.
        :``"new_filter"``: (:class:`.SequentialFilter`): new filter object for this :class:`.EstimateAgent`
    """
    # Update the filter with the successful observations, save the data
    estimate_agent.updateEstimate(successful_obs)

    # Common result, no new filter object
    result = {
        "estimate_id": estimate_agent.simulation_id,
        "filter_update": estimate_agent.nominal_filter.getUpdateResult(),
        "observations": successful_obs,
        "observed": bool(successful_obs),
        "new_filter": None,
    }

    # MMAE is closing
    if FilterFlag.ADAPTIVE_ESTIMATION_CLOSE in estimate_agent.nominal_filter.flags:
        estimate_agent.nominal_filter.flags ^= FilterFlag.ADAPTIVE_ESTIMATION_CLOSE
        result["new_filter"] = estimate_agent.nominal_filter

    # MMAE is beginning
    elif FilterFlag.ADAPTIVE_ESTIMATION_START in estimate_agent.nominal_filter.flags:
        estimate_agent.nominal_filter.flags ^= FilterFlag.ADAPTIVE_ESTIMATION_START
        result["new_filter"] = estimate_agent.nominal_filter

    return result


class EstimateUpdateRegistration(CallbackRegistration):
    """Callback registration for :class:`.EstimateAgent` update jobs."""

    def jobCreateCallback(self, **kwargs):
        """Create a :func:`.asyncUpdateEstimate` job.

        This relies on a common interface for :meth:`.SequentialFilter.update`.

        KeywordArgs:
            estimate_id (``int``): ID associated with the :class:`.EstimateAgent` to be updated.
            observations (``list``): :class:`.Observation` objects with which to update the :class:`EstimateAgent`.

        Returns:
            :class:`.Job`: job to be processed by :class:`.QueueManager`.
        """
        estimate_id = kwargs["estimate_id"]
        return Job(
            asyncUpdateEstimate,
            args=[
                self.registrant.estimate_agents[estimate_id],
                kwargs["observations"],
            ],
        )

    def jobCompleteCallback(self, job):
        """Save the *a posteriori* :attr:`.state_estimate` and :attr:`.error_covariance`.

        Also, update the :class:`.SequentialFilter` associated with the agent.

        Args:
            job (:class:`.Job`): job object that's returned when a job completes.
        """
        est_agent: EstimateAgent = self.registrant.estimate_agents[job.retval["estimate_id"]]
        est_agent.updateFromAsyncUpdateEstimate(job.retval)


class EstimateUpdateJobHandler(JobHandler):
    """Handle parallel jobs during the :class:`.EstimateAgent` update step of the simulation."""

    callback_class = EstimateUpdateRegistration

    def generateJobs(self, **kwargs):
        """Generate list of update jobs to submit to the :class:`.QueueManager`.

        KeywordArgs:
            observations (``list``): :class:`.Observation` objects with which to update the
                :class:`EstimateAgent`.

        Returns:
            ``list``: :class:`.Job` objects that will be submitted
        """
        jobs = []
        obs_dict = kwargs["observations"]
        for registration in self.callback_registry:
            for estimate_id in registration.registrant.target_agents:
                job = registration.jobCreateCallback(
                    estimate_id=estimate_id, observations=obs_dict[estimate_id]
                )
                self.job_id_registration_dict[job.id] = registration
                jobs.append(job)

        return jobs

    def deregisterCallback(self, callback_id):
        """Remove a registrant's :class:`.CallbackRegistration` from this :class:`.JobHandler`.

        Note:
            The only expected registrant for a :class:`.EstimateUpdateJobHandler` is the :class:`.Scenario` that's
            currently running. Because of this, there's no need to actually "deregister" anything. Instead, it should
            be sufficient to just remove a :attr:`.TargetAgent.simulation_id` from the :attr:`.Scenario.target_agents`
            dictionary.

        Args:
            callback_id (any): Unique identifier of the :class:`.CallbackRegistration` being removed.
        """
