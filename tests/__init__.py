"""Configure importable things that aren't pytest fixtures."""
from __future__ import annotations

# Standard Library Imports
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

# RESONAATE Imports
from resonaate.physics.time.stardate import JulianDate, datetimeToJulianDate

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
