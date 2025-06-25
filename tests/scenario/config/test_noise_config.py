from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.common.labels import NoiseLabel
from resonaate.scenario.config.noise_config import DEFAULT_RANDOM_SEED_VALUE, NoiseConfig

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any


@pytest.fixture(name="noise_cfg_dict")
def getNoiseConfig() -> dict:
    """Generate the default NoiseConfig dictionary."""
    return {
        "init_position_std_km": NoiseConfig.DEFAULT_POS_STD,
        "init_velocity_std_km_p_sec": NoiseConfig.DEFAULT_VEL_STD,
        "filter_noise_type": NoiseLabel.CONTINUOUS_WHITE_NOISE,
        "filter_noise_magnitude": NoiseConfig.DEFAULT_NOISE_MAG,
        "random_seed": DEFAULT_RANDOM_SEED_VALUE,
    }


def testCreateNoiseConfig(noise_cfg_dict: dict):
    """Test that NoiseConfig can be created from a dictionary."""
    noise_cfg = NoiseConfig(**noise_cfg_dict)

    assert noise_cfg.init_position_std_km == NoiseConfig.DEFAULT_POS_STD
    assert noise_cfg.init_velocity_std_km_p_sec == NoiseConfig.DEFAULT_VEL_STD
    assert noise_cfg.filter_noise_type == NoiseLabel.CONTINUOUS_WHITE_NOISE
    assert noise_cfg.filter_noise_magnitude == NoiseConfig.DEFAULT_NOISE_MAG
    # Converted to None if set to "os"
    assert noise_cfg.random_seed is None

    # Test that this can be created from an empty dictionary
    noise_cfg = NoiseConfig()
    assert noise_cfg is not None
    assert noise_cfg.init_position_std_km == NoiseConfig.DEFAULT_POS_STD
    assert noise_cfg.init_velocity_std_km_p_sec == NoiseConfig.DEFAULT_VEL_STD
    assert noise_cfg.filter_noise_type == NoiseLabel.CONTINUOUS_WHITE_NOISE
    assert noise_cfg.filter_noise_magnitude == NoiseConfig.DEFAULT_NOISE_MAG
    assert noise_cfg.random_seed is None


@pytest.mark.parametrize("seed", ["bad", 300.2, -20])
def testBadRandomSeed(seed: Any):
    """Test bad input random_seed values to NoiseConfig."""
    # Random seed must either be an int, the string literal "os", or None
    with pytest.raises(ValidationError):
        NoiseConfig(random_seed=seed)


def testBadNoiseType():
    """Test bad input noise type values to NoiseConfig."""
    with pytest.raises(ValidationError):
        NoiseConfig(filter_noise_type="bad")


def testBadNoiseMagnitude():
    """Test bad input noise type values to NoiseConfig."""
    with pytest.raises(ValidationError):
        NoiseConfig(filter_noise_magnitude=0.0)

    with pytest.raises(ValidationError):
        NoiseConfig(filter_noise_magnitude=-15.0)

    with pytest.raises(ValidationError):
        NoiseConfig(init_position_std_km=0.0)

    with pytest.raises(ValidationError):
        NoiseConfig(init_position_std_km=-15.0)

    with pytest.raises(ValidationError):
        NoiseConfig(init_velocity_std_km_p_sec=0.0)

    with pytest.raises(ValidationError):
        NoiseConfig(init_velocity_std_km_p_sec=-15.0)
