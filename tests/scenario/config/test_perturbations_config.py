from __future__ import annotations

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.scenario.config.perturbations_config import PerturbationsConfig, ThirdBody

THIRD_BODIES = [it.value for it in ThirdBody]


@pytest.fixture(name="perturbations_cfg_dict")
def getPerturbationsConfig() -> dict:
    """Generate the default PerturbationsConfig dictionary."""
    return {
        "third_bodies": THIRD_BODIES,
        "solar_radiation_pressure": True,
        "general_relativity": True,
    }


def testCreatePerturbationsConfig(perturbations_cfg_dict: dict):
    """Test that PerturbationsConfig can be created from a dictionary."""
    cfg = PerturbationsConfig(**perturbations_cfg_dict)
    assert cfg.third_bodies == THIRD_BODIES
    assert cfg.solar_radiation_pressure is True
    assert cfg.solar_radiation_pressure is True

    # Test that this can be created from an empty dictionary
    cfg = PerturbationsConfig()
    assert cfg is not None
    assert not cfg.third_bodies
    assert cfg.solar_radiation_pressure is False
    assert cfg.solar_radiation_pressure is False


def testInputsPerturbationsConfig(perturbations_cfg_dict: dict):
    """Test bad input values to PerturbationsConfig."""
    perturbations_cfg_dict["third_bodies"] = ["sun", "bad"]
    with pytest.raises(ValidationError):
        PerturbationsConfig(**perturbations_cfg_dict)
