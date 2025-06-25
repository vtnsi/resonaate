"""Module implementing distributed estimate update processing."""

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
    """Encapsulate arguments for :meth:`.asyncUpdateEstimate`."""

    estimate_agent: EstimateAgent
    """Remote handle to the :class:`.EstimateAgent` being updated."""

    successful_obs: list[Observation]
    """:class:`.Observation` objects to be incorporated in the filter update."""


@dataclass
class EstUpdateResult:
    """Encapsulate return value of :meth:`.asyncUpdateEstimate`."""

    estimate_id: int
    """Unique ID of the :class:`.EstimateAgent` that was updated."""

    observed: bool
    """Flag indicating whether the target tracked by this update was observed."""

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
    estimate_agent._update(submission.successful_obs)  # noqa: SLF001

    return EstUpdateResult(
        estimate_id=estimate_agent.simulation_id,
        observed=len(submission.successful_obs) > 0,
        iod_start_time=estimate_agent.iod_start_time,
        updated_filter=estimate_agent.nominal_filter,
        detected_maneuvers=estimate_agent._detected_maneuvers,  # noqa: SLF001
    )


class EstUpdateRegistration(Registration):
    """Encapsulates an updates step into a :class:`.Registration`."""

    def __init__(self, registrant: EstimateAgent, handle, observations):
        """Initialize a :class:`.EstUpdateRegistration`."""
        super().__init__(registrant)
        self._handle = handle
        self._observations = observations

    def generateSubmission(self) -> EstUpdateSubmission:
        """Generate a :class:`.EstUpdateSubmission` specifying how to update the estimate."""
        return EstUpdateSubmission(self._handle, self._observations)

    def processResults(self, results: EstUpdateResult):
        """Update the :class:`.EstimateAgent`'s filter and flags."""
        self._registrant._resetFilter(results.updated_filter)  # noqa: SLF001
        self._registrant._finalizeUpdate(results.observed)  # noqa: SLF001

        # [FIXME]: This feels hacky. May need to formalize MMAE/IOD conops in sub-classes?
        self._registrant.iod_start_time = results.iod_start_time

        if results.detected_maneuvers:
            self._registrant._detected_maneuvers = results.detected_maneuvers  # noqa: SLF001


class EstUpdateExecutor(JobExecutor):
    """Creates, executes, and processes the results of estimate update jobs."""

    @classmethod
    def getRemoteFunc(cls):
        """Pointer to :meth:`.asyncCalculateReward` function executed on remote worker."""
        return asyncUpdateEstimate
