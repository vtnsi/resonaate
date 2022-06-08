# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from datetime import timedelta
import os.path
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.scenario.scenario import Scenario
    from resonaate.physics.time.conversions import getTargetJulianDate
    from resonaate.physics.time.stardate import JulianDate
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase, FIXTURE_DATA_DIR


class TestScenarioApp(BaseTestCase):
    """Test class for scenario class."""

    output_database = None
    shared_database = None
    output_db_path = "db/output.db"
    shared_db_path = "db/shared.db"

    @pytest.fixture(scope="function", autouse=True)
    def fixtureSetUp(self, shared_db, output_db, redis):  # pylint: disable=unused-argument
        """Create shared & output DBs, and instantiate redis."""
        self.output_database = output_db
        self.shared_database = shared_db

    def _propagateScenario(self, init_file, elapsed_time):
        """Performs the basic operations required to step a simulation forward in time.

        Args:
            init_file (str): file path for Resonaate initialization file
            elapsed_time (`timedelta`): amount of time to simulate
        """
        # Create scenario from JSON init message
        app = Scenario.fromConfigFile(init_file)

        # Determine target Julian date based on elapsed time
        init_julian_date = JulianDate(app.clock.julian_date_start)
        target_julian_date = getTargetJulianDate(
            init_julian_date,
            elapsed_time
        )

        # Propagate scenario forward in time
        app.propagateTo(target_julian_date, output_database=self.output_database)

        assert app.clock.julian_date_epoch == target_julian_date

    def loadTargetTruthData(self, directory):
        """Load truth data for RSO targets into DB for Importer model."""
        self.shared_database.initDatabaseFromJSON(
            os.path.join(directory, 'json/rso_truth/11111-truth.json'),
            os.path.join(directory, 'json/rso_truth/11112-truth.json'),
            os.path.join(directory, 'json/rso_truth/11113-truth.json'),
            os.path.join(directory, 'json/rso_truth/11114-truth.json'),
            os.path.join(directory, 'json/rso_truth/11115-truth.json'),
            os.path.join(directory, 'json/rso_truth/11116-truth.json')
        )

    def loadSensorTruthData(self, directory):
        """Load truth data for satellite sensors into DB for Importer model."""
        self.shared_database.initDatabaseFromJSON(
            os.path.join(directory, 'json/sat_sensor_truth/37168-truth.json'),
            os.path.join(directory, 'json/sat_sensor_truth/40099-truth.json'),
            os.path.join(directory, 'json/sat_sensor_truth/40100-truth.json'),
            os.path.join(directory, 'json/sat_sensor_truth/41744-truth.json'),
            os.path.join(directory, 'json/sat_sensor_truth/41745-truth.json'),
            os.path.join(directory, 'json/sat_sensor_truth/43501-truth.json'),
            os.path.join(directory, 'json/sat_sensor_truth/43502-truth.json'),
            os.path.join(directory, 'json/sat_sensor_truth/43503-truth.json')
        )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testBuildFromConfig(self, datafiles):
        """Test building a scenario from config files."""
        init_file = os.path.join(datafiles, "json/config/init_messages/default_realtime_est_realtime_obs.json")
        Scenario.fromConfigFile(init_file)

    @pytest.mark.realtime
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagation(self, datafiles):
        """Test a small simulation using real time propagation. 5 minute long test."""
        init_file = os.path.join(datafiles, "json/config/init_messages/default_realtime_est_realtime_obs.json")
        elapsed_time = timedelta(minutes=6)
        self._propagateScenario(init_file, elapsed_time)

    @pytest.mark.slow
    @pytest.mark.realtime
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagationLong(self, datafiles):
        """Test a small simulation using real time propagation. 5 day long test."""
        init_file = os.path.join(datafiles, "json/config/init_messages/long_full_ssn_realtime_est_realtime_obs.json")
        elapsed_time = timedelta(days=5)
        self._propagateScenario(init_file, elapsed_time)

    @pytest.mark.importer
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModel(self, datafiles):
        """Test a small simulation using imported data. 5 minute long test."""
        init_file = os.path.join(datafiles, "json/config/init_messages/default_imported_est_imported_obs.json")
        elapsed_time = timedelta(minutes=6)
        self.loadTargetTruthData(datafiles)
        self._propagateScenario(init_file, elapsed_time)

    @pytest.mark.importer
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelForSensors(self, datafiles):
        """Include sensors that will utilize the importer model in a 10 minute test."""
        init_file = os.path.join(datafiles, "json/config/init_messages/long_sat_sen_imported_est_imported_obs.json")
        elapsed_time = timedelta(minutes=10)
        self.loadTargetTruthData(datafiles)
        self.loadSensorTruthData(datafiles)
        self._propagateScenario(init_file, elapsed_time)

    @pytest.mark.slow
    @pytest.mark.importer
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelLong(self, datafiles):
        """Test a small simulation using imported data. 5 day long test."""
        init_file = os.path.join(datafiles, "json/config/init_messages/long_full_ssn_imported_est_imported_obs.json")
        elapsed_time = timedelta(days=5)
        self.loadTargetTruthData(datafiles)
        self._propagateScenario(init_file, elapsed_time)


class TestScenarioFactory(BaseTestCase):
    """Tests for :func:`.scenarioFactory`."""

    JSON_DIR = os.path.join(
        FIXTURE_DATA_DIR, "json"
    )

    VALID_JSON_CONFIGS = [
        "minimal_init.json",
        "default_imported_est_imported_obs.json",
        "default_realtime_est_realtime_obs.json",
    ]

    INVALID_JSON_CONFIGS = [
        "no_sensors_init.json",
        "no_targets_init.json",
        "no_sensor_set_init.json",
        "no_target_set_init.json",
    ]

    @pytest.mark.datafiles(JSON_DIR)
    def testValidInitMessages(self, datafiles, redis):  # pylint: disable=unused-argument
        """Test passing a valid init messages."""
        init_dir = os.path.join(datafiles, "config", "init_messages")
        for init_file in self.VALID_JSON_CONFIGS:
            init_file_path = os.path.join(init_dir, init_file)
            Scenario.fromConfigFile(init_file_path)

    @pytest.mark.datafiles(JSON_DIR)
    def testInvalidInitMessages(self, datafiles, redis):  # pylint: disable=unused-argument
        """Test passing a invalid init messages."""
        init_dir = os.path.join(datafiles, "config", "init_messages")
        for init_file in self.INVALID_JSON_CONFIGS:
            init_file_path = os.path.join(init_dir, init_file)
            if init_file in ("no_sensors_init.json", "no_targets_init.json"):
                # Check empty target and sensor lists
                with pytest.raises(ValueError):
                    Scenario.fromConfigFile(init_file_path)
            else:
                # Check missing target_set & sensor_set fields
                with pytest.raises(KeyError):
                    Scenario.fromConfigFile(init_file_path)
