# pylint: disable=unused-argument
from __future__ import annotations

# Standard Library Imports
import os.path
from datetime import timedelta
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from numpy import isclose
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.detected_maneuver import DetectedManeuver
from resonaate.data.importer_database import ImporterDatabase
from resonaate.data.observation import Observation
from resonaate.physics.time.conversions import getTargetJulianDate
from resonaate.physics.time.stardate import JulianDate
from resonaate.scenario import buildScenarioFromConfigDict, buildScenarioFromConfigFile
from resonaate.scenario.config import ScenarioConfig

# Local Imports
from ..conftest import (
    FIXTURE_DATA_DIR,
    IMPORTER_DB_PATH,
    JSON_INIT_PATH,
    JSON_RSO_TRUTH,
    JSON_SENSOR_TRUTH,
    SHARED_DB_PATH,
)

# Type Checking Imports
if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.parallel import Redis
    from resonaate.scenario import Scenario


@pytest.fixture()
def _fixtureSetup(redis: Redis, reset_shared_db: None) -> None:
    """Instantiate redis & reset DB properly."""


def propagateScenario(
    data_directory: str,
    init_filepath: str,
    elapsed_time: timedelta,
    importer_db_path: str | None = None,
) -> Scenario:
    """Performs the basic operations required to step a simulation forward in time.

    Args:
        data_directory (str): file path for datafiles directory
        init_filepath (str): file path for Resonaate initialization file
        elapsed_time (`timedelta`): amount of time to simulate
        importer_db_path (``str``): path to external importer database for pre-canned data.
    """
    init_file = os.path.join(data_directory, JSON_INIT_PATH, init_filepath)
    shared_db_path = "sqlite:///" + os.path.join(data_directory, SHARED_DB_PATH)

    # Create scenario from JSON init message
    config_dict = ScenarioConfig.parseConfigFile(init_file)

    app = buildScenarioFromConfigDict(
        config_dict,
        internal_db_path=shared_db_path,
        importer_db_path=importer_db_path,
    )

    # Determine target Julian date based on elapsed time
    init_julian_date = JulianDate(app.clock.julian_date_start)
    target_julian_date = getTargetJulianDate(init_julian_date, elapsed_time)

    # Propagate scenario forward in time
    app.propagateTo(target_julian_date)

    assert isclose(app.clock.julian_date_epoch, target_julian_date)

    app.shutdown(flushall=True)

    return app


def loadTargetTruthData(directory: str, importer_database: ImporterDatabase) -> None:
    """Load truth data for RSO targets into DB for Importer model."""
    importer_database.initDatabaseFromJSON(
        os.path.join(directory, JSON_RSO_TRUTH, "11111-truth.json"),
        os.path.join(directory, JSON_RSO_TRUTH, "11112-truth.json"),
    )


def loadSensorTruthData(directory: str, importer_database: ImporterDatabase) -> None:
    """Load truth data for satellite sensors into DB for Importer model."""
    importer_database.initDatabaseFromJSON(
        os.path.join(directory, JSON_SENSOR_TRUTH, "60007-truth.json"),
        os.path.join(directory, JSON_SENSOR_TRUTH, "60008-truth.json"),
    )


@pytest.mark.scenario()
@pytest.mark.usefixtures("_fixtureSetup")
class TestScenarioApp:
    """Test class for scenario class."""

    MANEUVER_DETECTION_INIT = (
        "maneuver_detection_standard_nis.json",
        "maneuver_detection_sliding_nis.json",
        "maneuver_detection_fading_nis.json",
    )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testBuildFromConfig(self, datafiles: str):
        """Test building a scenario from config files."""
        init_filepath = os.path.join(
            datafiles, JSON_INIT_PATH, "default_realtime_est_realtime_obs.json"
        )
        _ = buildScenarioFromConfigFile(
            init_filepath, internal_db_path=None, importer_db_path=None
        )

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagation(self, datafiles: str):
        """Test a small simulation using real time propagation. 5 minute long test."""
        init_filepath = "default_realtime_est_realtime_obs.json"
        elapsed_time = timedelta(minutes=5)
        propagateScenario(datafiles, init_filepath, elapsed_time)

    @pytest.mark.slow()
    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagationLong(self, datafiles: str):
        """Test a small simulation using real time propagation. 5 hour long test."""
        init_filepath = "long_full_ssn_realtime_est_realtime_obs.json"
        elapsed_time = timedelta(hours=5)
        propagateScenario(datafiles, init_filepath, elapsed_time)

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testTruthSimulationOnly(self, datafiles: str, caplog: pytest.LogCaptureFixture):
        """Test a small simulation with Tasking and Estimation turned off."""
        init_filepath = "truth_simulation_only_init.json"
        elapsed_time = timedelta(minutes=10)
        propagateScenario(datafiles, init_filepath, elapsed_time)

        for record_tuple in caplog.record_tuples:
            assert record_tuple[2] != "Assess"

    @pytest.mark.importer()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModel(self, datafiles: str, reset_importer_db: None):
        """Test a small simulation using imported data. 5 minute long test."""
        init_filepath = "default_imported_est_imported_obs.json"
        elapsed_time = timedelta(minutes=5)
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        loadTargetTruthData(datafiles, importer_db)
        propagateScenario(datafiles, init_filepath, elapsed_time, importer_db_path=db_path)

    @pytest.mark.importer()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelForSensors(self, datafiles: str, reset_importer_db: None):
        """Include sensors that will utilize the importer model in a 5 minute test."""
        init_filepath = "long_sat_sen_imported_est_imported_obs.json"
        elapsed_time = timedelta(minutes=5)
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        loadTargetTruthData(datafiles, importer_db)
        loadSensorTruthData(datafiles, importer_db)
        propagateScenario(datafiles, init_filepath, elapsed_time, importer_db_path=db_path)

    @pytest.mark.slow()
    @pytest.mark.importer()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelLong(self, datafiles: str, reset_importer_db: None):
        """Test a small simulation using imported data. 5 day hour test."""
        init_filepath = "long_full_ssn_imported_est_imported_obs.json"
        elapsed_time = timedelta(hours=5)
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        loadTargetTruthData(datafiles, importer_db)
        propagateScenario(datafiles, init_filepath, elapsed_time, importer_db_path=db_path)

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    @pytest.mark.parametrize("init_filepath", MANEUVER_DETECTION_INIT)
    def testDetectedManeuver(self, datafiles: str, init_filepath: str):
        """Test a maneuver detection simulation using real time propagation. 20 minute long test."""
        elapsed_time = timedelta(minutes=20)
        app = propagateScenario(datafiles, init_filepath, elapsed_time)
        maneuver_query = Query(DetectedManeuver)
        assert app.database.getData(maneuver_query, multi=False) is not None

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testNoDetectedManeuver(self, datafiles: str):
        """Test no maneuver detection simulation using real time propagation. 20 minute long test."""
        init_filepath = "no_maneuver_detection_init.json"
        elapsed_time = timedelta(minutes=20)
        app = propagateScenario(datafiles, init_filepath, elapsed_time)
        maneuver_query = Query(DetectedManeuver)
        assert app.database.getData(maneuver_query, multi=False) is None

    @pytest.mark.regression()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testObservationNumber(self, datafiles: str):
        """Test that the main_init produces 29 observations on the first timestep."""
        init_filepath = "main_init.json"
        elapsed_time = timedelta(minutes=5)
        app = propagateScenario(datafiles, init_filepath, elapsed_time)
        observation_query = Query(Observation)
        assert len(app.database.getData(observation_query, multi=True)) == 29

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testSaveObservation(self, datafiles: str):
        """Test `_saveObservation` function."""
        # pylint: disable=protected-access
        init_filepath = "main_init.json"
        elapsed_time = timedelta(minutes=5)
        app = propagateScenario(datafiles, init_filepath, elapsed_time)
        app.saveDatabaseOutput()
        app._logObservations(app.tasking_engines[2].observations)
        app._logMissedObservations(app.tasking_engines[2].missed_observations)


@pytest.mark.scenario()
@pytest.mark.usefixtures("_fixtureSetup")
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
        importer_db.resetData(tables=ImporterDatabase.VALID_DATA_TYPES)

    @pytest.mark.parametrize("init_file", INVALID_JSON_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInvalidInitMessages(self, datafiles: str, init_file: str):
        """Test passing a invalid init messages."""
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        init_dir = os.path.join(datafiles, JSON_INIT_PATH)
        init_file_path = os.path.join(init_dir, init_file)

        # Check missing target_set & sensor_set fields
        with pytest.raises(KeyError):
            buildScenarioFromConfigFile(
                init_file_path,
                internal_db_path=None,
                importer_db_path=db_path if "import" in init_file else None,
            )

    @pytest.mark.parametrize("init_file", EMPTY_JSON_ENGINE_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInvalidEngineConfigs(self, datafiles: str, init_file: str):
        """Test passing a invalid engine."""
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
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
