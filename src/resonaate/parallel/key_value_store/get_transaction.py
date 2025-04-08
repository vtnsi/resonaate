"""Module implementing the 'get' key value store transaction."""

# Local Imports
from .transaction import Transaction


class GetTransaction(Transaction):
    """Transaction encapsulating retrieving a value from the key value store."""

    def transact(self, key_value_store):
        """Retrieve the value specified by :attr:`.key` from the key value store."""
        self.response_payload = key_value_store.get(self.key)
