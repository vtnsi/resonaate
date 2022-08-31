# pylint: disable=invalid-name
from __future__ import annotations

# Standard Library Imports
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from mjolnir import KeyValueStore

# RESONAATE Imports
from resonaate.common.behavioral_config import BehavioralConfig
from resonaate.data.importer_database import ImporterDatabase
from resonaate.data.resonaate_database import ResonaateDatabase
from resonaate.dynamics.special_perturbations import SpecialPerturbations
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config.geopotential_config import GeopotentialConfig
from resonaate.scenario.config.perturbations_config import PerturbationsConfig

# Type Checking Imports
if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.common.logger import Logger
    from resonaate.physics.time.stardate import JulianDate

FIXTURE_DATA_DIR = Path(__file__).parent / "datafiles"
IMPORTER_DB_PATH = Path("db/importer.sqlite3")
SHARED_DB_PATH = Path("db/importer.sqlite3")
JSON_INIT_PATH = Path("json/config/init_messages")
JSON_RSO_TRUTH = Path("json/rso_truth")
JSON_SENSOR_TRUTH = Path("json/sat_sensor_truth")


@pytest.fixture(autouse=True)
def _patchMissingEnvVariables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Automatically delete each environment variable, if set.

    Args:
        monkeypatch (:class:`pytest.monkeypatch.MonkeyPatch`): monkeypatch obj to track changes

    Note:
        This is used so tests can assume a "blank" configuration, and it won't
        overwrite a user's custom-set environment variables.
    """
    with monkeypatch.context() as m_patch:
        m_patch.delenv("RESONAATE_BEHAVIOR_CONFIG", raising=False)
        yield
        # Make sure we reset the config after each test function
        BehavioralConfig.getConfig()


@pytest.fixture(scope="session", name="test_logger")
def getTestLoggerObject() -> Logger:
    """Create a custom :class:`logging.Logger` object."""
    logger = logging.getLogger("Unit Test Logger")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger


@pytest.fixture(name="teardown_kvs")
def _teardownKeyValueStore():
    """Make sure that :class:`.KeyValueStore.Server` is shut down after each test that uses it."""
    yield
    KeyValueStore.stopServerProcess()


@pytest.fixture(name="reset_shared_db")
def _resetDatabase() -> None:
    """Reset the database tables to avoid data integrity errors.

    Note:
        This fixture should be utilized any time a :class:`.ScenarioClock` object is instantiated so that the "epochs"
        table is reset.
    """
    yield
    ResonaateDatabase.getSharedInterface().resetData(tables=ResonaateDatabase.VALID_DATA_TYPES)


@pytest.fixture(name="reset_importer_db")
def _resetImporterDatabase() -> None:
    """Reset the database tables to avoid data integrity errors.

    Note:
        This fixture should be utilized any time a :class:`.ScenarioClock` object is instantiated so that the "epochs"
        table is reset.
    """
    yield
    ImporterDatabase.getSharedInterface().resetData(tables=ImporterDatabase.VALID_DATA_TYPES)


@pytest.fixture(name="database")
def getDataInterface() -> ResonaateDatabase:
    """Create common, non-shared DB object for all tests.

    Yields:
        :class:`.ResonaateDatabase`: properly constructed DB object
    """
    # Create & yield instance.
    shared_interface = ResonaateDatabase.getSharedInterface()
    yield shared_interface
    shared_interface.resetData(ResonaateDatabase.VALID_DATA_TYPES)


TEST_START_JD: JulianDate = datetimeToJulianDate(datetime(2018, 12, 1, 12))


@pytest.fixture(name="geopotential_config")
def getGeopotentialConfig() -> GeopotentialConfig:
    """Return a :class:`.GeopotentialConfig` object based on :attr:`.GEOPOTENTIAL_CONFIG`."""
    cfg_dict = {"model": "egm96.txt", "degree": 4, "order": 4}
    return GeopotentialConfig(**cfg_dict)


@pytest.fixture(name="perturbations_config")
def getPerturbationsConfig() -> PerturbationsConfig:
    """Return a :class:`.PerturbationsConfig` object based on :attr:`.PERTURBATIONS_CONFIG`."""
    cfg_dict = {"third_bodies": ["sun", "moon"]}
    return PerturbationsConfig(**cfg_dict)


@pytest.fixture(name="dynamics")
def getDynamics(
    perturbations_config: PerturbationsConfig, geopotential_config: GeopotentialConfig
) -> SpecialPerturbations:
    """Return a :class:`.SpecialPerturbations` object based on configurations."""
    return SpecialPerturbations(TEST_START_JD, geopotential_config, perturbations_config, 0.0)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command line options."""
    parser.addoption("--runslow", action="store_true", default=False, help="run slow tests")


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest options without an .ini file."""
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "scenario: mark test as a scenario integration test")
    config.addinivalue_line("markers", "event: mark test as an event integration test")
    config.addinivalue_line("markers", "realtime: mark test as using real time propagation")
    config.addinivalue_line(
        "markers", "importer: mark test as using imported data rather than propagation"
    )


def pytest_collection_modifyitems(
    session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Collect pytest modifiers."""
    # pylint: disable=unused-argument
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
