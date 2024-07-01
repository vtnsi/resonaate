from __future__ import annotations

# Standard Library Imports
from pathlib import Path

# Third Party Imports
import pytest
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.data.filter_step import FilterStep
from resonaate.scenario import buildScenarioFromConfigFile
from resonaate.scenario.scenario import Scenario

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
            start_workers=False,
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
            start_workers=False,
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
                start_workers=False,
            )

    @pytest.mark.parametrize("init_file", EMPTY_JSON_ENGINE_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInvalidEngineConfigs(self, datafiles: str, init_file: str):
        """Test passing a invalid engine."""
        init_dir = Path(datafiles).joinpath(JSON_INIT_PATH)
        init_file_path = init_dir.joinpath(init_file)

        # Check for empty target and sensor configs
        error_msg = r"Empty JSON file: \/.*?\.json+"
        with pytest.raises(IOError, match=error_msg):
            buildScenarioFromConfigFile(
                init_file_path,
                internal_db_path=None,
                importer_db_path=None,
                start_workers=False,
            )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testFilterStepDB(self, datafiles: str):
        """Tests functionality of saving filter steps to the database.

        Args:
            datafiles (str): path to your data file.
        """
        init_filepath = Path(datafiles).joinpath(
            JSON_INIT_PATH,
            "default_realtime_est_realtime_obs.json",
        )
        test_scenario: Scenario = buildScenarioFromConfigFile(
            init_filepath,
            internal_db_path=None,
            importer_db_path=None,
            start_workers=False,
        )

        # Propagate scenrio here so we're not playing with empty filter step arrays

        # Get all the filter steps associated with the scenario
        filter_steps: list[FilterStep] = []  # These are the initial filter steps pre-test
        agents: list[EstimateAgent] = [
            test_scenario.estimate_agents[key] for key in test_scenario.estimate_agents
        ]
        for agent in agents:
            filter_steps += agent.getFilterSteps()

        # Go ahead and save filter steps
        test_scenario.saveDatabaseOutput()

        # Now go ahead and read in all the saved filter steps from the db
        filter_step_query = Query(FilterStep)
        db_filter_steps: list = test_scenario.database.getData(filter_step_query)

        for filter_step in filter_steps:  # Totally broken.
            assert filter_step in db_filter_steps
