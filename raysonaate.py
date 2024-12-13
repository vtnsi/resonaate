from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import time
from typing import TYPE_CHECKING

# Third Party Imports
import ray
from numpy import mean, ndarray

# RESONAATE Imports
from resonaate.physics.transforms.methods import ecef2lla, eci2ecef
from resonaate.physics.transforms.reductions import ReductionParams
from resonaate.scenario import buildScenarioFromConfigFile

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Optional

    # RESONAATE Imports
    from resonaate.agents.target_agent import TargetAgent
    from resonaate.dynamics import Dynamics
    from resonaate.dynamics.integration_events import ScheduledEventType
    from resonaate.dynamics.integration_events.station_keeping import StationKeeper
    from resonaate.physics.time.stardate import ScenarioTime


@dataclass
class PropagateSubmission:

    agent_id: int
    dynamics: Dynamics
    init_dt: datetime
    init_time: float
    final_time: float
    init_eci: ndarray
    station_keeping: Optional[list[StationKeeper]] = None
    scheduled_events: Optional[list[ScheduledEventType]] = None


@dataclass
class PropagateResult:

    agent_id: int
    final_time: float
    prev_state: ndarray
    final_eci: ndarray
    final_ecef: ndarray
    final_lla: ndarray


@ray.remote
def asyncPropagate(submission: PropagateSubmission):
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

class RayPropagator:

    def __init__(self, targets: dict[int, TargetAgent]):
        """TODO"""
        self._targets = targets
        self._remote_dyna_map: dict[int, Dynamics] = {}
        """values are technically ray remote object refs"""
        for sim_id, target in self._targets.items():
            self._remote_dyna_map[sim_id] = ray.put(target.dynamics)
        
        self._unfinished_tasks = []

    def propagateStep(self, step_start: datetime, dt_step: ScenarioTime):
        """TODO"""
        for target in self._targets.values():
            assert target.datetime_epoch == step_start
            assert target.dt_step == dt_step

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
            self._targets[result.agent_id].rayUpdate(result)


def rayPropagation():
    ray.init()
    scenario = buildScenarioFromConfigFile("configs/json/main_init.json", start_workers=False)

    ray_prop = RayPropagator(scenario.target_agents)

    times = []
    for it in range(12):
        start = time()
        ray_prop.propagateStep(scenario.clock.datetime_epoch, scenario.clock.dt_step)
        scenario.clock.ticToc()
        times.append(time() - start)
        print(f"{scenario.clock.dt_step}s step took {times[it]}")
    print(f"Mean step duration: {mean(times)}")


def sanityCheck():
    scenario = buildScenarioFromConfigFile("configs/json/main_init.json", start_workers=False)

    print(f"{datetime.now().isoformat()} - Starting serial...")
    for target in scenario.target_agents.values():
        new_time = target.time + scenario.clock.dt_step
        new_state = target.dynamics.propagate(target.time, new_time, target.eci_state)
        target.time = new_time
        target.eci_state = new_state
    print(f"{datetime.now().isoformat()} - Done!")


if __name__ == "__main__":
    rayPropagation()
