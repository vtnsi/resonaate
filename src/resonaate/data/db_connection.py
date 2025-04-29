"""Manage shared database connections."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ..parallel.key_value_store import KeyValueStore
from ..parallel.key_value_store.transaction import Transaction

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any, ClassVar

    # Local Imports
    from .resonaate_database import ResonaateDatabase


DB_PATH_KEY = "db_path"
"""``str``: common KVS key for """


class DBConnectionError(Exception):
    """Raised during failed database connection requests."""


class ExclusiveSet(Transaction):
    """Set transaction that fails if the key already exists."""

    def transact(self, key_value_store: dict) -> None:
        """Execute the transaction on the specified `key_value_store`.

        Args:
            key_value_store (``dict``): Key value store to execute the encapsulated transaction on.
        """
        if key_value_store.get(self.key):
            self.error = KeyError(self.key)
        else:
            key_value_store[self.key] = self.request_payload
            self.response_payload = self.request_payload


class _GetDBConnection(Transaction):
    """Transaction logic for managing shared database connections."""

    __cached_interfaces: ClassVar[dict[str, Any]] = {}

    def transact(self, key_value_store: dict) -> None:
        """Execute the transaction on the specified `key_value_store`.

        Args:
            key_value_store (``dict``): Key value store to execute the encapsulated transaction on.
        """
        self.response_payload = key_value_store.get(DB_PATH_KEY)
        if self.response_payload is None:
            self.error = DBConnectionError(
                "setDBPath() must be called once before getDBConnection()",
            )

    def getResponse(self) -> Any:
        """Returns the response payload of this executed transaction.

        Returns:
            ``Any``: Response payload of this executed transaction.

        Raises:
            Exception: If an error occurred while executing this transaction.
        """
        db_path = super().getResponse()
        if self.__cached_interfaces.get(db_path) is None:
            # Local Imports
            from .resonaate_database import ResonaateDatabase

            self.__cached_interfaces[db_path] = ResonaateDatabase(db_path=db_path)
        return self.__cached_interfaces[db_path]


def setDBPath(path: str) -> None:
    """Set the shared DB path in the KVS.

    This must be called before any DB interactions, and it should only be called once.

    Args:
        path (``str``): qualified SQL database path.
    """
    try:
        KeyValueStore.submitTransaction(ExclusiveSet(DB_PATH_KEY, path))
    except KeyError as err:
        raise DBConnectionError(
            "setDBPath() should only be called once per script/simulation",
        ) from err


def clearDBPath() -> None:
    """Clear the KVS of the database connections."""
    KeyValueStore.setValue(DB_PATH_KEY, None)


def getDBConnection() -> ResonaateDatabase:
    """Retrieve the shared database instance from the KVS.

    This fails if :func:`.setDBPath` is not properly called first.

    Returns:
        :class:`.ResonaateDatabase`: valid instance of shared database.
    """
    return KeyValueStore.submitTransaction(_GetDBConnection(DB_PATH_KEY))
