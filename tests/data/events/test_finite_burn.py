# pylint: disable=no-self-use, unused-argument
# Standard Library Imports
from datetime import datetime
from unittest.mock import create_autospec
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.scenario.config.event_configs import ScheduledFiniteBurnConfigObject
    from resonaate.scenario.config.base import ConfigError
    from resonaate.physics.time.stardate import datetimeToJulianDate
    from resonaate.data.events import EventScope, ScheduledFiniteBurnEvent
    from resonaate.agents.target_agent import TargetAgent
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ...conftest import BaseTestCase


class TestFiniteBurnEventConfig(BaseTestCase):
    """Test class for :class:`.ScheduledFiniteBurnEventConfig` class."""

    def testInitGoodArgs(self):
        """Test :class:`.ScheduledFiniteBurnEventConfig` constructor with good arguments."""
        assert ScheduledFiniteBurnConfigObject({
            "scope": ScheduledFiniteBurnConfigObject.EVENT_CLASS.INTENDED_SCOPE.value,
            "scope_instance_id": 28868,
            "start_time": datetime(2019, 2, 1, 15, 20),
            "end_time": datetime(2019, 2, 1, 15, 22),
            "event_type": ScheduledFiniteBurnConfigObject.EVENT_CLASS.EVENT_TYPE,
            "acc_vector": [0.0, 0.0, 0.00123],
            "thrust_frame": "ntw"
        })

    def testInitBadScope(self):
        """Test :class:`.ScheduledFiniteBurnEventConfig` constructor with bad ``scope`` argument."""
        expected_err = f"{ScheduledFiniteBurnEvent} must have scope set to {ScheduledFiniteBurnEvent.INTENDED_SCOPE}"
        with pytest.raises(ConfigError, match=expected_err):
            ScheduledFiniteBurnConfigObject({
                "scope": EventScope.SCENARIO_STEP.value,  # pylint: disable=no-member
                "scope_instance_id": 28868,
                "start_time": datetime(2019, 2, 1, 15, 20),
                "end_time": datetime(2019, 2, 1, 15, 22),
                "event_type": ScheduledFiniteBurnEvent.EVENT_TYPE,
                "acc_vector": [0.0, 0.0, 0.00123],
                "thrust_frame": "ntw"
            })

    def testInitBadThrustType(self):
        """Test :class:`.ScheduledFiniteBurnEventConfig` constructor with bad ``applied_bias`` type."""
        with pytest.raises(ConfigError):
            ScheduledFiniteBurnConfigObject({
                "scope": ScheduledFiniteBurnConfigObject.EVENT_CLASS.INTENDED_SCOPE.value,
                "scope_instance_id": 28868,
                "start_time": datetime(2019, 2, 1, 15, 20),
                "end_time": datetime(2019, 2, 1, 15, 22),
                "event_type": ScheduledFiniteBurnConfigObject.EVENT_CLASS.EVENT_TYPE,
                "acc_vector": [0.0, 0.0, 0.00123],
                "thrust_frame": True
            })


@pytest.fixture(name="mocked_target")
def getMockedAgent():
    """Get mocked :class:`.TargetAgent` object."""
    mocked_target = create_autospec(TargetAgent)
    mocked_target.julian_date_start = datetimeToJulianDate(datetime(2019, 2, 1, 0, 0))
    return mocked_target


class TestFiniteBurnEvent(BaseTestCase):
    """Test class for :class:`.SensorFiniteBurnEvent` class."""

    def testFromConfig(self):
        """Test :meth:`.ScheduledFiniteBurnEvent.fromConfig()`."""
        burn_config = ScheduledFiniteBurnConfigObject({
            "scope": ScheduledFiniteBurnEvent.INTENDED_SCOPE.value,
            "scope_instance_id": 28868,
            "start_time": datetime(2019, 2, 1, 15, 20),
            "end_time": datetime(2019, 2, 1, 15, 22),
            "event_type": ScheduledFiniteBurnEvent.EVENT_TYPE,
            "acc_vector": [0.0, 0.0, 0.00123],
            "thrust_frame": "ntw"
        })
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
            thrust_frame="ntw"
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
            thrust_frame="eci"
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
            thrust_frame="bad"
        )
        expected_err = f"{burn_event.thrust_frame} is not a valid coordinate frame."
        with pytest.raises(ValueError, match=expected_err):
            burn_event.handleEvent(mocked_target)
