# Standard Library Imports
from collections.abc import MutableSequence
# Package Imports
from .transaction import Transaction


class AppendTransaction(Transaction):
    """Append a value to the value specified by :attr:`.key` from the :class:`.KeyValueStore`."""

    def transact(self, key_value_store: dict):
        existing_value = key_value_store.get(self.key)
        if existing_value:
            if isinstance(existing_value, MutableSequence):
                existing_value.append(self.request_payload)
            else:
                self.error = TypeError("Existing value is not a MutableSequence")
        else:
            key_value_store[self.key] = [self.request_payload]
        self.response_payload = key_value_store[self.key]
