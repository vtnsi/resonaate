# Standard Library Imports
from collections.abc import MutableSequence
# Package Imports
from .transaction import Transaction


class PopTransaction(Transaction):
    """Remove and return an element of the current value specified by :attr:`.key`."""

    def transact(self, key_value_store: dict):
        existing_value = key_value_store.get(self.key)
        if existing_value:
            if isinstance(existing_value, MutableSequence):
                try:
                    value = existing_value.pop(self.request_payload)
                except IndexError:
                    pass
                else:
                    self.response_payload = value
            else:
                self.error = TypeError("Existing value is not a MutableSequence")
