from __future__ import annotations

# Standard Library Imports
from datetime import timedelta
from pathlib import Path

# Third Party Imports
import pytest
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.detected_maneuver import DetectedManeuver
from resonaate.data.observation import Observation

# Local Imports
from .. import FIXTURE_DATA_DIR, PropagateFunc


@pytest.mark.scenario()
@pytest.mark.regression()
class TestScenarioRegression:
    """Regression tests for general simulations."""

    MANEUVER_DETECTION_INIT = (
        "maneuver_detection_standard_nis.json",
        "maneuver_detection_sliding_nis.json",
        "maneuver_detection_fading_nis.json",
    )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    @pytest.mark.parametrize("init_filepath", MANEUVER_DETECTION_INIT)
    def testDetectedManeuver(
        self,
        datafiles: Path,
        propagate_scenario: PropagateFunc,
        init_filepath: str,
    ):
        """Test a maneuver detection simulation using real time propagation. 20 minute long test."""
        elapsed_time = timedelta(minutes=20)
        app = propagate_scenario(datafiles, init_filepath, elapsed_time)
        assert app.database.getData(Query(DetectedManeuver), multi=False) is not None

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testNoDetectedManeuver(self, datafiles: Path, propagate_scenario: PropagateFunc):
        """Test no maneuver detection simulation using real time propagation. 20 minute long test."""
        init_filepath = "no_maneuver_detection_init.json"
        elapsed_time = timedelta(minutes=20)
        app = propagate_scenario(datafiles, init_filepath, elapsed_time)
        assert app.database.getData(Query(DetectedManeuver), multi=False) is None

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testObservationNumber(self, datafiles: Path, propagate_scenario: PropagateFunc):
        """Test that the main_init produces 30 observations on the first timestep."""
        init_filepath = "main_init.json"
        elapsed_time = timedelta(minutes=5)
        app = propagate_scenario(datafiles, init_filepath, elapsed_time)
        assert len(app.database.getData(Query(Observation), multi=True)) == 30
