from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from datetime import datetime
from json import dumps
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.data.data_interface import AgentModel
from resonaate.data.events import SensorAdditionEvent
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config.base import ConfigError
from resonaate.scenario.config.event_configs import SensorAdditionEventConfig
from resonaate.sensors.sensor_base import (
    CONIC_FOV_LABEL,
    OPTICAL_LABEL,
    RADAR_LABEL,
    RECTANGULAR_FOV_LABEL,
)

if TYPE_CHECKING:
    # Standard Library Imports
    from unittest.mock import MagicMock


@pytest.fixture(name="radar_ground_config")
def getSensorConfigGround():
    """``dict``: ground sensor agent config."""
    return {
        "name": "Test Ground Radar",
        "id": 100000,
        "covariance": [[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]],
        "slew_rate": 0.2617993877991494,
        "azimuth_range": [0.0, 6.283185132646661],
        "elevation_range": [0.0, 1.5707961522619713],
        "efficiency": 0.98,
        "aperture_area": 0.8107319665559964,
        "sensor_type": RADAR_LABEL,
        "field_of_view": {"fov_shape": RECTANGULAR_FOV_LABEL},
        "background_observations": False,
        "lat": 0.1,
        "lon": 1.1,
        "alt": 1.0,
        "host_type": "GroundFacility",
        "tx_power": 3e6,
        "tx_frequency": 1.5e9,
        "min_detectable_power": 1.4314085925969573e-14,
    }


@pytest.fixture(name="optical_space_config")
def getSensorConfigSpace():
    """``dict``: ground sensor agent config."""
    return {
        "name": "Test Space Optical",
        "id": 40001,
        "covariance": [[9.869604401089358e-14, 0.0], [0.0, 9.869604401089358e-14]],
        "slew_rate": 0.04363323129985824,
        "azimuth_range": [0.0, 6.283185132646661],
        "elevation_range": [-1.5707961522619713, 1.5707961522619713],
        "efficiency": 0.99,
        "aperture_area": 0.031415926535897934,
        "sensor_type": OPTICAL_LABEL,
        "init_eci": [
            -6997.811593501495,
            63.69359356853797,
            -447.53287804600023,
            0.48666918798751624,
            1.0600865385159703,
            -7.448488839044817,
        ],
        "field_of_view": {"fov_shape": CONIC_FOV_LABEL},
        "background_observations": False,
        "host_type": "Spacecraft",
        "station_keeping": {"routines": ["LEO"]},
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
        event_config_dict["sensor"] = radar_ground_config
        assert SensorAdditionEventConfig(**event_config_dict)

    def testInitOtherGoodArgs(self, optical_space_config: dict, event_config_dict: dict):
        """Test :class:`.SensorAdditionEventConfig` constructor with other good arguments.

        Args:
            optical_space_config (``dict``): space sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        event_config_dict["sensor"] = optical_space_config
        assert SensorAdditionEventConfig(**event_config_dict)

    def testInitNoState(self, optical_space_config: dict, event_config_dict: dict):
        """Test :class:`.SensorAdditionEventConfig` constructor with no state configuration.

        Args:
            optical_space_config (``dict``): space sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        sen_config = deepcopy(optical_space_config)
        del sen_config["init_eci"]

        event_config_dict["sensor"] = sen_config
        with pytest.raises(ConfigError):
            _ = SensorAdditionEventConfig(**event_config_dict)

    def testInitDuplicateState(self, optical_space_config: dict, event_config_dict: dict):
        """Test :class:`.SensorAdditionEventConfig` constructor with duplicate state configurations.

        Args:
            optical_space_config (``dict``): space sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        sen_config = deepcopy(optical_space_config)
        sen_config["lat"] = 0.1
        sen_config["lon"] = 1.1
        sen_config["alt"] = 1.0

        event_config_dict["sensor"] = sen_config
        with pytest.raises(ConfigError):
            _ = SensorAdditionEventConfig(**event_config_dict)

    def testInitBadECIState(self, optical_space_config: dict, event_config_dict: dict):
        """Test :class:`.SensorAdditionEventConfig` constructor with a bad initial ECI state.

        Args:
            optical_space_config (``dict``): space sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        bad_eci = [0, 1, 2]
        expected_err = f"ECI vector should have 6 elements, not {len(bad_eci)}"
        sen_config = deepcopy(optical_space_config)
        sen_config["init_eci"] = bad_eci

        event_config_dict["sensor"] = sen_config
        with pytest.raises(ConfigError, match=expected_err):
            _ = SensorAdditionEventConfig(**event_config_dict)

    def testInitRadarNoTx(self, radar_ground_config: dict, event_config_dict: dict):
        """Test :class:`.SensorAdditionEventConfig` constructor with no transmit info for a radar.

        Args:
            radar_ground_config (``dict``): ground sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        expected_err = r"\w*Sensor \d+: Radar specific parameters not set\w*"
        sen_config = deepcopy(radar_ground_config)
        del sen_config["tx_power"]

        event_config_dict["sensor"] = sen_config
        with pytest.raises(ConfigError, match=expected_err):
            _ = SensorAdditionEventConfig(**event_config_dict)

    def testInitGroundFacilityWithStationKeeping(
        self, radar_ground_config: dict, event_config_dict: dict
    ):
        """Test :class:`.SensorAdditionEventConfig` constructor with station keeping set for a ground facility.

        Args:
            radar_ground_config (``dict``): ground sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        expected_err = "Ground based sensors cannot perform station keeping"
        sen_config = deepcopy(radar_ground_config)
        sen_config["station_keeping"] = {"routines": ["LEO"]}

        event_config_dict["sensor"] = sen_config
        with pytest.raises(ConfigError, match=expected_err):
            _ = SensorAdditionEventConfig(**event_config_dict)

    def testDataDependency(self, optical_space_config: dict, event_config_dict: dict):
        """Test that :class:`.SensorAdditionEventConfig`'s data dependencies are correct.

        Args:
            optical_space_config (``dict``): space sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        event_config_dict["sensor"] = optical_space_config
        addition_config = SensorAdditionEventConfig(**event_config_dict)
        addition_dependencies = addition_config.getDataDependencies()
        assert len(addition_dependencies) == 1

        agent_dependency = addition_dependencies[0]
        assert agent_dependency.data_type == AgentModel
        assert agent_dependency.attributes == {
            "unique_id": addition_config.sensor.id,
            "name": addition_config.sensor.name,
        }


class TestSensorAdditionEvent:
    """Test class for :class:`.SensorAdditionEvent` class."""

    def testFromConfigRadar(self, optical_space_config: dict, event_config_dict: dict):
        """Test :meth:`.SensorAdditionEvent.fromConfig()`.

        Args:
            optical_space_config (``dict``): space sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        event_config_dict["sensor"] = optical_space_config
        addition_config = SensorAdditionEventConfig(**event_config_dict)
        assert SensorAdditionEvent.fromConfig(addition_config)

    def testFromConfigOptical(self, radar_ground_config: dict, event_config_dict: dict):
        """Test :meth:`.SensorAdditionEvent.fromConfig()`.

        Args:
            radar_ground_config (``dict``): ground sensor fixture
            event_config_dict (``dict``): sensor addition configuration
        """
        event_config_dict["sensor"] = radar_ground_config
        addition_config = SensorAdditionEventConfig(**event_config_dict)
        assert SensorAdditionEvent.fromConfig(addition_config)

    def testHandleEventOptical(self, mocked_scenario: MagicMock):
        """Test :meth:`.SensorAdditionEvent.handleEvent()`.

        Args:
            mocked_scenario (:class:`.MagicMock`): Mocked scenario object
        """
        agent_obj = AgentModel(unique_id=12345, name="additional sensor")
        impulse_event = SensorAdditionEvent(
            scope=SensorAdditionEvent.INTENDED_SCOPE,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=SensorAdditionEvent.EVENT_TYPE,
            tasking_engine_id=123,
            agent=agent_obj,
            host_type="GroundFacility",
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
            aperture_area=0.8107319665559964,
            efficiency=0.98,
            slew_rate=0.2617993877991494,
            sensor_type=OPTICAL_LABEL,
            fov_shape=CONIC_FOV_LABEL,
            background_observations=False,
            station_keeping_json=dumps([]),
        )
        impulse_event.handleEvent(mocked_scenario)

    def testHandleEventRadar(self, mocked_scenario: MagicMock):
        """Test :meth:`.SensorAdditionEvent.handleEvent()`.

        Args:
            mocked_scenario (:class:`.MagicMock`): Mocked scenario object
        """
        agent_obj = AgentModel(unique_id=12345, name="additional sensor")
        impulse_event = SensorAdditionEvent(
            scope=SensorAdditionEvent.INTENDED_SCOPE,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=SensorAdditionEvent.EVENT_TYPE,
            tasking_engine_id=123,
            agent=agent_obj,
            host_type="GroundFacility",
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
            aperture_area=0.8107319665559964,
            efficiency=0.98,
            slew_rate=0.2617993877991494,
            sensor_type=RADAR_LABEL,
            tx_power=2.5e6,
            tx_frequency=1.5e9,
            min_detectable_power=3.5699513926877067e-19,
            fov_shape=RECTANGULAR_FOV_LABEL,
            background_observations=False,
            station_keeping_json=dumps([]),
        )
        impulse_event.handleEvent(mocked_scenario)
