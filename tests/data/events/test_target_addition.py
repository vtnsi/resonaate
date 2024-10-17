from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from datetime import datetime
from json import dumps
from unittest.mock import MagicMock

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.data.data_interface import AgentModel
from resonaate.data.events import TargetAdditionEvent
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config.event_configs import TargetAdditionEventConfig


@pytest.fixture(name="tgt_config_eci")
def getTargetConfigECI():
    """``dict``: target agent config with ECI state."""
    return {
        "id": 12345,
        "name": "new satellite",
        "state": {"type": "eci", "position": [0, 10000, 2], "velocity": [3, 4, 5]},
        "platform": {"type": "spacecraft"},
    }


@pytest.fixture(name="tgt_config_coe")
def getTargetConfigCOE():
    """``dict``: target agent config with COE state."""
    return {
        "id": 12345,
        "name": "new satellite",
        "state": {
            "type": "coe",
            "semi_major_axis": 10000,
            "eccentricity": 0.00,
            "inclination": 10.0,
            "right_ascension": 100.0,
            "argument_periapsis": 1.0,
            "true_anomaly": 1.0,
        },
        "platform": {"type": "spacecraft"},
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


class TestTargetAdditionEventConfig:
    """Test class for :class:`.TargetAdditionEventConfig` class."""

    def testInitGoodArgs(self, tgt_config_eci, event_config_dict):
        """Test :class:`.TargetAdditionEventConfig` constructor with good arguments."""
        event_config_dict["target_agent"] = tgt_config_eci
        assert TargetAdditionEventConfig(**event_config_dict)

    def testInitOtherGoodArgs(self, tgt_config_coe, event_config_dict):
        """Test :class:`.TargetAdditionEventConfig` constructor with other good arguments."""
        event_config_dict["target_agent"] = tgt_config_coe
        assert TargetAdditionEventConfig(**event_config_dict)

    def testInitBadECIState(self, tgt_config_eci, event_config_dict):
        """Test :class:`.TargetAdditionEventConfig` constructor with a bad initial ECI state."""
        bad_eci = [0, 1, 2]
        tgt_config = deepcopy(tgt_config_eci)
        tgt_config["state"]["position"] = bad_eci

        event_config_dict["target_agent"] = tgt_config
        with pytest.raises(ValidationError):
            _ = TargetAdditionEventConfig(**event_config_dict)

    def testDataDependency(self, tgt_config_eci, event_config_dict):
        """Test that :class:`.TargetAdditionEventConfig`'s data dependencies are correct."""
        event_config_dict["target_agent"] = tgt_config_eci
        addition_config = TargetAdditionEventConfig(**event_config_dict)
        addition_dependencies = addition_config.getDataDependencies()
        assert len(addition_dependencies) == 1

        agent_dependency = addition_dependencies[0]
        assert agent_dependency.data_type == AgentModel
        assert agent_dependency.attributes == {
            "unique_id": addition_config.target_agent.id,
            "name": addition_config.target_agent.name,
        }


class TestTargetAdditionEvent:
    """Test class for :class:`.TargetAdditionEvent` class."""

    def testFromConfig(self, tgt_config_eci, event_config_dict):
        """Test :meth:`.TargetAdditionEvent.fromConfig()`."""
        event_config_dict["target_agent"] = tgt_config_eci
        addition_config = TargetAdditionEventConfig(**event_config_dict)
        addition_event = TargetAdditionEvent.fromConfig(addition_config)
        assert addition_event.eci[:3] == addition_config.target_agent.state.position
        assert addition_event.eci[3:] == addition_config.target_agent.state.velocity
        assert (
            addition_event.station_keeping["routines"]
            == addition_config.target_agent.platform.station_keeping.routines
        )

    def testHandleEvent(self, mocked_scenario):
        """Test :meth:`.TargetAdditionEvent.handleEvent()`."""
        mocked_scenario.addTarget = MagicMock()
        agent_obj = AgentModel(unique_id=12345, name="additional sat")
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
        mocked_scenario.addTarget.assert_called_once()
