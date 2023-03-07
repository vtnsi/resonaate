# pylint: disable=unused-argument
from __future__ import annotations

# Standard Library Imports
import os.path
from datetime import timedelta
from pathlib import Path

# Third Party Imports
import pytest
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.epoch import Epoch
from resonaate.data.importer_database import ImporterDatabase

# Local Imports
from .. import FIXTURE_DATA_DIR, IMPORTER_DB_PATH, JSON_RSO_TRUTH, JSON_SENSOR_TRUTH, PropagateFunc


@pytest.mark.scenario()
@pytest.mark.integration()
class TestScenarioRealtime:
    """Test class for scenario class using realtime propagation."""

    # [TODO]: More coverage here

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagation(self, datafiles: str, propagate_scenario: PropagateFunc):
        """Test a small simulation using real time propagation. 5 minute long test."""
        init_filepath = "default_realtime_est_realtime_obs.json"
        elapsed_time = timedelta(minutes=5)
        propagate_scenario(datafiles, init_filepath, elapsed_time)

    @pytest.mark.slow()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagationLong(self, datafiles: str, propagate_scenario: PropagateFunc):
        """Test a small simulation using real time propagation. 5 hour long test."""
        init_filepath = "long_full_ssn_realtime_est_realtime_obs.json"
        elapsed_time = timedelta(hours=5)
        propagate_scenario(datafiles, init_filepath, elapsed_time)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testTruthSimulationOnly(
        self, datafiles: str, propagate_scenario: PropagateFunc, caplog: pytest.LogCaptureFixture
    ):
        """Test a small simulation with Tasking and Estimation turned off."""
        init_filepath = "truth_simulation_only_init.json"
        elapsed_time = timedelta(minutes=10)
        propagate_scenario(datafiles, init_filepath, elapsed_time)

        for record_tuple in caplog.record_tuples:
            assert record_tuple[2] != "Assess"

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testSaveObservation(self, datafiles: Path, propagate_scenario: PropagateFunc):
        """Test `_saveObservation` function."""
        # pylint: disable=protected-access
        init_filepath = "main_init.json"
        elapsed_time = timedelta(minutes=5)
        app = propagate_scenario(datafiles, init_filepath, elapsed_time)
        app.saveDatabaseOutput()
        app._logObservations(app.tasking_engines[2].observations)
        app._logMissedObservations(app.tasking_engines[2].missed_observations)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testSaveObservationInsertsEpochs(self, datafiles: Path, propagate_scenario: PropagateFunc):
        """Test `saveDatabaseOutput` will insert `Epoch` rows to the DB if they do not already exist."""
        init_filepath = "quick_init.json"
        elapsed_time = timedelta(minutes=6)
        app = propagate_scenario(datafiles, init_filepath, elapsed_time)
        epoch_query = Query(Epoch).filter(Epoch.timestampISO == "2021-03-30T16:06:00.000000")
        assert app.database.getData(epoch_query, multi=False) is None
        app.saveDatabaseOutput()
        assert app.database.getData(epoch_query, multi=False) is not None


def loadTargetTruthData(directory: Path, importer_database: ImporterDatabase) -> None:
    """Load truth data for RSO targets into DB for Importer model."""
    importer_database.initDatabaseFromJSON(
        os.path.join(directory, JSON_RSO_TRUTH, "11111-truth.json"),
        os.path.join(directory, JSON_RSO_TRUTH, "11112-truth.json"),
    )


def loadSensorTruthData(directory: Path, importer_database: ImporterDatabase) -> None:
    """Load truth data for satellite sensors into DB for Importer model."""
    importer_database.initDatabaseFromJSON(
        os.path.join(directory, JSON_SENSOR_TRUTH, "60007-truth.json"),
        os.path.join(directory, JSON_SENSOR_TRUTH, "60008-truth.json"),
    )


@pytest.mark.scenario()
@pytest.mark.integration()
@pytest.mark.usefixtures("reset_importer_db")
class TestScenarioImporter:
    """Test class for scenario class using imported states."""

    # [TODO]: Imported observations
    # [FIXME]: Loading data seems to not work...?

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModel(self, datafiles: str, propagate_scenario: PropagateFunc):
        """Test a small simulation using imported data. 5 minute long test."""
        init_filepath = "default_imported_est_imported_obs.json"
        elapsed_time = timedelta(minutes=5)
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        loadTargetTruthData(datafiles, importer_db)
        propagate_scenario(datafiles, init_filepath, elapsed_time, importer_db_path=db_path)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelForSensors(self, datafiles: Path, propagate_scenario: PropagateFunc):
        """Include sensors that will utilize the importer model in a 5 minute test."""
        init_filepath = "long_sat_sen_imported_est_imported_obs.json"
        elapsed_time = timedelta(minutes=5)
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        loadTargetTruthData(datafiles, importer_db)
        loadSensorTruthData(datafiles, importer_db)
        propagate_scenario(datafiles, init_filepath, elapsed_time, importer_db_path=db_path)

    @pytest.mark.slow()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelLong(self, datafiles: Path, propagate_scenario: PropagateFunc):
        """Test a small simulation using imported data. 5 day hour test."""
        init_filepath = "long_full_ssn_imported_est_imported_obs.json"
        elapsed_time = timedelta(hours=5)
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        loadTargetTruthData(datafiles, importer_db)
        propagate_scenario(datafiles, init_filepath, elapsed_time, importer_db_path=db_path)
