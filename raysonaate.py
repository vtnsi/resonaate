from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

# Third Party Imports
import ray
from numpy import ndarray

# RESONAATE Imports
from resonaate.scenario import buildScenarioFromConfigFile

if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.agents.target_agent import TargetAgent
    from resonaate.dynamics import Dynamics


@dataclass
class PropagateSubmission:

    agent_id: int
    dynamics: Dynamics
    init_time: float
    final_time: float
    init_state: ndarray


@dataclass
class PropagateResult:

    agent_id: int
    final_time: float
    final_state: ndarray


@ray.remote
def asyncPropagate(submission: PropagateSubmission):
    new_state = submission.dynamics.propagate(
        submission.init_time,
        submission.final_time,
        submission.init_state
    )
    return PropagateResult(
        submission.agent_id,
        submission.final_time,
        new_state
    )

STEP = 300

def main():
    ray.init()
    scenario = buildScenarioFromConfigFile("configs/json/main_init.json", start_workers=False)

    print(f"{datetime.now().isoformat()} - Queuing actor propagation...")
    unfinished_tasks = []
    for target in scenario.target_agents.values():
        submission = PropagateSubmission(
            target.simulation_id,
            target.dynamics,
            target.time,
            target.time + STEP,
            target.eci_state
        )
        unfinished_tasks.append(
            asyncPropagate.remote(submission)
        )
    
    init_task_count = len(unfinished_tasks)
    print_seg_size = int(init_task_count / 4)
    completed_task_count = 0
    while unfinished_tasks:
        finished_tasks, unfinished_tasks = ray.wait(unfinished_tasks)
        result: PropagateResult = ray.get(finished_tasks[0])
        scenario.target_agents[result.agent_id].time = result.final_time
        scenario.target_agents[result.agent_id].eci_state = result.final_state

        completed_task_count += 1
        if completed_task_count % print_seg_size == 0:
            print(f"Progress: {completed_task_count:03d} / {init_task_count:03d}")

    print(f"{datetime.now().isoformat()} - Done!")


if __name__ == "__main__":
    main()
