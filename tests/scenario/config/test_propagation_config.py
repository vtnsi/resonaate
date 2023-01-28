from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from dataclasses import fields

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.dynamics.constants import RK45_LABEL, SPECIAL_PERTURBATIONS_LABEL
from resonaate.scenario.config.base import ConfigValueError
from resonaate.scenario.config.propagation_config import PropagationConfig


@pytest.fixture(name="propagation_cfg_dict")
def getPropagationConfig() -> dict:
    """Generate the default PropagationConfig dictionary."""
    return {
        "propagation_model": SPECIAL_PERTURBATIONS_LABEL,
        "integration_method": RK45_LABEL,
        "station_keeping": False,
        "target_realtime_propagation": True,
        "sensor_realtime_propagation": True,
        "truth_simulation_only": False,
    }


def testCreatePropagationConfig(propagation_cfg_dict: dict):
    """Test that PropagationConfig can be created from a dictionary."""
    cfg = PropagationConfig(**propagation_cfg_dict)
    assert cfg.CONFIG_LABEL == "propagation"
    assert cfg.propagation_model == SPECIAL_PERTURBATIONS_LABEL
    assert cfg.integration_method == RK45_LABEL
    assert cfg.station_keeping is False
    assert cfg.target_realtime_propagation is True
    assert cfg.sensor_realtime_propagation is True
    assert cfg.truth_simulation_only is False

    # Test that this can be created from an empty dictionary
    cfg = PropagationConfig(**{})
    assert cfg is not None
    for field in fields(PropagationConfig):
        assert field.name in cfg.__dict__
        assert getattr(cfg, field.name) is not None

    # Ensure the correct amount of req/opt keys
    assert len(PropagationConfig.getRequiredFields()) == 0
    assert len(PropagationConfig.getOptionalFields()) == 6


def testInputsPropagationConfig(propagation_cfg_dict: dict):
    """Test bad input values to PropagationConfig."""
    cfg_dict = deepcopy(propagation_cfg_dict)
    cfg_dict["propagation_model"] = "bad"
    with pytest.raises(ConfigValueError):
        PropagationConfig(**cfg_dict)

    cfg_dict = deepcopy(propagation_cfg_dict)
    cfg_dict["integration_method"] = "bad"
    with pytest.raises(ConfigValueError):
        PropagationConfig(**cfg_dict)
