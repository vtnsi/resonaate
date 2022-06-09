# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from datetime import timedelta
import os.path
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.data.importer_database import ImporterDatabase
    from resonaate.scenario.config import ScenarioConfig
    from resonaate.scenario import buildScenarioFromConfigFile, buildScenarioFromConfigDict
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

    @pytest.fixture(scope="function", autouse=True)
    def fixtureSetUp(self, redis):  # pylint: disable=unused-argument
        """Instantiate redis."""

    def _propagateScenario(self, init_file, elapsed_time, importer_db_path):
        """Performs the basic operations required to step a simulation forward in time.

        Args:
            init_file (str): file path for Resonaate initialization file
            elapsed_time (`timedelta`): amount of time to simulate
            importer_db_path (``str``, optional): path to external importer database for pre-canned
                data. Defaults to ``None``.
        """
        # Create scenario from JSON init message
        config_dict = ScenarioConfig.parseConfigFile(init_file)

        app = buildScenarioFromConfigDict(
            config_dict,
            internal_db_path=self.shared_db_path,
            importer_db_path=importer_db_path,
        )

        # Determine target Julian date based on elapsed time
        init_julian_date = JulianDate(app.clock.julian_date_start)
        target_julian_date = getTargetJulianDate(
            init_julian_date,
            elapsed_time
        )

        # Propagate scenario forward in time
        app.propagateTo(target_julian_date)

        assert app.clock.julian_date_epoch == target_julian_date

        app.database.resetData(tables=app.database.VALID_DATA_TYPES)

    def loadTargetTruthData(self, directory, importer_database):
        """Load truth data for RSO targets into DB for Importer model."""
        importer_database.initDatabaseFromJSON(
            os.path.join(directory, self.json_rso_truth, '11111-truth.json'),
            os.path.join(directory, self.json_rso_truth, '11112-truth.json'),
        )

    def loadSensorTruthData(self, directory, importer_database):
        """Load truth data for satellite sensors into DB for Importer model."""
        importer_database.initDatabaseFromJSON(
            os.path.join(directory, self.json_sensor_truth, '43502-truth.json'),
            os.path.join(directory, self.json_sensor_truth, '43503-truth.json')
        )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testBuildFromConfig(self, datafiles):
        """Test building a scenario from config files."""
        init_file = os.path.join(datafiles, self.json_init_path, "default_realtime_est_realtime_obs.json")
        app = buildScenarioFromConfigFile(init_file, internal_db_path=self.shared_db_path, importer_db_path=None)
        app.database.resetData(tables=app.database.VALID_DATA_TYPES)

    @pytest.mark.realtime
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagation(self, datafiles):
        """Test a small simulation using real time propagation. 5 minute long test."""
        init_file = os.path.join(datafiles, self.json_init_path, "default_realtime_est_realtime_obs.json")
        elapsed_time = timedelta(minutes=5)
        self._propagateScenario(init_file, elapsed_time, None)

    @pytest.mark.slow
    @pytest.mark.realtime
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagationLong(self, datafiles):
        """Test a small simulation using real time propagation. 5 hour long test."""
        init_file = os.path.join(datafiles, self.json_init_path, "long_full_ssn_realtime_est_realtime_obs.json")
        elapsed_time = timedelta(hours=5)
        self._propagateScenario(init_file, elapsed_time, None)

    @pytest.mark.importer
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModel(self, datafiles):
        """Test a small simulation using imported data. 5 minute long test."""
        init_file = os.path.join(datafiles, self.json_init_path, "default_imported_est_imported_obs.json")
        elapsed_time = timedelta(minutes=5)
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        self.loadTargetTruthData(datafiles, importer_db)
        self._propagateScenario(init_file, elapsed_time, db_path)
        importer_db.resetData(tables=ImporterDatabase.VALID_DATA_TYPES)

    @pytest.mark.importer
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelForSensors(self, datafiles):
        """Include sensors that will utilize the importer model in a 5 minute test."""
        init_file = os.path.join(datafiles, self.json_init_path, "long_sat_sen_imported_est_imported_obs.json")
        elapsed_time = timedelta(minutes=5)
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        self.loadTargetTruthData(datafiles, importer_db)
        self.loadSensorTruthData(datafiles, importer_db)
        self._propagateScenario(init_file, elapsed_time, db_path)
        importer_db.resetData(tables=ImporterDatabase.VALID_DATA_TYPES)

    @pytest.mark.slow
    @pytest.mark.importer
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelLong(self, datafiles):
        """Test a small simulation using imported data. 5 day hour test."""
        init_file = os.path.join(datafiles, self.json_init_path, "long_full_ssn_imported_est_imported_obs.json")
        elapsed_time = timedelta(hours=5)
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        self.loadTargetTruthData(datafiles, importer_db)
        self._propagateScenario(init_file, elapsed_time, db_path)
        importer_db.resetData(tables=ImporterDatabase.VALID_DATA_TYPES)


class TestScenarioFactory(BaseTestCase):
    """Tests for :func:`.scenarioFactory`."""

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

    @pytest.fixture(scope="function", autouse=True)
    def fixtureSetup(self, redis):  # pylint: disable=unused-argument
        """Instantiate redis."""

    @pytest.mark.parametrize("init_file", VALID_JSON_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testValidInitMessages(self, datafiles, init_file):
        """Test passing a valid init messages."""
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        init_dir = os.path.join(datafiles, self.json_init_path)
        init_file_path = os.path.join(init_dir, init_file)

        app = buildScenarioFromConfigFile(
            init_file_path,
            internal_db_path=self.shared_db_path,
            importer_db_path=db_path if 'import' in init_file else None
        )
        importer_db.resetData(tables=ImporterDatabase.VALID_DATA_TYPES)
        app.database.resetData(tables=app.database.VALID_DATA_TYPES)

    @pytest.mark.parametrize("init_file", INVALID_JSON_CONFIGS)
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInvalidInitMessages(self, datafiles, init_file):
        """Test passing a invalid init messages."""
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        init_dir = os.path.join(datafiles, self.json_init_path)
        init_file_path = os.path.join(init_dir, init_file)

        # Check missing target_set & sensor_set fields
        with pytest.raises(KeyError):
            buildScenarioFromConfigFile(
                init_file_path,
                internal_db_path=self.shared_db_path,
                importer_db_path=db_path if 'import' in init_file else None,
            )

        importer_db.resetData(tables=ImporterDatabase.VALID_DATA_TYPES)
