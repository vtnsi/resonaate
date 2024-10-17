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
from resonaate.common.labels import FoVLabel, SensorLabel
from resonaate.data.data_interface import AgentModel
from resonaate.data.events import SensorAdditionEvent
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config.event_configs import SensorAdditionEventConfig


@pytest.fixture(name="radar_ground_config")
def getSensorConfigGround():
    """``dict``: ground sensor agent config."""
    return {
        "name": "Test Ground Radar",
        "id": 100000,
        "platform": {"type": "ground_facility"},
        "state": {
            "type": "lla",
            "latitude": 0.1,
            "longitude": 1.1,
            "altitude": 1.0,
        },
        "sensor": {
            "covariance": [[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]],
            "slew_rate": 0.2617993877991494,
            "azimuth_range": [0.0, 6.283185132646661],
            "elevation_range": [0.0, 1.5707961522619713],
            "efficiency": 0.98,
            "aperture_diameter": 1.016,
            "type": SensorLabel.RADAR,
            "field_of_view": {"fov_shape": FoVLabel.RECTANGULAR},
            "background_observations": False,
            "tx_power": 3e6,
            "tx_frequency": 1.5e9,
            "min_detectable_power": 1.4314085925969573e-14,
        },
    }


@pytest.fixture(name="optical_space_config")
def getSensorConfigSpace():
    """``dict``: ground sensor agent config."""
    return {
        "name": "Test Space Optical",
        "id": 40001,
        "platform": {
            "type": "spacecraft",
            "station_keeping": {"routines": ["LEO"]},
        },
        "state": {
            "type": "eci",
            "position": [
                -6997.811593501495,
                63.69359356853797,
                -447.53287804600023,
            ],
            "velocity": [
                0.48666918798751624,
                1.0600865385159703,
                -7.448488839044817,
            ],
        },
        "sensor": {
            "covariance": [[9.869604401089358e-14, 0.0], [0.0, 9.869604401089358e-14]],
            "slew_rate": 0.04363323129985824,
            "azimuth_range": [0.0, 6.283185132646661],
            "elevation_range": [-1.5707961522619713, 1.5707961522619713],
            "efficiency": 0.99,
            "aperture_diameter": 0.2,
            "type": SensorLabel.OPTICAL,
            "field_of_view": {"fov_shape": FoVLabel.CONIC},
            "background_observations": False,
        },
    }


@pytest.fixture(name="event_config_dict")
def getSensorAddition():
    """``dict``: config dictionary for target addition."""
    return {
        "scope": SensorAdditionEvent.INTENDED_SCOPE.value,
        "scope_instance_id": 123,
        "start_time": datetime(2021, 8, 3, 12),
        "end_time": datetime(2021, 8, 3, 12),
        "event_type": SensorAdditionEvent.EVENT_TYPE,
        "tasking_engine_id": 123,
    }


class TestSensorAdditionEventConfig:
    """Test class for :class:`.SensorAdditionEventConfig` class."""

    def testInitGoodArgs(self, radar_ground_config: dict, event_config_dict: dict):
        """Test :class:`.SensorAdditionEventConfig` constructor with good arguments.

        Args:
            radar_ground_config (``dict``): ground sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        event_config_dict["sensor_agent"] = radar_ground_config
        assert SensorAdditionEventConfig(**event_config_dict)

    def testInitOtherGoodArgs(self, optical_space_config: dict, event_config_dict: dict):
        """Test :class:`.SensorAdditionEventConfig` constructor with other good arguments.

        Args:
            optical_space_config (``dict``): space sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        event_config_dict["sensor_agent"] = optical_space_config
        assert SensorAdditionEventConfig(**event_config_dict)

    def testInitBadECIState(self, optical_space_config: dict, event_config_dict: dict):
        """Test :class:`.SensorAdditionEventConfig` constructor with a bad initial ECI state.

        Args:
            optical_space_config (``dict``): space sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        bad_eci = [0, 1, 2]
        sen_config = deepcopy(optical_space_config)
        sen_config["state"]["position"] = bad_eci

        event_config_dict["sensor_agent"] = sen_config
        with pytest.raises(ValidationError):
            _ = SensorAdditionEventConfig(**event_config_dict)

    def testDataDependency(self, optical_space_config: dict, event_config_dict: dict):
        """Test that :class:`.SensorAdditionEventConfig`'s data dependencies are correct.

        Args:
            optical_space_config (``dict``): space sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        event_config_dict["sensor_agent"] = optical_space_config
        addition_config = SensorAdditionEventConfig(**event_config_dict)
        addition_dependencies = addition_config.getDataDependencies()
        assert len(addition_dependencies) == 1

        agent_dependency = addition_dependencies[0]
        assert agent_dependency.data_type == AgentModel
        assert agent_dependency.attributes == {
            "unique_id": addition_config.sensor_agent.id,
            "name": addition_config.sensor_agent.name,
        }


class TestSensorAdditionEvent:
    """Test class for :class:`.SensorAdditionEvent` class."""

    def testFromConfigRadar(self, optical_space_config: dict, event_config_dict: dict):
        """Test :meth:`.SensorAdditionEvent.fromConfig()`.

        Args:
            optical_space_config (``dict``): space sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        event_config_dict["sensor_agent"] = optical_space_config
        addition_config = SensorAdditionEventConfig(**event_config_dict)
        assert SensorAdditionEvent.fromConfig(addition_config)

    def testFromConfigOptical(self, radar_ground_config: dict, event_config_dict: dict):
        """Test :meth:`.SensorAdditionEvent.fromConfig()`.

        Args:
            radar_ground_config (``dict``): ground sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        event_config_dict["sensor_agent"] = radar_ground_config
        addition_config = SensorAdditionEventConfig(**event_config_dict)
        assert SensorAdditionEvent.fromConfig(addition_config)

    def testHandleEventOptical(self, mocked_scenario: MagicMock):
        """Test :meth:`.SensorAdditionEvent.handleEvent()`.

        Args:
            mocked_scenario (:class:`.MagicMock`): Mocked scenario object
        """
        mocked_scenario.addSensor = MagicMock()
        agent_obj = AgentModel(unique_id=12345, name="additional sensor")
        impulse_event = SensorAdditionEvent(
            scope=SensorAdditionEvent.INTENDED_SCOPE,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=SensorAdditionEvent.EVENT_TYPE,
            tasking_engine_id=123,
            agent=agent_obj,
            platform="GroundFacility",
            pos_x_km=0,
            pos_y_km=1,
            pos_z_km=2,
            vel_x_km_p_sec=3,
            vel_y_km_p_sec=4,
            vel_z_km_p_sec=5,
            azimuth_min=0,
            azimuth_max=1,
            elevation_min=0,
            elevation_max=1,
            covariance_json=dumps([[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]]),
            aperture_diameter=1.016,
            efficiency=0.98,
            slew_rate=0.2617993877991494,
            sensor_type=SensorLabel.OPTICAL,
            fov_shape=FoVLabel.CONIC,
            background_observations=False,
            station_keeping_json=dumps([]),
        )
        impulse_event.handleEvent(mocked_scenario)
        mocked_scenario.addSensor.assert_called_once()

    def testHandleEventRadar(self, mocked_scenario: MagicMock):
        """Test :meth:`.SensorAdditionEvent.handleEvent()`.

        Args:
            mocked_scenario (:class:`.MagicMock`): Mocked scenario object
        """
        mocked_scenario.addSensor = MagicMock()
        agent_obj = AgentModel(unique_id=12345, name="additional sensor")
        impulse_event = SensorAdditionEvent(
            scope=SensorAdditionEvent.INTENDED_SCOPE,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=SensorAdditionEvent.EVENT_TYPE,
            tasking_engine_id=123,
            agent=agent_obj,
            platform="GroundFacility",
            pos_x_km=0,
            pos_y_km=1,
            pos_z_km=2,
            vel_x_km_p_sec=3,
            vel_y_km_p_sec=4,
            vel_z_km_p_sec=5,
            azimuth_min=0,
            azimuth_max=1,
            elevation_min=0,
            elevation_max=1,
            covariance_json=dumps([[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]]),
            aperture_diameter=1.016,
            efficiency=0.98,
            slew_rate=0.2617993877991494,
            sensor_type=SensorLabel.RADAR,
            tx_power=2.5e6,
            tx_frequency=1.5e9,
            min_detectable_power=3.5699513926877067e-19,
            fov_shape=FoVLabel.RECTANGULAR,
            background_observations=False,
            station_keeping_json=dumps([]),
        )
        impulse_event.handleEvent(mocked_scenario)
        mocked_scenario.addSensor.assert_called_once()
