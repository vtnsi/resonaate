from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.config import OutputDbUrlSpec
from resonaate.data.db_connection import (
    DB_PARAMS_KEY,
    DBConnectionError,
    ExclusiveSet,
    _GetDBConnection,
    clearDBParams,
    getDBConnection,
    setDBParams,
)
from resonaate.data.resonaate_database import ResonaateDatabase
from resonaate.parallel.key_value_store import KeyValueStore

# Local Imports
from .. import FIXTURE_DATA_DIR, SHARED_DB_PATH

if TYPE_CHECKING:
    # Standard Library Imports
    from pathlib import Path


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testSetParams(datafiles: Path):
    """Test setting the DB path using KVS."""
    db_params = OutputDbUrlSpec(output_db_name=str(datafiles.joinpath(SHARED_DB_PATH)))

    # Ensure db path is set
    setDBParams(db_params)
    assert KeyValueStore.getValue(DB_PARAMS_KEY) == db_params.model_dump_json()

    # Ensure error raised on setting db path twice
    with pytest.raises(DBConnectionError):
        setDBParams(db_params)

    KeyValueStore.flush()


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testGetDB(datafiles: Path):
    """Test getting the DB instance using KVS."""
    db_params = OutputDbUrlSpec(output_db_name=str(datafiles.joinpath(SHARED_DB_PATH)))

    # Ensure db path is set before getting db connections
    with pytest.raises(DBConnectionError):
        getDBConnection()

    setDBParams(db_params)

    # Ensure db connection is same instance
    db_inst = getDBConnection()
    other_inst = getDBConnection()
    assert db_inst is other_inst


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testClearPath(datafiles: Path):
    """Test clearing the DB path using KVS."""
    db_params = OutputDbUrlSpec(output_db_name=str(datafiles.joinpath(SHARED_DB_PATH)))

    # Ensure db path is set before getting db connections
    setDBParams(db_params)
    assert KeyValueStore.getValue(DB_PARAMS_KEY) is not None

    clearDBParams()
    assert KeyValueStore.getValue(DB_PARAMS_KEY) is None

    # getting DB connection should now fail
    with pytest.raises(DBConnectionError):
        getDBConnection()

    # key should be empty
    assert KeyValueStore.getValue(DB_PARAMS_KEY) is None
    KeyValueStore.flush()


def testExclusiveSetTransact():
    """Test exclusive set transaction."""
    kvs = {}
    value = "a_path_to_db"
    transaction = ExclusiveSet(DB_PARAMS_KEY, value)
    transaction.transact(kvs)

    assert kvs[DB_PARAMS_KEY] == value
    assert transaction.request_payload == value
    assert transaction.response_payload == value
    assert transaction.error is None

    # Ensure that once the key is set, it fails via setting error
    new_transaction = ExclusiveSet(DB_PARAMS_KEY, "new_value")
    new_transaction.transact(kvs)
    assert isinstance(new_transaction.error, KeyError)

    # Different key should work though
    new_transaction = ExclusiveSet("other_key", "new_value")
    new_transaction.transact(kvs)
    assert new_transaction.error is None


def testDBConnectionTransact():
    """Test DB connection transaction."""
    kvs = {}
    transaction = _GetDBConnection(DB_PARAMS_KEY)

    # Test fail when key hasn't been set
    transaction.transact(kvs)
    assert isinstance(transaction.error, DBConnectionError)

    # Now make sure it works with a set key
    transaction = _GetDBConnection(DB_PARAMS_KEY)
    value = object()
    kvs[DB_PARAMS_KEY] = value
    transaction.transact(kvs)
    assert transaction.response_payload == value
    assert transaction.error is None


def testDBConnectionGetResponse(tmp_path: Path):
    """Test DB connection get response."""
    tmp_db_path = tmp_path / "temp_db.sqlite3"
    transaction = _GetDBConnection(DB_PARAMS_KEY)
    transaction.response_payload = OutputDbUrlSpec(output_db_name=str(tmp_db_path)).model_dump_json()

    response = transaction.getResponse()
    assert isinstance(response, ResonaateDatabase)

    new_response = transaction.getResponse()
    assert new_response is response
