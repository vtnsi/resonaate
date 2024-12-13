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
def asyncPropagate(submissions: list[PropagateSubmission]):
    results = []
    for submission in submissions:
        new_eci = submission.dynamics.propagate(
            submission.init_time,
            submission.final_time,
            submission.init_eci
        )
        new_dt = submission.init_dt + timedelta(seconds=submission.final_time - submission.init_time)
        new_ecef = eci2ecef(new_eci, new_dt)
        new_lla = ecef2lla(new_ecef)
        results.append(PropagateResult(
            agent_id=submission.agent_id,
            final_time=submission.final_time,
            prev_state=submission.init_eci,
            final_eci=new_eci,
            final_ecef=new_ecef,
            final_lla=new_lla
        ))
    return results

SUBMIT_SIZE = 30
"""Number of RSOs to include in a propagation submission."""

STEP = 300

def rayPropagation():
    ray.init()
    scenario = buildScenarioFromConfigFile("configs/json/main_init.json", start_workers=False)

    times = []
    for it in range(12):
        start = time()
        rayPropStep(scenario)
        times.append(time() - start)
        print(f"{STEP}s step took {times[it]}")
    print(f"Mean step duration: {mean(times)}")


def rayPropStep(scenario):
    unfinished_tasks = []
    submit_buffer = []
    for target in scenario.target_agents.values():
        target: TargetAgent
        submit_buffer.append(
            PropagateSubmission(
                agent_id=target.simulation_id,
                dynamics=target.dynamics,
                init_dt=target.datetime_epoch,
                init_time=target.time,
                final_time=target.time + STEP,
                init_eci=target.eci_state
            )
        )
        if len(submit_buffer) == SUBMIT_SIZE:
            unfinished_tasks.append(
                asyncPropagate.remote(submit_buffer)
            )
            submit_buffer = []
    if submit_buffer:
        unfinished_tasks.append(
            asyncPropagate.remote(submit_buffer)
        )
        del submit_buffer

    while unfinished_tasks:
        finished_tasks, unfinished_tasks = ray.wait(unfinished_tasks)
        results: list[PropagateResult] = ray.get(finished_tasks[0])
        for result in results:
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
