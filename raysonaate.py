from __future__ import annotations

# Standard Library Imports
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


@ray.remote
class RayTargetAgent:

    def __init__(self, target_agent: TargetAgent):
        self._target_agent = target_agent

    def propagate(self, step: float):
        new_time = self._target_agent.time + step
        new_state = self._target_agent.dynamics.propagate(
            self._target_agent.time,
            new_time,
            self._target_agent.eci_state
        )
        self._target_agent.time = new_time
        self._target_agent.eci_state = new_state
        return new_state


def main():
    ray.init(num_cpus=6)
    scenario = buildScenarioFromConfigFile("configs/json/main_init.json", start_workers=False)

    print("Initializing actors...")
    actors = []
    for target in scenario.target_agents.values():
        actors.append(
            RayTargetAgent.remote(target)
        )

    print(f"{datetime.now().isoformat()} - Queuing actor propagation...")
    state_promises = []
    for actor in actors:
        state_promises.append(
            actor.propagate.remote(300)
        )

    print("Retrieving new states...")
    for promise in state_promises:
        ray.get(promise)
    print(f"{datetime.now().isoformat()} - Done!")


if __name__ == "__main__":
    main()
