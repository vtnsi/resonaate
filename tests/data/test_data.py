from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from os.path import join
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.data import createDatabasePath

# Local Imports
from ..conftest import FIXTURE_DATA_DIR, SHARED_DB_PATH

# Type Checking Imports
if TYPE_CHECKING:
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
def testFileExists(datafiles: str):
    """Make sure if a file exists, creating a DB doesn't overwrite the file."""
    shared_db_url = join(datafiles, SHARED_DB_PATH)
    with pytest.raises(FileExistsError):
        createDatabasePath(shared_db_url)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testCreateDBPath(datafiles: str):
    """Test null and non-null values of function arguments."""
    # Auto-generate db path:
    db_url = createDatabasePath(None)
    assert db_url is not None

    # Custom-defined db path
    db_path = join(datafiles, "db/new_db.sqlite3")
    db_url = createDatabasePath(db_path)
    assert db_url is not None
