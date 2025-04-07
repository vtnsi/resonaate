"""Module implementing the 'flush' key value store transaction."""

from __future__ import annotations

# Local Imports
from .transaction import Transaction


class FlushTransaction(Transaction):
    """Implements a transaction that flushes the key value store."""

    def __init__(self):
        """Initialize a :class:`.FlushTransaction`."""
        super().__init__(key=None)

    def transact(self, key_value_store: dict) -> None:
        """Flush the contents of the key value store.

        Args:
            key_value_store: The dictionary object being transacted on.

        See Also:
            :meth:`.KeyValueStore.flush()`.
        """
        key_value_store.clear()
        self.response_payload = key_value_store
