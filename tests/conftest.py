from __future__ import annotations

# Standard Library Imports
import logging
import shutil
import sys
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.config import OutputDbUrlSpec, getConfig, rootConfigSpec
from resonaate.data import clearDBParams, getDBConnection, setDBParams
from resonaate.dynamics.special_perturbations import SpecialPerturbations
from resonaate.parallel.key_value_store import KeyValueStore
from resonaate.parallel.key_value_store.flush_transaction import FlushTransaction
from resonaate.scenario.config.geopotential_config import GeopotentialConfig
from resonaate.scenario.config.perturbations_config import PerturbationsConfig

# Local Imports
from . import FIXTURE_DATA_DIR, SHARED_DB_PATH, TEST_START_JD, PropagateFunc, propagateScenario

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from pathlib import Path

    # RESONAATE Imports
    from resonaate.common.logger import Logger
    from resonaate.data.resonaate_database import ResonaateDatabase



@pytest.fixture(autouse=True)
def _clearCaches():
    """Make sure cached config info is cleared between tests."""
    yield
    rootConfigSpec.cache_clear()
    getConfig.cache_clear()


@pytest.fixture(scope="session", name="test_logger")
def getTestLoggerObject() -> Logger:
    """Create a custom :class:`logging.Logger` object."""
    logger = logging.getLogger("Unit Test Logger")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger


@pytest.fixture(name="key_value_store", autouse=True)
def _generateKeyValueStore():
    """Make sure that :class:`.KeyValueStore.Server` is flushed after each test, but not shutdown."""
    ref = KeyValueStore.getClient()
    yield
    ref.submitTransaction(FlushTransaction())


@pytest.fixture(name="database")
def getDataInterface(tmp_path: Path) -> ResonaateDatabase:
    """Create common, non-shared DB object for all tests.

    Yields:
        :class:`.ResonaateDatabase`: properly constructed DB object
    """
    # [NOTE]: copy blank test DBs to pytest tmp dir
    orig_db_dir = FIXTURE_DATA_DIR / SHARED_DB_PATH.parent
    tmp_db_dir = tmp_path / SHARED_DB_PATH.parent
    shutil.copytree(orig_db_dir, tmp_db_dir, dirs_exist_ok=True)
    # [NOTE]: properly set DB connection string using tmp dir
    db_params = OutputDbUrlSpec(output_db_name=str(tmp_path / SHARED_DB_PATH))
    setDBParams(db_params)
    yield getDBConnection()
    clearDBParams()


@pytest.fixture(name="propagate_scenario")
def propagateFixture() -> PropagateFunc:
    """Returns function that propagates a scenario."""
    return propagateScenario


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
    perturbations_config: PerturbationsConfig,
    geopotential_config: GeopotentialConfig,
) -> SpecialPerturbations:
    """Return a :class:`.SpecialPerturbations` object based on configurations."""
    return SpecialPerturbations(TEST_START_JD, geopotential_config, perturbations_config, 0.0)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command line options."""
    parser.addoption("--runslow", action="store_true", default=False, help="run slow tests")


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest options without an .ini file."""
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "regression: mark test as a regression test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "scenario: mark test as a scenario test")
    config.addinivalue_line("markers", "event: mark test as an event test")
    config.addinivalue_line("markers", "estimation: mark test as an integration test")
    config.addinivalue_line("markers", "no_debug: turn off parallel debug mode for test")


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Collect pytest modifiers."""
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
