from __future__ import annotations

# Standard Library Imports
import re
from datetime import timedelta
from pathlib import Path

# Third Party Imports
import pytest
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.common.exceptions import MissingEphemerisError
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
        self,
        datafiles: str,
        propagate_scenario: PropagateFunc,
        caplog: pytest.LogCaptureFixture,
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
        directory.joinpath(JSON_RSO_TRUTH, "11111-truth.json"),
        directory.joinpath(JSON_RSO_TRUTH, "11112-truth.json"),
    )


def loadSensorTruthData(directory: Path, importer_database: ImporterDatabase) -> None:
    """Load truth data for satellite sensors into DB for Importer model."""
    importer_database.initDatabaseFromJSON(
        Path(directory).joinpath(JSON_SENSOR_TRUTH, "60001-truth.json"),
        Path(directory).joinpath(JSON_SENSOR_TRUTH, "60002-truth.json"),
        Path(directory).joinpath(JSON_SENSOR_TRUTH, "60003-truth.json"),
        Path(directory).joinpath(JSON_SENSOR_TRUTH, "60004-truth.json"),
        Path(directory).joinpath(JSON_SENSOR_TRUTH, "60005-truth.json"),
        Path(directory).joinpath(JSON_SENSOR_TRUTH, "60006-truth.json"),
        Path(directory).joinpath(JSON_SENSOR_TRUTH, "60007-truth.json"),
        Path(directory).joinpath(JSON_SENSOR_TRUTH, "60008-truth.json"),
    )


def assertImporterDBLogWarnings(
    caplog: pytest.LogCaptureFixture,
    sub_string: re.Pattern[str],
    expected: int,
) -> None:
    """Uses regular expressions to check for proper ImporterDB warning logs."""
    base_pattern = re.compile(
        r"Could not find importer truth for \d*\. Defaulting to realtime propagation!",
    )
    matches = []
    for record in caplog.records:
        # Only grab importer DB warnings
        if match := base_pattern.match(record.message):
            # ensure imported sensors/targets aren't listed
            assert not re.search(sub_string, match.string)
            matches.append(match)

    # Number of sensors
    assert len(matches) == expected


@pytest.mark.scenario()
@pytest.mark.integration()
class TestScenarioImporter:
    """Test class for scenario class using imported states."""

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testMissingImporterDB(
        self,
        datafiles: str,
        propagate_scenario: PropagateFunc,
    ):
        """Validate that error is thrown if config.propagation.*_realtime_propagation is False and no importer db is provided."""
        init_filepath = "default_imported_est_imported_obs.json"
        elapsed_time = timedelta(minutes=5)
        with pytest.raises(ValueError, match="Importer database requires a valid url path"):
            _ = propagate_scenario(datafiles, init_filepath, elapsed_time)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testMissingTargetEphemeris(
        self,
        datafiles: str,
        propagate_scenario: PropagateFunc,
    ):
        """Validate that error is thrown if an importer target is missing ephemeris data."""
        init_filepath = "default_imported_est_imported_obs.json"
        elapsed_time = timedelta(minutes=5)
        db_path = Path(datafiles).joinpath(IMPORTER_DB_PATH)
        importer_db = ImporterDatabase("sqlite:///" + str(db_path))
        loadSensorTruthData(Path(datafiles), importer_db)
        with pytest.raises(
            MissingEphemerisError,
            match="Missing ephemeris data for agents",
        ) as exc_info:
            _ = propagate_scenario(
                datafiles,
                init_filepath,
                elapsed_time,
                importer_db_path=db_path,
            )
        assert not re.search(r"6000[1-8]", exc_info.value.args[0])

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testMissingSensorEphemeris(
        self,
        datafiles: str,
        propagate_scenario: PropagateFunc,
    ):
        """Validate that error is thrown if an importer sensor is missing ephemeris data."""
        init_filepath = "default_imported_est_imported_obs.json"
        elapsed_time = timedelta(minutes=5)
        db_path = Path(datafiles).joinpath(IMPORTER_DB_PATH)
        importer_db = ImporterDatabase("sqlite:///" + str(db_path))
        loadTargetTruthData(Path(datafiles), importer_db)
        with pytest.raises(
            MissingEphemerisError,
            match="Missing ephemeris data for agents",
        ) as exc_info:
            _ = propagate_scenario(
                datafiles,
                init_filepath,
                elapsed_time,
                importer_db_path=db_path,
            )
        assert not re.search(r"1111[12]", exc_info.value.args[0])

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImportedEphemeris(
        self,
        datafiles: str,
        propagate_scenario: PropagateFunc,
    ):
        """Validate that simulation is successful if run with imported target and sensor ephemeris."""
        init_filepath = "default_imported_est_imported_obs.json"
        elapsed_time = timedelta(minutes=5)
        db_path = Path(datafiles).joinpath(IMPORTER_DB_PATH)
        importer_db = ImporterDatabase("sqlite:///" + str(db_path))
        loadSensorTruthData(Path(datafiles), importer_db)
        loadTargetTruthData(Path(datafiles), importer_db)
        _ = propagate_scenario(
            datafiles,
            init_filepath,
            elapsed_time,
            importer_db_path=db_path,
        )

    @pytest.mark.slow()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterModelLong(
        self,
        datafiles: Path,
        propagate_scenario: PropagateFunc,
        caplog: pytest.LogCaptureFixture,
    ):
        """Test a small simulation using imported data. 5 day hour test."""
        init_filepath = "long_full_ssn_imported_est_imported_obs.json"
        elapsed_time = timedelta(hours=4, minutes=59)
        db_path = Path(datafiles).joinpath(IMPORTER_DB_PATH)
        importer_db = ImporterDatabase("sqlite:///" + str(db_path))
        loadTargetTruthData(Path(datafiles), importer_db)
        loadSensorTruthData(Path(datafiles), importer_db)
        propagate_scenario(datafiles, init_filepath, elapsed_time, importer_db_path=db_path)

        assertImporterDBLogWarnings(caplog, sub_string=r"1111[12]|6000[1-8]", expected=0)
