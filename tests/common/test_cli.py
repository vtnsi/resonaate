# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
import os
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.common import cli
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase, FIXTURE_DATA_DIR


class TestCommandLineInterface(BaseTestCase):
    """Test all functions in cli module."""

    def validateArgs(self, args):
        """Wrap `parser.parseargs()` to catch `SystemExit` for easier unit testing."""
        try:
            parser = cli.getCommandLineParser()
            parser.parse_args(args)
            return True
        except SystemExit:
            return False

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInitFile(self, datafiles):
        """Test a valid and a invalid init file."""
        init_file = os.path.join(datafiles, self.json_init_path, "minimal_init.json")
        assert self.validateArgs([f'{init_file}']) is True
        assert self.validateArgs([f'{init_file}' + 'bad']) is False

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testResonaateDatabaseFile(self, datafiles):
        """Test a valid and a invalid RESONAATE db file."""
        init_file = os.path.join(datafiles, self.json_init_path, "minimal_init.json")
        # Any file-like string will work
        db_file1 = os.path.join(datafiles, "db/good.sqlite3")
        db_file2 = os.path.join(datafiles, self.shared_db_path)
        assert self.validateArgs([init_file, '-d', f'{db_file1}']) is True
        assert self.validateArgs([init_file, '--db-path', f'{db_file2}']) is True
        # Only strings are valid
        with pytest.raises(TypeError):
            assert self.validateArgs([init_file, '-d', 34209382]) is False

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterDatabaseFile(self, datafiles):
        """Test a valid and a invalid importer db file."""
        init_file = os.path.join(datafiles, self.json_init_path, "minimal_init.json")
        # Any file-like string will work
        db_file = os.path.join(datafiles, self.importer_db_path)
        assert self.validateArgs([init_file, '-i', f'{db_file}']) is True
        assert self.validateArgs([init_file, '--importer-db-path', f'{db_file}']) is True
        # Only strings are valid
        with pytest.raises(TypeError):
            assert self.validateArgs([init_file, '-i', 34209382]) is False
        # Fail file checking logic
        assert self.validateArgs([init_file, '-i', f'{db_file}' + 'bad']) is False

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testSimTime(self, datafiles):
        """Test a valid and a invalid importer db file."""
        init_file = os.path.join(datafiles, self.json_init_path, "minimal_init.json")
        assert self.validateArgs([init_file, '-t', '0.5']) is True
        assert self.validateArgs([init_file, '--time', '0.5']) is True
        # Only floats are valid
        assert self.validateArgs([init_file, '-t', 'abcde']) is False

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testDebugMode(self, datafiles):
        """Test set and unset debug flag values."""
        parser = cli.getCommandLineParser()
        init_file = os.path.join(datafiles, self.json_init_path, "minimal_init.json")

        args = parser.parse_args([init_file, '-t', '0.5'])
        assert args.debug_mode is False
        args = parser.parse_args([init_file, '-t', '0.5', '--debug'])
        assert args.debug_mode is True
