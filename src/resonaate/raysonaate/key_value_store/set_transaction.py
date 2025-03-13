# Package Imports
from .transaction import Transaction


class SetTransaction(Transaction):
    """Set the value specified by :attr:`.key` in the :class:`.KeyValueStore`."""

    def transact(self, key_value_store: dict):
        key_value_store[self.key] = self.request_payload
        self.response_payload = self.request_payload
