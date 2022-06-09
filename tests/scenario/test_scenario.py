# pylint: disable=attribute-defined-outside-init
# Standard Library Imports
import os.path
from datetime import timedelta

# Third Party Imports
import pytest
from sqlalchemy.orm import Query

try:
    # RESONAATE Imports
    from resonaate.data.detected_maneuver import DetectedManeuver
    from resonaate.data.importer_database import ImporterDatabase
    from resonaate.physics.time.conversions import getTargetJulianDate
    from resonaate.physics.time.stardate import JulianDate
    from resonaate.scenario import buildScenarioFromConfigDict, buildScenarioFromConfigFile
    from resonaate.scenario.config import ScenarioConfig
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import FIXTURE_DATA_DIR, BaseTestCase


@pytest.mark.scenario()
class TestScenarioApp(BaseTestCase):
    """Test class for scenario class."""

    MANEUVER_DETECTION_INIT = (
        "maneuver_detection_standard_nis.json",
        "maneuver_detection_sliding_nis.json",
        "maneuver_detection_fading_nis.json",
    )

    @pytest.fixture(autouse=True)
    def _fixtureSetUp(self, redis, reset_shared_db):  # pylint: disable=unused-argument
        """Instantiate redis & reset DB properly."""

    def _propagateScenario(
        self, data_directory, init_filepath, elapsed_time, importer_db_path=None
    ):
        """Performs the basic operations required to step a simulation forward in time.

        Args:
            data_directory (str): file path for datafiles directory
            init_filepath (str): file path for Resonaate initialization file
            elapsed_time (`timedelta`): amount of time to simulate
            importer_db_path (``str``): path to external importer database for pre-canned data.
        """
        init_file = os.path.join(data_directory, self.json_init_path, init_filepath)
        shared_db_path = "sqlite:///" + os.path.join(data_directory, self.shared_db_path)

        # Create scenario from JSON init message
        config_dict = ScenarioConfig.parseConfigFile(init_file)

        self.app = buildScenarioFromConfigDict(
            config_dict,
            internal_db_path=shared_db_path,
            importer_db_path=importer_db_path,
        )

        # Determine target Julian date based on elapsed time
        init_julian_date = JulianDate(self.app.clock.julian_date_start)
        target_julian_date = getTargetJulianDate(init_julian_date, elapsed_time)

        # Propagate scenario forward in time
        self.app.propagateTo(target_julian_date)

        assert self.app.clock.julian_date_epoch == target_julian_date

        self.app.shutdown(flushall=True)

    def loadTargetTruthData(self, directory, importer_database):
        """Load truth data for RSO targets into DB for Importer model."""
        importer_database.initDatabaseFromJSON(
            os.path.join(directory, self.json_rso_truth, "11111-truth.json"),
            os.path.join(directory, self.json_rso_truth, "11112-truth.json"),
        )

    def loadSensorTruthData(self, directory, importer_database):
        """Load truth data for satellite sensors into DB for Importer model."""
        importer_database.initDatabaseFromJSON(
            os.path.join(directory, self.json_sensor_truth, "60007-truth.json"),
            os.path.join(directory, self.json_sensor_truth, "60008-truth.json"),
        )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testBuildFromConfig(self, datafiles):
        """Test building a scenario from config files."""
        init_filepath = os.path.join(
            datafiles, self.json_init_path, "default_realtime_est_realtime_obs.json"
        )
        _ = buildScenarioFromConfigFile(
            init_filepath, internal_db_path=None, importer_db_path=None
        )

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagation(self, datafiles):
        """Test a small simulation using real time propagation. 5 minute long test."""
        init_filepath = "default_realtime_est_realtime_obs.json"
        elapsed_time = timedelta(minutes=5)
        self._propagateScenario(datafiles, init_filepath, elapsed_time)

    @pytest.mark.slow()
    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagationLong(self, datafiles):  # pylint: disable=unused-argument
        """Test a small simulation using real time propagation. 5 hour long test."""
        init_filepath = "long_full_ssn_realtime_est_realtime_obs.json"
        elapsed_time = timedelta(hours=5)
        self._propagateScenario(datafiles, init_filepath, elapsed_time)

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testTruthSimulationOnly(self, datafiles, caplog):
        """Test a small simulation with Tasking and Estimation turned off."""
        init_filepath = "truth_simulation_only_init.json"
        elapsed_time = timedelta(minutes=10)
        self._propagateScenario(datafiles, init_filepath, elapsed_time)

        for record_tuple in caplog.record_tuples:
            assert record_tuple[2] != "Assess"

    @pytest.mark.importer()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModel(self, datafiles, reset_importer_db):  # pylint: disable=unused-argument
        """Test a small simulation using imported data. 5 minute long test."""
        init_filepath = "default_imported_est_imported_obs.json"
        elapsed_time = timedelta(minutes=5)
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        self.loadTargetTruthData(datafiles, importer_db)
        self._propagateScenario(datafiles, init_filepath, elapsed_time, importer_db_path=db_path)

    @pytest.mark.importer()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelForSensors(
        self, datafiles, reset_importer_db
    ):  # pylint: disable=unused-argument
        """Include sensors that will utilize the importer model in a 5 minute test."""
        init_filepath = "long_sat_sen_imported_est_imported_obs.json"
        elapsed_time = timedelta(minutes=5)
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        self.loadTargetTruthData(datafiles, importer_db)
        self.loadSensorTruthData(datafiles, importer_db)
        self._propagateScenario(datafiles, init_filepath, elapsed_time, importer_db_path=db_path)

    @pytest.mark.slow()
    @pytest.mark.importer()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelLong(
        self, datafiles, reset_importer_db
    ):  # pylint: disable=unused-argument
        """Test a small simulation using imported data. 5 day hour test."""
        init_filepath = "long_full_ssn_imported_est_imported_obs.json"
        elapsed_time = timedelta(hours=5)
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        self.loadTargetTruthData(datafiles, importer_db)
        self._propagateScenario(datafiles, init_filepath, elapsed_time, importer_db_path=db_path)

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    @pytest.mark.parametrize("init_filepath", MANEUVER_DETECTION_INIT)
    def testDetectedManeuver(self, datafiles, init_filepath):
        """Test a maneuver detection simulation using real time propagation. 20 minute long test."""
        elapsed_time = timedelta(minutes=20)
        self._propagateScenario(datafiles, init_filepath, elapsed_time)
        maneuver_query = Query(DetectedManeuver)
        assert self.app.database.getData(maneuver_query, multi=False) is not None

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testNoDetectedManeuver(self, datafiles):
        """Test no maneuver detection simulation using real time propagation. 20 minute long test."""
        init_filepath = "no_maneuver_detection_init.json"
        elapsed_time = timedelta(minutes=20)
        self._propagateScenario(datafiles, init_filepath, elapsed_time)
        maneuver_query = Query(DetectedManeuver)
        assert self.app.database.getData(maneuver_query, multi=False) is None


@pytest.mark.scenario()
class TestScenarioFactory(BaseTestCase):
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

    @pytest.fixture(autouse=True)
    def _fixtureSetUp(self, redis, reset_shared_db):  # pylint: disable=unused-argument
        """Instantiate redis & reset DB properly."""

    @pytest.mark.parametrize("init_file", VALID_JSON_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testValidInitMessages(self, datafiles, init_file):
        """Test passing a valid init messages."""
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        init_dir = os.path.join(datafiles, self.json_init_path)
        init_file_path = os.path.join(init_dir, init_file)

        _ = buildScenarioFromConfigFile(
            init_file_path,
            internal_db_path=None,
            importer_db_path=db_path if "import" in init_file else None,
        )
        importer_db.resetData(tables=ImporterDatabase.VALID_DATA_TYPES)

    @pytest.mark.parametrize("init_file", INVALID_JSON_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInvalidInitMessages(self, datafiles, init_file):
        """Test passing a invalid init messages."""
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        init_dir = os.path.join(datafiles, self.json_init_path)
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
    def testInvalidEngineConfigs(self, datafiles, init_file):
        """Test passing a invalid engine."""
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        init_dir = os.path.join(datafiles, self.json_init_path)
        init_file_path = os.path.join(init_dir, init_file)

        # Check for empty target and sensor configs
        error_msg = r"Empty JSON file: \/.*?\.json+"
        with pytest.raises(IOError, match=error_msg):
            buildScenarioFromConfigFile(
                init_file_path,
                internal_db_path=None,
                importer_db_path=db_path if "import" in init_file else None,
            )
