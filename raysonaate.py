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
from resonaate.scenario import buildScenarioFromConfigFile

if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.agents.target_agent import TargetAgent
    from resonaate.dynamics import Dynamics


@dataclass
class PropagateSubmission:

    agent_id: int
    dynamics: Dynamics
    init_dt: datetime
    init_time: float
    final_time: float
    init_eci: ndarray


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
        submission.init_eci
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

STEP = 300

def rayPropagation():
    ray.init()
    scenario = buildScenarioFromConfigFile("configs/json/main_init.json", start_workers=False)

    remote_dyna_map = {}
    for sim_id, target in scenario.target_agents.items():
        remote_dyna_map[sim_id] = ray.put(target.dynamics)

    times = []
    for it in range(12):
        start = time()
        rayPropStep(scenario, remote_dyna_map)
        times.append(time() - start)
        print(f"{STEP}s step took {times[it]}")
    print(f"Mean step duration: {mean(times)}")


def rayPropStep(scenario, remote_dyna_map):
    unfinished_tasks = []
    for target in scenario.target_agents.values():
        target: TargetAgent
        unfinished_tasks.append(
            asyncPropagate.remote(
                PropagateSubmission(
                    agent_id=target.simulation_id,
                    dynamics=remote_dyna_map[target.simulation_id],
                    init_dt=target.datetime_epoch,
                    init_time=target.time,
                    final_time=target.time + STEP,
                    init_eci=target.eci_state
                )
            )
        )

    while unfinished_tasks:
        finished_tasks, unfinished_tasks = ray.wait(unfinished_tasks)
        result: PropagateResult = ray.get(finished_tasks[0])
        scenario.target_agents[result.agent_id].rayUpdate(result)


def sanityCheck():
    scenario = buildScenarioFromConfigFile("configs/json/main_init.json", start_workers=False)

    print(f"{datetime.now().isoformat()} - Starting serial...")
    for target in scenario.target_agents.values():
        new_time = target.time + STEP
        new_state = target.dynamics.propagate(target.time, new_time, target.eci_state)
        target.time = new_time
        target.eci_state = new_state
    print(f"{datetime.now().isoformat()} - Done!")


if __name__ == "__main__":
    rayPropagation()
