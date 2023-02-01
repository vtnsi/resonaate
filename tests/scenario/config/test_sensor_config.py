# pylint: disable=attribute-defined-outside-init, unused-argument
from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.labels import SensorLabel
from resonaate.scenario.config.base import ConfigValueError
from resonaate.scenario.config.sensor_config import (
    AdvRadarConfig,
    FieldOfViewConfig,
    OpticalConfig,
    RadarConfig,
    SensorConfig,
)
from resonaate.sensors.sensor_base import DEFAULT_VIEWING_ANGLE


def testFieldOfViewConfig():
    """Test field of view config."""
    cone_cfg = FieldOfViewConfig(fov_shape="conic", cone_angle=DEFAULT_VIEWING_ANGLE)
    assert cone_cfg.CONFIG_LABEL == "field_of_view"
    assert cone_cfg.cone_angle == DEFAULT_VIEWING_ANGLE

    cone_cfg = FieldOfViewConfig(fov_shape="conic")
    assert cone_cfg.CONFIG_LABEL == "field_of_view"
    assert cone_cfg.cone_angle == DEFAULT_VIEWING_ANGLE

    rect_cfg = FieldOfViewConfig(
        fov_shape="rectangular",
        azimuth_angle=DEFAULT_VIEWING_ANGLE,
        elevation_angle=DEFAULT_VIEWING_ANGLE,
    )
    assert rect_cfg.CONFIG_LABEL == "field_of_view"
    assert rect_cfg.azimuth_angle == DEFAULT_VIEWING_ANGLE
    assert rect_cfg.elevation_angle == DEFAULT_VIEWING_ANGLE

    rect_cfg = FieldOfViewConfig(fov_shape="rectangular")
    assert rect_cfg.azimuth_angle == DEFAULT_VIEWING_ANGLE
    assert rect_cfg.elevation_angle == DEFAULT_VIEWING_ANGLE


def testBadInputsFieldOfViewConfig():
    """Test bad inputs for field of view config."""
    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="invalid")

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="conic", cone_angle=0.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="conic", cone_angle=180.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="conic", cone_angle=-1.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="conic", cone_angle=181.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", azimuth_angle=0.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", azimuth_angle=180.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", azimuth_angle=-1.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", azimuth_angle=181.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", elevation_angle=0.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", elevation_angle=180.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", elevation_angle=-1.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", elevation_angle=181.0)


@pytest.fixture(name="base_sensor_dict")
def getSensorDict() -> dict:
    """Create dict of common required sensor config fields."""
    return {
        "azimuth_range": (0.0, 360.0),
        "elevation_range": (0.0, 90.0),
        "covariance": [[2.0, 0.0], [0.0, 3.0]],
        "aperture_area": 21.0,
        "efficiency": 0.98,
        "slew_rate": 10.0,
    }


class TestSensorConfig:
    """Test base SensorConfig object."""

    @pytest.mark.parametrize("sensor_type", SensorConfig.VALID_LABELS)
    def testCreation(self, sensor_type: str, base_sensor_dict: dict):
        """Test creating sensor config."""
        base_sensor_dict["type"] = sensor_type
        base_sensor_dict["field_of_view"] = {"fov_shape": "conic", "cone_angle": 20.0}
        _ = SensorConfig(**base_sensor_dict)

    @pytest.mark.parametrize("sensor_type", ["invalid", None, 10])
    def testCreationBadType(self, sensor_type: str, base_sensor_dict: dict):
        """Test creating sensor config with bad params."""
        base_sensor_dict["type"] = sensor_type
        with pytest.raises(ConfigValueError):
            _ = SensorConfig(**base_sensor_dict)

        with pytest.raises(ConfigValueError):
            _ = SensorConfig.fromDict(base_sensor_dict)


def testOpticalConfig(base_sensor_dict: dict):
    """Test creating sensor config."""
    base_sensor_dict["type"] = SensorLabel.OPTICAL
    cfg = OpticalConfig(**base_sensor_dict)
    assert cfg
    assert cfg.type == SensorLabel.OPTICAL

    new_cfg_dict = deepcopy(base_sensor_dict)
    new_cfg_dict["minimum_range"] = 100.0
    cfg = OpticalConfig.fromDict(new_cfg_dict)
    assert cfg
    assert cfg.type == SensorLabel.OPTICAL


def testRadarConfig(base_sensor_dict: dict):
    """Test creating sensor config."""
    base_sensor_dict["type"] = SensorLabel.RADAR
    base_sensor_dict["tx_power"] = 2.5e6
    base_sensor_dict["tx_frequency"] = 1.5e9
    base_sensor_dict["min_detectable_power"] = 1.4314085925969573e-14
    cfg = RadarConfig(**base_sensor_dict)
    assert cfg
    assert cfg.type == SensorLabel.RADAR

    new_cfg_dict = deepcopy(base_sensor_dict)
    new_cfg_dict["minimum_range"] = 100.0
    new_cfg_dict["tx_frequency"] = "s"
    cfg = RadarConfig.fromDict(new_cfg_dict)
    assert cfg
    assert cfg.type == SensorLabel.RADAR

    new_cfg_dict = deepcopy(base_sensor_dict)
    del new_cfg_dict["min_detectable_power"]
    with pytest.raises(ConfigValueError):
        _ = RadarConfig.fromDict(new_cfg_dict)

    del new_cfg_dict["tx_frequency"]
    with pytest.raises(ConfigValueError):
        _ = RadarConfig.fromDict(new_cfg_dict)

    del new_cfg_dict["tx_power"]
    with pytest.raises(ConfigValueError):
        _ = RadarConfig.fromDict(new_cfg_dict)


def testAdvRadarConfig(base_sensor_dict: dict):
    """Test creating sensor config."""
    base_sensor_dict["type"] = SensorLabel.ADV_RADAR
    base_sensor_dict["tx_power"] = 2.5e6
    base_sensor_dict["tx_frequency"] = 1.5e9
    base_sensor_dict["min_detectable_power"] = 1.4314085925969573e-14
    cfg = AdvRadarConfig(**base_sensor_dict)
    assert cfg
    assert cfg.type == SensorLabel.ADV_RADAR

    new_cfg_dict = deepcopy(base_sensor_dict)
    new_cfg_dict["minimum_range"] = 100.0
    new_cfg_dict["tx_frequency"] = "s"
    cfg = AdvRadarConfig.fromDict(new_cfg_dict)
    assert cfg
    assert cfg.type == SensorLabel.ADV_RADAR

    new_cfg_dict = deepcopy(base_sensor_dict)
    del new_cfg_dict["min_detectable_power"]
    with pytest.raises(ConfigValueError):
        _ = AdvRadarConfig.fromDict(new_cfg_dict)

    del new_cfg_dict["tx_frequency"]
    with pytest.raises(ConfigValueError):
        _ = AdvRadarConfig.fromDict(new_cfg_dict)

    del new_cfg_dict["tx_power"]
    with pytest.raises(ConfigValueError):
        _ = AdvRadarConfig.fromDict(new_cfg_dict)
