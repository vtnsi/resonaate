from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import TYPE_CHECKING

# Third Party Imports
import ray

# Local Imports
from . import JobExecutor, Registration

if TYPE_CHECKING:
    # Local Imports
    from ..agents.estimate_agent import EstimateAgent
    from ..data.detected_maneuver import DetectedManeuver
    from ..data.observation import Observation
    from ..estimation import AdaptiveFilter, SequentialFilter
    from ..physics.time.stardate import ScenarioTime


@dataclass
class EstUpdateSubmission:
    """Encapsulate arguments for `asyncUpdateEstimate`."""

    estimate_agent: EstimateAgent
    """Remote handle to the :class:`.EstimateAgent` being updated."""

    successful_obs: list[Observation]
    """:class:`.Observation` objects to be incorporated in the filter update."""


@dataclass
class EstUpdateResult:
    """Encapsulate ..."""

    estimate_id: int
    """Unique ID of the :class:`.EstimateAgent` that was updated."""

    observations: list[Observation]  # XXX: is this necessary?
    """Successful :class:`.Observation`s made of this agent during the time step."""

    updated_filter: SequentialFilter | AdaptiveFilter
    """The agent's associated filter object that is updated with new values."""

    iod_start_time: ScenarioTime | None
    """Ff configured, when the IOD started. None when IOD is not active."""

    detected_maneuvers: list[DetectedManeuver]
    """Maneuvers that were detected during the parallel update."""


@ray.remote
def asyncUpdateEstimate(submission: EstUpdateSubmission) -> EstUpdateResult:
    """Update the state estimate for the specified :class:`.EstimateAgent`."""
    estimate_agent = ray.get(submission.estimate_agent)
    estimate_agent.nominal_filter.update(submission.successful_obs)
    estimate_agent._update(submission.successful_obs)

    return EstUpdateResult(
        estimate_id=estimate_agent.simulation_id,
        observations=submission.successful_obs,
        iod_start_time=estimate_agent.iod_start_time,
        updated_filter=estimate_agent.nominal_filter,
        detected_maneuvers=estimate_agent._detected_maneuvers,
    )


class EstUpdateRegistration(Registration):
    """Encapsulates an updates step into a :class:`.Registration`."""

    def __init__(self, registrant: EstimateAgent):
        """Initialize a :class:`.EstUpdateRegistration`."""
        super().__init__(registrant)

    @property
    def sim_id(self) -> int:
        return self._registrant.simulation_id

    def generateSubmission(self):
        raise Exception("Don't actually call this.")
    
    def processResults(self, results):
        # [NOTE]: Reset the filter. Likely faster to do this each time, than check and
        #   convert, and then partially reset?
        self._registrant._resetFilter(results.updated_filter)
        self._registrant._finalizeUpdate(results.observations)

        # [FIXME]: This feels hacky. May need to formalize MMAE/IOD conops in sub-classes?
        self._registrant.iod_start_time = results.iod_start_time

        if results.detected_maneuvers:
            self._registrant._detected_maneuvers = results.detected_maneuvers


class EstUpdateExecutor(JobExecutor):

    def registerAgent(self, agent: EstimateAgent):
        """Convenience method for registering a :class:`.EstimateAgent`.

        Args:
            agent: Agent to create a :class:`.EstUpdateRegistration` from.
        """
        self.register(EstUpdateRegistration(agent))

    @classmethod
    def getRemoteFunc(cls):
        return asyncUpdateEstimate

    def execute(self, estimate_store: dict, obs_dict: dict[int, list[Observation]]):
        """
        Args:
            estimate_store: Dictionary mapping remote :class:`.EstimateAgent` handles to
                simulation IDs.
            obs_dict: Dictionary mapping successful observations to simulation
                :class:`.EstimateAgent` simulations IDs.
        """
        for registration in self._registrations:
            submission = EstUpdateSubmission(
                estimate_store[registration.sim_id],
                obs_dict.get(registration.sim_id, list())
            )
            remote_ref = self.getRemoteFunc().remote(submission)
            self._unfinished_jobs.append(remote_ref)
            self._result_reg_mapping[remote_ref] = registration

        while self._unfinished_jobs:
            finished_jobs, self._unfinished_jobs = ray.wait(self._unfinished_jobs)
            result = ray.get(finished_jobs[0])
            self._result_reg_mapping[finished_jobs[0]].processResults(result)

