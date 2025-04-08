"""Module implementing the 'pop' key value store transaction."""

# Standard Library Imports
from collections.abc import MutableSequence

# Local Imports
from .transaction import Transaction


class PopTransaction(Transaction):
    """Transaction encapsulating popping a value from the key value store."""

    def __init__(self, key, index: int = -1):
        """Initialize a :class:`.PopTransaction`.

        Args:
            key: Key to transact with in the key value store.
            index: The index to be popped from the existing value in the key value store.
        """
        super().__init__(key)
        self.request_payload = {
            "index": index,
        }

    @property
    def index(self) -> int:
        """The index to be popped from the existing value."""
        return self.request_payload["index"]

    def transact(self, key_value_store: dict):
        """Retrieve an element from the key value store, and remove it from the existing value.

        Args:
            key_value_store: Dictionary object being transacted upon.
        """
        existing_value = key_value_store.get(self.key)
        if existing_value:
            if isinstance(existing_value, MutableSequence):
                try:
                    value = existing_value.pop(self.index)
                except IndexError:
                    pass
                else:
                    self.response_payload = value
            else:
                self.error = TypeError("Existing value is not a MutableSequence")
