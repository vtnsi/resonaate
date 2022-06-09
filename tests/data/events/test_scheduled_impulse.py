# pylint: disable=no-self-use, unused-argument
# Standard Library Imports
from datetime import datetime
from unittest.mock import create_autospec
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.scenario.config.event_configs import ScheduledImpulseEventConfigObject
    from resonaate.scenario.config.base import ConfigError
    from resonaate.physics.time.stardate import datetimeToJulianDate
    from resonaate.data.data_interface import Epoch
    from resonaate.data.events import EventScope, ScheduledImpulseEvent, TargetAdditionEvent
    from resonaate.agents.target_agent import TargetAgent
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ...conftest import BaseTestCase


class TestScheduledImpulseEventConfig(BaseTestCase):
    """Test class for :class:`.ScheduledImpulseEventConfig` class."""

    def testInitGoodArgs(self):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with good arguments."""
        assert ScheduledImpulseEventConfigObject({
            "scope": ScheduledImpulseEventConfigObject.EVENT_CLASS.INTENDED_SCOPE.value,
            "scope_instance_id": 123,
            "start_time": datetime(2021, 8, 3, 12),
            "event_type": ScheduledImpulseEventConfigObject.EVENT_CLASS.EVENT_TYPE,
            "thrust_vector": [0.0, 0.0, 0.00123],
            "thrust_frame": "ntw"
        })

    def testInitOtherGoodArgs(self):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with other good arguments."""
        assert ScheduledImpulseEventConfigObject({
            "scope": ScheduledImpulseEventConfigObject.EVENT_CLASS.INTENDED_SCOPE.value,
            "scope_instance_id": 123,
            "start_time": datetime(2021, 8, 3, 12),
            "end_time": datetime(2021, 8, 3, 12),
            "event_type": ScheduledImpulseEventConfigObject.EVENT_CLASS.EVENT_TYPE,
            "thrust_vector": [0.0, 0.0, 0.00123],
            "thrust_frame": "eci"
        })

    def testInitBadScope(self):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with bad ``scope`` argument."""
        expected_err = f"{ScheduledImpulseEvent} must have scope set to {ScheduledImpulseEvent.INTENDED_SCOPE}"
        with pytest.raises(ConfigError, match=expected_err):
            ScheduledImpulseEventConfigObject({
                "scope": EventScope.SCENARIO_STEP.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "end_time": datetime(2021, 8, 3, 12),
                "event_type": ScheduledImpulseEvent.EVENT_TYPE,
                "thrust_vector": [0.0, 0.0, 0.00123],
                "thrust_frame": "eci"
            })

    def testInitBadEventType(self):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with bad ``event_type`` argument."""
        expected_err = f"{ScheduledImpulseEvent} must have event_type set to {ScheduledImpulseEvent.EVENT_TYPE}"
        with pytest.raises(ConfigError, match=expected_err):
            ScheduledImpulseEventConfigObject({
                "scope": ScheduledImpulseEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "end_time": datetime(2021, 8, 3, 12),
                "event_type": TargetAdditionEvent.EVENT_TYPE,
                "thrust_vector": [0.0, 0.0, 0.00123],
                "thrust_frame": "eci"
            })

    def testInitBadVectorSize(self):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with bad ``thrust_vector`` size."""
        bad_vector = [0.0, 0.0, 0.00123, 0.0]
        expected_err = f"Delta vector defining an impulsive maneuver should be 3 dimensional, not {len(bad_vector)}"
        with pytest.raises(ConfigError, match=expected_err):
            ScheduledImpulseEventConfigObject({
                "scope": ScheduledImpulseEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": ScheduledImpulseEvent.EVENT_TYPE,
                "thrust_vector": bad_vector,
                "thrust_frame": "ntw"
            })

    def testDataDependency(self):
        """Test that :class:`.ScheduledImpulseEventConfig`'s data dependencies are correct."""
        impulse_config = ScheduledImpulseEventConfigObject({
            "scope": ScheduledImpulseEventConfigObject.EVENT_CLASS.INTENDED_SCOPE.value,
            "scope_instance_id": 123,
            "start_time": datetime(2021, 8, 3, 12),
            "event_type": ScheduledImpulseEventConfigObject.EVENT_CLASS.EVENT_TYPE,
            "thrust_vector": [0.0, 0.0, 0.00123],
            "thrust_frame": "ntw"
        })
        impulse_dependencies = impulse_config.getDataDependencies()
        assert len(impulse_dependencies) == 1

        epoch_dependency = impulse_dependencies[0]
        assert epoch_dependency.data_type == Epoch
        assert epoch_dependency.attributes is None


@pytest.fixture(name="mocked_target")
def getMockedAgent():
    """Get mocked :class:`.TargetAgent` object."""
    mocked_target = create_autospec(TargetAgent)
    mocked_target.julian_date_start = datetimeToJulianDate(datetime(2021, 8, 3, 12))
    return mocked_target


class TestScheduledImpulseEvent(BaseTestCase):
    """Test class for :class:`.ScheduledImpulseEvent` class."""

    def testFromConfig(self):
        """Test :meth:`.ScheduledImpulseEvent.fromConfig()`."""
        impulse_config = ScheduledImpulseEventConfigObject({
            "scope": ScheduledImpulseEvent.INTENDED_SCOPE.value,
            "scope_instance_id": 123,
            "start_time": datetime(2021, 8, 3, 12),
            "event_type": ScheduledImpulseEvent.EVENT_TYPE,
            "thrust_vector": [0.0, 0.0, 0.00123],
            "thrust_frame": "ntw"
        })
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
            thrust_frame="ntw"
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
            thrust_frame="eci"
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
            thrust_frame="bad"
        )
        expected_err = f"{impulse_event.thrust_frame} is not a valid coordinate frame."
        with pytest.raises(ValueError, match=expected_err):
            impulse_event.handleEvent(mocked_target)
