from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import ray

if TYPE_CHECKING:
    # Local Imports
    from ..agents.agent_base import Agent


@ray.remote
class AgentStore:
    """Ray actor for keeping :class:`.Agent` state across many workers."""

    def __init__(self):
        """Initialize an :class:`.AgentStore`."""
        self._agents = dict()

    def setAgents(self, agents: dict[int, Agent]):
        """Set the internal :class:`.Agent` dictionary to specified `agents`.

        Args:
            agents: Dictionary of unique ID, :class:`.Agent` pairs.
        """
        self._agents = agents

    def putAgent(self, agent: Agent):
        """Update a single :class:`.Agent` in internal store.

        Arg:
            agent: :class:`.Agent` object being put in the internal store.
        """
        self._agents[agent.simulation_id] = agent

    def getAgent(self, sim_id: int) -> Agent:
        """Retrieve a single :class:`.Agent` from the store.

        Args:
            sim_id: Unique identifier of the :class:`.Agent` being retrieved.

        Returns:
            :class:`.Agent` instance stored with `sim_id` as its unique identifier.

        Raises:
            KeyError: If the `sim_id` does not have a corresponding :class:`.Agent` in the store.
        """
        return self._agents[sim_id]

    def getManyAgents(self, sim_ids: list[int]) -> dict[int, Agent]:
        """Retrieve several :class:`.Agent`s specified by `sim_ids`.

        Args:
            sim_ids: List of unique identifiers of the :class:`.Agent`s to be retrieved.

        Returns:
            Dictionary of unique identifier, :class:`.Agent` pairs.

        Raises:
            KeyError: If the any of the specified `sim_ids` do not have a corresponding
                :class:`.Agent` in the store.
        """
        ret_agents = {}
        for sim_id in sim_ids:
            ret_agents[sim_id] = self._agents[sim_id]
        return ret_agents

    def getAllAgents(self) -> dict[int, Agent]:
        """Retrieve the entire internal store dictionary."""
        return self._agents


def getTargetStore():
    """Return a remote handle to the :class:`.AgentStore` storing :class:`.TargetAgents`.

    The remote Ray object will be instantiated if it wasn't already.
    """
    return AgentStore.options(name="target_agents", get_if_exists=True).remote()

def getSensorStore():
    """Return a remote handle to the :class:`.AgentStore` storing :class:`.SensingAgents`.

    The remote Ray object will be instantiated if it wasn't already.
    """
    return AgentStore.options(name="sensing_agents", get_if_exists=True).remote()

def getEstimateStore():
    """Return a remote handle to the :class:`.AgentStore` storing :class:`.EstimateAgents`.

    The remote Ray object will be instantiated if it wasn't already.
    """
    return AgentStore.options(name="estimate_agents", get_if_exists=True).remote()
