from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import TYPE_CHECKING

# Third Party Imports
import ray

# Local Imports
from . import JobExecutor, Registration

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Optional

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..agents.estimate_agent import EstimateAgent
    from ..estimation.sequential.sequential_filter import SequentialFilter
    from ..physics.time.stardate import ScenarioTime


@dataclass
class EstPredictSubmission:
    """Encapsulate arguments for `asyncPredict`."""

    seq_filter: SequentialFilter
    """Filter object used to predict state estimates."""

    time: ScenarioTime
    """Time during the scenario to predict to."""

    scheduled_events: Optional[list] = None
    """List of event objects that an estimate could predict...?"""


@dataclass
class EstPredictResult:
    """Encapsulate attributes of return value for `asyncPredict`."""

    time: ScenarioTime
    """New time after prediction."""

    est_x: ndarray
    """Estimate state at `time` - dt_step."""

    est_p: ndarray
    """Estimate covariance at `time` - dt_step."""

    pred_x: ndarray
    """Predicted state estimate at `time`."""

    pred_p: ndarray
    """Predicted covariance at `time`."""

    sigma_points: ndarray
    """Sigma points used to generate prediction results."""

    sigma_x_res: ndarray
    """Prediction residuals ... ?"""


@ray.remote
def asyncPredict(submission: EstPredictSubmission) -> EstPredictResult:
    """Wrap a filter prediction method for use with a parallel job submission module.

    Args:
        submission: Encapsulation of attributes defining the prediction of an estimate.

    Returns:
        Result of estimate prediction.
    """
    submission.seq_filter.predict(submission.time, submission.scheduled_events)
    return EstPredictResult(
        time=submission.seq_filter.time,
        est_x=submission.seq_filter.est_x,
        est_p=submission.seq_filter.est_p,
        pred_x=submission.seq_filter.pred_x,
        pred_p=submission.seq_filter.pred_p,
        sigma_points=submission.seq_filter.sigma_points,
        sigma_x_res=submission.seq_filter.sigma_x_res,
    )


class EstPredictRegistration(Registration):
    """Encapsulates a prediction step into a :class:`.Registration`."""

    def __init__(self, registrant: EstimateAgent):
        """Initialize a :class:`.EstPredictRegistration`."""
        super().__init__(registrant)

    def generateSubmission(self) -> EstPredictSubmission:
        """Generate a :class:`.EstPredictSubmission` for the :attr:`._registrant`'s current time step."""
        self._registrant: EstimateAgent
        self._registrant.prunePropagateEvents()
        return EstPredictSubmission(
            seq_filter=self._registrant.nominal_filter,
            time=self._registrant.time + self._registrant.dt_step,
            scheduled_events=self._registrant.propagate_event_queue,
        )

    def processResults(self, results: EstPredictResult):
        """Update the :attr:`._registrant`'s state with the new prediction results."""
        self._registrant.nominal_filter.time = results.time
        self._registrant.nominal_filter.est_x = results.est_x
        self._registrant.nominal_filter.est_p = results.est_p
        self._registrant.nominal_filter.pred_x = results.pred_x
        self._registrant.nominal_filter.pred_p = results.pred_p
        self._registrant.nominal_filter.sigma_points = results.sigma_points
        self._registrant.nominal_filter.sigma_x_res = results.sigma_x_res

        self._registrant.time = results.time
        self._registrant.state_estimate = results.pred_x
        self._registrant.error_covariance = results.pred_p


class EstPredictExecutor(JobExecutor):
    """Creates, executes, and processes the results of estimate prediction jobs."""

    @classmethod
    def getRemoteFunc(cls):
        """Pointer to :meth:`.asyncPredict` function executed on remote worker."""
        return asyncPredict

    def registerAgent(self, agent: EstimateAgent):
        """Convenience method for registering a :class:`.EstimateAgent`.

        Args:
            agent: Agent to create a :class:`.EstPredictRegistration` from.
        """
        self.register(EstPredictRegistration(agent))
