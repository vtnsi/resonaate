# pylint: disable=no-self-use, unused-argument
# Standard Library Imports
from datetime import datetime
from unittest.mock import create_autospec
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.scenario.config.event_configs import SensorTimeBiasEventConfigObject
    from resonaate.scenario.config.base import ConfigError
    from resonaate.physics.time.stardate import datetimeToJulianDate
    from resonaate.data.events import SensorTimeBiasEvent
    from resonaate.agents.sensing_agent import SensingAgent
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ...conftest import BaseTestCase


class TestSensorTimeBiasEventConfig(BaseTestCase):
    """Test class for :class:`.ScheduledImpulseEventConfig` class."""

    def testInitGoodArgs(self):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with good arguments."""
        assert SensorTimeBiasEventConfigObject({
            "scope": SensorTimeBiasEventConfigObject.EVENT_CLASS.INTENDED_SCOPE.value,
            "scope_instance_id": 300000,
            "start_time": datetime(2019, 2, 1, 15, 20),
            "end_time": datetime(2019, 2, 1, 15, 20),
            "event_type": SensorTimeBiasEventConfigObject.EVENT_CLASS.EVENT_TYPE,
            "applied_bias": 0.001
        })

    def testInitBadScope(self):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with bad ``scope`` argument."""
        with pytest.raises(AttributeError):
            SensorTimeBiasEventConfigObject({
                "scope": SensorTimeBiasEventConfigObject.SCENARIO_STEP.value,  # pylint: disable=no-member
                "scope_instance_id": 300000,
                "start_time": datetime(2019, 2, 1, 15, 20),
                "end_time": datetime(2019, 2, 1, 15, 20),
                "event_type": SensorTimeBiasEventConfigObject.EVENT_CLASS.EVENT_TYPE,
                "applied_bias": 0.001
            })

    def testInitBadbiasType(self):
        """Test :class:`.SensorTimeBiasEventConfig` constructor with bad ``applied_bias`` type."""
        with pytest.raises(ConfigError):
            SensorTimeBiasEventConfigObject({
                "scope": SensorTimeBiasEventConfigObject.EVENT_CLASS.INTENDED_SCOPE.value,
                "scope_instance_id": 300000,
                "start_time": datetime(2019, 2, 1, 15, 20),
                "end_time": datetime(2019, 2, 1, 15, 20),
                "event_type": SensorTimeBiasEventConfigObject.EVENT_CLASS.EVENT_TYPE,
                "applied_bias": True
            })


@pytest.fixture(name="mocked_sensor")
def getMockedAgent():
    """Get mocked :class:`.SensingAgent` object."""
    mocked_sensor = create_autospec(SensingAgent)
    mocked_sensor.julian_date_start = datetimeToJulianDate(datetime(2019, 2, 1, 15, 20))
    return mocked_sensor


class TestSensorTimeBiasEvent(BaseTestCase):
    """Test class for :class:`.SensorTimeBiasEvent` class."""

    def testFromConfig(self):
        """Test :meth:`.SensorTimeBiasEvent.fromConfig()`."""
        bias_config = SensorTimeBiasEventConfigObject({
            "scope": SensorTimeBiasEventConfigObject.EVENT_CLASS.INTENDED_SCOPE.value,
            "scope_instance_id": 300000,
            "start_time": datetime(2019, 2, 1, 15, 20),
            "end_time": datetime(2019, 2, 1, 15, 20),
            "event_type": SensorTimeBiasEventConfigObject.EVENT_CLASS.EVENT_TYPE,
            "applied_bias": 0.001
        })
        assert SensorTimeBiasEvent.fromConfig(bias_config)

    def testHandleEvent(self, mocked_sensor):
        """Test :meth:`.SensorTimeBiasEvent.handleEvent()` with an NTW impulse."""
        bias_event = SensorTimeBiasEvent(
            scope=SensorTimeBiasEvent.INTENDED_SCOPE.value,
            scope_instance_id=300000,
            start_time_jd=datetime(2019, 2, 1, 15, 20),
            end_time_jd=datetime(2019, 2, 1, 15, 20),
            event_type=SensorTimeBiasEvent.EVENT_TYPE,
            applied_bias=0.001
        )
        bias_event.handleEvent(mocked_sensor)
