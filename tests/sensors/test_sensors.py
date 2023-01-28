from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents import GROUND_FACILITY_LABEL
from resonaate.scenario.config.agent_config import SensingAgentConfig
from resonaate.scenario.config.platform_config import PlatformConfig
from resonaate.scenario.config.sensor_config import FieldOfViewConfig
from resonaate.scenario.config.state_config import LLA_LABEL, StateConfig
from resonaate.sensors import (
    ADV_RADAR_LABEL,
    CONIC_FOV_LABEL,
    OPTICAL_LABEL,
    RADAR_LABEL,
    RECTANGULAR_FOV_LABEL,
    AdvRadar,
    Optical,
    Radar,
    fieldOfViewFactory,
    sensorFactory,
)


@pytest.fixture(name="fov_conic")
def getConicFoV() -> FieldOfViewConfig:
    """Create a conic FOV config object."""
    return FieldOfViewConfig(fov_shape=CONIC_FOV_LABEL, cone_angle=15.0)


@pytest.fixture(name="fov_rect")
def getRectangularFoV() -> FieldOfViewConfig:
    """Create a rectangular FOV config object."""
    return FieldOfViewConfig(
        fov_shape=RECTANGULAR_FOV_LABEL, azimuth_angle=5.0, elevation_angle=5.0
    )


@pytest.fixture(name="platform_cfg")
def getPlatformConfig(state_cfg: StateConfig) -> PlatformConfig:
    """Create platform config."""
    return PlatformConfig.fromDict({"type": GROUND_FACILITY_LABEL}, state=state_cfg)


@pytest.fixture(name="state_cfg")
def getStateConfig() -> StateConfig:
    """Create state config."""
    return StateConfig.fromDict(
        {
            "type": LLA_LABEL,
            "latitude": 20.0,
            "longitude": -40.0,
            "altitude": 0.5,
        }
    )


@pytest.fixture(name="radar_agent_cfg")
def getRadarAgentConfig(
    platform_cfg: PlatformConfig, state_cfg: StateConfig
) -> SensingAgentConfig:
    """Create valid Radar Sensing Agent config object."""
    sensor_dict = {
        "type": RADAR_LABEL,
        "azimuth_range": [0, 360],
        "elevation_range": (0, 90),
        "covariance": np.eye(4),
        "aperture_area": 10.0,
        "efficiency": 0.95,
        "slew_rate": 180,
        "tx_power": 1.0,
        "tx_frequency": 1.0,
        "min_detectable_power": 1.0,
    }
    return SensingAgentConfig(
        id=20000,
        name="Radar Test Agent",
        platform=platform_cfg,
        state=state_cfg,
        sensor=sensor_dict,
    )


@pytest.fixture(name="adv_radar_agent_cfg")
def getAdvRadarAgentConfig(
    platform_cfg: PlatformConfig, state_cfg: StateConfig
) -> SensingAgentConfig:
    """Create valid Advanced Radar Sensing Agent config object."""
    sensor_dict = {
        "type": ADV_RADAR_LABEL,
        "azimuth_range": [0, 360],
        "elevation_range": (0, 90),
        "covariance": np.eye(4),
        "aperture_area": 10.0,
        "efficiency": 0.95,
        "slew_rate": 10,
        "tx_power": 1.0,
        "tx_frequency": 1.0,
        "min_detectable_power": 1.0,
    }
    return SensingAgentConfig(
        id=20000,
        name="Radar Test Agent",
        platform=platform_cfg,
        state=state_cfg,
        sensor=sensor_dict,
    )


@pytest.fixture(name="optical_agent_cfg")
def getOpticalAgentConfig(
    platform_cfg: PlatformConfig, state_cfg: StateConfig
) -> SensingAgentConfig:
    """Create valid Optical Sensing Agent config object."""
    sensor_dict = {
        "type": OPTICAL_LABEL,
        "azimuth_range": [0, 360],
        "elevation_range": (0, 90),
        "covariance": np.eye(2),
        "aperture_area": 10.0,
        "efficiency": 0.95,
        "slew_rate": 5,
    }
    return SensingAgentConfig(
        id=20000,
        name="Radar Test Agent",
        platform=platform_cfg,
        state=state_cfg,
        sensor=sensor_dict,
    )


def testFOVFactory(fov_conic: FieldOfViewConfig, fov_rect: FieldOfViewConfig) -> None:
    """Test the FOV factory function."""
    assert fieldOfViewFactory(fov_conic)
    assert fieldOfViewFactory(fov_rect)

    bad_fov_config = deepcopy(fov_conic)
    bad_fov_config.fov_shape = "Bad FOV Type"
    err_match = f"wrong FoV shape: {bad_fov_config.fov_shape}"
    with pytest.raises(ValueError, match=err_match):
        fieldOfViewFactory(bad_fov_config)


def testSensorFactory(
    radar_agent_cfg: SensingAgentConfig,
    adv_radar_agent_cfg: SensingAgentConfig,
    optical_agent_cfg: SensingAgentConfig,
) -> None:
    """Test the Sensor factory function."""
    radar_sensor = sensorFactory(radar_agent_cfg.sensor)
    assert isinstance(radar_sensor, Radar)
    adv_radar_sensor = sensorFactory(adv_radar_agent_cfg.sensor)
    assert isinstance(adv_radar_sensor, AdvRadar)
    optical_sensor = sensorFactory(optical_agent_cfg.sensor)
    assert isinstance(optical_sensor, Optical)

    radar_agent_cfg.sensor.type = "Invalid"
    with pytest.raises(ValueError, match=r"Invalid sensor type provided to config: \w+"):
        _ = sensorFactory(radar_agent_cfg.sensor)
