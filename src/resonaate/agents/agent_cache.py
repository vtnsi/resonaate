# Third Party Imports
from strmbrkr.key_value_store.transaction import Transaction


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
        level = key_value_store
        for depth, _key in enumerate(self.request_payload):
            def levelInfo():
                level_info = "kvs"
                for it in range(depth):
                    level_info += f"[{self.request_payload[it]}]"
                return level_info

            try:
                level = level.get(_key)
            except AttributeError:
                err = f"'{levelInfo()}' raised an AttributeError: '{_key}'"
                self.error = RuntimeError(err)
                return
            if level is None:
                err = f"'{levelInfo()}' raised KeyError: '{_key}'"
                self.error = RuntimeError(err)
                return
        self.response_payload = level
