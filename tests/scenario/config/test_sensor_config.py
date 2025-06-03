from __future__ import annotations

# Third Party Imports
import pytest
from pydantic import BaseModel, ValidationError

# RESONAATE Imports
from resonaate.common.labels import FoVLabel, SensorLabel
from resonaate.scenario.config.sensor_config import (
    AdvRadarConfig,
    ConicFieldOfViewConfig,
    FieldOfViewConfig,
    OpticalConfig,
    RadarConfig,
    RectangularFieldOfViewConfig,
    ScheduledDowntimeConfig,
    SensorConfig,
)
from resonaate.sensors.sensor_base import DEFAULT_VIEWING_ANGLE


class FovWrapper(BaseModel):
    """Test model to make sure different types of FoV configurations are parsed correctly."""

    fov_config: FieldOfViewConfig
    """Wrapped field of view configuration."""


def testFieldOfViewConfigConic():
    """Test conic field of view config."""
    cone_cfg = FovWrapper(
        fov_config={
            "fov_shape": FoVLabel.CONIC,
            "cone_angle": DEFAULT_VIEWING_ANGLE,
        },
    )
    assert isinstance(cone_cfg.fov_config, ConicFieldOfViewConfig)
    assert cone_cfg.fov_config.cone_angle == DEFAULT_VIEWING_ANGLE

    cone_cfg = FovWrapper(
        fov_config={
            "fov_shape": FoVLabel.CONIC,
        },
    )
    assert isinstance(cone_cfg.fov_config, ConicFieldOfViewConfig)
    assert cone_cfg.fov_config.cone_angle == DEFAULT_VIEWING_ANGLE


def testFieldOfViewConfigRect():
    """Test rectangular field of view config."""
    rect_cfg = FovWrapper(
        fov_config={
            "fov_shape": FoVLabel.RECTANGULAR,
            "azimuth_angle": DEFAULT_VIEWING_ANGLE,
            "elevation_angle": DEFAULT_VIEWING_ANGLE,
        },
    )
    assert isinstance(rect_cfg.fov_config, RectangularFieldOfViewConfig)
    assert rect_cfg.fov_config.azimuth_angle == DEFAULT_VIEWING_ANGLE
    assert rect_cfg.fov_config.elevation_angle == DEFAULT_VIEWING_ANGLE

    rect_cfg = FovWrapper(
        fov_config={
            "fov_shape": FoVLabel.RECTANGULAR,
        },
    )
    assert isinstance(rect_cfg.fov_config, RectangularFieldOfViewConfig)
    assert rect_cfg.fov_config.azimuth_angle == DEFAULT_VIEWING_ANGLE
    assert rect_cfg.fov_config.elevation_angle == DEFAULT_VIEWING_ANGLE


def testBadInputsFieldOfViewConfig():
    """Test bad inputs for field of view config."""
    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "invalid",
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "conic",
                "cone_angle": 0.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "conic",
                "cone_angle": 180.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "conic",
                "cone_angle": -1.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "conic",
                "cone_angle": 181.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "rectangular",
                "azimuth_angle": 0.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "rectangular",
                "azimuth_angle": 180.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "rectangular",
                "azimuth_angle": -1.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "rectangular",
                "azimuth_angle": 181.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "rectangular",
                "elevation_angle": 0.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "rectangular",
                "elevation_angle": 180.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "rectangular",
                "elevation_angle": -1.0,
            },
        )

    with pytest.raises(ValidationError):
        _ = FovWrapper(
            fov_config={
                "fov_shape": "rectangular",
                "elevation_angle": 181.0,
            },
        )


class SensorWrapper(BaseModel):
    """Test model to make sure different types of sensor configurations are parsed correctly."""

    sensor_config: SensorConfig
    """Wrapped sensor configuration."""


@pytest.fixture(name="downtime_config")
def getDowntimeDict() -> dict:
    """Generates a fixture config for sensor downtime."""
    return {
        "period": 86400,
        "duration": 7200,
        "offset": 14000,
    }


@pytest.fixture(name="base_sensor_dict")
def getSensorDict() -> dict:
    """Create dict of common required sensor config fields."""
    return {
        "azimuth_range": (0.0, 359.99),
        "elevation_range": (0.0, 90.0),
        "covariance": [[2.0, 0.0], [0.0, 3.0]],
        "aperture_diameter": 5.170882945826411,
        "efficiency": 0.98,
        "slew_rate": 10.0,
    }


@pytest.fixture(name="base_sensor_revisit_dict")
def getSensorRevisitDict(base_sensor_dict: dict) -> dict:
    """Creates a sensor config that adds a non-zero minimum revisit time."""
    new_dict = base_sensor_dict
    new_dict["min_revisit_time"] = 3600.0
    return new_dict


@pytest.mark.parametrize("sensor_type", ["invalid", None, 10])
def testCreationBadType(sensor_type: str, base_sensor_dict: dict):
    """Test creating sensor config with bad params."""
    base_sensor_dict["type"] = sensor_type
    with pytest.raises(ValidationError):
        _ = SensorWrapper(sensor_config=base_sensor_dict)


def testOpticalConfig(base_sensor_dict: dict):
    """Test creating sensor config."""
    base_sensor_dict["type"] = SensorLabel.OPTICAL
    cfg = SensorWrapper(sensor_config=base_sensor_dict)
    assert isinstance(cfg.sensor_config, OpticalConfig)


def testRadarConfigMissing(base_sensor_dict: dict):
    """Test creating a radar configuration with missing required options."""
    base_sensor_dict["type"] = SensorLabel.RADAR
    with pytest.raises(ValidationError):
        _ = SensorWrapper(sensor_config=base_sensor_dict)


def testRadarConfig(base_sensor_dict: dict):
    """Test creating sensor config."""
    base_sensor_dict["type"] = SensorLabel.RADAR
    base_sensor_dict["tx_power"] = 2.5e6
    base_sensor_dict["tx_frequency"] = 1.5e9
    base_sensor_dict["min_detectable_power"] = 1.4314085925969573e-14
    cfg = SensorWrapper(sensor_config=base_sensor_dict)
    assert isinstance(cfg.sensor_config, RadarConfig)


def testAdvRadarConfigMissing(base_sensor_dict: dict):
    """Test creating an advanced radar configuration with missing required options."""
    base_sensor_dict["type"] = SensorLabel.ADV_RADAR
    with pytest.raises(ValidationError):
        _ = SensorWrapper(sensor_config=base_sensor_dict)


def testAdvRadarConfig(base_sensor_dict: dict):
    """Test creating sensor config."""
    base_sensor_dict["type"] = SensorLabel.ADV_RADAR
    base_sensor_dict["tx_power"] = 2.5e6
    base_sensor_dict["tx_frequency"] = 1.5e9
    base_sensor_dict["min_detectable_power"] = 1.4314085925969573e-14
    cfg = SensorWrapper(sensor_config=base_sensor_dict)
    assert isinstance(cfg.sensor_config, AdvRadarConfig)


def testMinRevisitField(base_sensor_revisit_dict: dict) -> None:
    """Test creating a sensor config with min revisit time too."""
    base_sensor_revisit_dict["type"] = SensorLabel.OPTICAL
    cfg = SensorWrapper(sensor_config=base_sensor_revisit_dict)
    assert isinstance(cfg.sensor_config, OpticalConfig)

    base_sensor_revisit_dict["min_revisit_time"] = -3600.0  # Test invalid
    with pytest.raises(ValidationError):
        _ = SensorWrapper(sensor_config=base_sensor_revisit_dict)


def testConstructSensorDowntime(downtime_config: dict) -> None:
    """Tests construction of a downtime config object."""
    cfg = ScheduledDowntimeConfig(**downtime_config)
    assert isinstance(cfg, ScheduledDowntimeConfig)

    # Test invalid fields
    downtime_config["period"] = -5000
    with pytest.raises(ValidationError):
        _ = ScheduledDowntimeConfig(**downtime_config)
    downtime_config["period"] = 7200
    downtime_config["duration"] = -5000
    with pytest.raises(ValidationError):
        _ = ScheduledDowntimeConfig(**downtime_config)
    downtime_config["duration"] = 5000
    downtime_config["offset"] = -5000
    with pytest.raises(ValidationError):
        _ = ScheduledDowntimeConfig(**downtime_config)


def testConstructSensorWithDowntime(
    base_sensor_dict: dict,
    downtime_config: dict,
) -> None:
    """Tests constructing a sensor object with downtime configs."""
    downtime = ScheduledDowntimeConfig(**downtime_config)

    # Construct a simple radar with the downtimes.
    base_sensor_dict["type"] = SensorLabel.RADAR
    base_sensor_dict["tx_power"] = 2.5e6
    base_sensor_dict["tx_frequency"] = 1.5e9
    base_sensor_dict["min_detectable_power"] = 1.4314085925969573e-14
    base_sensor_dict["downtimes"] = [downtime_config]

    sensor_cfg = SensorWrapper(sensor_config=base_sensor_dict)

    assert len(sensor_cfg.sensor_config.downtimes) == 1
    assert sensor_cfg.sensor_config.downtimes == [downtime]
