# Standard Library Imports
from datetime import timedelta
from os.path import join
# Third Party Imports
import pytest
from sqlalchemy.orm import Query
# RESONAATE Imports
try:
    from resonaate.data.maneuver_detection import ManeuverDetection
    from resonaate.data.resonaate_database import ResonaateDatabase
    from resonaate.scenario.config import ScenarioConfig
    from resonaate.filters.statistics import Nis, SlidingNis, FadingMemoryNis
    from resonaate.scenario import buildScenarioFromConfigDict
    from resonaate.physics.time.conversions import getTargetJulianDate
    from resonaate.physics.time.stardate import JulianDate
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase, FIXTURE_DATA_DIR


class TestManeuverDetection(BaseTestCase):
    """Test Class for NIS Maneuver detection."""

    @pytest.fixture(scope="function", autouse=True)
    def fixtureSetUp(self, redis):  # pylint: disable=unused-argument
        """Instantiate redis."""

    def _propagateScenario(self, init_file, elapsed_time, realtime_db_path):  # pylint: disable=no-self-use
        """Performs the basic operations required to step a simulation forward in time.

        Args:
            init_file (str): file path for Resonaate initialization file
            elapsed_time (`timedelta`): amount of time to simulate
            importer_db_path (``str``): path to external importer database for pre-canned data.
        """
        # Create scenario from JSON init message
        config_dict = ScenarioConfig.parseConfigFile(init_file)

        app = buildScenarioFromConfigDict(
            config_dict,
            internal_db_path=realtime_db_path,
            importer_db_path=None,
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

    # pylint:disable=no-self-use
    def testManeuverDetectionClassInits(self):
        """Test a Maneuver detection inits."""
        # pylint:disable=unused-variable
        standard_nis = Nis(0.01)
        sliding_nis = SlidingNis(0.01, 4)
        fading_nis = FadingMemoryNis(0.01)

    @pytest.mark.realtime
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testManeuverDetection(self, datafiles):
        """Test a maneuver detection simulation using real time propagation. 20 minute long test."""
        init_file = join(datafiles, self.json_init_path, "maneuver_detection_init.json")
        maneuver_file = "sqlite:///" + join(datafiles, self.maneuver_db_path)
        elapsed_time = timedelta(minutes=20)
        database = ResonaateDatabase.getSharedInterface(maneuver_file)
        self._propagateScenario(init_file, elapsed_time, maneuver_file)
        maneuver_query = Query(ManeuverDetection)
        assert database.getData(maneuver_query, multi=False) is not None
        database.resetData(tables=database.VALID_DATA_TYPES)

    @pytest.mark.realtime
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testNoManeuverDetection(self, datafiles):
        """Test no maneuver detection simulation using real time propagation. 20 minute long test."""
        init_file = join(datafiles, self.json_init_path, "no_maneuver_detection_init.json")
        maneuver_file = "sqlite:///" + join(datafiles, self.maneuver_db_path)
        elapsed_time = timedelta(minutes=20)
        database = ResonaateDatabase.getSharedInterface(maneuver_file)
        self._propagateScenario(init_file, elapsed_time, maneuver_file)
        maneuver_query = Query(ManeuverDetection)
        assert database.getData(maneuver_query, multi=False) is None
        database.resetData(tables=database.VALID_DATA_TYPES)
