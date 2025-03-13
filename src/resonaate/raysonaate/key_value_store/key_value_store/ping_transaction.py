# Standard Library Imports
from time import time_ns
# Package Imports
from .transaction import Transaction


class PingTransaction(Transaction):
    """Simple encapsulation of a ``ping`` transaction that a client could use to test connectivity with the server."""

    def __init__(self):
        super().__init__(None, time_ns())

    def transact(self, key_value_store: dict):
        self.response_payload = time_ns()

    def getResponse(self):
        """Return a dictionary containing relevant ping information.

        Returns:
            dict: With the following items:
                sent (int): Epoch time that the transaction was created (in nanoseconds).
                transacted (int): Epoch time that the transaction was transacted on the server (in nanoseconds).
                received (int): Epoch time that the transaction was returned to the client (in nanoseconds).
        """
        return {
            "sent": self.request_payload,
            "transacted": super().getResponse(),
            "received": time_ns()
        }