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
from resonaate.data.events import EventScope, ScheduledFiniteBurnEvent
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config.event_configs import ScheduledFiniteBurnConfig


@pytest.fixture(name="event_config_dict")
def getScheduledBurn():
    """``dict``: config dictionary for scheduled burn event."""
    return {
        "scope": ScheduledFiniteBurnEvent.INTENDED_SCOPE.value,
        "scope_instance_id": 28868,
        "start_time": datetime(2019, 2, 1, 15, 20),
        "end_time": datetime(2019, 2, 1, 15, 22),
        "event_type": ScheduledFiniteBurnEvent.EVENT_TYPE,
        "acc_vector": [0.0, 0.0, 0.00123],
        "thrust_frame": "ntw",
        "planned": True,
    }


class TestFiniteBurnEventConfig:
    """Test class for :class:`.ScheduledFiniteBurnEventConfig` class."""

    def testInitGoodArgs(self, event_config_dict):
        """Test :class:`.ScheduledFiniteBurnEventConfig` constructor with good arguments."""
        assert ScheduledFiniteBurnConfig(**event_config_dict)

    def testInitBadScope(self, event_config_dict):
        """Test :class:`.ScheduledFiniteBurnEventConfig` constructor with bad ``scope`` argument."""
        expected_err = f"{ScheduledFiniteBurnEvent} must have scope set to {ScheduledFiniteBurnEvent.INTENDED_SCOPE}"
        burn_config = deepcopy(event_config_dict)
        burn_config["scope"] = EventScope.SCENARIO_STEP.value
        with pytest.raises(ValidationError, match=expected_err):
            ScheduledFiniteBurnConfig(**burn_config)

    def testInitBadThrustType(self, event_config_dict):
        """Test :class:`.ScheduledFiniteBurnEventConfig` constructor with bad ``thrust_frame`` type."""
        burn_config = deepcopy(event_config_dict)
        burn_config["thrust_frame"] = True
        with pytest.raises(ValidationError):
            ScheduledFiniteBurnConfig(**burn_config)


@pytest.fixture(name="mocked_target")
def getMockedAgent():
    """Get mocked :class:`.TargetAgent` object."""
    mocked_target = create_autospec(TargetAgent, instance=True)
    mocked_target.julian_date_start = datetimeToJulianDate(datetime(2019, 2, 1, 0, 0))
    return mocked_target


class TestFiniteBurnEvent:
    """Test class for :class:`.SensorFiniteBurnEvent` class."""

    def testFromConfig(self, event_config_dict):
        """Test :meth:`.ScheduledFiniteBurnEvent.fromConfig()`."""
        burn_config = ScheduledFiniteBurnConfig(**event_config_dict)
        assert ScheduledFiniteBurnEvent.fromConfig(burn_config)

    def testHandleNTWEvent(self, mocked_target):
        """Test :meth:`.ScheduledFiniteBurnEvent.handleEvent()` with an NTW burn."""
        burn_event = ScheduledFiniteBurnEvent(
            scope=ScheduledFiniteBurnEvent.INTENDED_SCOPE.value,
            scope_instance_id=28868,
            start_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 20)),
            end_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 22)),
            event_type=ScheduledFiniteBurnEvent.EVENT_TYPE,
            acc_vec_0=0.0,
            acc_vec_1=0.0,
            acc_vec_2=0.00123,
            thrust_frame="ntw",
            planned=True,
        )
        burn_event.handleEvent(mocked_target)

    def testHandleECISEvent(self, mocked_target):
        """Test :meth:`.ScheduledFiniteBurnEvent.handleEvent()` with an ECI burn."""
        burn_event = ScheduledFiniteBurnEvent(
            scope=ScheduledFiniteBurnEvent.INTENDED_SCOPE.value,
            scope_instance_id=28868,
            start_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 20)),
            end_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 22)),
            event_type=ScheduledFiniteBurnEvent.EVENT_TYPE,
            acc_vec_0=0.0,
            acc_vec_1=0.0,
            acc_vec_2=0.00123,
            thrust_frame="eci",
            planned=True,
        )
        burn_event.handleEvent(mocked_target)

    def testHandleEventBadFrame(self, mocked_target):
        """Test :meth:`.ScheduledFiniteBurnEvent.handleEvent()` with a bad burn frame."""
        burn_event = ScheduledFiniteBurnEvent(
            scope=ScheduledFiniteBurnEvent.INTENDED_SCOPE.value,
            scope_instance_id=28868,
            start_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 20)),
            end_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 22)),
            event_type=ScheduledFiniteBurnEvent.EVENT_TYPE,
            acc_vec_0=0.0,
            acc_vec_1=0.0,
            acc_vec_2=0.00123,
            thrust_frame="bad",
            planned=True,
        )
        expected_err = f"'{burn_event.thrust_frame}' is not a valid ThrustFrame"
        with pytest.raises(ValueError, match=expected_err):
            burn_event.handleEvent(mocked_target)
