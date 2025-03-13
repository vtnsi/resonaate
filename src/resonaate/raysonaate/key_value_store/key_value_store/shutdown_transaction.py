# Package Imports
from .transaction import Transaction


class ShutdownTransaction(Transaction):
    """Shutdown the :class:`.KeyValueStore.Server`."""

    def __init__(self):
        super().__init__(self.SERVER_SHUTDOWN_KEY)

    def _allowShutdown(self):
        return True

    def transact(self, key_value_store: dict):
        key_value_store[self.key] = True
        self.response_payload = True
