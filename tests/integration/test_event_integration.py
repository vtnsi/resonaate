from __future__ import annotations

# Standard Library Imports
import os.path
from datetime import timedelta
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.agent import AgentModel
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config import ScenarioConfig, constructFromUnion
from resonaate.scenario.config.event_configs import EventConfig
from resonaate.scenario.scenario import Scenario
from resonaate.scenario.scenario_builder import ScenarioBuilder

# Local Imports
from .. import FIXTURE_DATA_DIR, JSON_INIT_PATH

if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.data.resonaate_database import ResonaateDatabase


def _getMainConfig(datafiles_dir: str) -> ScenarioConfig:
    """Set up a main :class:`.ScenarioConfig` object."""
    init_file = os.path.join(datafiles_dir, JSON_INIT_PATH, "main_init.json")
    return ScenarioConfig.fromConfigFile(init_file)


def _getMinimalConfig(datafiles_dir: str) -> ScenarioConfig:
    """Set up a minimal :class:`.ScenarioConfig` object."""
    init_file = os.path.join(datafiles_dir, JSON_INIT_PATH, "minimal_init.json")
    return ScenarioConfig.fromConfigFile(init_file)


def _getManeuverDetectionConfig(datafiles_dir: str) -> ScenarioConfig:
    """Set up a minimal :class:`.ScenarioConfig` object."""
    init_file = os.path.join(datafiles_dir, JSON_INIT_PATH, "minimal_maneuver_detection_init.json")
    return ScenarioConfig.fromConfigFile(init_file)


@pytest.mark.event()
@pytest.mark.integration()
class TestEventIntegration:
    """Test class encapsulating tests that exercise event integration."""

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testBuildScheduledImpulse(self, datafiles: str, database: ResonaateDatabase):
        """Validate that no errors are thrown when building a :class:`.ScheduledImpulseEvent`."""
        minimal_config = _getMinimalConfig(datafiles)
        time = minimal_config.time.start_timestamp + timedelta(minutes=2)

        test_event = constructFromUnion(EventConfig, {
            "scope": "agent_propagation",
            "scope_instance_id": 123,
            "start_time": time,
            "end_time": time,
            "event_type": "impulse",
            "thrust_vector": [0.0, 0.0, 0.00123],
            "thrust_frame": "ntw",
        })
        minimal_config.events.append(test_event)
        assert ScenarioBuilder(minimal_config)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testBuildTargetTaskingPriorityDependency(
        self,
        datafiles: str,
        database: ResonaateDatabase,
    ):
        """Validate that a TargetTaskingPriority's data dependency is built."""
        minimal_config = _getMinimalConfig(datafiles)
        priority_agent = {"unique_id": 12345, "name": "important sat"}
        time = minimal_config.time.start_timestamp + timedelta(minutes=2)

        test_event = constructFromUnion(EventConfig, {
            "scope": "task_reward_generation",
            "scope_instance_id": 123,
            "start_time": time,
            "end_time": time,
            "event_type": "task_priority",
            "target_id": priority_agent["unique_id"],
            "target_name": priority_agent["name"],
            "priority": 2.0,
            "is_dynamic": False,
        })
        minimal_config.events.append(test_event)
        _ = ScenarioBuilder(minimal_config)
        assert database.getData(
            Query([AgentModel]).filter(
                AgentModel.unique_id == priority_agent["unique_id"],
                AgentModel.name == priority_agent["name"],
            ),
            multi=False,
        )

    @pytest.mark.parametrize("seconds", [0, 2])
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testExecuteScheduledImpulse(
        self,
        datafiles: str,
        caplog: pytest.LogCaptureFixture,
        seconds: int,
        database: ResonaateDatabase,
    ):
        """Validate that a ScheduledImpulse is handled correctly."""
        minimal_config = _getMinimalConfig(datafiles)

        tasking_engine = minimal_config.engines[0]
        maneuvering_target = tasking_engine.targets[0]
        time = minimal_config.time.start_timestamp + timedelta(minutes=2, seconds=seconds)

        test_event = constructFromUnion(EventConfig, {
            "scope": "agent_propagation",
            "scope_instance_id": maneuvering_target.id,
            "start_time": time,
            "end_time": time,
            "event_type": "impulse",
            "thrust_vector": [0.0, 0.0, 0.125],
            "thrust_frame": "ntw",
            "planned": False,
        })
        minimal_config.events.append(test_event)

        builder = ScenarioBuilder(minimal_config)
        app = Scenario(
            builder.config,
            builder.clock,
            builder.target_agents,
            builder.estimate_agents,
            builder.sensor_agents,
            builder.tasking_engines,
            logger=builder.logger,
        )
        target_time = datetimeToJulianDate(
            minimal_config.time.start_timestamp + timedelta(minutes=5),
        )
        app.propagateTo(target_time)

        looking_for = "1 events of type NTW Impulse performed."
        found = False
        for log_message in caplog.get_records("call"):
            if log_message.message == looking_for:
                found = True
                break
        assert found, "logs indicate that no impulse took place"

    @pytest.mark.skip(reason="Fails randomly in CI jobs, cannot reproduce")
    @pytest.mark.parametrize("planned", [True, False])
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testDetectScheduledImpulse(
        self,
        datafiles: str,
        caplog: pytest.LogCaptureFixture,
        planned: bool,
        database: ResonaateDatabase,
    ):
        """Validate that a ScheduledImpulse is handled correctly."""
        minimal_config = _getManeuverDetectionConfig(datafiles)

        tasking_engine = minimal_config.engines[0]
        maneuvering_target = tasking_engine.targets[0]
        time = minimal_config.time.start_timestamp + timedelta(minutes=2)

        test_event = constructFromUnion(EventConfig, {
            "scope": "agent_propagation",
            "scope_instance_id": maneuvering_target.id,
            "start_time": time,
            "end_time": time,
            "event_type": "impulse",
            "thrust_vector": [0.0, 0.0, 0.125],
            "thrust_frame": "ntw",
            "planned": planned,
        })
        minimal_config.events.append(test_event)

        builder = ScenarioBuilder(minimal_config)
        app = Scenario(
            builder.config,
            builder.clock,
            builder.target_agents,
            builder.estimate_agents,
            builder.sensor_agents,
            builder.tasking_engines,
            logger=builder.logger,
        )
        target_time = datetimeToJulianDate(
            minimal_config.time.start_timestamp + timedelta(minutes=5),
        )
        app.propagateTo(target_time)

        looking_for = f"maneuver detections of targets {{{maneuvering_target.id}}}"
        found = False
        for log_message in caplog.get_records("call"):
            if looking_for in log_message.message:
                found = True
                break
        if planned:
            assert not found, "logs indicate that a planned maneuver was incorrectly flagged"
        else:
            assert found, "logs indicate that an unplanned maneuver was not detected"

    @pytest.mark.parametrize("planned", [True, False])
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testDetectScheduledFiniteBurn(
        self,
        datafiles: str,
        caplog: pytest.LogCaptureFixture,
        planned: bool,
        database: ResonaateDatabase,
    ):
        """Validate that a ScheduledImpulse is handled correctly."""
        minimal_config = _getManeuverDetectionConfig(datafiles)

        tasking_engine = minimal_config.engines[0]
        maneuvering_target = tasking_engine.targets[0]
        time_1 = minimal_config.time.start_timestamp + timedelta(minutes=2)
        time_2 = minimal_config.time.start_timestamp + timedelta(minutes=4)

        test_event = constructFromUnion(EventConfig, {
            "scope": "agent_propagation",
            "scope_instance_id": maneuvering_target.id,
            "start_time": time_1,
            "end_time": time_2,
            "event_type": "finite_burn",
            "acc_vector": [0.0, 0.0, 0.002],
            "thrust_frame": "ntw",
            "planned": planned,
        })
        minimal_config.events.append(test_event)

        builder = ScenarioBuilder(minimal_config)
        app = Scenario(
            builder.config,
            builder.clock,
            builder.target_agents,
            builder.estimate_agents,
            builder.sensor_agents,
            builder.tasking_engines,
            logger=builder.logger,
        )
        target_time = datetimeToJulianDate(
            minimal_config.time.start_timestamp + timedelta(minutes=5),
        )
        app.propagateTo(target_time)

        looking_for = f"maneuver detections of targets {{{maneuvering_target.id}}}"
        found = False
        for log_message in caplog.get_records("call"):
            if looking_for in log_message.message:
                found = True
                break
        if planned:
            assert not found, "logs indicate that a planned maneuver was incorrectly flagged"
        else:
            assert found, "logs indicate that an unplanned maneuver was not detected"

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testExecuteTargetTaskPriority(
        self,
        datafiles: str,
        caplog: pytest.LogCaptureFixture,
        database: ResonaateDatabase,
    ):
        """Validate that a TargetTaskPriority is handled correctly."""
        minimal_config = _getMinimalConfig(datafiles)

        tasking_engine = minimal_config.engines[0]
        priority_target = tasking_engine.targets[0]
        time_1 = minimal_config.time.start_timestamp + timedelta(minutes=2)
        time_2 = minimal_config.time.start_timestamp + timedelta(minutes=4)

        test_event = constructFromUnion(EventConfig, {
            "scope": "task_reward_generation",
            "scope_instance_id": tasking_engine.unique_id,
            "start_time": time_1,
            "end_time": time_2,
            "event_type": "task_priority",
            "target_id": priority_target.id,
            "target_name": priority_target.name,
            "priority": 2.0,
            "is_dynamic": False,
        })
        minimal_config.events.append(test_event)

        builder = ScenarioBuilder(minimal_config)
        app = Scenario(
            builder.config,
            builder.clock,
            builder.target_agents,
            builder.estimate_agents,
            builder.sensor_agents,
            builder.tasking_engines,
            logger=builder.logger,
        )
        target_time = datetimeToJulianDate(
            minimal_config.time.start_timestamp + timedelta(minutes=5),
        )
        app.propagateTo(target_time)

        looking_for = f"Handled 1 'task_reward_generation' events of types { {'task_priority'} }"
        expected_count = 3
        for log_message in caplog.get_records("call"):
            if log_message.message == looking_for:
                expected_count -= 1
        assert (
            not expected_count
        ), "logs indicate that tasking priority took place less than 3 times"

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testExecuteTargetAddition(
        self,
        datafiles: str,
        caplog: pytest.LogCaptureFixture,
        database: ResonaateDatabase,
    ):
        """Validate that a TargetAddition is handled correctly."""
        minimal_config = _getMinimalConfig(datafiles)

        tasking_engine = minimal_config.engines[0]
        addition_id = 11116

        target_agent = {
            "id": addition_id,
            "name": "test_target_addition",
            "state": {
                "type": "eci",
                "position": [
                    34532.51759487585,
                    -23974.32804541272,
                    -3273.2937902514736,
                ],
                "velocity": [
                    1.7635318397028281,
                    2.5020107992826763,
                    0.28890951790512437,
                ],
            },
            "platform": {"type": "spacecraft"},
        }

        time = minimal_config.time.start_timestamp + timedelta(minutes=2)

        test_event = constructFromUnion(EventConfig, {
            "scope": "scenario_step",
            "scope_instance_id": 0,
            "start_time": time,
            "end_time": time,
            "event_type": "target_addition",
            "target_agent": target_agent,
            "tasking_engine_id": tasking_engine.unique_id,
        })
        minimal_config.events.append(test_event)

        builder = ScenarioBuilder(minimal_config)
        app = Scenario(
            builder.config,
            builder.clock,
            builder.target_agents,
            builder.estimate_agents,
            builder.sensor_agents,
            builder.tasking_engines,
            logger=builder.logger,
        )
        initial_target_count = len(app.target_agents)
        initial_engine_target_count = app.tasking_engines[tasking_engine.unique_id].num_targets

        target_time = datetimeToJulianDate(
            minimal_config.time.start_timestamp + timedelta(minutes=5),
        )
        app.propagateTo(target_time)

        looking_for = f"Handled 1 'scenario_step' events of types { {'target_addition'} }"
        found = False
        for log_message in caplog.get_records("call"):
            if log_message.message == looking_for:
                found = True
                break
        assert found, "logs indicate that a target wasn't added"

        assert len(app.target_agents) == initial_target_count + 1
        assert len(app.estimate_agents) == initial_target_count + 1
        assert (
            app.tasking_engines[tasking_engine.unique_id].num_targets
            == initial_engine_target_count + 1
        )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testExecuteSensorAddition(
        self,
        datafiles: str,
        caplog: pytest.LogCaptureFixture,
        database: ResonaateDatabase,
    ):
        """Validate that a SensorAddition is handled correctly."""
        minimal_config = _getMinimalConfig(datafiles)

        tasking_engine = minimal_config.engines[0]
        addition_id = 60002

        sensor_agent = {
            "name": "Geo Space Sensor 1",
            "id": addition_id,
            "state": {
                "type": "eci",
                "position": [
                    42499.60206485572,
                    184.76309877864716,
                    4.838191959393135,
                ],
                "velocity": [
                    -0.013241150121066223,
                    3.0793657899539326,
                    0.08063602923669937,
                ],
            },
            "platform": {"type": "spacecraft"},
            "sensor": {
                "type": "optical",
                "covariance": [[9.869604401089358e-14, 0.0], [0.0, 9.869604401089358e-14]],
                "slew_rate": 0.03490658503988659,
                "azimuth_range": [0.0, 6.283185132646661],
                "elevation_range": [-1.5707961522619713, 1.5707961522619713],
                "efficiency": 0.99,
                "aperture_diameter": 0.5,
                "field_of_view": {
                    "fov_shape": "conic",
                },
                "background_observations": False,
                "detectable_vismag": 25.0,
                "minimum_range": 0.0,
                "maximum_range": 99000,
            },
        }
        time = minimal_config.time.start_timestamp + timedelta(minutes=2)

        test_event = constructFromUnion(EventConfig, {
            "scope": "scenario_step",
            "scope_instance_id": 0,
            "start_time": time,
            "end_time": time,
            "event_type": "sensor_addition",
            "sensor_agent": sensor_agent,
            "tasking_engine_id": tasking_engine.unique_id,
        })

        minimal_config.events.append(test_event)

        builder = ScenarioBuilder(minimal_config)
        app = Scenario(
            builder.config,
            builder.clock,
            builder.target_agents,
            builder.estimate_agents,
            builder.sensor_agents,
            builder.tasking_engines,
            logger=builder.logger,
        )
        initial_sensor_count = len(app.sensor_agents)
        initial_engine_sensor_count = app.tasking_engines[tasking_engine.unique_id].num_sensors

        target_time = datetimeToJulianDate(
            minimal_config.time.start_timestamp + timedelta(minutes=5),
        )
        app.propagateTo(target_time)

        looking_for = f"Handled 1 'scenario_step' events of types { {'sensor_addition'} }"
        found = False
        for log_message in caplog.get_records("call"):
            if log_message.message == looking_for:
                found = True
                break
        assert found, "logs indicate that a sensor wasn't added"

        assert len(app.sensor_agents) == initial_sensor_count + 1
        assert (
            app.tasking_engines[tasking_engine.unique_id].num_sensors
            == initial_engine_sensor_count + 1
        )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testExecuteAgentRemovalTarget(
        self,
        datafiles: str,
        caplog: pytest.LogCaptureFixture,
        database: ResonaateDatabase,
    ):
        """Validate that a AgentRemoval of a target is handled correctly."""
        minimal_config = _getMainConfig(datafiles)

        tasking_engine = minimal_config.engines[0]
        removed_target = tasking_engine.targets[0]
        time = minimal_config.time.start_timestamp + timedelta(minutes=2)

        test_event = constructFromUnion(EventConfig, {
            "scope": "scenario_step",
            "scope_instance_id": 0,
            "start_time": time,
            "end_time": time,
            "event_type": "agent_removal",
            "tasking_engine_id": tasking_engine.unique_id,
            "agent_id": removed_target.id,
            "agent_type": "target",
        })
        minimal_config.events.append(test_event)

        builder = ScenarioBuilder(minimal_config)
        app = Scenario(
            builder.config,
            builder.clock,
            builder.target_agents,
            builder.estimate_agents,
            builder.sensor_agents,
            builder.tasking_engines,
            logger=builder.logger,
        )
        initial_target_count = len(app.target_agents)
        initial_engine_target_count = app.tasking_engines[tasking_engine.unique_id].num_targets

        target_time = datetimeToJulianDate(
            minimal_config.time.start_timestamp + timedelta(minutes=5),
        )
        app.propagateTo(target_time)

        looking_for = f"Handled 1 'scenario_step' events of types { {'agent_removal'} }"
        found = False
        for log_message in caplog.get_records("call"):
            if log_message.message == looking_for:
                found = True
                break
        assert found, "logs indicate that a target wasn't removed"

        assert len(app.target_agents) == initial_target_count - 1
        assert len(app.estimate_agents) == initial_target_count - 1
        assert (
            app.tasking_engines[tasking_engine.unique_id].num_targets
            == initial_engine_target_count - 1
        )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testExecuteAgentRemovalSensor(
        self,
        datafiles: str,
        caplog: pytest.LogCaptureFixture,
        database: ResonaateDatabase,
    ):
        """Validate that a AgentRemoval of a target is handled correctly."""
        minimal_config = _getMinimalConfig(datafiles)

        tasking_engine = minimal_config.engines[0]
        removed_sensor = tasking_engine.sensors[0]
        time = minimal_config.time.start_timestamp + timedelta(minutes=2)

        test_event = constructFromUnion(EventConfig, {
            "scope": "scenario_step",
            "scope_instance_id": 0,
            "start_time": time,
            "end_time": time,
            "event_type": "agent_removal",
            "tasking_engine_id": tasking_engine.unique_id,
            "agent_id": removed_sensor.id,
            "agent_type": "sensor",
        })
        minimal_config.events.append(test_event)

        builder = ScenarioBuilder(minimal_config)
        app = Scenario(
            builder.config,
            builder.clock,
            builder.target_agents,
            builder.estimate_agents,
            builder.sensor_agents,
            builder.tasking_engines,
            logger=builder.logger,
        )
        initial_sensor_count = len(app.sensor_agents)
        initial_engine_sensor_count = app.tasking_engines[tasking_engine.unique_id].num_sensors

        target_time = datetimeToJulianDate(
            minimal_config.time.start_timestamp + timedelta(minutes=5),
        )
        app.propagateTo(target_time)

        looking_for = f"Handled 1 'scenario_step' events of types { {'agent_removal'} }"
        found = False
        for log_message in caplog.get_records("call"):
            if log_message.message == looking_for:
                found = True
                break
        assert found, "logs indicate that a sensor wasn't removed"

        assert len(app.sensor_agents) == initial_sensor_count - 1
        assert (
            app.tasking_engines[tasking_engine.unique_id].num_sensors
            == initial_engine_sensor_count - 1
        )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testMultiEvent(
        self,
        datafiles: str,
        caplog: pytest.LogCaptureFixture,
        database: ResonaateDatabase,
    ):
        """Validate that multiple consecutive events are handled correctly."""
        minimal_config = _getMinimalConfig(datafiles)

        tasking_engine = minimal_config.engines[0]
        addition_id = 11116

        target_agent = {
            "id": addition_id,
            "name": "Target6",
            "state": {
                "type": "eci",
                "position": [
                    34532.51759487585,
                    -23974.32804541272,
                    -3273.2937902514736,
                ],
                "velocity": [
                    1.7635318397028281,
                    2.5020107992826763,
                    0.28890951790512437,
                ],
            },
            "platform": {"type": "spacecraft"},
        }

        time_1 = minimal_config.time.start_timestamp + timedelta(minutes=2)
        time_2 = minimal_config.time.start_timestamp + timedelta(minutes=2.5)
        time_3 = minimal_config.time.start_timestamp + timedelta(minutes=4)

        test_event_1 = constructFromUnion(EventConfig, {
            "scope": "scenario_step",
            "scope_instance_id": 0,
            "start_time": time_1,
            "end_time": time_1,
            "event_type": "target_addition",
            "target_agent": target_agent,
            "tasking_engine_id": tasking_engine.unique_id,
        })
        test_event_2 = constructFromUnion(EventConfig, {
            "scope": "agent_propagation",
            "scope_instance_id": addition_id,
            "start_time": time_2,
            "end_time": time_2,
            "event_type": "impulse",
            "thrust_vector": [0.0, 0.0, 0.125],
            "thrust_frame": "ntw",
        })
        test_event_3 = constructFromUnion(EventConfig, {
            "scope": "scenario_step",
            "scope_instance_id": 0,
            "start_time": time_3,
            "end_time": time_3,
            "event_type": "agent_removal",
            "tasking_engine_id": tasking_engine.unique_id,
            "agent_id": addition_id,
            "agent_type": "target",
        })
        minimal_config.events = [test_event_1, test_event_2, test_event_3]

        builder = ScenarioBuilder(minimal_config)
        app = Scenario(
            builder.config,
            builder.clock,
            builder.target_agents,
            builder.estimate_agents,
            builder.sensor_agents,
            builder.tasking_engines,
            logger=builder.logger,
        )
        target_time = datetimeToJulianDate(
            minimal_config.time.start_timestamp + timedelta(minutes=5),
        )
        app.propagateTo(target_time)

        message_contents = {
            "addition": f"Handled 1 'scenario_step' events of types { {'target_addition'} }",
            "maneuver": "1 events of type NTW Impulse performed.",
            "removal": f"Handled 1 'scenario_step' events of types { {'agent_removal'} }",
        }
        message_found = {"addition": False, "maneuver": False, "removal": False}
        for log_message in caplog.get_records("call"):
            for msg_type, msg_content in message_contents.items():
                if log_message.message == msg_content:
                    message_found[msg_type] = True

        for msg_type, msg_found in message_found.items():
            assert msg_found, f"logs indicate that {msg_type} didn't take place"
