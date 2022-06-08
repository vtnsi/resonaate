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
    from resonaate.data.data_interface import DataInterface
    from resonaate.filters.unscented_kalman_filter import UnscentedKalmanFilter
    from resonaate.networks.sosi_network import SOSINetwork
    from resonaate.parallel import getRedisConnection, isMaster, resetMaster
    from resonaate.parallel.task import Task
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
    """Base unit test class for all to override.

    This is primarily so DB fixtures can assume that the class will have the `shared_db_url` and
    the `output_db_url` attributes.
    """

    shared_db_path = None
    output_db_path = None


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
    isMaster()
    yield
    resetMaster()


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
@pytest.fixture(scope="function", name="shared_db")
def getSharedDatabaseInstance(datafiles, request):
    """Setup and destroy a shared instance of :class:`.DataInterface`."""
    # Check if class overrides DB path
    if request.cls.shared_db_path:
        shared_db_url = "sqlite:///" + os.path.join(datafiles, request.cls.shared_db_path)
    else:
        shared_db_url = None

    # Create & yield instance. Delete after test completes
    drop_tables = (
        "truth_ephemeris", "estimate_ephemeris", "sensor_tasks",
        "node_additions", "observations", "tasking_data"
    )
    shared_interface = DataInterface.getSharedInterface(db_url=shared_db_url)
    yield shared_interface
    shared_interface.resetData(tables=drop_tables)
    if shared_interface:
        del shared_interface


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
@pytest.fixture(scope="function", name="output_db")
def getOutputDatabaseInstance(datafiles, request):
    """Setup and destroy an instance of :class:`.DataInterface`. for output."""
    # Check if class overrides DB path
    if request.cls.output_db_path:
        output_db_url = os.path.join(datafiles, request.cls.output_db_path)
    else:
        output_db_url = os.path.join(datafiles, "db/output_test.db")
    output_db_url = "sqlite:///" + output_db_url

    # Create & yield instance. Delete after test completes
    output_db = DataInterface(db_url=output_db_url)
    yield output_db
    if output_db:
        del output_db


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


@pytest.fixture(scope="class", name="mocked_error_task")
def getMockedErrorTaskObject():
    """Create a mocked error :class:`.Task` object."""
    task = create_autospec(Task)
    task.id = 1
    task.error = "F"

    return task


@pytest.fixture(scope="class", name="mocked_valid_task")
def getMockedValidTaskObject():
    """Create a mocked valid :class:`.Task` object."""
    task = create_autospec(Task)
    task.id = 1
    task.status = "processed"
    task.retval = {
        "reward_matrix": [0, 0, 1],
        "visibility": [1, 0, 1],
    }

    return task


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


@pytest.fixture(scope="class", name="mocked_sosi_network")
def getMockedSOSINetworkObject():
    """Create a mocked :class:`.SOSINetwork` object."""
    sosi_network = create_autospec(SOSINetwork)

    return sosi_network


@pytest.fixture(scope="class", name="mocked_central_tasking_engine")
def getMockedCentralizedTaskingEngineObject():
    """Create a mocked :class:`.CentralizedTaskingEngine` object."""
    cental_engine = create_autospec(CentralizedTaskingEngine)

    return cental_engine


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
