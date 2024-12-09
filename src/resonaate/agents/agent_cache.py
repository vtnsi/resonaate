"""Defines how :class:`.Agent` objects are cached in the key value store."""
# Third Party Imports
from strmbrkr.key_value_store import KeyValueStore
from strmbrkr.key_value_store.transaction import Transaction

# Local Imports
from .agent_base import Agent


class AgentCache:
    """Encapsulates a named agent cache."""

    def __init__(self, cache_name: str):
        """Instantiate an :class:`.AgentCache`.

        Args:
            cache_name (str): Name of agent cache.
        """
        self.cache_name = cache_name

    def updateCache(self, agent_dict: dict[int, Agent]):
        """Update this :class:`.AgentCache` with updated :class:`.Agent` states.

        Args:
            agent_dict (dict[int, Agent]): Dictionary of :class:`.Agent` objects where keys are
                unique identifiers.
        """
        KeyValueStore.setValue(self.cache_name, agent_dict)

    def getAgent(self, agent_id: int) -> Agent:
        """Retrieve an :class:`.Agent` from this :class:`.AgentClass`.

        Args:
            agent_id (int): Unique identifier of :class:`.Agent` being retrieved.

        Returns:
            Agent: The cached :class:`.Agent` specified by `agent_id`.

        Raises:
            RuntimeError: If the specified :class:`.Agent` has not been cached.
        """
        trans = NestedGet([self.cache_name, agent_id])
        return KeyValueStore.submitTransaction(trans)

    def getCache(self) -> dict[int, Agent]:
        """Retrieve the contents of the entire cache.

        Returns:
            dict[int, Agent]: Dictionary of :class:`.Agent` objects where keys are unique
                identifiers.
        """
        return KeyValueStore.getValue(self.cache_name)


class AgentCaches:
    """Collection of :class:`.AgentCache` objects."""

    targets = AgentCache("target_agents")
    """AgentCache: Cache of :class:`.TargetAgent` objects."""

    sensors = AgentCache("sensor_agents")
    """AgentCache: Cache of :class:`.SensingAgent` objects."""

    estimates = AgentCache("estimate_agents")
    """AgentCache: Cache of :class:`.EstimateAgent` objects."""


class NestedGet(Transaction):
    """Defines a methodology for retrieved nested values in the :class:`.KeyValueStore`."""

    def __init__(self, keys: list):
        """Instantiate a :class:`.NestedGet` transaction.

        Args:
            keys (list[str]): List of keys to lookup at each depth of nesting.
                E.g. `["foo", "bar"]` would evaluate to `key_value_store["foo"]["bar"]`.
        """
        if len(keys) < 1:
            raise ValueError("Nested get transaction requires at least one key.")
        super().__init__(keys[0], request_payload=keys)

    def transact(self, key_value_store):
        """Attempt to retrieve the nested value specified by this transaction from the key value store.

        Note:
            If an error is encountered, this function will not raise an Exception and will instead
                set :attr:`.error`.

        Args:
            key_value_store (dict): Key value store to retrieve the specified nested value from.

        Raises:
            RuntimeError: If specified nested value does not exist in the key value store.
        """
        def levelInfo(depth: int):
            """Return string representation of nested keys being accessed."""
            level_info = "kvs"
            for it in range(depth):
                level_info += f"[{self.request_payload[it]}]"
            return level_info
        level = key_value_store
        for depth, _key in enumerate(self.request_payload):
            try:
                level = level.get(_key)
            except AttributeError:
                err = f"'{levelInfo(depth)}' raised an AttributeError: '{_key}'"
                self.error = RuntimeError(err)
                return
            if level is None:
                err = f"'{levelInfo(depth)}' raised KeyError: '{_key}'"
                self.error = RuntimeError(err)
                return
        self.response_payload = level
