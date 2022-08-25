from __future__ import annotations

# Standard Library Imports
from dataclasses import fields
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.physics.noise import DISCRETE_WHITE_NOISE_LABEL, SIMPLE_NOISE_LABEL
from resonaate.scenario.config.base import ConfigError, ConfigTypeError, ConfigValueError
from resonaate.scenario.config.noise_config import (
    DEFAULT_FILTER_NOISE_MAGNITUDE,
    DEFAULT_POSITION_STD,
    DEFAULT_RANDOM_SEED_VALUE,
    DEFAULT_VELOCITY_STD,
    NoiseConfig,
)

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any


@pytest.fixture(name="noise_cfg_dict")
def getNoiseConfig() -> dict:
    """Generate the default NoiseConfig dictionary."""
    return {
        "init_position_std_km": DEFAULT_POSITION_STD,
        "init_velocity_std_km_p_sec": DEFAULT_VELOCITY_STD,
        "dynamics_noise_type": SIMPLE_NOISE_LABEL,
        "dynamics_noise_magnitude": 1e-20,
        "filter_noise_type": DISCRETE_WHITE_NOISE_LABEL,
        "filter_noise_magnitude": DEFAULT_FILTER_NOISE_MAGNITUDE,
        "random_seed": DEFAULT_RANDOM_SEED_VALUE,
    }


def testCreateNoiseConfig(noise_cfg_dict: dict):
    """Test that NoiseConfig can be created from a dictionary."""
    noise_cfg = NoiseConfig(**noise_cfg_dict)
    assert noise_cfg.CONFIG_LABEL == "noise"
    assert noise_cfg.init_position_std_km == DEFAULT_POSITION_STD
    assert noise_cfg.init_velocity_std_km_p_sec == DEFAULT_VELOCITY_STD
    assert noise_cfg.dynamics_noise_type == SIMPLE_NOISE_LABEL
    assert noise_cfg.dynamics_noise_magnitude == 1e-20
    assert noise_cfg.filter_noise_type == DISCRETE_WHITE_NOISE_LABEL
    assert noise_cfg.filter_noise_magnitude == DEFAULT_FILTER_NOISE_MAGNITUDE
    # Converted to None if set to "os"
    assert noise_cfg.random_seed is None

    # Test that this can be created from an empty dictionary
    noise_cfg = NoiseConfig(**{})
    assert noise_cfg is not None
    for field in fields(NoiseConfig):
        assert field.name in noise_cfg.__dict__
        if field.name == "random_seed":
            assert noise_cfg.random_seed is None
        else:
            assert getattr(noise_cfg, field.name) is not None

    # Ensure the correct amount of req/opt keys
    assert len(NoiseConfig.getRequiredFields()) == 0
    assert len(NoiseConfig.getOptionalFields()) == 7


BAD_RANDOM_SEEDS = (
    ("bad", ConfigValueError),
    (300.0, ConfigTypeError),
    (-20, ConfigValueError),
    (None, ConfigTypeError),
)


@pytest.mark.parametrize(("seed", "err"), BAD_RANDOM_SEEDS)
def testBadRandomSeed(seed: Any, err: ConfigError):
    """Test bad input random_seed values to NoiseConfig."""
    # Random seed must either be an int, the string literal "os", or None
    with pytest.raises(err):
        NoiseConfig(random_seed=seed)


def testBadNoiseType():
    """Test bad input noise type values to NoiseConfig."""
    with pytest.raises(ConfigValueError):
        NoiseConfig(dynamics_noise_type="bad")

    with pytest.raises(ConfigValueError):
        NoiseConfig(filter_noise_type="bad")


def testBadNoiseMagnitude():
    """Test bad input noise type values to NoiseConfig."""
    with pytest.raises(ConfigValueError):
        NoiseConfig(dynamics_noise_magnitude=0.0)

    with pytest.raises(ConfigValueError):
        NoiseConfig(dynamics_noise_magnitude=-10.0)

    with pytest.raises(ConfigValueError):
        NoiseConfig(filter_noise_magnitude=0.0)

    with pytest.raises(ConfigValueError):
        NoiseConfig(filter_noise_magnitude=-15.0)

    with pytest.raises(ConfigValueError):
        NoiseConfig(init_position_std_km=0.0)

    with pytest.raises(ConfigValueError):
        NoiseConfig(init_position_std_km=-15.0)

    with pytest.raises(ConfigValueError):
        NoiseConfig(init_velocity_std_km_p_sec=0.0)

    with pytest.raises(ConfigValueError):
        NoiseConfig(init_velocity_std_km_p_sec=-15.0)
