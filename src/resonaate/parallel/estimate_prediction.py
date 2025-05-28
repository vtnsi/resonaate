"""Module implementing distributed estimate prediction processing."""

from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import TYPE_CHECKING

# Third Party Imports
import ray

# RESONAATE Imports
from resonaate.estimation.particle.particle_filter import ParticleFilter

# Local Imports
from . import JobExecutor, Registration

if TYPE_CHECKING:
    # Local Imports
    from ..agents.estimate_agent import EstimateAgent
    from ..estimation.results import SeqFilterPredictResult
    from ..estimation.sequential_filter import SequentialFilter
    from ..physics.time.stardate import ScenarioTime


@dataclass
class EstPredictSubmission:
    """Encapsulate arguments for `asyncPredict`."""

    seq_filter: SequentialFilter
    """Filter object used to predict state estimates."""

    time: ScenarioTime
    """Time during the scenario to predict to."""

    scheduled_events: list | None = None
    """List of event objects that an estimate could predict...?"""


@ray.remote
def asyncPredict(submission: EstPredictSubmission) -> SeqFilterPredictResult:
    """Wrap a filter prediction method for use with a parallel job submission module.

    Args:
        submission: Encapsulation of attributes defining the prediction of an estimate.

    Returns:
        Result of estimate prediction.
    """
    submission.seq_filter.predict(submission.time, submission.scheduled_events)
    return submission.seq_filter.getPredictionResult()


class EstPredictRegistration(Registration):
    """Encapsulates a prediction step into a :class:`.Registration`."""

    def generateSubmission(self) -> EstPredictSubmission:
        """Generate a :class:`.EstPredictSubmission` for the :attr:`._registrant`'s current time step."""
        self._registrant: EstimateAgent
        self._registrant.prunePropagateEvents()
        return EstPredictSubmission(
            seq_filter=self._registrant.nominal_filter,
            time=self._registrant.time + self._registrant.dt_step,
            scheduled_events=self._registrant.propagate_event_queue,
        )

    def processResults(self, results: SeqFilterPredictResult):
        """Update the :attr:`._registrant`'s state with the new prediction results."""
        results.apply(self._registrant.nominal_filter)

        self._registrant.time = results.time
        self._registrant.state_estimate = results.pred_x
        self._registrant.error_covariance = results.pred_p

        if isinstance(self._registrant.nominal_filter, ParticleFilter):
            self._registrant._saveFilterStep()  # noqa: SLF001


class EstPredictExecutor(JobExecutor):
    """Creates, executes, and processes the results of estimate prediction jobs."""

    @classmethod
    def getRemoteFunc(cls):
        """Pointer to :meth:`.asyncPredict` function executed on remote worker."""
        return asyncPredict
