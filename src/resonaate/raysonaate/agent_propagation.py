from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

# Third Party Imports
import ray

# RESONAATE Imports
from resonaate.physics.transforms.methods import ecef2lla, eci2ecef
from resonaate.physics.transforms.reductions import ReductionParams

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Optional, Union

    # Third Party Imports
    from numpy import ndarray

    # RESONAATE Imports
    from resonaate.agents.sensing_agent import SensingAgent
    from resonaate.agents.target_agent import TargetAgent
    from resonaate.dynamics import Dynamics
    from resonaate.dynamics.integration_events import ScheduledEventType
    from resonaate.dynamics.integration_events.station_keeping import StationKeeper
    from resonaate.physics.time.stardate import ScenarioTime


@dataclass
class PropagateSubmission:
    """Encapsulate arguments for `asyncPropagate`."""

    agent_id: int
    """Unique identifier of agent being propagated."""

    dynamics: Dynamics
    """Dynamics object to propagate."""

    init_dt: datetime
    """Datetime representation of time that propagation is starting from."""

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

    final_ecef: ndarray
    """6x1 state vector of object after propagation in the ECEF frame."""

    final_lla: ndarray
    """3x1 position vector of object after propagation in lat, lon, & alt."""


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
    new_dt = submission.init_dt + timedelta(seconds=submission.final_time - submission.init_time)
    new_ecef = eci2ecef(new_eci, new_dt)
    new_lla = ecef2lla(new_ecef)
    return PropagateResult(
        agent_id=submission.agent_id,
        final_time=submission.final_time,
        prev_state=submission.init_eci,
        final_eci=new_eci,
        final_ecef=new_ecef,
        final_lla=new_lla
    )

class AgentPropagator:
    """Class encapsulating process for propagating Agents using ray parallelization."""

    def __init__(self):
        """Initialize internal properties."""
        self._agents: dict[int, Union[TargetAgent, SensingAgent]] = {}
        self._remote_dyna_map: dict[int, Dynamics] = {}  # values are technically ray remote object refs
        self._unfinished_tasks = []

    def registerAgent(self, agent: Union[TargetAgent, SensingAgent]):
        """
        Args:
            agent:
        """
        self._agents[agent.simulation_id] = agent
        self._remote_dyna_map[agent.simulation_id] = ray.put(agent.dynamics)

    def propagateStep(self, step_start: datetime, dt_step: ScenarioTime):
        """Propagate all tracked agents from `step_start` to `step_start` + `dt_step`.

        Args:
            step_start: When this propagation step starts.
            dt_step: How long this propagation step is.

        Raises:
            ValueError: if `step_start` or `dt_step` don't align with tracked agents.
        """
        for target in self._agents.values():
            if target.datetime_epoch != step_start:
                err = f"Target epoch {target.datetime_epoch} not aligned with arg {step_start}"
                raise ValueError(err)
            if target.dt_step != dt_step:
                err = f"Target dt_step {target.dt_step} not aligned with arg {dt_step}"
                raise ValueError(err)

            target.prunePropagateEvents()
            reductions = ReductionParams.build(step_start)
            for item in target.station_keeping:
                item.reductions = reductions

            self._unfinished_tasks.append(
                asyncPropagate.remote(
                    PropagateSubmission(
                        agent_id=target.simulation_id,
                        dynamics=self._remote_dyna_map[target.simulation_id],
                        init_dt=target.datetime_epoch,
                        init_time=target.time,
                        final_time=target.time + target.dt_step,
                        init_eci=target.eci_state,
                        station_keeping=target.station_keeping,
                        scheduled_events=target.propagate_event_queue,
                    )
                )
            )

        while self._unfinished_tasks:
            finished_tasks, self._unfinished_tasks = ray.wait(self._unfinished_tasks)
            result: PropagateResult = ray.get(finished_tasks[0])
            self._agents[result.agent_id].rayUpdate(result)
