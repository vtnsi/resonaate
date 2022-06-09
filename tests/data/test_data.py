# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from copy import deepcopy
from os.path import join
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.data import createDatabasePath
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase, FIXTURE_DATA_DIR


class TestDataModule(BaseTestCase):
    """Tests for :class:`.DataInterface` class."""

    def testComparison(self, epoch, target_agent):
        """Ensure comparison between data objects behave properly."""
        with pytest.raises(TypeError):
            assert epoch == target_agent

        new_target = deepcopy(target_agent)
        assert new_target == target_agent

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testFileExists(self, datafiles):
        """Make sure if a file exists, creating a DB doesn't overwrite the file."""
        shared_db_url = join(datafiles, self.shared_db_path)
        with pytest.raises(FileExistsError):
            createDatabasePath(shared_db_url)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testCreateDBPath(self, datafiles):
        """Test null and non-null values of function arguments."""
        # Auto-generate db path:
        db_url = createDatabasePath(None)
        assert db_url is not None

        # Custom-defined db path
        db_path = join(datafiles, "db/new_db.sqlite3")
        db_url = createDatabasePath(db_path)
        assert db_url is not None
