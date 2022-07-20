# pylint: disable=unused-argument
# Standard Library Imports
from copy import deepcopy
from datetime import datetime
from json import dumps

# Third Party Imports
import pytest

try:
    # RESONAATE Imports
    from resonaate.data.data_interface import Agent
    from resonaate.data.events import TargetAdditionEvent
    from resonaate.physics.time.stardate import datetimeToJulianDate
    from resonaate.scenario.config.base import ConfigError
    from resonaate.scenario.config.event_configs import TargetAdditionEventConfig
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ...conftest import BaseTestCase


@pytest.fixture(name="tgt_config_eci")
def getTargetConfigECI():
    """``dict``: target agent config with ECI state."""
    return {
        "sat_num": 12345,
        "sat_name": "new satellite",
        "init_eci": [0, 1, 2, 3, 4, 5],
        "station_keeping": {},
    }


@pytest.fixture(name="tgt_config_coe")
def getTargetConfigCOE():
    """``dict``: target agent config with COE state."""
    return {
        "sat_num": 12345,
        "sat_name": "new satellite",
        "init_coe": {
            "sma": 10000,
            "ecc": 0.00,
            "inc": 10.0,
            "raan": 100.0,
            "arg_p": 1.0,
            "true_anom": 1.0,
        },
        "station_keeping": {},
    }


@pytest.fixture(name="event_config_dict")
def getTargetAdditionConfigDict():
    """``dict``: config dictionary for target addition."""
    return {
        "scope": TargetAdditionEvent.INTENDED_SCOPE.value,
        "scope_instance_id": 123,
        "start_time": datetime(2021, 8, 3, 12),
        "end_time": datetime(2021, 8, 3, 12),
        "event_type": TargetAdditionEvent.EVENT_TYPE,
        "tasking_engine_id": 123,
    }


class TestTargetAdditionEventConfig(BaseTestCase):
    """Test class for :class:`.TargetAdditionEventConfig` class."""

    def testInitGoodArgs(self, tgt_config_eci, event_config_dict):
        """Test :class:`.TargetAdditionEventConfig` constructor with good arguments."""
        event_config_dict["target"] = tgt_config_eci
        assert TargetAdditionEventConfig(**event_config_dict)

    def testInitOtherGoodArgs(self, tgt_config_coe, event_config_dict):
        """Test :class:`.TargetAdditionEventConfig` constructor with other good arguments."""
        event_config_dict["target"] = tgt_config_coe
        assert TargetAdditionEventConfig(**event_config_dict)

    def testInitNoState(self, tgt_config_eci, event_config_dict):
        """Test :class:`.TargetAdditionEventConfig` constructor with no state configuration."""
        tgt_config = deepcopy(tgt_config_eci)
        del tgt_config["init_eci"]

        event_config_dict["target"] = tgt_config
        with pytest.raises(ConfigError):
            _ = TargetAdditionEventConfig(**event_config_dict)

    def testInitDuplicateState(self, tgt_config_eci, event_config_dict):
        """Test :class:`.TargetAdditionEventConfig` constructor with duplicate state configurations."""
        tgt_config = deepcopy(tgt_config_eci)
        tgt_config["init_coe"] = {
            "sma": 10000,
            "ecc": 0.01,
            "inc": 10.0,
            "raan": 100.0,
            "arg_p": 1.0,
            "true_anomaly": 1.0,
        }

        event_config_dict["target"] = tgt_config
        with pytest.raises(ConfigError):
            _ = TargetAdditionEventConfig(**event_config_dict)

    def testInitBadECIState(self, tgt_config_eci, event_config_dict):
        """Test :class:`.TargetAdditionEventConfig` constructor with a bad initial ECI state."""
        bad_eci = [0, 1, 2]
        expected_err = f"ECI vector should have 6 elements, not {len(bad_eci)}"
        tgt_config = deepcopy(tgt_config_eci)
        tgt_config["init_eci"] = bad_eci

        event_config_dict["target"] = tgt_config
        with pytest.raises(ConfigError, match=expected_err):
            _ = TargetAdditionEventConfig(**event_config_dict)

    def testDataDependency(self, tgt_config_eci, event_config_dict):
        """Test that :class:`.TargetAdditionEventConfig`'s data dependencies are correct."""
        event_config_dict["target"] = tgt_config_eci
        addition_config = TargetAdditionEventConfig(**event_config_dict)
        addition_dependencies = addition_config.getDataDependencies()
        assert len(addition_dependencies) == 1

        agent_dependency = addition_dependencies[0]
        assert agent_dependency.data_type == Agent
        assert agent_dependency.attributes == {
            "unique_id": addition_config.target.sat_num,
            "name": addition_config.target.sat_name,
        }


class TestTargetAdditionEvent(BaseTestCase):
    """Test class for :class:`.TargetAdditionEvent` class."""

    def testFromConfig(self, tgt_config_eci, event_config_dict):
        """Test :meth:`.TargetAdditionEvent.fromConfig()`."""
        event_config_dict["target"] = tgt_config_eci
        addition_config = TargetAdditionEventConfig(**event_config_dict)
        addition_event = TargetAdditionEvent.fromConfig(addition_config)
        assert addition_event.eci == addition_config.target.init_eci
        assert (
            addition_event.station_keeping["routines"]
            == addition_config.target.station_keeping.routines
        )

    def testHandleEvent(self, mocked_scenario):
        """Test :meth:`.TargetAdditionEvent.handleEvent()`."""
        agent_obj = Agent(unique_id=12345, name="additional sat")
        impulse_event = TargetAdditionEvent(
            scope=TargetAdditionEvent.INTENDED_SCOPE.value,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=TargetAdditionEvent.EVENT_TYPE,
            tasking_engine_id=123,
            agent=agent_obj,
            pos_x_km=0,
            pos_y_km=1,
            pos_z_km=2,
            vel_x_km_p_sec=3,
            vel_y_km_p_sec=4,
            vel_z_km_p_sec=5,
            station_keeping_json=dumps([]),
        )
        impulse_event.handleEvent(mocked_scenario)
