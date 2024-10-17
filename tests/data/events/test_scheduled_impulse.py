from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from datetime import datetime
from unittest.mock import create_autospec

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.agents.target_agent import TargetAgent
from resonaate.data.events import EventScope, ScheduledImpulseEvent, TargetAdditionEvent
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config.event_configs import ScheduledImpulseEventConfig


@pytest.fixture(name="event_config_dict")
def getScheduledImpulse():
    """``dict``: config dictionary for scheduled impulse event."""
    return {
        "scope": ScheduledImpulseEvent.INTENDED_SCOPE.value,
        "scope_instance_id": 123,
        "start_time": datetime(2021, 8, 3, 12, 5),
        "end_time": datetime(2021, 8, 3, 12, 5),
        "event_type": ScheduledImpulseEvent.EVENT_TYPE,
        "thrust_vector": [0.0, 0.0, 0.00123],
        "thrust_frame": "ntw",
        "planned": False,
    }


class TestScheduledImpulseEventConfig:
    """Test class for :class:`.ScheduledImpulseEventConfig` class."""

    def testInitGoodArgs(self, event_config_dict):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with good arguments."""
        assert ScheduledImpulseEventConfig(**event_config_dict)

    def testInitOtherGoodArgs(self, event_config_dict):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with other good arguments."""
        impulse_config = deepcopy(event_config_dict)
        impulse_config["thrust_frame"] = "eci"
        impulse_config["planned"] = True
        assert ScheduledImpulseEventConfig(**impulse_config)

    def testInitBadScope(self, event_config_dict):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with bad ``scope`` argument."""
        expected_err = f"{ScheduledImpulseEvent} must have scope set to {ScheduledImpulseEvent.INTENDED_SCOPE}"
        impulse_config = deepcopy(event_config_dict)
        impulse_config["scope"] = EventScope.SCENARIO_STEP.value
        with pytest.raises(ValidationError, match=expected_err):
            ScheduledImpulseEventConfig(**impulse_config)

    def testInitBadEventType(self, event_config_dict):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with bad ``event_type`` argument."""
        expected_err = f"Input should be '{ScheduledImpulseEvent.EVENT_TYPE}'"
        impulse_config = deepcopy(event_config_dict)
        impulse_config["event_type"] = TargetAdditionEvent.EVENT_TYPE
        with pytest.raises(ValidationError, match=expected_err):
            ScheduledImpulseEventConfig(**impulse_config)

    def testInitBadVectorSize(self, event_config_dict):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with bad ``thrust_vector`` size."""
        bad_vector = [0.0, 0.0, 0.00123, 0.0]
        impulse_config = deepcopy(event_config_dict)
        impulse_config["thrust_vector"] = bad_vector
        with pytest.raises(ValidationError):
            ScheduledImpulseEventConfig(**impulse_config)

    def testDataDependency(self, event_config_dict):
        """Test that :class:`.ScheduledImpulseEventConfig`'s data dependencies are correct."""
        impulse_config = ScheduledImpulseEventConfig(**event_config_dict)
        impulse_dependencies = impulse_config.getDataDependencies()
        assert len(impulse_dependencies) == 0


@pytest.fixture(name="mocked_target")
def getMockedAgent():
    """Get mocked :class:`.TargetAgent` object."""
    mocked_target = create_autospec(TargetAgent, instance=True)
    mocked_target.julian_date_start = datetimeToJulianDate(datetime(2021, 8, 3, 12))
    return mocked_target


class TestScheduledImpulseEvent:
    """Test class for :class:`.ScheduledImpulseEvent` class."""

    def testFromConfig(self, event_config_dict):
        """Test :meth:`.ScheduledImpulseEvent.fromConfig()`."""
        impulse_config = ScheduledImpulseEventConfig(**event_config_dict)
        assert ScheduledImpulseEvent.fromConfig(impulse_config)

    def testHandleEventNTW(self, mocked_target):
        """Test :meth:`.ScheduledImpulseEvent.handleEvent()` with an NTW impulse."""
        impulse_event = ScheduledImpulseEvent(
            scope=ScheduledImpulseEvent.INTENDED_SCOPE.value,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=ScheduledImpulseEvent.EVENT_TYPE,
            thrust_vec_0=0.0,
            thrust_vec_1=0.0,
            thrust_vec_2=0.00123,
            thrust_frame="ntw",
            planned=True,
        )
        impulse_event.handleEvent(mocked_target)

    def testHandleEventECI(self, mocked_target):
        """Test :meth:`.ScheduledImpulseEvent.handleEvent()` with an ECI impulse."""
        impulse_event = ScheduledImpulseEvent(
            scope=ScheduledImpulseEvent.INTENDED_SCOPE.value,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=ScheduledImpulseEvent.EVENT_TYPE,
            thrust_vec_0=0.0,
            thrust_vec_1=0.0,
            thrust_vec_2=0.00123,
            thrust_frame="eci",
            planned=True,
        )
        impulse_event.handleEvent(mocked_target)

    def testHandleEventBadFrame(self, mocked_target):
        """Test :meth:`.ScheduledImpulseEvent.handleEvent()` with a bad thrust frame."""
        impulse_event = ScheduledImpulseEvent(
            scope=ScheduledImpulseEvent.INTENDED_SCOPE.value,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=ScheduledImpulseEvent.EVENT_TYPE,
            thrust_vec_0=0.0,
            thrust_vec_1=0.0,
            thrust_vec_2=0.00123,
            thrust_frame="bad",
            planned=True,
        )
        expected_err = f"'{impulse_event.thrust_frame}' is not a valid ThrustFrame"
        with pytest.raises(ValueError, match=expected_err):
            impulse_event.handleEvent(mocked_target)
