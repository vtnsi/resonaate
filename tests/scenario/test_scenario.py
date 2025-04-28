from __future__ import annotations

# Standard Library Imports
from pathlib import Path

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.scenario import buildScenarioFromConfigFile

# Local Imports
from .. import FIXTURE_DATA_DIR, IMPORTER_DB_PATH, JSON_INIT_PATH


class TestScenarioFactory:
    """Tests for :func:`.scenarioFactory`."""

    VALID_JSON_CONFIGS = [  # noqa: RUF012
        "minimal_init.json",
        "default_imported_est_imported_obs.json",
        "default_realtime_est_realtime_obs.json",
    ]

    INVALID_JSON_CONFIGS = [  # noqa: RUF012
        "no_sensor_set_init.json",
        "no_target_set_init.json",
    ]

    EMPTY_JSON_ENGINE_CONFIGS = [  # noqa: RUF012
        "no_sensors_init.json",
        "no_targets_init.json",
    ]

    @pytest.mark.usefixtures("custom_database")
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testBuildFromConfig(self, datafiles: str):
        """Test building a scenario from config files."""
        init_filepath = Path(datafiles).joinpath(
            JSON_INIT_PATH,
            "default_realtime_est_realtime_obs.json",
        )
        _ = buildScenarioFromConfigFile(
            init_filepath,
            internal_db_path=None,
            importer_db_path=None,
        )

    @pytest.mark.usefixtures("custom_database")
    @pytest.mark.parametrize("init_file", VALID_JSON_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testValidInitMessages(self, datafiles: str, init_file: str):
        """Test passing a valid init messages."""
        db_path = Path(datafiles).joinpath(IMPORTER_DB_PATH)
        init_dir = Path(datafiles).joinpath(JSON_INIT_PATH)
        init_file_path = init_dir.joinpath(init_file)

        _ = buildScenarioFromConfigFile(
            init_file_path,
            internal_db_path=None,
            importer_db_path=db_path if "import" in init_file else None,
        )

    @pytest.mark.parametrize("init_file", INVALID_JSON_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInvalidInitMessages(self, datafiles: str, init_file: str):
        """Test passing a invalid init messages."""
        init_dir = Path(datafiles).joinpath(JSON_INIT_PATH)
        init_file_path = init_dir.joinpath(init_file)

        # Check missing target_set & sensor_set fields
        with pytest.raises(KeyError):
            _ = buildScenarioFromConfigFile(
                init_file_path,
                internal_db_path=None,
                importer_db_path=None,
            )

    @pytest.mark.parametrize("init_file", EMPTY_JSON_ENGINE_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInvalidEngineConfigs(self, datafiles: str, init_file: str):
        """Test passing a invalid engine."""
        init_dir = Path(datafiles).joinpath(JSON_INIT_PATH)
        init_file_path = init_dir.joinpath(init_file)

        # Check for empty target and sensor configs
        with pytest.raises(IOError, match="Empty JSON file:") as io_err:
            buildScenarioFromConfigFile(
                init_file_path,
                internal_db_path=None,
                importer_db_path=None,
            )
        err_msg: str = io_err.value.args[0]
        assert err_msg.endswith(".json")
