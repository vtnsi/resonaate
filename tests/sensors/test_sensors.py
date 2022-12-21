from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents import GROUND_FACILITY_LABEL
from resonaate.physics.constants import PI
from resonaate.scenario.config.agent_configs import FieldOfViewConfig, SensingAgentConfig
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


@pytest.fixture(name="radar_agent_cfg")
def getRadarAgentConfig() -> SensingAgentConfig:
    """Create valid Radar Sensing Agent config object."""
    return SensingAgentConfig(
        id=20000,
        name="Radar Test Agent",
        host_type=GROUND_FACILITY_LABEL,
        sensor_type=RADAR_LABEL,
        azimuth_range=[0, 2 * PI],
        elevation_range=(0, PI * 0.5),
        covariance=np.eye(4),
        aperture_area=10.0,
        efficiency=0.95,
        slew_rate=PI / 180,
        lat=20.0,
        lon=-40.0,
        alt=0.5,
        tx_power=1.0,
        tx_frequency=1.0,
        min_detectable_power=1.0,
    )


@pytest.fixture(name="adv_radar_agent_cfg")
def getAdvRadarAgentConfig() -> SensingAgentConfig:
    """Create valid Advanced Radar Sensing Agent config object."""
    return SensingAgentConfig(
        id=20000,
        name="Radar Test Agent",
        host_type=GROUND_FACILITY_LABEL,
        sensor_type=ADV_RADAR_LABEL,
        azimuth_range=[0, 2 * PI],
        elevation_range=(0, PI * 0.5),
        covariance=np.eye(4),
        aperture_area=10.0,
        efficiency=0.95,
        slew_rate=PI / 180,
        lat=20.0,
        lon=-40.0,
        alt=0.5,
        tx_power=1.0,
        tx_frequency=1.0,
        min_detectable_power=1.0,
    )


@pytest.fixture(name="optical_agent_cfg")
def getOpticalAgentConfig() -> SensingAgentConfig:
    """Create valid Optical Sensing Agent config object."""
    return SensingAgentConfig(
        id=20000,
        name="Radar Test Agent",
        host_type=GROUND_FACILITY_LABEL,
        sensor_type=OPTICAL_LABEL,
        azimuth_range=[0, 2 * PI],
        elevation_range=(0, PI * 0.5),
        covariance=np.eye(2),
        aperture_area=10.0,
        efficiency=0.95,
        slew_rate=PI / 180,
        lat=20.0,
        lon=-40.0,
        alt=0.5,
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
    radar_sensor = sensorFactory(radar_agent_cfg)
    assert isinstance(radar_sensor, Radar)
    adv_radar_sensor = sensorFactory(adv_radar_agent_cfg)
    assert isinstance(adv_radar_sensor, AdvRadar)
    optical_sensor = sensorFactory(optical_agent_cfg)
    assert isinstance(optical_sensor, Optical)

    radar_agent_cfg.sensor_type = "Invalid"
    with pytest.raises(ValueError, match=r"Invalid sensor type provided to config: \w+"):
        _ = sensorFactory(radar_agent_cfg)
