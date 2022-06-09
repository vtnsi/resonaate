# pylint: disable=unused-argument
# Standard Library Imports
from datetime import datetime
from unittest.mock import create_autospec

# Third Party Imports
import pytest
from numpy import zeros

# RESONAATE Imports
from resonaate.physics.time.stardate import JulianDate

try:
    # RESONAATE Imports
    from resonaate.data.data_interface import Agent
    from resonaate.data.events import TargetTaskPriority
    from resonaate.scenario.config.event_configs import TargetTaskPriorityConfigObject
    from resonaate.tasking.engine.engine_base import TaskingEngine
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ...conftest import BaseTestCase


class TestTargetTaskPriorityConfig(BaseTestCase):
    """Test class for :class:`.TargetTaskPriorityConfigObject` class."""

    def testInitGoodArgs(self):
        """Test :class:`.TargetTaskPriorityConfigObject` constructor with good arguments."""
        assert TargetTaskPriorityConfigObject(
            {
                "scope": TargetTaskPriority.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": TargetTaskPriority.EVENT_TYPE,
                "target_id": 12345,
                "target_name": "important sat",
                "priority": 2.0,
                "is_dynamic": False,
            }
        )

    def testDataDependency(self):
        """Test that :class:`.ScheduledImpulseEventConfig`'s data dependencies are correct."""
        priority_config = TargetTaskPriorityConfigObject(
            {
                "scope": TargetTaskPriority.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": TargetTaskPriority.EVENT_TYPE,
                "target_id": 12345,
                "target_name": "important sat",
                "priority": 2.0,
                "is_dynamic": False,
            }
        )
        priority_dependencies = priority_config.getDataDependencies()
        assert len(priority_dependencies) == 1

        agent_dependency = priority_dependencies[0]
        assert agent_dependency.data_type == Agent
        assert agent_dependency.attributes == {
            "unique_id": priority_config.target_id,
            "name": priority_config.target_name,
        }


@pytest.fixture(name="mocked_engine")
def getMockedEngine():
    """Get mocked :class:`.TaskingEngine` object."""
    mocked_engine = create_autospec(TaskingEngine)
    mocked_engine.reward_matrix = zeros((10, 10), dtype=float)
    return mocked_engine


class TestTargetTaskPriority(BaseTestCase):
    """Test class for :class:`.TargetTaskPriority` class."""

    def testFromConfig(self):
        """Test :meth:`.TargetTaskPriority.fromConfig()`."""
        priority_config = TargetTaskPriorityConfigObject(
            {
                "scope": TargetTaskPriority.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": TargetTaskPriority.EVENT_TYPE,
                "target_id": 12345,
                "target_name": "important sat",
                "priority": 2.0,
                "is_dynamic": False,
            }
        )
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
