from __future__ import annotations

# Standard Library Imports
from datetime import datetime

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.data.data_interface import AgentModel
from resonaate.data.events import AgentRemovalEvent
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config.event_configs import AgentRemovalEventConfig


@pytest.fixture(name="event_config_dict")
def getAgentRemoval():
    """``dict``: config dictionary for agent removal."""
    return {
        "scope": AgentRemovalEvent.INTENDED_SCOPE.value,
        "scope_instance_id": 123,
        "start_time": datetime(2021, 8, 3, 12),
        "end_time": datetime(2021, 8, 3, 12),
        "event_type": AgentRemovalEvent.EVENT_TYPE,
        "tasking_engine_id": 123,
        "agent_id": 12345,
        "agent_type": "target",
    }


class TestAgentRemovalEventConfig:
    """Test class for :class:`.AgentRemovalEventConfig` class."""

    def testInitGoodArgs(self, event_config_dict):
        """Test :class:`.AgentRemovalEventConfig` constructor with good arguments."""
        assert AgentRemovalEventConfig(**event_config_dict)

    def testDataDependency(self, event_config_dict):
        """Test that :class:`.AgentRemovalEventConfig`'s data dependencies are correct."""
        removal_config = AgentRemovalEventConfig(**event_config_dict)
        removal_dependencies = removal_config.getDataDependencies()
        assert len(removal_dependencies) == 1

        agent_dependency = removal_dependencies[0]
        assert agent_dependency.data_type == AgentModel
        assert agent_dependency.attributes is None


class TestAgentRemovalEvent:
    """Test class for :class:`.AgentRemovalEvent` class."""

    def testFromConfig(self, event_config_dict):
        """Test :meth:`.AgentRemovalEvent.fromConfig()`."""
        removal_config = AgentRemovalEventConfig(**event_config_dict)
        assert AgentRemovalEvent.fromConfig(removal_config)

    def testHandleEventTarget(self, mocked_scenario):
        """Test :meth:`.AgentRemovalEvent.handleEvent()`."""
        impulse_event = AgentRemovalEvent(
            scope=AgentRemovalEvent.INTENDED_SCOPE.value,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=AgentRemovalEvent.EVENT_TYPE,
            tasking_engine_id=123,
            agent_id=12345,
            agent_type="target",
        )
        impulse_event.handleEvent(mocked_scenario)

    def testHandleEventSensor(self, mocked_scenario):
        """Test :meth:`.AgentRemovalEvent.handleEvent()`."""
        impulse_event = AgentRemovalEvent(
            scope=AgentRemovalEvent.INTENDED_SCOPE.value,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=AgentRemovalEvent.EVENT_TYPE,
            tasking_engine_id=123,
            agent_id=12345,
            agent_type="sensor",
        )
        impulse_event.handleEvent(mocked_scenario)

    def testHandleEventBadAgentType(self, mocked_scenario):
        """Test :meth:`.AgentRemovalEvent.handleEvent()`."""
        bad_agent_type = "bad agent type"
        impulse_event = AgentRemovalEvent(
            scope=AgentRemovalEvent.INTENDED_SCOPE.value,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=AgentRemovalEvent.EVENT_TYPE,
            tasking_engine_id=123,
            agent_id=12345,
            agent_type=bad_agent_type,
        )
        expected_err = f"{bad_agent_type!r} is not a valid agent type."
        with pytest.raises(ValueError, match=expected_err):
            impulse_event.handleEvent(mocked_scenario)
