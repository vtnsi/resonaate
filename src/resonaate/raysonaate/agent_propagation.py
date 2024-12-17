from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

# Third Party Imports
import ray

# Local Imports
from ..physics.transforms.methods import ecef2lla, eci2ecef
from ..physics.transforms.reductions import ReductionParams
from . import JobExecutor, Registration

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Optional, Union

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..agents.sensing_agent import SensingAgent
    from ..agents.target_agent import TargetAgent
    from ..dynamics import Dynamics
    from ..dynamics.integration_events import ScheduledEventType
    from ..dynamics.integration_events.station_keeping import StationKeeper
    from ..physics.time.stardate import ScenarioTime


@dataclass
class PropagateSubmission:
    """Encapsulate arguments for `asyncPropagate`."""

    agent_id: int
    """Unique identifier of agent being propagated."""

    dynamics: Dynamics
    """Dynamics object to propagate."""

    init_time: ScenarioTime
    """:class:`.ScenarioTime` representation of time that propagation is starting from."""

    final_time: ScenarioTime
    """:class:`.ScenarioTime` representation of time that propagation is going to."""

    init_eci: ndarray
    """6x1 state vector of object at :attr:`.init_time`."""

    station_keeping: Optional[list[StationKeeper]] = None
    """Collection of :class:`.StationKeeper` objects that affect propagation."""

    scheduled_events: Optional[list[ScheduledEventType]] = None
    """Collection of :class:`.ScheduledEventType` objects that affect propagation."""


@dataclass
class PropagateResult:
    """Encapsulate attributes of return value from `asyncPropagate`."""

    agent_id: int
    """Unique identifier of agent being propagated."""

    final_time: ScenarioTime
    """:class:`.ScenarioTime` representation of time that propagation finished."""

    prev_state: ndarray
    """6x1 state vector of object before propagation."""

    final_eci: ndarray
    """6x1 state vector of object after propagation in the ECI frame."""


@ray.remote
def asyncPropagate(submission: PropagateSubmission) -> PropagateResult:
    """Wrap a dynamics propagation method for use with a parallel job submission module.

    Args:
        submission: Encapsulation of attributes defining the propagation of an Agent.

    Returns:
        Result of propagation.
    """
    dyna = ray.get(submission.dynamics)
    new_eci = dyna.propagate(
        submission.init_time,
        submission.final_time,
        submission.init_eci,
        station_keeping=submission.station_keeping,
        scheduled_events=submission.scheduled_events,
    )
    return PropagateResult(
        agent_id=submission.agent_id,
        final_time=submission.final_time,
        prev_state=submission.init_eci,
        final_eci=new_eci,
    )


class PropagateRegistration(Registration):
    """Encapsulates a propagation step into a :class:`.Registration`."""

    def __init__(self, registrant: Union[TargetAgent, SensingAgent]):
        """Initialize a :class:`.PropagateRegistration`.

        This initialization has a side effect of putting the `registrant`'s :class:`.Dynamics`
        class on `ray`'s remote object store because the object is relatively static and this will
        reduce the amount of times that it will need to be serialized.
        """
        super().__init__(registrant)
        self._remote_dyna_ref = ray.put(registrant.dynamics)

    def generateSubmission(self) -> PropagateSubmission:
        """Generate a :class:`.PropagateSubmission` for the :attr:`._registrant`'s current time step."""
        self._registrant.prunePropagateEvents()
        reductions = ReductionParams.build(self._registrant.datetime_epoch)
        for item in self._registrant.station_keeping:
            item.reductions = reductions

        return PropagateSubmission(
            agent_id=self._registrant.simulation_id,
            dynamics=self._remote_dyna_ref,
            init_time=self._registrant.time,
            final_time=self._registrant.time + self._registrant.dt_step,
            init_eci=self._registrant.eci_state,
            station_keeping=self._registrant.station_keeping,
            scheduled_events=self._registrant.propagate_event_queue,
        )

    def processResults(self, results: PropagateResult):
        """Update the :attr:`._registrant`'s state with the new propagation results."""
        self._registrant.time = results.final_time
        self._registrant.eci_state = results.final_eci


class PropagateExecutor(JobExecutor):
    """Creates, executes, and processes the results of propagation jobs."""

    @classmethod
    def getRemoteFunc(cls):
        """Pointer to :meth:`.asyncPropagate` function executed on remote worker."""
        return asyncPropagate

    def registerAgent(self, agent: Union[TargetAgent, SensingAgent]):
        """Convenience method for registering a :class:`.TargetAgent` or :class:`.SensingAgent`.

        Args:
            agent: Agent to create a :class:`.PropagateRegistration` from.
        """
        self.register(PropagateRegistration(agent))
