from __future__ import annotations

# Standard Library Imports
import os

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common import cli

# Local Imports
from .. import FIXTURE_DATA_DIR, IMPORTER_DB_PATH, JSON_INIT_PATH, SHARED_DB_PATH


def validateArgs(args):
    """Wrap `parser.parseargs()` to catch `SystemExit` for easier unit testing."""
    try:
        parser = cli.getCommandLineParser()
        parser.parse_args(args)
        return True
    except SystemExit:
        return False


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testInitFile(datafiles):
    """Test a valid and a invalid init file."""
    init_file = os.path.join(datafiles, JSON_INIT_PATH, "minimal_init.json")
    assert validateArgs([f"{init_file}"]) is True
    assert validateArgs([f"{init_file}" + "bad"]) is False


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testResonaateDatabaseFile(datafiles):
    """Test a valid and a invalid RESONAATE db file."""
    init_file = os.path.join(datafiles, JSON_INIT_PATH, "minimal_init.json")
    # Any file-like string will work
    db_file1 = os.path.join(datafiles, "db/good.sqlite3")
    db_file2 = os.path.join(datafiles, SHARED_DB_PATH)
    assert validateArgs([init_file, "-d", f"{db_file1}"]) is True
    assert validateArgs([init_file, "--db-path", f"{db_file2}"]) is True
    # Only strings are valid
    with pytest.raises(TypeError):
        assert validateArgs([init_file, "-d", 34209382]) is False


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testImporterDatabaseFile(datafiles):
    """Test a valid and a invalid importer db file."""
    init_file = os.path.join(datafiles, JSON_INIT_PATH, "minimal_init.json")
    # Any file-like string will work
    db_file = os.path.join(datafiles, IMPORTER_DB_PATH)
    assert validateArgs([init_file, "-i", f"{db_file}"]) is True
    assert validateArgs([init_file, "--importer-db-path", f"{db_file}"]) is True
    # Only strings are valid
    with pytest.raises(TypeError):
        assert validateArgs([init_file, "-i", 34209382]) is False
    # Fail file checking logic
    assert validateArgs([init_file, "-i", f"{db_file}" + "bad"]) is False


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testSimTime(datafiles):
    """Test a valid and a invalid importer db file."""
    init_file = os.path.join(datafiles, JSON_INIT_PATH, "minimal_init.json")
    assert validateArgs([init_file, "-t", "0.5"]) is True
    assert validateArgs([init_file, "--time", "0.5"]) is True
    # Only floats are valid
    assert validateArgs([init_file, "-t", "abcde"]) is False


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testDebugMode(datafiles):
    """Test set and unset debug flag values."""
    parser = cli.getCommandLineParser()
    init_file = os.path.join(datafiles, JSON_INIT_PATH, "minimal_init.json")

    args = parser.parse_args([init_file, "-t", "0.5"])
    assert args.debug_mode is False
    args = parser.parse_args([init_file, "-t", "0.5", "--debug"])
    assert args.debug_mode is True
