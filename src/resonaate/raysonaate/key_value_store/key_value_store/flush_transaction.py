from __future__ import annotations

# Package Imports
from .transaction import Transaction


class FlushTransaction(Transaction):
    """Flush the contents of the key value store."""

    def __init__(self):
        super().__init__(key=None)

    def transact(self, key_value_store: dict) -> None:
        key_value_store.clear()
        self.response_payload = key_value_store
