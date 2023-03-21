from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from mjolnir import KeyValueStore

# RESONAATE Imports
from resonaate.data.db_connection import (
    DB_PATH_KEY,
    DBConnectionError,
    clearDBPath,
    getDBConnection,
    setDBPath,
)

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
