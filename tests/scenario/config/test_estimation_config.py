from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from dataclasses import fields
from unittest.mock import patch

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.labels import DynamicsLabel, InitialOrbitDeterminationLabel, StackingLabel
from resonaate.estimation import VALID_MANEUVER_DETECTION_LABELS
from resonaate.scenario.config.base import ConfigValueError
from resonaate.scenario.config.estimation_config import (
    DEFAULT_IOD_OBSERVATION_SPACING,
    DEFAULT_MANEUVER_DETECTION_THRESHOLD,
    DEFAULT_MODEL_TIME_INTERVAL,
    DEFAULT_OBSERVATION_WINDOW,
    DEFAULT_PRUNE_PERCENTAGE,
    DEFAULT_PRUNE_THRESHOLD,
    AdaptiveEstimationConfig,
    EstimationConfig,
    InitialOrbitDeterminationConfig,
    ManeuverDetectionConfig,
    SequentialFilterConfig,
)


@pytest.fixture(name="estimation_cfg_dict")
@patch("resonaate.scenario.config.estimation_config.SequentialFilterConfig", autospec=True)
@patch("resonaate.scenario.config.estimation_config.AdaptiveEstimationConfig", autospec=True)
@patch(
    "resonaate.scenario.config.estimation_config.InitialOrbitDeterminationConfig",
    autospec=True,
)
def getEstimationConfig(
    initial_orbit_determination: InitialOrbitDeterminationConfig,
    adaptive_filter: AdaptiveEstimationConfig,
    seq_filter: SequentialFilterConfig,
) -> dict:
    """Generate the default EstimationConfig dictionary."""
    return {
        "sequential_filter": seq_filter,
        "adaptive_filter": adaptive_filter,
        "initial_orbit_determination": initial_orbit_determination,
    }


def testCreateEstimationConfig(estimation_cfg_dict: dict):
    """Test that EstimationConfig can be created from a dictionary."""
    cfg = EstimationConfig(**estimation_cfg_dict)
    assert cfg.CONFIG_LABEL == "estimation"
    assert isinstance(cfg.sequential_filter, SequentialFilterConfig)
    assert isinstance(cfg.adaptive_filter, AdaptiveEstimationConfig)
    assert isinstance(cfg.initial_orbit_determination, InitialOrbitDeterminationConfig)

    for field in fields(EstimationConfig):
        assert field.name in cfg.__dict__
        assert getattr(cfg, field.name) is not None

    # Cannot be created from empty dictionary
    with pytest.raises(TypeError):
        _ = EstimationConfig()

    # Use sub configs as dicts
    cfg_dict = {"sequential_filter": {"name": "ukf"}}
    cfg = EstimationConfig(**cfg_dict)
    assert cfg is not None
    assert isinstance(cfg.sequential_filter, SequentialFilterConfig)
    assert cfg.adaptive_filter is None

    cfg_dict["adaptive_filter"] = {"name": "smm"}
    cfg = EstimationConfig(**cfg_dict)
    assert cfg is not None
    assert isinstance(cfg.adaptive_filter, AdaptiveEstimationConfig)

    cfg_dict["initial_orbit_determination"] = {"name": "lambert_universal"}
    cfg = EstimationConfig(**cfg_dict)
    assert cfg is not None
    assert isinstance(cfg.initial_orbit_determination, InitialOrbitDeterminationConfig)

    # Ensure the correct amount of req/opt keys
    assert len(EstimationConfig.getRequiredFields()) == 1
    assert len(EstimationConfig.getOptionalFields()) == 2


@pytest.fixture(name="sequential_filter_cfg_dict")
def getSequentialFilterConfig() -> dict:
    """Generate the default SequentialFilterConfig dictionary."""
    return {
        "name": "ukf",
        "dynamics_model": DynamicsLabel.SPECIAL_PERTURBATIONS,
        "maneuver_detection": None,
        "adaptive_estimation": False,
        "parameters": {},
    }


def testCreateSequentialFilterConfig(sequential_filter_cfg_dict: dict):
    """Test that SequentialFilterConfig can be created from a dictionary."""
    cfg = SequentialFilterConfig(**sequential_filter_cfg_dict)
    assert cfg.CONFIG_LABEL == "sequential_filter"
    assert cfg.name == "ukf"
    assert cfg.dynamics_model == DynamicsLabel.SPECIAL_PERTURBATIONS
    assert cfg.maneuver_detection is None
    assert cfg.adaptive_estimation is False
    assert cfg.initial_orbit_determination is False
    assert not cfg.parameters
    assert cfg.parameters is not None

    for field in fields(SequentialFilterConfig):
        assert field.name in cfg.__dict__
        if field.name == "maneuver_detection":
            continue
        assert getattr(cfg, field.name) is not None

    # Cannot be created from empty dictionary
    with pytest.raises(TypeError):
        _ = SequentialFilterConfig()

    # Use sub configs as dicts
    cfg_dict = deepcopy(sequential_filter_cfg_dict)
    cfg_dict["maneuver_detection"] = {"name": VALID_MANEUVER_DETECTION_LABELS[0]}
    cfg = SequentialFilterConfig(**cfg_dict)
    assert cfg.maneuver_detection is not None
    assert cfg.adaptive_estimation is False

    # Ensure the correct amount of req/opt keys
    assert len(SequentialFilterConfig.getRequiredFields()) == 1
    assert len(SequentialFilterConfig.getOptionalFields()) == 5


def testBadInputsSequentialFilterConfig(sequential_filter_cfg_dict: dict):
    """Test that SequentialFilterConfig cannot be created from bad inputs."""
    cfg_dict = deepcopy(sequential_filter_cfg_dict)
    cfg_dict["name"] = "invalid"
    with pytest.raises(ConfigValueError):
        _ = SequentialFilterConfig(**cfg_dict)

    cfg_dict = deepcopy(sequential_filter_cfg_dict)
    cfg_dict["dynamics_model"] = "invalid"
    with pytest.raises(ConfigValueError):
        _ = SequentialFilterConfig(**cfg_dict)


@pytest.fixture(name="maneuver_detection_cfg_dict")
def getManeuverDetectionConfig() -> dict:
    """Generate the default ManeuverDetectionConfig dictionary."""
    return {
        "name": "sliding_nis",
        "threshold": DEFAULT_MANEUVER_DETECTION_THRESHOLD,
        "parameters": {},
    }


def testCreateManeuverDetectionConfig(maneuver_detection_cfg_dict: dict):
    """Test that ManeuverDetectionConfig can be created from a dictionary."""
    cfg = ManeuverDetectionConfig(**maneuver_detection_cfg_dict)
    assert cfg.CONFIG_LABEL == "maneuver_detection"
    assert cfg.name == "sliding_nis"
    assert cfg.threshold == DEFAULT_MANEUVER_DETECTION_THRESHOLD
    assert not cfg.parameters
    assert cfg.parameters is not None

    for field in fields(ManeuverDetectionConfig):
        assert field.name in cfg.__dict__
        assert getattr(cfg, field.name) is not None

    # Cannot be created from empty dictionary
    with pytest.raises(TypeError):
        _ = ManeuverDetectionConfig()

    # Ensure the correct amount of req/opt keys
    assert len(ManeuverDetectionConfig.getRequiredFields()) == 1
    assert len(ManeuverDetectionConfig.getOptionalFields()) == 2


def testBadInputsManeuverDetectionConfig(maneuver_detection_cfg_dict: dict):
    """Test that ManeuverDetectionConfig cannot be created from bad inputs."""
    cfg_dict = deepcopy(maneuver_detection_cfg_dict)
    cfg_dict["name"] = "invalid"
    with pytest.raises(ConfigValueError):
        _ = ManeuverDetectionConfig(**cfg_dict)

    cfg_dict = deepcopy(maneuver_detection_cfg_dict)
    cfg_dict["threshold"] = -1.0
    with pytest.raises(ConfigValueError):
        _ = ManeuverDetectionConfig(**cfg_dict)

    cfg_dict = deepcopy(maneuver_detection_cfg_dict)
    cfg_dict["threshold"] = 1.0
    with pytest.raises(ConfigValueError):
        _ = ManeuverDetectionConfig(**cfg_dict)

    cfg_dict = deepcopy(maneuver_detection_cfg_dict)
    cfg_dict["threshold"] = 0.0
    with pytest.raises(ConfigValueError):
        _ = ManeuverDetectionConfig(**cfg_dict)

    cfg_dict = deepcopy(maneuver_detection_cfg_dict)
    cfg_dict["threshold"] = 2.0
    with pytest.raises(ConfigValueError):
        _ = ManeuverDetectionConfig(**cfg_dict)


@pytest.fixture(name="adaptive_estimation_cfg_dict")
def getAdaptiveEstimationConfig() -> dict:
    """Generate the default AdaptiveEstimationConfig dictionary."""
    return {
        "name": "smm",
        "orbit_determination": InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL,
        "stacking_method": StackingLabel.ECI_STACKING,
        "model_interval": DEFAULT_MODEL_TIME_INTERVAL,
        "observation_window": DEFAULT_OBSERVATION_WINDOW,
        "prune_threshold": DEFAULT_PRUNE_THRESHOLD,
        "prune_percentage": DEFAULT_PRUNE_PERCENTAGE,
        "parameters": {},
    }


def testCreateAdaptiveEstimationConfig(adaptive_estimation_cfg_dict: dict):
    """Test that AdaptiveEstimationConfig can be created from a dictionary."""
    cfg = AdaptiveEstimationConfig(**adaptive_estimation_cfg_dict)
    assert cfg.CONFIG_LABEL == "adaptive_filter"
    assert cfg.name == "smm"
    assert cfg.orbit_determination == InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL
    assert cfg.stacking_method == StackingLabel.ECI_STACKING
    assert cfg.model_interval == DEFAULT_MODEL_TIME_INTERVAL
    assert cfg.observation_window == DEFAULT_OBSERVATION_WINDOW
    assert cfg.prune_threshold == DEFAULT_PRUNE_THRESHOLD
    assert cfg.prune_percentage == DEFAULT_PRUNE_PERCENTAGE
    assert not cfg.parameters
    assert cfg.parameters is not None

    for field in fields(AdaptiveEstimationConfig):
        assert field.name in cfg.__dict__
        assert getattr(cfg, field.name) is not None

    # Cannot be created from empty dictionary
    with pytest.raises(TypeError):
        _ = AdaptiveEstimationConfig()

    # Ensure the correct amount of req/opt keys
    assert len(AdaptiveEstimationConfig.getRequiredFields()) == 1
    assert len(AdaptiveEstimationConfig.getOptionalFields()) == 7


def testBadInputsAdaptiveEstimationConfig(adaptive_estimation_cfg_dict: dict):
    """Test that AdaptiveEstimationConfig cannot be created from bad inputs."""
    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["name"] = "invalid"
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["orbit_determination"] = "invalid"
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["stacking_method"] = "invalid"
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["model_interval"] = -1
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["model_interval"] = 0
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["observation_window"] = -1
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["observation_window"] = 0
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["observation_window"] = -1
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["prune_threshold"] = 0.0
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["prune_threshold"] = -1.0
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["prune_threshold"] = 1.0
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["prune_threshold"] = 2.0
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["prune_percentage"] = 0.0
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["prune_percentage"] = -1.0
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["prune_percentage"] = 1.0
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)

    cfg_dict = deepcopy(adaptive_estimation_cfg_dict)
    cfg_dict["prune_percentage"] = 2.0
    with pytest.raises(ConfigValueError):
        _ = AdaptiveEstimationConfig(**cfg_dict)


@pytest.fixture(name="initial_orbit_determination_cfg_dict")
def getInitialOrbitDeterminationConfig() -> dict:
    """Generate the default InitialOrbitDeterminationConfig dictionary."""
    return {
        "name": InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL,
        "minimum_observation_spacing": DEFAULT_IOD_OBSERVATION_SPACING,
    }


def testCreateInitialOrbitDeterminationConfig(initial_orbit_determination_cfg_dict: dict):
    """Test that InitialOrbitDeterminationConfig can be created from a dictionary."""
    cfg = InitialOrbitDeterminationConfig(**initial_orbit_determination_cfg_dict)
    assert cfg.CONFIG_LABEL == "initial_orbit_determination"
    assert cfg.name == InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL
    assert cfg.minimum_observation_spacing == DEFAULT_IOD_OBSERVATION_SPACING

    for field in fields(InitialOrbitDeterminationConfig):
        assert field.name in cfg.__dict__
        assert getattr(cfg, field.name) is not None

    # Can be created from empty dictionary
    _ = InitialOrbitDeterminationConfig()

    # Ensure the correct amount of req/opt keys
    assert len(InitialOrbitDeterminationConfig.getRequiredFields()) == 0
    assert len(InitialOrbitDeterminationConfig.getOptionalFields()) == 2


def testBadInputsInitialOrbitDeterminationConfig(initial_orbit_determination_cfg_dict: dict):
    """Test that InitialOrbitDeterminationConfig cannot be created from bad inputs."""
    cfg_dict = deepcopy(initial_orbit_determination_cfg_dict)
    cfg_dict["name"] = "invalid"
    with pytest.raises(ConfigValueError):
        _ = InitialOrbitDeterminationConfig(**cfg_dict)

    cfg_dict = deepcopy(initial_orbit_determination_cfg_dict)
    cfg_dict["minimum_observation_spacing"] = -1
    with pytest.raises(ConfigValueError):
        _ = InitialOrbitDeterminationConfig(**cfg_dict)

    cfg_dict = deepcopy(initial_orbit_determination_cfg_dict)
    cfg_dict["minimum_observation_spacing"] = 0
    with pytest.raises(ConfigValueError):
        _ = InitialOrbitDeterminationConfig(**cfg_dict)
