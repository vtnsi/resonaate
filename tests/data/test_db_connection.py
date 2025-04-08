from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.data.db_connection import (
    DB_PATH_KEY,
    DBConnectionError,
    ExclusiveSet,
    _GetDBConnection,
    clearDBPath,
    getDBConnection,
    setDBPath,
)
from resonaate.data.resonaate_database import ResonaateDatabase
from resonaate.parallel.key_value_store import KeyValueStore

# Local Imports
from .. import FIXTURE_DATA_DIR, SHARED_DB_PATH

if TYPE_CHECKING:
    # Standard Library Imports
    from pathlib import Path


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testSetPath(datafiles: Path):
    """Test setting the DB path using KVS."""
    db_path = "sqlite:///" + str(datafiles.joinpath(SHARED_DB_PATH))

    # Ensure db path is set
    setDBPath(db_path)
    assert KeyValueStore.getValue(DB_PATH_KEY) == db_path

    # Ensure error raised on setting db path twice
    with pytest.raises(DBConnectionError):
        setDBPath(db_path)

    KeyValueStore.flush()


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testGetDB(datafiles: Path):
    """Test getting the DB instance using KVS."""
    db_path = "sqlite:///" + str(datafiles.joinpath(SHARED_DB_PATH))

    # Ensure db path is set before getting db connections
    with pytest.raises(DBConnectionError):
        getDBConnection()

    setDBPath(db_path)

    # Ensure db connection is same instance
    db_inst = getDBConnection()
    other_inst = getDBConnection()
    assert db_inst is other_inst
    KeyValueStore.flush()


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testClearPath(datafiles: Path):
    """Test clearing the DB path using KVS."""
    db_path = "sqlite:///" + str(datafiles.joinpath(SHARED_DB_PATH))

    # Ensure db path is set before getting db connections
    setDBPath(db_path)
    assert KeyValueStore.getValue(DB_PATH_KEY) is not None

    clearDBPath()

    # getting DB connection should now fail
    with pytest.raises(DBConnectionError):
        getDBConnection()

    # key should be empty
    assert KeyValueStore.getValue(DB_PATH_KEY) is None
    KeyValueStore.flush()


def testExclusiveSetTransact():
    """Test exclusive set transaction."""
    kvs = {}
    value = "a_path_to_db"
    transaction = ExclusiveSet(DB_PATH_KEY, value)
    transaction.transact(kvs)

    assert kvs[DB_PATH_KEY] == value
    assert transaction.request_payload == value
    assert transaction.response_payload == value
    assert transaction.error is None

    # Ensure that once the key is set, it fails via setting error
    new_transaction = ExclusiveSet(DB_PATH_KEY, "new_value")
    new_transaction.transact(kvs)
    assert isinstance(new_transaction.error, KeyError)

    # Different key should work though
    new_transaction = ExclusiveSet("other_key", "new_value")
    new_transaction.transact(kvs)
    assert new_transaction.error is None


def testDBConnectionTransact():
    """Test DB connection transaction."""
    kvs = {}
    transaction = _GetDBConnection(DB_PATH_KEY)

    # Test fail when key hasn't been set
    transaction.transact(kvs)
    assert isinstance(transaction.error, DBConnectionError)

    # Now make sure it works with a set key
    transaction = _GetDBConnection(DB_PATH_KEY)
    value = object()
    kvs[DB_PATH_KEY] = value
    transaction.transact(kvs)
    assert transaction.response_payload == value
    assert transaction.error is None


def testDBConnectionGetResponse():
    """Test DB connection get response."""
    transaction = _GetDBConnection(DB_PATH_KEY)
    transaction.response_payload = "sqlite://"

    response = transaction.getResponse()
    assert isinstance(response, ResonaateDatabase)

    new_response = transaction.getResponse()
    assert new_response is response

    transaction.response_payload = None
    new_response = transaction.getResponse()
    assert isinstance(new_response, ResonaateDatabase)
    assert new_response is not response
