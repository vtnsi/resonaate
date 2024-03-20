from __future__ import annotations

# Standard Library Imports
import os.path
import re
from copy import deepcopy
from unittest.mock import Mock, create_autospec, patch

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.exceptions import (
    DuplicateEngineError,
    DuplicateSensorError,
    DuplicateTargetError,
)
from resonaate.data.resonaate_database import ResonaateDatabase
from resonaate.scenario.config import ScenarioConfig
from resonaate.scenario.config.event_configs import (
    DataDependency,
    MissingDataDependencyError,
    TargetTaskPriorityConfig,
)
from resonaate.scenario.scenario_builder import ScenarioBuilder

# Local Imports
from .. import FIXTURE_DATA_DIR, JSON_INIT_PATH


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testSafeDuplicateTargets(datafiles: str, database: ResonaateDatabase):
    """Verify no errors are thrown if two engines are looking at the same target network."""
    init_filepath = os.path.join(datafiles, JSON_INIT_PATH, "test_init.json")
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(init_filepath)
    first_target_network = None
    for engine in scenario_cfg_dict["engines"]:
        if not first_target_network:
            first_target_network = engine["targets"]
        else:
            engine["targets"] = first_target_network

    config = ScenarioConfig(**scenario_cfg_dict)
    ScenarioBuilder(config)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testECICOEDuplicateTargets(datafiles: str, database: ResonaateDatabase):
    """Verify errors are thrown if two engines are looking at the same target with different initial states."""
    init_filepath = os.path.join(datafiles, JSON_INIT_PATH, "test_init.json")
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(init_filepath)
    first_target_network = None
    for engine in scenario_cfg_dict["engines"]:
        if not first_target_network:
            first_target_network = deepcopy(engine["targets"])
            first_target_network[0]["state"] = {
                "type": "coe",
                "semi_major_axis": 7000.0,
                "eccentricity": 0,
                "inclination": 0,
                "true_longitude": 0,
            }
        else:
            engine["targets"] = first_target_network

    config = ScenarioConfig(**scenario_cfg_dict)
    with pytest.raises(DuplicateTargetError):
        ScenarioBuilder(config)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testDiffStateDuplicateTargets(datafiles: str, database: ResonaateDatabase):
    """Verify errors are thrown if two engines are looking at the same target with different initial states."""
    init_filepath = os.path.join(datafiles, JSON_INIT_PATH, "test_init.json")
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(init_filepath)
    first_target_network = None
    for engine in scenario_cfg_dict["engines"]:
        if not first_target_network:
            first_target_network = deepcopy(engine["targets"])
            first_target_network[0]["state"]["position"][0] += 0.1
        else:
            engine["targets"] = first_target_network

    config = ScenarioConfig(**scenario_cfg_dict)
    with pytest.raises(DuplicateTargetError):
        ScenarioBuilder(config)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testDuplicateSensors(datafiles: str, database: ResonaateDatabase):
    """Verify errors are thrown if two engines are tasking the same sensors."""
    init_filepath = os.path.join(datafiles, JSON_INIT_PATH, "test_init.json")
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(init_filepath)
    first_sensor_network = None
    for engine in scenario_cfg_dict["engines"]:
        if not first_sensor_network:
            first_sensor_network = engine["sensors"]
        else:
            engine["sensors"] = first_sensor_network

    config = ScenarioConfig(**scenario_cfg_dict)
    with pytest.raises(DuplicateSensorError):
        ScenarioBuilder(config)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testDuplicateEngines(datafiles: str, database: ResonaateDatabase):
    """Verify errors are thrown if two engines are tasking the same sensors."""
    init_filepath = os.path.join(datafiles, JSON_INIT_PATH, "test_init.json")
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(init_filepath)

    # Add a duplicate engine (engine with same ID)
    scenario_cfg_dict["engines"].append(deepcopy(scenario_cfg_dict["engines"][0]))

    config = ScenarioConfig(**scenario_cfg_dict)
    unique_id = scenario_cfg_dict["engines"][0]["unique_id"]
    expected = f"Engines share a unique ID: {unique_id}"
    with pytest.raises(DuplicateEngineError, match=re.escape(expected)):
        ScenarioBuilder(config)


@pytest.fixture(name="tgt_task_priority")
def getTargetTaskPriorityDict() -> dict:
    """Return a dictionary of target task priority configs."""
    return {
        "scope": "task_reward_generation",
        "scope_instance_id": 1,
        "start_time": "2018-12-01T12:10:00.000Z",
        "end_time": "2018-12-01T12:30:00.000Z",
        "event_type": "task_priority",
        "target_id": 12089,
        "target_name": "INTELSAT 502",
        "priority": 5.0,
        "is_dynamic": True,
    }


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testFoundDataDependency(datafiles: str, tgt_task_priority: dict, database: ResonaateDatabase):
    """Verify no errors are thrown if two engines are looking at the same target network."""
    init_filepath = os.path.join(datafiles, JSON_INIT_PATH, "test_init.json")
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(init_filepath)

    # This dependency should be found
    scenario_cfg_dict["events"].append(tgt_task_priority)
    _ = ScenarioBuilder(ScenarioConfig(**scenario_cfg_dict))


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testNotFoundDataDependency(
    datafiles: str,
    tgt_task_priority: dict,
    database: ResonaateDatabase,
):
    """Verify no errors are thrown if two engines are looking at the same target network."""
    init_filepath = os.path.join(datafiles, JSON_INIT_PATH, "test_init.json")
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(init_filepath)

    # This dependency is not found
    tgt_task_priority["target_id"] = 100
    tgt_task_priority["target_name"] = "Random RSO"
    tgt_task_priority["priority"] = False
    scenario_cfg_dict["events"].append(tgt_task_priority)
    _ = ScenarioBuilder(ScenarioConfig(**scenario_cfg_dict))


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
@patch.object(ResonaateDatabase, "getData", return_value=None)
def testMissingDataDependency(
    mocked_db: ResonaateDatabase,
    datafiles: str,
    tgt_task_priority: dict,
    database: ResonaateDatabase,
):
    """Verify ValuerError is thrown if you can't find, nor create a DataDependency."""
    init_filepath = os.path.join(datafiles, JSON_INIT_PATH, "test_init.json")
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(init_filepath)

    # [NOTE]: This is necessary, because you can't create mocked `EventConfig` objects,
    #   or at least I haven't been able to.
    tgt_event = TargetTaskPriorityConfig(**tgt_task_priority)

    # Mock the `DataDependency` used by `TargetTaskPriorityConfig`, so that calling
    #   `dependency.createDependency()` raises a `MissingDataDependency` exception.
    dummy_data_dependency = create_autospec(DataDependency, instance=True)
    dummy_data_dependency.query = "SQL QUERY"
    _udder_mock = Mock(side_effect=MissingDataDependencyError("DataType"))
    dummy_data_dependency.createDependency = _udder_mock

    # Mock the `getDataDependencies()` method of the `EventConfig` class, so that it returns
    #   the `dummy_data_dependency` object.
    _mock = Mock(return_value=[dummy_data_dependency])
    tgt_event.getDataDependencies = _mock

    # This dependency is not found
    scenario_cfg_dict["events"].append(tgt_event)

    expected = f"Event {tgt_event.event_type!r} is missing a data dependency."
    with pytest.raises(ValueError, match=re.escape(expected)):
        _ = ScenarioBuilder(ScenarioConfig(**scenario_cfg_dict))
