"""Manage shared database connections."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ..common.config import OutputDbUrlSpec
from ..parallel.key_value_store import KeyValueStore
from ..parallel.key_value_store.transaction import Transaction

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any, ClassVar

    # Local Imports
    from .resonaate_database import ResonaateDatabase


DB_PARAMS_KEY: str = "db_connection_params"
"""Key used to store database connection parameters in the key value store."""


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
        self.response_payload = key_value_store.get(DB_PARAMS_KEY)
        if self.response_payload is None:
            self.error = DBConnectionError(
                "setDBParams() must be called once before getDBConnection()",
            )

    def getResponse(self) -> Any:
        """Returns the response payload of this executed transaction.

        Returns:
            ``Any``: Response payload of this executed transaction.

        Raises:
            Exception: If an error occurred while executing this transaction.
        """
        params_json = super().getResponse()
        if self.__cached_interfaces.get(params_json) is None:
            # Local Imports
            from .resonaate_database import ResonaateDatabase

            valid_db_params = OutputDbUrlSpec.model_validate_json(params_json)
            self.__cached_interfaces[params_json] = ResonaateDatabase(
                connection_params=valid_db_params
            )
        return self.__cached_interfaces[params_json]


def setDBParams(connection_params: OutputDbUrlSpec) -> None:
    """Set the shared DB path in the KVS.

    This must be called before any DB interactions, and it should only be called once.

    Args:
        connection_params: Collection of parameters specifying how to connect to the shared database.
    """
    try:
        KeyValueStore.submitTransaction(
            ExclusiveSet(DB_PARAMS_KEY, connection_params.model_dump_json())
        )
    except KeyError as err:
        raise DBConnectionError(
            "setDBParams() should only be called once per script/simulation",
        ) from err


def clearDBParams() -> None:
    """Clear the KVS of the database connections."""
    KeyValueStore.setValue(DB_PARAMS_KEY, None)


def getDBConnection() -> ResonaateDatabase:
    """Retrieve the shared database instance from the KVS.

    This fails if :func:`.setDBParams` is not properly called first.

    Returns:
        :class:`.ResonaateDatabase`: valid instance of shared database.
    """
    return KeyValueStore.submitTransaction(_GetDBConnection(DB_PARAMS_KEY))
