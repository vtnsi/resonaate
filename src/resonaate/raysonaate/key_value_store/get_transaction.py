# Package Imports
from .transaction import Transaction


class GetTransaction(Transaction):
    """Retrieve the value specified by :attr:`.key` from the :class:`.KeyValueStore`."""

    def transact(self, key_value_store):
        self.response_payload = key_value_store.get(self.key)
