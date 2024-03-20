from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from dataclasses import fields

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.scenario.config.base import ConfigValueError
from resonaate.scenario.config.geopotential_config import (
    DEFAULT_GRAVITY_DEGREE,
    DEFAULT_GRAVITY_MODEL,
    DEFAULT_GRAVITY_ORDER,
    GeopotentialConfig,
)


@pytest.fixture(name="geopotential_cfg_dict")
def getGeopotentialConfig() -> dict:
    """Generate the default GeopotentialConfig dictionary."""
    return {
        "model": DEFAULT_GRAVITY_MODEL,
        "degree": DEFAULT_GRAVITY_DEGREE,
        "order": DEFAULT_GRAVITY_ORDER,
    }


def testCreateGeopotentialConfig(geopotential_cfg_dict: dict):
    """Test that GeopotentialConfig can be created from a dictionary."""
    cfg = GeopotentialConfig(**geopotential_cfg_dict)
    assert cfg.CONFIG_LABEL == "geopotential"
    assert cfg.model == DEFAULT_GRAVITY_MODEL
    assert cfg.degree == DEFAULT_GRAVITY_DEGREE
    assert cfg.order == DEFAULT_GRAVITY_ORDER

    # Test that this can be created from an empty dictionary
    cfg = GeopotentialConfig()
    assert cfg is not None
    for field in fields(GeopotentialConfig):
        assert field.name in cfg.__dict__
        assert getattr(cfg, field.name) is not None

    # Ensure the correct amount of req/opt keys
    assert len(GeopotentialConfig.getRequiredFields()) == 0
    assert len(GeopotentialConfig.getOptionalFields()) == 3


def testInputsGeopotentialConfig(geopotential_cfg_dict: dict):
    """Test bad input values to GeopotentialConfig."""
    cfg_dict = deepcopy(geopotential_cfg_dict)
    cfg_dict["model"] = "bad"
    with pytest.raises(ConfigValueError):
        GeopotentialConfig(**cfg_dict)

    cfg_dict = deepcopy(geopotential_cfg_dict)
    cfg_dict["degree"] = -1
    with pytest.raises(ConfigValueError):
        GeopotentialConfig(**cfg_dict)

    cfg_dict = deepcopy(geopotential_cfg_dict)
    cfg_dict["degree"] = 1000
    with pytest.raises(ConfigValueError):
        GeopotentialConfig(**cfg_dict)

    cfg_dict = deepcopy(geopotential_cfg_dict)
    cfg_dict["order"] = -1
    with pytest.raises(ConfigValueError):
        GeopotentialConfig(**cfg_dict)

    cfg_dict = deepcopy(geopotential_cfg_dict)
    cfg_dict["order"] = 1000
    with pytest.raises(ConfigValueError):
        GeopotentialConfig(**cfg_dict)
