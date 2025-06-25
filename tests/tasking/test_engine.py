from __future__ import annotations

# Standard Library Imports
import re
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, create_autospec, patch

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.data.importer_database import ImporterDatabase
from resonaate.data.observation import MissedObservation, Observation
from resonaate.physics.time.stardate import JulianDate
from resonaate.scenario.config.decision_config import MunkresDecisionConfig
from resonaate.scenario.config.reward_config import CostConstrainedRewardConfig
from resonaate.sensors.sensor_base import Sensor
from resonaate.tasking.decisions import decisionFactory
from resonaate.tasking.engine.centralized_engine import CentralizedTaskingEngine
from resonaate.tasking.engine.engine_base import TaskingEngine
from resonaate.tasking.rewards import rewardsFactory

# Type Checking Imports
if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.tasking.decisions import Decision
    from resonaate.tasking.rewards import Reward

SENSOR_NUMS: list[int] = [100000]
TARGET_NUMS: list[int] = [10001, 10002, 10003]


pytestmark = pytest.mark.usefixtures("database")


@pytest.fixture(name="decision")
def getDecision() -> Decision:
    """Returns a valid Decision object."""
    decision_config = MunkresDecisionConfig()
    return decisionFactory(decision_config)


@pytest.fixture(name="reward")
def getReward() -> Reward:
    """Returns a valid Reward object."""
    reward_config = CostConstrainedRewardConfig(
        metrics=[
            {"name": "KLDivergence", "parameters": {}},
            {"name": "SlewDistanceMinimization", "parameters": {}},
            {"name": "LyapunovStability", "parameters": {}},
        ],
    )
    return rewardsFactory(reward_config)


@pytest.fixture(name="centralized_tasking_engine")
def getCentralizedEngineClass(reward: Reward, decision: Decision) -> CentralizedTaskingEngine:
    """Return reference to a minimal :class:`.Engine` class.

    Args:
        reward (:class:`.Reward`): Loaded reward object
        decision (:class:`.Decision`): Loaded decision object

    Returns:
        :class:`.CentralizedTaskingEngine`
    """
    return CentralizedTaskingEngine(
        engine_id=0,
        sensor_ids=SENSOR_NUMS,
        target_ids=TARGET_NUMS,
        reward=reward,
        decision=decision,
        importer_db_path=None,
        realtime_obs=True,
    )


def testGenerateTaskingNull(centralized_tasking_engine: CentralizedTaskingEngine):
    """Test generateTasking() null case.

    Args:
        centralized_tasking_engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
    """
    centralized_tasking_engine.visibility_matrix = np.array([[0, 0, 0]], dtype=bool)
    centralized_tasking_engine.reward_matrix = np.array([[0, 0, 0]], dtype=float)
    centralized_tasking_engine.decision_matrix = np.zeros((3, 1), dtype=bool)
    centralized_tasking_engine.generateTasking()
    assert np.array_equal(centralized_tasking_engine.decision_matrix, [[False, False, False]])


def testNormalizeMetrics(centralized_tasking_engine: CentralizedTaskingEngine):
    """Test normalizeMetrics().

    Args:
        centralized_tasking_engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
    """
    metric_matrix = np.array([[[0.1, 0.0, 0.0]], [[0.0, 2.0, 0.0]], [[0.0, 0.0, 3.0]]])
    metrics = centralized_tasking_engine.reward.normalizeMetrics(metric_matrix)
    assert metrics.max() <= 1.0


def testCalculateRewards(centralized_tasking_engine: CentralizedTaskingEngine):
    """Test calculateRewards().

    Args:
        centralized_tasking_engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
    """
    centralized_tasking_engine.metric_matrix = np.eye(3)
    centralized_tasking_engine.calculateRewards()
    assert np.isclose(
        centralized_tasking_engine.reward_matrix,
        np.array([[0.85], [-0.15], [0.85]]),
    ).all()


def testGenerateTasking(centralized_tasking_engine: CentralizedTaskingEngine):
    """Test generateTasking().

    Args:
        centralized_tasking_engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
    """
    centralized_tasking_engine.visibility_matrix = np.array([[1, 0.1, 3.0]], dtype=bool)
    centralized_tasking_engine.reward_matrix = np.array([[7.0, 5.0, 0]], dtype=float)
    centralized_tasking_engine.decision_matrix = np.zeros((3, 1), dtype=bool)
    centralized_tasking_engine.generateTasking()
    assert np.array_equal(centralized_tasking_engine.decision_matrix, [[True, False, False]])


@patch("resonaate.tasking.engine.centralized_engine.handleRelevantEvents")
def testAssessWithNoObservations(
    event_handler_mock: MagicMock,
    centralized_tasking_engine: CentralizedTaskingEngine,
):
    """Test assess() when no observations occur.

    Args:
        event_handler_mock (``MagicMock``): Fake event handler
        centralized_tasking_engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
    """
    julian_date = JulianDate.getJulianDate(2019, 1, 23, 17, 42, 23.2)
    next_julian_date = JulianDate.getJulianDate(2019, 1, 23, 17, 43, 23.2)
    # Set realtime_obs to False to test that the engine does not attempt to handle events
    centralized_tasking_engine._realtime_obs = False
    centralized_tasking_engine._reward_executor.enqueueJob = MagicMock()
    centralized_tasking_engine._task_exec_executor.enqueueJob = MagicMock()
    centralized_tasking_engine.assess(julian_date, next_julian_date)
    # Assert handlers are not called
    centralized_tasking_engine._reward_executor.enqueueJob.assert_not_called()
    centralized_tasking_engine._task_exec_executor.enqueueJob.assert_not_called()
    event_handler_mock.assert_not_called()
    assert centralized_tasking_engine._observations == []


@patch("resonaate.tasking.engine.centralized_engine.handleRelevantEvents")
def testAssessWithObservations(
    event_handler_mock: MagicMock,
    centralized_tasking_engine: CentralizedTaskingEngine,
):
    """Test assess() when no observations occur.

    Args:
        event_handler_mock (``MagicMock``): Fake event handler
        centralized_tasking_engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
    """
    datetime_epoch = datetime(2019, 1, 23, 17, 42, 23, 200000)
    next_datetime_epoch = datetime(2019, 1, 23, 17, 43, 23, 200000)
    # Create obs tuples to store
    obs_1 = create_autospec(Observation, instance=True)
    obs_1.sensor_id = 100000
    obs_2 = create_autospec(Observation, instance=True)
    obs_2.sensor_id = 100001
    # centralized_tasking_engine._observations = [obs_1, obs_2]

    # [FIXME]: This is a hack to get the engine to store the observations
    #   This is required because the engine resets the observations at the beginning of each
    #   assess()
    def handleEvents(engine: CentralizedTaskingEngine, *args, **kwargs):
        """Mock a side effect to dynamically set the observations.

        Args:
            engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
            args (Any): not used.
            kwargs (Any): not used.
        """
        engine._observations = [obs_1, obs_2]

    event_handler_mock.side_effect = handleEvents

    centralized_tasking_engine._reward_executor.enqueueJob = MagicMock()
    centralized_tasking_engine._task_exec_executor.enqueueJob = MagicMock()
    centralized_tasking_engine._estimate_store = {
        est_id: None for est_id in centralized_tasking_engine.target_list
    }
    centralized_tasking_engine._sensor_store = {
        obs_1.sensor_id: getMockedSensingAgentObject(obs_1.sensor_id),
        obs_2.sensor_id: getMockedSensingAgentObject(obs_2.sensor_id),
    }
    centralized_tasking_engine.assess(datetime_epoch, next_datetime_epoch)
    # Assert handlers are called
    assert centralized_tasking_engine._reward_executor.enqueueJob.call_count == len(
        centralized_tasking_engine.target_list,
    )
    centralized_tasking_engine._task_exec_executor.enqueueJob.assert_not_called()
    event_handler_mock.assert_called_once()
    # Assert targets & observations are updated
    assert len(centralized_tasking_engine._observations) == 2


@patch.object(CentralizedTaskingEngine, "loadImportedObservations")
@patch.object(CentralizedTaskingEngine, "saveObservations")
def testAssessWithImportedObservations(
    save_obs_mock: MagicMock,
    load_obs_mock: MagicMock,
    centralized_tasking_engine: CentralizedTaskingEngine,
):
    """Test assess() when no observations occur.

    Args:
        save_obs_mock (``MagicMock``): Fake saveObservations()
        load_obs_mock (``MagicMock``): Fake loadImportedObservations()
        centralized_tasking_engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
    """
    centralized_tasking_engine._realtime_obs = False
    centralized_tasking_engine._importer_db = True
    mock_obs = create_autospec(Observation, instance=True)
    load_obs_mock.return_value = [mock_obs]
    datetime_epoch = datetime(2019, 1, 23, 17, 42, 23, 200000)
    next_datetime_epoch = datetime(2019, 1, 23, 17, 43, 23, 200000)
    # Set realtime_obs to False to test that the engine does not attempt to handle events
    centralized_tasking_engine._realtime_obs = False
    centralized_tasking_engine.assess(datetime_epoch, next_datetime_epoch)
    # Assert handlers are not called
    load_obs_mock.assert_called_once_with(next_datetime_epoch)
    save_obs_mock.assert_called_once_with([mock_obs])


def testGetSaveObservation(centralized_tasking_engine: CentralizedTaskingEngine):
    """Test saveObservations().

    Args:
        centralized_tasking_engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
    """
    assert centralized_tasking_engine.observations == []
    assert centralized_tasking_engine._saved_observations == []
    assert centralized_tasking_engine.getCurrentObservations() == []
    assert centralized_tasking_engine.observations == []
    assert centralized_tasking_engine._saved_observations == []

    # Test saving no observations
    centralized_tasking_engine.saveObservations([])
    assert centralized_tasking_engine._saved_observations == []
    assert centralized_tasking_engine.getCurrentObservations() == []
    assert centralized_tasking_engine.observations == []
    assert centralized_tasking_engine._saved_observations == []

    # Test saving observations
    mock_obs = create_autospec(Observation, instance=True)
    centralized_tasking_engine.saveObservations([mock_obs])
    assert centralized_tasking_engine.observations == [mock_obs]
    centralized_tasking_engine.saveObservations([mock_obs])
    assert centralized_tasking_engine._saved_observations == [mock_obs, mock_obs]
    assert centralized_tasking_engine.getCurrentObservations() == [mock_obs, mock_obs]
    # Test that the saved observations are cleared
    assert centralized_tasking_engine._saved_observations == []


def testGetSaveMissedObservation(centralized_tasking_engine: CentralizedTaskingEngine):
    """Test saveMissedObservations().

    Args:
        centralized_tasking_engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
    """
    assert centralized_tasking_engine.missed_observations == []
    assert centralized_tasking_engine._saved_missed_observations == []
    assert centralized_tasking_engine.getCurrentMissedObservations() == []
    assert centralized_tasking_engine.missed_observations == []
    assert centralized_tasking_engine._saved_missed_observations == []

    # Test saving no missed observations
    centralized_tasking_engine.saveMissedObservations([])
    assert centralized_tasking_engine._saved_missed_observations == []
    assert centralized_tasking_engine.getCurrentObservations() == []
    assert centralized_tasking_engine.missed_observations == []
    assert centralized_tasking_engine._saved_missed_observations == []

    # Test saving missed observations
    mock_missed_obs = create_autospec(MissedObservation, instance=True)
    centralized_tasking_engine.saveMissedObservations([mock_missed_obs])
    assert centralized_tasking_engine.missed_observations == [mock_missed_obs]
    centralized_tasking_engine.saveMissedObservations([mock_missed_obs])
    assert centralized_tasking_engine._saved_missed_observations == [
        mock_missed_obs,
        mock_missed_obs,
    ]
    assert centralized_tasking_engine.getCurrentMissedObservations() == [
        mock_missed_obs,
        mock_missed_obs,
    ]
    # Test that the saved missed observations are cleared
    assert centralized_tasking_engine._saved_missed_observations == []


def testGetCurrentTasking(reward: Reward, decision: Decision):
    """Test getCurrentTasking() returns valid tasks.

    Args:
        reward (:class:`.Reward`): Loaded reward object
        decision (:class:`.Decision`): Loaded decision object
    """
    rng = np.random.default_rng(seed=654135132156)
    sensor_list = set(rng.integers(low=10000, high=20000, size=20))
    target_list = set(rng.integers(low=60000, high=70000, size=100))

    engine = CentralizedTaskingEngine(
        engine_id=1,
        sensor_ids=sensor_list,
        target_ids=target_list,
        reward=reward,
        decision=decision,
        importer_db_path=None,
        realtime_obs=True,
    )
    julian_date = JulianDate.getJulianDate(2019, 1, 23, 17, 42, 23.2)
    sensor_list = sorted(sensor_list)
    target_list = sorted(target_list)

    # Null tasks
    assert list(engine.getCurrentTasking(julian_date))
    for task in engine.getCurrentTasking(julian_date):
        assert task.sensor_id in sensor_list
        assert task.target_id in target_list
        assert task.reward == 0.0
        assert bool(task.decision) is False
        assert bool(task.visibility) is False

    # Apply "tasking algorithm"
    engine.visibility_matrix = rng.integers(
        low=0,
        high=1,
        size=(engine.num_targets, engine.num_sensors),
        endpoint=True,
    )
    engine.reward_matrix = rng.uniform(
        low=0,
        high=1,
        size=(engine.num_targets, engine.num_sensors),
    )
    engine.decision_matrix = np.multiply(engine.visibility_matrix, engine.reward_matrix)

    # Some task should be none null
    for task in engine.getCurrentTasking(julian_date):
        sen_idx = sensor_list.index(task.sensor_id)
        tgt_idx = target_list.index(task.target_id)
        assert task.sensor_id in sensor_list
        assert task.target_id in target_list
        assert task.visibility == engine.visibility_matrix[tgt_idx, sen_idx]
        assert task.reward == engine.reward_matrix[tgt_idx, sen_idx]
        assert task.decision == engine.decision_matrix[tgt_idx, sen_idx]
        assert task.julian_date == julian_date


def getMockedSensingAgentObject(agent_id: int) -> SensingAgent:
    """Create a mocked :class:`.SensingAgent` object.

    Args:
        agent_id (``int``): satcat ID

    Returns:
        :class:`.SensingAgent`
    """
    mocked_sensor = create_autospec(Sensor, instance=True)
    sensing_agent = create_autospec(SensingAgent, instance=True)
    sensing_agent._id = agent_id

    sensing_agent.sensors = mocked_sensor
    return sensing_agent


def mockedAttachObsMetadata(self, observation: Observation) -> Observation:
    """Fake replacement for :meth:`.CentralizedEngine._attachObsMetadata()`.

    Args:
        self: Reference to the :class:`.TaskingEngine` making this call.
        observation: The :class:`.Observation` that metadata is supposed to be attached to.
    """
    return observation


@patch.object(CentralizedTaskingEngine, "_attachObsMetadata", new=mockedAttachObsMetadata)
@patch("resonaate.tasking.engine.engine_base.ImporterDatabase", autospec=True)
def testLoadImportedObservation(
    mocked_importer_db: MagicMock,
    centralized_tasking_engine: CentralizedTaskingEngine,
):
    """Test loadImportedObservations().

    Args:
        mocked_meta_attach: Fake metadata attachment method.
        mocked_importer_db (``MagicMock``): Fake imported database
        centralized_tasking_engine (:class:`.CentralizedTaskingEngine`): Loaded Engine
    """
    mocked_importer_db.getData = MagicMock()
    centralized_tasking_engine._importer_db = mocked_importer_db
    datetime_epoch = datetime(2019, 1, 23, 17, 42, 23, 200000)
    # Create mock observations
    obs_1 = create_autospec(Observation, instance=True)
    sensing_agent_1_id = 1111
    obs_1.pos_x_km = 7000
    obs_1.pos_y_km = 0
    obs_1.pos_z_km = 0
    obs_1.vel_x_km_p_sec = 2
    obs_1.vel_y_km_p_sec = 2
    obs_1.vel_z_km_p_sec = 2
    obs_1.target_id = 1
    obs_1.sensor_id = sensing_agent_1_id
    obs_1.makeDictionary = MagicMock()

    sensing_agent_2_id = 1112
    obs_2 = create_autospec(Observation, instance=True)
    obs_2.pos_x_km = -7000
    obs_2.pos_y_km = 0
    obs_2.pos_z_km = 0
    obs_2.vel_x_km_p_sec = 2
    obs_2.vel_y_km_p_sec = 2
    obs_2.vel_z_km_p_sec = 2
    obs_2.target_id = 1
    obs_2.sensor_id = sensing_agent_2_id
    obs_2.makeDictionary = MagicMock()

    # Test observations that aren't from duplicate sensors
    mocked_importer_db.getData.return_value = [obs_1, obs_2]

    imported_obs = centralized_tasking_engine.loadImportedObservations(datetime_epoch)

    # Assert mock calls
    obs_1.makeDictionary.assert_not_called()
    obs_2.makeDictionary.assert_not_called()
    mocked_importer_db.getData.assert_called_once()
    for imported_ob in imported_obs:
        assert isinstance(imported_ob, Observation)

    # Reset mocks
    mocked_importer_db.getData.reset_mock()
    obs_1.makeDictionary.reset_mock()
    obs_2.makeDictionary.reset_mock()

    # Test observations that are from duplicate sensors
    obs_2.pos_x_km = 7000
    obs_2.pos_y_km = 0
    obs_2.pos_z_km = 0
    obs_2.vel_x_km_p_sec = 2
    obs_2.vel_y_km_p_sec = 2
    obs_2.vel_z_km_p_sec = 2
    obs_2.target_id = 1
    mocked_importer_db.getData.return_value = [obs_1, obs_2]
    centralized_tasking_engine.loadImportedObservations(datetime_epoch)
    # [NOTE]: Only the second one will be seen as a duplicate
    obs_1.makeDictionary.assert_not_called()
    obs_2.makeDictionary.assert_called_once()
    mocked_importer_db.getData.assert_called_once()
    for imported_ob in imported_obs:
        assert isinstance(imported_ob, Observation)

    # Reset mocks
    mocked_importer_db.getData.reset_mock()
    obs_1.makeDictionary.reset_mock()
    obs_2.makeDictionary.reset_mock()

    # Test no imported observations
    mocked_importer_db.getData.return_value = []
    centralized_tasking_engine.loadImportedObservations(datetime_epoch)
    obs_1.makeDictionary.assert_not_called()
    obs_2.makeDictionary.assert_not_called()
    mocked_importer_db.getData.assert_called_once()
    for imported_ob in imported_obs:
        assert isinstance(imported_ob, Observation)


@patch.multiple(TaskingEngine, __abstractmethods__=set())
@patch("resonaate.tasking.engine.engine_base.ImporterDatabase")
def testCreateTaskingEngine(mocked_importer_db: MagicMock, reward: Reward, decision: Decision):
    """Test creating the base class & basic functionality.

    Args:
        mocked_importer_db (``MagicMock``): Fake shared mock
        reward (:class:`.Reward`): Loaded reward object
        decision (:class:`.Decision`): Loaded decision object
    """
    # Valid creation
    engine = TaskingEngine(
        engine_id=0,
        sensor_ids=SENSOR_NUMS,
        target_ids=TARGET_NUMS,
        reward=reward,
        decision=decision,
    )

    assert engine.unique_id == 0
    assert engine.reward is reward
    assert engine.decision is decision
    assert not engine.observations
    assert engine._importer_db is None

    # Valid creation with importer db
    mocked_importer_db.return_value = create_autospec(ImporterDatabase, instance=True)
    engine = TaskingEngine(
        engine_id=0,
        sensor_ids=SENSOR_NUMS,
        target_ids=TARGET_NUMS,
        reward=reward,
        decision=decision,
        importer_db_path="test.db",
    )
    mocked_importer_db.assert_called_once_with(db_path="test.db")
    assert isinstance(engine._importer_db, ImporterDatabase)

    # Test invalid reward/decision
    with pytest.raises(TypeError):
        _ = TaskingEngine(
            engine_id=0,
            sensor_ids=SENSOR_NUMS,
            target_ids=TARGET_NUMS,
            reward="not a reward class",
            decision=decision,
        )

    with pytest.raises(TypeError):
        _ = TaskingEngine(
            engine_id=0,
            sensor_ids=SENSOR_NUMS,
            target_ids=TARGET_NUMS,
            reward=reward,
            decision="not a decision class",
        )


@patch.multiple(TaskingEngine, __abstractmethods__=set())
def testSortOnCreation(reward: Reward, decision: Decision):
    """Test that the sensor & target lists are sorted on creation.

    Args:
        reward (:class:`.Reward`): Loaded reward object
        decision (:class:`.Decision`): Loaded decision object
    """
    rng = np.random.default_rng(seed=654135132156)
    sensor_list = set(rng.integers(low=10000, high=20000, size=200))
    target_list = set(rng.integers(low=60000, high=70000, size=1000))

    # Valid creation
    engine = TaskingEngine(
        engine_id=0,
        sensor_ids=sensor_list,
        target_ids=target_list,
        reward=reward,
        decision=decision,
    )
    assert np.array_equal(engine.sensor_list, list(engine.sensor_indices.keys()))
    assert np.array_equal(engine.sensor_list, sorted(sensor_list))
    assert len(engine.sensor_list) == len(engine.sensor_indices)
    assert np.array_equal(engine.target_list, list(engine.target_indices.keys()))
    assert np.array_equal(engine.target_list, sorted(target_list))
    assert len(engine.target_list) == len(engine.target_indices)


@patch.multiple(TaskingEngine, __abstractmethods__=set())
def testAddingRemovingSensors(reward: Reward, decision: Decision):
    """Test adding/removing senors.

    Args:
        reward (:class:`.Reward`): Loaded reward object
        decision (:class:`.Decision`): Loaded decision object
    """
    engine = TaskingEngine(
        engine_id=0,
        sensor_ids=[],
        target_ids=TARGET_NUMS,
        reward=reward,
        decision=decision,
    )
    assert engine.num_sensors == 0
    assert not engine.sensor_list
    assert not engine.sensor_indices

    engine.addSensor(100)
    assert engine.num_sensors == 1
    assert engine.sensor_indices == {100: 0}

    engine.addSensor(101)
    assert engine.num_sensors == 2
    assert engine.sensor_list == [100, 101]
    assert engine.sensor_indices == {100: 0, 101: 1}

    engine.removeSensor(100)
    assert engine.num_sensors == 1
    assert engine.sensor_list == [101]
    assert engine.sensor_indices == {101: 0}

    engine.removeSensor(101)
    assert engine.num_sensors == 0
    assert not engine.sensor_list
    assert not engine.sensor_indices

    # Test sorting of sensors on add/remove
    engine.addSensor(102)
    engine.addSensor(101)
    engine.addSensor(100)
    assert engine.sensor_list == [100, 101, 102]
    assert engine.sensor_indices == {100: 0, 101: 1, 102: 2}

    engine.removeSensor(100)
    assert engine.sensor_list == [101, 102]
    assert engine.sensor_indices == {101: 0, 102: 1}

    engine.removeSensor(101)
    assert engine.sensor_list == [102]
    assert engine.sensor_indices == {102: 0}

    # Test bad removal index
    with pytest.raises(ValueError, match=re.escape("list.remove(x): x not in list")):
        engine.removeSensor(100)


@patch.multiple(TaskingEngine, __abstractmethods__=set())
def testAddingRemovingTargets(reward: Reward, decision: Decision):
    """Test adding/removing targets.

    Args:
        reward (:class:`.Reward`): Loaded reward object
        decision (:class:`.Decision`): Loaded decision object
    """
    engine = TaskingEngine(
        engine_id=0,
        sensor_ids=SENSOR_NUMS,
        target_ids=[],
        reward=reward,
        decision=decision,
    )
    assert engine.num_targets == 0
    assert not engine.target_list
    assert not engine.target_indices

    engine.addTarget(1000)
    assert engine.num_targets == 1
    assert engine.target_list == [1000]
    assert engine.target_indices == {1000: 0}

    engine.addTarget(1001)
    assert engine.num_targets == 2
    assert engine.target_list == [1000, 1001]
    assert engine.target_indices == {1000: 0, 1001: 1}

    engine.removeTarget(1000)
    assert engine.num_targets == 1
    assert engine.target_list == [1001]
    assert engine.target_indices == {1001: 0}

    engine.removeTarget(1001)
    assert engine.num_targets == 0
    assert not engine.target_list
    assert not engine.target_indices

    engine.addTarget(1002)
    engine.addTarget(1001)
    engine.addTarget(1000)
    assert engine.num_targets == 3
    assert engine.target_list == [1000, 1001, 1002]
    assert engine.target_indices == {1000: 0, 1001: 1, 1002: 2}

    engine.removeTarget(1000)
    assert engine.target_list == [1001, 1002]
    assert engine.target_indices == {1001: 0, 1002: 1}

    engine.removeTarget(1001)
    assert engine.target_list == [1002]
    assert engine.target_indices == {1002: 0}

    # Test bad removal index
    with pytest.raises(ValueError, match=re.escape("list.remove(x): x not in list")):
        engine.removeTarget(1000)
