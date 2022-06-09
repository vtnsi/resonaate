# pylint: disable=invalid-name, attribute-defined-outside-init, no-self-use
# Standard Library Imports
import logging
import os
import sys
from unittest.mock import create_autospec
# Third Party Imports
from numpy import asarray
import pytest
# Resonaate Imports
try:
    from resonaate.agents.estimate_agent import EstimateAgent
    from resonaate.agents.sensing_agent import SensingAgent
    from resonaate.common.behavioral_config import BehavioralConfig
    from resonaate.filters.unscented_kalman_filter import UnscentedKalmanFilter
    from resonaate.parallel import getRedisConnection, isMaster, resetMaster
    from resonaate.parallel.job import Job
    from resonaate.scenario.clock import ScenarioClock
    from resonaate.physics.time.stardate import ScenarioTime
    from resonaate.sensors.sensor_base import Sensor
    from resonaate.tasking.decisions.decision_base import Decision
    from resonaate.tasking.engine.centralized_engine import CentralizedTaskingEngine
    from resonaate.tasking.metrics.metric_base import Metric
    from resonaate.tasking.rewards.reward_base import Reward
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error


FIXTURE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "datafiles",
)


class BaseTestCase:
    """Base unit test class for all to inherit from.

    This is primarily for storing global constants/common file locations, etc.
    """

    importer_db_path = "db/importer.sqlite3"
    shared_db_path = "db/shared.sqlite3"
    json_init_path = "json/config/init_messages"
    json_rso_truth = "json/rso_truth"
    json_sensor_truth = "json/sat_sensor_truth"


@pytest.fixture(autouse=True)
def patchMissingEnvVariables(monkeypatch):
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
def getTestLoggerObject():
    """Create a custom :class:`logging.Logger` object."""
    logger = logging.getLogger("Unit Test Logger")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(handler)
    return logger


@pytest.fixture(scope="function", name="redis")
def getRedisInstance():
    """Setup and destroy an instance of Redis key-value store."""
    redis_conn = getRedisConnection()
    redis_conn.flushall()
    yield isMaster()
    resetMaster()


@pytest.fixture(scope="class", name="mocked_clock")
def getMockedClockObject():
    """Create a mocked :class:`.ScenarioClock` object."""
    clock = create_autospec(ScenarioClock)
    clock.dt_step = 60
    clock.julian_date_start = 2458454.0
    clock.time = ScenarioTime(2458454.0)
    return clock


@pytest.fixture(scope="class", name="mocked_estimate")
def getMockedEstimateObject():
    """Create a mocked :class:`.EstimateAgent` object."""
    estimate = create_autospec(EstimateAgent)
    estimate.nominal_filter.pred_p = asarray([[4, 23], [1, 67]])
    estimate.nominal_filter.est_p = asarray([[1, 1], [2, 4]])
    estimate.nominal_filter.cross_cvr = asarray(
        [
            [3, 1, 12],
            [12, 344, 2]
        ]
    )
    estimate.initial_covariance = asarray([[1, 1], [3, 2]])
    estimate.last_observed_at = 2458454.0
    return estimate


@pytest.fixture(scope="class", name="mocked_sensor")
def getMockedSensorObject():
    """Create a mocked :class:`.Sensor` object."""
    sensor = create_autospec(Sensor)
    sensor.r_matrix = asarray(
        [
            [7.0e-4, 0.0, 0.0],
            [0.0, 6.5e-4, 0.0],
            [0.0, 0.0, 8.0e-4]
        ]
    )
    sensor.delta_boresight = 4.0
    sensor.slew_rate = 2.0
    return sensor


@pytest.fixture(scope="class", name="mocked_sensing_agent")
def getMockedSensingAgentObject(mocked_sensor):
    """Create a mocked :class:`.SensingAgent` object."""
    sensing_agent = create_autospec(SensingAgent)
    mocked_sensor.r_matrix = asarray(
        [
            [7.0e-4, 0.0, 0.0],
            [0.0, 6.5e-4, 0.0],
            [0.0, 0.0, 8.0e-4]
        ]
    )
    mocked_sensor.delta_boresight = 4.0
    mocked_sensor.slew_rate = 2.0

    sensing_agent.sensors = mocked_sensor
    return sensing_agent


@pytest.fixture(scope="class", name="mocked_metric")
def getMockedMetricObject():
    """Create a mocked :class:`.Metric` object."""
    metric = create_autospec(Metric)

    return metric


@pytest.fixture(scope="class", name="mocked_error_job")
def getMockedErrorJobObject():
    """Create a mocked error :class:`.Job` object."""
    job = create_autospec(Job)
    job.id = 1
    job.error = "F"

    return job


@pytest.fixture(scope="class", name="mocked_valid_job")
def getMockedValidJobObject():
    """Create a mocked valid :class:`.Job` object."""
    job = create_autospec(Job)
    job.id = 1
    job.status = "processed"
    job.retval = {
        "reward_matrix": [0, 0, 1],
        "visibility": [1, 0, 1],
    }

    return job


@pytest.fixture(scope="class", name="mocked_reward")
def getMockedRewardObject():
    """Create a mocked :class:`.Reward` object."""
    reward = create_autospec(Reward)

    return reward


@pytest.fixture(scope="class", name="mocked_decision")
def getMockedDecisionObject():
    """Create a mocked :class:`.Decision` object."""
    decision = create_autospec(Decision)

    return decision


@pytest.fixture(scope="class", name="mocked_central_tasking_engine")
def getMockedCentralizedTaskingEngineObject():
    """Create a mocked :class:`.CentralizedTaskingEngine` object."""
    central_engine = create_autospec(CentralizedTaskingEngine)

    return central_engine


@pytest.fixture(scope="class", name="mocked_filter")
def getMockedFilterObject():
    """Create a mocked :class:`.UnscentedKalmanFilter` object."""
    mocked_filter = create_autospec(UnscentedKalmanFilter)

    return mocked_filter


def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    """Configure pytest options without an *.ini file."""
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "realtime: mark test as using real time propagation")
    config.addinivalue_line("markers", "importer: mark test as using real time propagation")
    config.addinivalue_line("markers", "datafiles: creates tmpdirs for required data")


def pytest_collection_modifyitems(config, items):
    """Collect pytest modifiers."""
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
