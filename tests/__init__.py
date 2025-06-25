"""Configure importable things that aren't pytest fixtures."""

from __future__ import annotations

# Standard Library Imports
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Optional

# Third Party Imports
from numpy import isclose

# RESONAATE Imports
from resonaate.physics.time.conversions import getTargetJulianDate
from resonaate.physics.time.stardate import JulianDate, datetimeToJulianDate
from resonaate.scenario import buildScenarioFromConfigFile
from resonaate.scenario.scenario import Scenario

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from typing_extensions import TypeAlias


# Common file paths
FIXTURE_DATA_DIR = Path(__file__).parent / "datafiles"
IMPORTER_DB_PATH = Path("db/importer.sqlite3")
SHARED_DB_PATH = Path("db/shared.sqlite3")
JSON_INIT_PATH = Path("json/config/init_messages")
JSON_RSO_TRUTH = Path("json/rso_truth")
JSON_SENSOR_TRUTH = Path("json/sat_sensor_truth")


# Common julian dates
TEST_START_DATETIME = datetime(2018, 12, 1, 12)
TEST_START_JD: JulianDate = datetimeToJulianDate(TEST_START_DATETIME)

PropagateFunc: TypeAlias = Callable[[str, str, timedelta, Optional[str]], Scenario]
"""Function signature for propagate_func fixture."""


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
    shared_db_path = Path(data_directory).joinpath(SHARED_DB_PATH)
    init_file = Path(data_directory).joinpath(JSON_INIT_PATH, init_filepath)

    app = buildScenarioFromConfigFile(
        init_file,
        internal_db_path=shared_db_path,
        importer_db_path=importer_db_path,
    )

    # Determine target Julian date based on elapsed time
    init_julian_date = JulianDate(app.clock.julian_date_start)
    target_julian_date = getTargetJulianDate(init_julian_date, elapsed_time)

    # Propagate scenario forward in time
    app.propagateTo(target_julian_date)

    assert isclose(app.clock.julian_date_epoch, target_julian_date)

    return app


def patchCreateDatabasePath(path: str | Path | None, importer: bool) -> str:
    """Quick and dirty patch of createDatabasePath() so test can overwrite DB files."""
    base = "sqlite:///"
    if path is None:
        return base

    # else
    return base + str(path)
