"""Module implementing the 'set' key value store transaction."""

# Local Imports
from .transaction import Transaction


class SetTransaction(Transaction):
    """Transaction encapsulating setting a value in the key value store."""

    def transact(self, key_value_store: dict):
        """Set the value specified by :attr:`.key` to :attr:`.request_payload`.

        Args:
            key_value_store: Dictionary object being transacted upon.
        """
        key_value_store[self.key] = self.request_payload
        self.response_payload = self.request_payload
