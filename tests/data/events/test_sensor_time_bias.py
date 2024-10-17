from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from datetime import datetime
from unittest.mock import create_autospec

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.data.events import SensorTimeBiasEvent
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config.event_configs import SensorTimeBiasEventConfig


@pytest.fixture(name="event_config_dict")
def getTimeBias():
    """``dict``: config dictionary for time bias event."""
    return {
        "scope": SensorTimeBiasEventConfig.getEventClass().INTENDED_SCOPE.value,
        "scope_instance_id": 300000,
        "start_time": datetime(2019, 2, 1, 15, 20),
        "end_time": datetime(2019, 2, 1, 20, 20),
        "event_type": SensorTimeBiasEventConfig.getEventClass().EVENT_TYPE,
        "applied_bias": 0.001,
    }


class TestSensorTimeBiasEventConfig:
    """Test class for :class:`.ScheduledImpulseEventConfig` class."""

    def testInitGoodArgs(self, event_config_dict):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with good arguments."""
        assert SensorTimeBiasEventConfig(**event_config_dict)

    def testInitBadScope(self, event_config_dict):
        """Test :class:`.ScheduledImpulseEventConfig` constructor with bad ``scope`` argument."""
        bias_config = deepcopy(event_config_dict)
        bias_config["scope"] = "agent_propagation"
        with pytest.raises(ValidationError):
            SensorTimeBiasEventConfig(**bias_config)

    def testInitBadBiasType(self, event_config_dict):
        """Test :class:`.SensorTimeBiasEventConfig` constructor with bad ``applied_bias`` type."""
        bias_config = deepcopy(event_config_dict)
        bias_config["applied_bias"] = "bad value"
        with pytest.raises(ValidationError):
            SensorTimeBiasEventConfig(**bias_config)


@pytest.fixture(name="mocked_sensor")
def getMockedAgent():
    """Get mocked :class:`.SensingAgent` object."""
    mocked_sensor = create_autospec(SensingAgent, instance=True)
    mocked_sensor.julian_date_start = datetimeToJulianDate(datetime(2019, 2, 1, 15, 20))
    return mocked_sensor


class TestSensorTimeBiasEvent:
    """Test class for :class:`.SensorTimeBiasEvent` class."""

    def testFromConfig(self, event_config_dict):
        """Test :meth:`.SensorTimeBiasEvent.fromConfig()`."""
        bias_config = SensorTimeBiasEventConfig(**event_config_dict)
        assert SensorTimeBiasEvent.fromConfig(bias_config)

    def testHandleEvent(self, mocked_sensor):
        """Test :meth:`.SensorTimeBiasEvent.handleEvent()` with an NTW impulse."""
        bias_event = SensorTimeBiasEvent(
            scope=SensorTimeBiasEvent.INTENDED_SCOPE.value,
            scope_instance_id=300000,
            start_time_jd=datetime(2019, 2, 1, 15, 20),
            end_time_jd=datetime(2019, 2, 1, 15, 20),
            event_type=SensorTimeBiasEvent.EVENT_TYPE,
            applied_bias=0.001,
        )
        bias_event.handleEvent(mocked_sensor)
