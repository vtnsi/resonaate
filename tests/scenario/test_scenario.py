# pylint: disable=unused-argument
from __future__ import annotations

# Standard Library Imports
import os.path

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.data.importer_database import ImporterDatabase
from resonaate.scenario import buildScenarioFromConfigFile

# Local Imports
from .. import FIXTURE_DATA_DIR, IMPORTER_DB_PATH, JSON_INIT_PATH


@pytest.mark.usefixtures("reset_shared_db")
class TestScenarioFactory:
    """Tests for :func:`.scenarioFactory`."""

    VALID_JSON_CONFIGS = [
        "minimal_init.json",
        "default_imported_est_imported_obs.json",
        "default_realtime_est_realtime_obs.json",
    ]

    INVALID_JSON_CONFIGS = [
        "no_sensor_set_init.json",
        "no_target_set_init.json",
    ]

    EMPTY_JSON_ENGINE_CONFIGS = [
        "no_sensors_init.json",
        "no_targets_init.json",
    ]

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testBuildFromConfig(self, datafiles: str):
        """Test building a scenario from config files."""
        init_filepath = os.path.join(
            datafiles, JSON_INIT_PATH, "default_realtime_est_realtime_obs.json"
        )
        _ = buildScenarioFromConfigFile(
            init_filepath, internal_db_path=None, importer_db_path=None
        )

    @pytest.mark.parametrize("init_file", VALID_JSON_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testValidInitMessages(self, datafiles: str, init_file: str):
        """Test passing a valid init messages."""
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        init_dir = os.path.join(datafiles, JSON_INIT_PATH)
        init_file_path = os.path.join(init_dir, init_file)

        _ = buildScenarioFromConfigFile(
            init_file_path,
            internal_db_path=None,
            importer_db_path=db_path if "import" in init_file else None,
        )

        if "import" in init_file:
            importer_db.resetData(tables=ImporterDatabase.VALID_DATA_TYPES)

    @pytest.mark.parametrize("init_file", INVALID_JSON_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInvalidInitMessages(self, datafiles: str, init_file: str):
        """Test passing a invalid init messages."""
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        init_dir = os.path.join(datafiles, JSON_INIT_PATH)
        init_file_path = os.path.join(init_dir, init_file)

        # Check missing target_set & sensor_set fields
        with pytest.raises(KeyError):
            _ = buildScenarioFromConfigFile(
                init_file_path,
                internal_db_path=None,
                importer_db_path=db_path if "import" in init_file else None,
            )

        if "import" in init_file:
            importer_db.resetData(tables=ImporterDatabase.VALID_DATA_TYPES)

    @pytest.mark.parametrize("init_file", EMPTY_JSON_ENGINE_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInvalidEngineConfigs(self, datafiles: str, init_file: str):
        """Test passing a invalid engine."""
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        init_dir = os.path.join(datafiles, JSON_INIT_PATH)
        init_file_path = os.path.join(init_dir, init_file)

        # Check for empty target and sensor configs
        error_msg = r"Empty JSON file: \/.*?\.json+"
        with pytest.raises(IOError, match=error_msg):
            buildScenarioFromConfigFile(
                init_file_path,
                internal_db_path=None,
                importer_db_path=db_path if "import" in init_file else None,
            )

        if "import" in init_file:
            importer_db.resetData(tables=ImporterDatabase.VALID_DATA_TYPES)
