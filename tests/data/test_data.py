from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.data import createDatabasePath

# Local Imports
from .. import FIXTURE_DATA_DIR, SHARED_DB_PATH

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from pathlib import Path

    # RESONAATE Imports
    from resonaate.data.agent import AgentModel
    from resonaate.data.epoch import Epoch


def testComparison(epoch: Epoch, target_agent: AgentModel):
    """Ensure comparison between data objects behave properly."""
    with pytest.raises(TypeError):
        assert epoch == target_agent

    new_target = deepcopy(target_agent)
    assert new_target == target_agent


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testFileExists(datafiles: Path):
    """Make sure if a file exists, creating a DB doesn't overwrite the file."""
    shared_db_url = datafiles.joinpath(SHARED_DB_PATH)
    shared_db_url.touch()
    with pytest.raises(FileExistsError):
        createDatabasePath(shared_db_url)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testCreateDBPath(datafiles: Path):
    """Test null and non-null values of function arguments."""
    # Auto-generate db path:
    db_url = createDatabasePath(None)
    assert db_url is not None

    # Custom-defined db path
    db_path = datafiles.joinpath("db/new_db.sqlite3")
    db_url = createDatabasePath(db_path)
    assert db_url is not None
