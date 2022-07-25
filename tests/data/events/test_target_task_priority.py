from __future__ import annotations

# Standard Library Imports
from datetime import datetime
from unittest.mock import create_autospec

# Third Party Imports
import pytest
from numpy import zeros

# RESONAATE Imports
from resonaate.data.data_interface import AgentModel
from resonaate.data.events import TargetTaskPriority
from resonaate.physics.time.stardate import JulianDate
from resonaate.scenario.config.event_configs import TargetTaskPriorityConfig
from resonaate.tasking.engine.engine_base import TaskingEngine


@pytest.fixture(name="event_config_dict")
def getTargetTaskPriority():
    """``dict``: config dictionary for changing a tasking priority."""
    return {
        "scope": TargetTaskPriority.INTENDED_SCOPE.value,
        "scope_instance_id": 123,
        "start_time": datetime(2021, 8, 3, 12),
        "end_time": datetime(2021, 8, 3, 12),
        "event_type": TargetTaskPriority.EVENT_TYPE,
        "target_id": 12345,
        "target_name": "important sat",
        "priority": 2.0,
        "is_dynamic": False,
    }


class TestTargetTaskPriorityConfig:
    """Test class for :class:`.TestTargetTaskPriorityConfig` class."""

    def testInitGoodArgs(self, event_config_dict):
        """Test :class:`.TestTargetTaskPriorityConfig` constructor with good arguments."""
        assert TargetTaskPriorityConfig(**event_config_dict)

    def testDataDependency(self, event_config_dict):
        """Test that :class:`.ScheduledImpulseEventConfig`'s data dependencies are correct."""
        priority_config = TargetTaskPriorityConfig(**event_config_dict)
        priority_dependencies = priority_config.getDataDependencies()
        assert len(priority_dependencies) == 1

        agent_dependency = priority_dependencies[0]
        assert agent_dependency.data_type == AgentModel
        assert agent_dependency.attributes == {
            "unique_id": priority_config.target_id,
            "name": priority_config.target_name,
        }


@pytest.fixture(name="mocked_engine")
def getMockedEngine():
    """Get mocked :class:`.TaskingEngine` object."""
    mocked_engine = create_autospec(TaskingEngine, instance=True)
    mocked_engine.reward_matrix = zeros((10, 10), dtype=float)
    return mocked_engine


class TestTargetTaskPriority:
    """Test class for :class:`.TargetTaskPriority` class."""

    def testFromConfig(self, event_config_dict):
        """Test :meth:`.TargetTaskPriority.fromConfig()`."""
        priority_config = TargetTaskPriorityConfig(**event_config_dict)
        assert TargetTaskPriority.fromConfig(priority_config)

    def testHandleEvent(self, mocked_engine):
        """Test :meth:`.TargetTaskPriority.handleEvent()`."""
        priority_event = TargetTaskPriority(
            scope=TargetTaskPriority.INTENDED_SCOPE.value,
            scope_instance_id=123,
            start_time_jd=float(JulianDate.getJulianDate(2021, 8, 3, 12, 0, 0)),
            event_type=TargetTaskPriority.EVENT_TYPE,
            agent_id=12345,
            priority=2.0,
            is_dynamic=False,
        )
        mocked_engine.target_indices = {priority_event.agent_id: 5}
        priority_event.handleEvent(mocked_engine)
