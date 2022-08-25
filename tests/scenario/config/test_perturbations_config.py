from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from dataclasses import fields

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.scenario.config.base import ConfigValueError
from resonaate.scenario.config.perturbations_config import (
    SUPPORTED_THIRD_BODIES,
    PerturbationsConfig,
)


@pytest.fixture(name="perturbations_cfg_dict")
def getPerturbationsConfig() -> dict:
    """Generate the default PerturbationsConfig dictionary."""
    return {
        "third_bodies": SUPPORTED_THIRD_BODIES,
        "solar_radiation_pressure": True,
        "general_relativity": True,
    }


def testCreatePerturbationsConfig(perturbations_cfg_dict: dict):
    """Test that PerturbationsConfig can be created from a dictionary."""
    cfg = PerturbationsConfig(**perturbations_cfg_dict)
    assert cfg.CONFIG_LABEL == "perturbations"
    assert cfg.third_bodies == SUPPORTED_THIRD_BODIES
    assert cfg.solar_radiation_pressure is True
    assert cfg.solar_radiation_pressure is True

    # Test that this can be created from an empty dictionary
    cfg = PerturbationsConfig(**{})
    assert cfg is not None
    for field in fields(PerturbationsConfig):
        assert field.name in cfg.__dict__
        assert getattr(cfg, field.name) is not None

    assert not cfg.third_bodies
    assert cfg.solar_radiation_pressure is False
    assert cfg.solar_radiation_pressure is False

    # Ensure the correct amount of req/opt keys
    assert len(PerturbationsConfig.getRequiredFields()) == 0
    assert len(PerturbationsConfig.getOptionalFields()) == 3


def testInputsPerturbationsConfig(perturbations_cfg_dict: dict):
    """Test bad input values to PerturbationsConfig."""
    cfg_dict = deepcopy(perturbations_cfg_dict)
    cfg_dict["third_bodies"] = ["sun", "bad"]
    with pytest.raises(ConfigValueError):
        PerturbationsConfig(**cfg_dict)
