# pylint: disable=attribute-defined-outside-init, unused-argument
from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.labels import PlatformLabel, SensorLabel
from resonaate.scenario.config.agent_config import SensingAgentConfig, TargetAgentConfig
from resonaate.scenario.config.base import ConfigValueError
from resonaate.scenario.config.platform_config import PlatformConfig
from resonaate.scenario.config.sensor_config import SensorConfig
from resonaate.scenario.config.state_config import StateConfig

# Local Imports
from .conftest import EARTH_SENSORS, GEO_TARGETS, LEO_TARGETS, SPACE_SENSORS


class TestTargetConfig:
    """Test the target config object with valid/invalid sets of JSON configs."""

    @pytest.mark.parametrize("tgt_dict", GEO_TARGETS + LEO_TARGETS)
    def testValidConfig(self, tgt_dict):
        """Test basic construction of TargetAgentConfig & optional attributes."""
        tgt_cfg_obj = TargetAgentConfig(**tgt_dict)
        assert tgt_cfg_obj.id == tgt_dict["id"]
        assert tgt_cfg_obj.name == tgt_dict["name"]
        assert tgt_cfg_obj.state.type == tgt_dict["state"]["type"]
        assert tgt_cfg_obj.platform.type == tgt_dict["platform"]["type"]
        assert tgt_cfg_obj.platform.type in (
            PlatformLabel.GROUND_FACILITY,
            PlatformLabel.SPACECRAFT,
        )

        new_cfg_dict = deepcopy(tgt_dict)
        state_cfg = StateConfig.fromDict(tgt_dict["state"])
        platform_cfg = PlatformConfig.fromDict(tgt_dict["platform"], state=state_cfg)
        new_cfg_dict["state"] = state_cfg
        new_cfg_dict["platform"] = platform_cfg

        _ = TargetAgentConfig(**new_cfg_dict)

    def testInValidStateType(self):
        """Test a mismatch of the StateConfig.type and PlatformConfig."""
        tgt_dict = deepcopy(LEO_TARGETS[0])
        tgt_dict["state"] = {
            "type": "lla",
            "latitude": -35.0,
            "longitude": 100,
            "altitude": 2.0,
        }
        with pytest.raises(ConfigValueError):
            _ = TargetAgentConfig(**tgt_dict)


class TestSensorConfig:
    """Test the sensor config object with valid/invalid sets of JSON configs."""

    @pytest.mark.parametrize("sen_dict", EARTH_SENSORS + SPACE_SENSORS)
    def testValidConfig(self, sen_dict):
        """Test basic construction of TestSensorConfig & optional attributes."""
        sen_cfg_obj = SensingAgentConfig(**sen_dict)
        assert sen_cfg_obj.id == sen_dict["id"]
        assert sen_cfg_obj.name == sen_dict["name"]
        assert sen_cfg_obj.sensor.azimuth_range == sen_dict["sensor"]["azimuth_range"]
        assert sen_cfg_obj.sensor.elevation_range == sen_dict["sensor"]["elevation_range"]
        assert sen_cfg_obj.sensor.covariance == sen_dict["sensor"]["covariance"]
        assert sen_cfg_obj.sensor.aperture_area == sen_dict["sensor"]["aperture_area"]
        assert sen_cfg_obj.sensor.efficiency == sen_dict["sensor"]["efficiency"]
        assert sen_cfg_obj.sensor.aperture_area == sen_dict["sensor"]["aperture_area"]
        assert sen_cfg_obj.state.type == sen_dict["state"]["type"]
        assert sen_cfg_obj.sensor.type == sen_dict["sensor"]["type"]
        assert sen_cfg_obj.platform.type == sen_dict["platform"]["type"]
        assert sen_cfg_obj.platform.type in (
            PlatformLabel.GROUND_FACILITY,
            PlatformLabel.SPACECRAFT,
        )

        assert sen_cfg_obj.sensor.type in (
            SensorLabel.OPTICAL,
            SensorLabel.RADAR,
            SensorLabel.ADV_RADAR,
        )
        if sen_cfg_obj.sensor.type in (SensorLabel.RADAR, SensorLabel.ADV_RADAR):
            assert sen_cfg_obj.sensor.tx_frequency == sen_dict["sensor"]["tx_frequency"]
            assert sen_cfg_obj.sensor.tx_power == sen_dict["sensor"]["tx_power"]
            assert (
                sen_cfg_obj.sensor.min_detectable_power
                == sen_dict["sensor"]["min_detectable_power"]
            )

        new_cfg_dict = deepcopy(sen_dict)
        state_cfg = StateConfig.fromDict(sen_dict["state"])
        platform_cfg = PlatformConfig.fromDict(sen_dict["platform"], state=state_cfg)
        sensor_cfg = SensorConfig.fromDict(sen_dict["sensor"])
        new_cfg_dict["state"] = state_cfg
        new_cfg_dict["platform"] = platform_cfg
        new_cfg_dict["sensor"] = sensor_cfg

        _ = SensingAgentConfig(**new_cfg_dict)
