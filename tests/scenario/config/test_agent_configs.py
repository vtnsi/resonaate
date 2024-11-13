from __future__ import annotations

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.labels import PlatformLabel, SensorLabel
from resonaate.scenario.config.agent_config import AgentConfig, SensingAgentConfig

# Local Imports
from . import EARTH_SENSORS, GEO_TARGETS, LEO_TARGETS, SPACE_SENSORS


@pytest.mark.parametrize("tgt_dict", GEO_TARGETS + LEO_TARGETS)
def testValidAgentConfig(tgt_dict):
    """Test basic construction of TargetAgentConfig & optional attributes."""
    tgt_cfg_obj = AgentConfig(**tgt_dict)
    assert tgt_cfg_obj.id == tgt_dict["id"]
    assert tgt_cfg_obj.name == tgt_dict["name"]
    assert tgt_cfg_obj.state.type == tgt_dict["state"]["type"]
    assert tgt_cfg_obj.platform.type == tgt_dict["platform"]["type"]
    assert tgt_cfg_obj.platform.type in (
        PlatformLabel.GROUND_FACILITY,
        PlatformLabel.SPACECRAFT,
    )


@pytest.mark.parametrize("sen_dict", EARTH_SENSORS + SPACE_SENSORS)
def testValidSensingAgentConfig(sen_dict):
    """Test basic construction of TestSensorConfig & optional attributes."""
    sen_cfg_obj = SensingAgentConfig(**sen_dict)
    assert sen_cfg_obj.id == sen_dict["id"]
    assert sen_cfg_obj.name == sen_dict["name"]
    assert sen_cfg_obj.sensor.azimuth_range == sen_dict["sensor"]["azimuth_range"]
    assert sen_cfg_obj.sensor.elevation_range == sen_dict["sensor"]["elevation_range"]
    assert sen_cfg_obj.sensor.covariance == sen_dict["sensor"]["covariance"]
    assert sen_cfg_obj.sensor.aperture_diameter == sen_dict["sensor"]["aperture_diameter"]
    assert sen_cfg_obj.sensor.efficiency == sen_dict["sensor"]["efficiency"]
    assert sen_cfg_obj.sensor.aperture_diameter == sen_dict["sensor"]["aperture_diameter"]
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
