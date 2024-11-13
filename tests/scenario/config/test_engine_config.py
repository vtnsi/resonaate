from __future__ import annotations

# Standard Library Imports
from itertools import combinations
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from pydantic import TypeAdapter, ValidationError

# RESONAATE Imports
from resonaate.scenario.config.decision_config import DecisionConfig, DecisionLabel
from resonaate.scenario.config.engine_config import EngineConfig
from resonaate.scenario.config.reward_config import (
    MetricConfig,
    MetricLabel,
    RewardConfig,
    RewardLabel,
)

# Local Imports
from . import EARTH_SENSORS, LEO_TARGETS

if TYPE_CHECKING:
    # RESONAATE Imports
    pass


VALID_REWARD_CONFIGS: tuple[RewardConfig] = RewardConfig.__args__[0].__args__
"""Tuple of valid :class:`.RewardConfig` classes."""

VALID_DECISION_CONFIGS: tuple[DecisionConfig] = DecisionConfig.__args__[0].__args__
"""Tuple of valid :class:`.DecisionConfig` classes."""


MetricConfigValidator = TypeAdapter(MetricConfig)
"""TypeAdapter: Helper class to validate :class:`.MetricConfig` specification."""


RewardConfigValidator = TypeAdapter(RewardConfig)
"""TypeAdapter: Helper class to validate :class:`.RewardConfig` specification."""


DecisionConfigValidator = TypeAdapter(DecisionConfig)
"""TypeAdapter: Helper class to validate :class:`.DecisionConfig` specification."""


def getMetricDict(metric_name: MetricLabel):
    """Wrap `metric_name` in the dictionary format for a :class:`.MetricConfig`."""
    return {"name": metric_name}


@pytest.fixture(name="metrics_configs")
def getMetricsConfig(request: list[MetricLabel]):
    """Fixture that gets indirectly populated with metric configurations."""
    return [getMetricDict(_name) for _name in request.param]


@pytest.fixture(name="reward_cfg_dict")
def getRewardConfig() -> dict:
    """Return a simple reward configuration dictionary."""
    return {
        "name": RewardLabel.SIMPLE_SUM,
        "metrics": [
            getMetricDict(MetricLabel.SHANNON_INFO),
            getMetricDict(MetricLabel.TIME_SINCE_OBS),
        ],
    }


def getDecisionDict(decision_name: DecisionLabel) -> dict:
    """Wrap `decision_name` in the dictionary format for a :class:`.DecisionConfig`."""
    return {"name": decision_name}


@pytest.fixture(name="decision_cfg_dict")
def getDecisionConfig() -> dict:
    """Return a simple decision configuration dictionary."""
    return getDecisionDict(DecisionLabel.MUNKRES)


@pytest.fixture(name="engine_cfg_dict")
def getEngineConfig(reward_cfg_dict: dict, decision_cfg_dict: dict) -> dict:
    """Return a simple engine configuration dictionary."""
    return {
        "unique_id": 1,
        "reward": reward_cfg_dict,
        "decision": decision_cfg_dict,
        "sensors": EARTH_SENSORS,
        "targets": LEO_TARGETS,
    }


@pytest.mark.parametrize("metric_label", list(MetricLabel))
def testMetricConfigs(metric_label: MetricLabel):
    """Validate that all metrics have valid configurations."""
    MetricConfigValidator.validate_python(getMetricDict(metric_label))


@pytest.mark.parametrize("metric_input", ["not a metric", 123, None])
def testBadMetricInput(metric_input):
    """Validate that various bad metric inputs throw a validation error."""
    with pytest.raises(ValidationError):
        MetricConfigValidator.validate_python(getMetricDict(metric_input))


@pytest.mark.parametrize("reward_label", list(RewardLabel))
@pytest.mark.parametrize(
    "metrics_configs",
    combinations(list(MetricLabel), 2),
    indirect=True,
)
def testRewardConfig(reward_label, metrics_configs):
    """Validate that many combinations of metrics within reward configurations are valid."""
    reward_config_dict = {
        "name": reward_label.value,
        "metrics": metrics_configs,
    }
    RewardConfigValidator.validate_python(reward_config_dict)


@pytest.mark.parametrize("reward_input", ["not a reward", 123, None])
def testBadRewardInput(reward_cfg_dict: dict, reward_input):
    """Validate that various bad reward inputs throw a validation error."""
    reward_cfg_dict["name"] = reward_input
    with pytest.raises(ValidationError):
        RewardConfigValidator.validate_python(reward_cfg_dict)


def testMissingMetrics(reward_cfg_dict: dict):
    """Validate that a reward configuration that's missing metrics throws a validation error."""
    reward_cfg_dict["metrics"] = []
    with pytest.raises(ValidationError):
        RewardConfigValidator.validate_python(reward_cfg_dict)


@pytest.mark.parametrize("decision_label", list(DecisionLabel))
def testDecisionConfigs(decision_label: DecisionLabel):
    """Validate that all decisions have valid configurations."""
    DecisionConfigValidator.validate_python(getDecisionDict(decision_label))


@pytest.mark.parametrize("decision_input", ["not a decision", 123, None])
def testBadDecisionInput(decision_input):
    """Validate that various bad decision inputs throw a validation error."""
    with pytest.raises(ValidationError):
        DecisionConfigValidator.validate_python(getDecisionDict(decision_input))


def testEmptyEngineConfig():
    """Test that EngineConfig throws a validation error if no arguments are specified."""
    with pytest.raises(ValidationError):
        _ = EngineConfig()


def testCreateEngineConfig(engine_cfg_dict: dict):
    """Test that EngineConfig can be created from a valid dictionary."""
    cfg = EngineConfig(**engine_cfg_dict)
    assert isinstance(cfg.reward, VALID_REWARD_CONFIGS)
    assert isinstance(cfg.decision, VALID_DECISION_CONFIGS)
    assert len(cfg.targets) == len(engine_cfg_dict["targets"])
    assert len(cfg.sensors) == len(engine_cfg_dict["sensors"])


def testMissingSensors(engine_cfg_dict: dict):
    """Test that EngineConfig throws a validation error if no sensors are specified."""
    engine_cfg_dict["sensors"] = []
    with pytest.raises(ValidationError):
        EngineConfig(**engine_cfg_dict)


def testMissingTargets(engine_cfg_dict: dict):
    """Test that EngineConfig throws a validation error if no targets are specified."""
    engine_cfg_dict["targets"] = []
    with pytest.raises(ValidationError):
        EngineConfig(**engine_cfg_dict)
