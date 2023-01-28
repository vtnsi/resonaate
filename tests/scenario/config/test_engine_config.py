from __future__ import annotations

# Standard Library Imports
from copy import copy, deepcopy
from dataclasses import fields
from typing import TYPE_CHECKING
from unittest.mock import patch

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.scenario.config.base import (
    ConfigError,
    ConfigMissingRequiredError,
    ConfigObjectList,
    ConfigValueError,
)
from resonaate.scenario.config.decision_config import DecisionConfig
from resonaate.scenario.config.engine_config import EngineConfig
from resonaate.scenario.config.reward_config import MetricConfig, RewardConfig

if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.scenario.config.agent_config import SensingAgentConfig, TargetAgentConfig


@pytest.fixture(name="engine_cfg_dict")
@patch("resonaate.scenario.config.agent_config.SensingAgentConfig", autospec=True)
@patch("resonaate.scenario.config.agent_config.TargetAgentConfig", autospec=True)
@patch("resonaate.scenario.config.engine_config.DecisionConfig", autospec=True)
@patch("resonaate.scenario.config.engine_config.RewardConfig", autospec=True)
def getEngineConfig(
    reward: RewardConfig,
    decision: DecisionConfig,
    tgt_agent: TargetAgentConfig,
    sen_agent: SensingAgentConfig,
) -> dict:
    """Generate the default EngineConfig dictionary."""
    decision.name = "AllVisibleDecision"
    sen_agent.sensor_type = "adv_radar"
    sen_agent.id = 11111
    return {
        "unique_id": 1,
        "reward": reward,
        "decision": decision,
        "sensors": [sen_agent],
        "targets": [tgt_agent, tgt_agent],
    }


def testCreateEngineConfig(engine_cfg_dict: dict):
    """Test that EngineConfig can be created from a dictionary."""
    cfg = EngineConfig(**engine_cfg_dict)
    assert isinstance(cfg.reward, RewardConfig)
    assert isinstance(cfg.decision, DecisionConfig)
    assert isinstance(cfg.sensors, ConfigObjectList)
    assert isinstance(cfg.targets, ConfigObjectList)
    assert len(cfg.sensors) == 1
    assert len(cfg.targets) == 2

    assert cfg is not None
    for field in fields(EngineConfig):
        assert field.name in cfg.__dict__
        assert getattr(cfg, field.name) is not None

    # Test that this can be created from an empty dictionary
    with pytest.raises(TypeError):
        _ = EngineConfig(**{})

    # Use sub configs as dicts
    cfg_dict = copy(engine_cfg_dict)
    cfg_dict["reward"] = [
        {
            "name": "SimpleSummationReward",
            "metrics": {"name": "FisherInformation"},
        }
    ]
    cfg_dict["decision"] = {"name": "MunkresDecision"}
    cfg = EngineConfig(**cfg_dict)
    assert cfg is not None

    # Ensure the correct amount of req/opt keys
    assert len(EngineConfig.getRequiredFields()) == 5
    assert len(EngineConfig.getOptionalFields()) == 0


def testInputsEngineConfig(engine_cfg_dict: dict):
    """Test bad input values to EngineConfig."""
    cfg_dict = copy(engine_cfg_dict)
    cfg_dict["sensors"] = []
    with pytest.raises(ConfigMissingRequiredError):
        EngineConfig(**cfg_dict)

    cfg_dict = copy(engine_cfg_dict)
    cfg_dict["targets"] = []
    with pytest.raises(ConfigMissingRequiredError):
        EngineConfig(**cfg_dict)

    cfg_dict = copy(engine_cfg_dict)
    cfg_dict["sensors"][0].sensor_type = "Optical"
    with pytest.raises(ConfigError):
        EngineConfig(**cfg_dict)


@pytest.fixture(name="metric_cfg_dict")
def getMetricConfig() -> dict:
    """Generate the default MetricConfig dictionary."""
    return {
        "name": "FisherInformation",
        "parameters": {},
    }


def testCreateMetricConfig(metric_cfg_dict: dict):
    """Test that MetricConfig can be created from a dictionary."""
    cfg = MetricConfig(**metric_cfg_dict)
    assert isinstance(cfg, MetricConfig)
    assert cfg is not None
    assert cfg.name == "FisherInformation"
    assert not cfg.parameters
    assert cfg.parameters is not None

    # Ensure the correct amount of req/opt keys
    assert len(MetricConfig.getRequiredFields()) == 1
    assert len(MetricConfig.getOptionalFields()) == 1


def testBadInputsMetricConfig(metric_cfg_dict: dict):
    """Test bad input values to RewardConfig."""
    cfg_dict = deepcopy(metric_cfg_dict)
    cfg_dict["name"] = "Not a metric"
    with pytest.raises(ConfigValueError):
        MetricConfig(**cfg_dict)


@pytest.fixture(name="reward_cfg_dict")
def getRewardConfig(metric_cfg_dict) -> dict:
    """Generate the default RewardConfig dictionary."""
    return {
        "name": "SimpleSummationReward",
        "metrics": [metric_cfg_dict, {"name": "LyapunovStability"}],
        "parameters": {},
    }


def testCreateRewardConfig(reward_cfg_dict: dict, metric_cfg_dict: dict):
    """Test that RewardConfig can be created from a dictionary."""
    cfg = RewardConfig(**reward_cfg_dict)
    assert cfg.CONFIG_LABEL == "reward"
    assert isinstance(cfg, RewardConfig)
    assert cfg is not None
    assert cfg.name == "SimpleSummationReward"
    assert isinstance(cfg.metrics, ConfigObjectList)
    assert len(cfg.metrics) == 2
    assert cfg.metrics[0] == MetricConfig(**metric_cfg_dict)
    assert cfg.metrics[1] == MetricConfig(**{"name": "LyapunovStability"})
    assert not cfg.parameters
    assert cfg.parameters is not None

    # Ensure the correct amount of req/opt keys
    assert len(RewardConfig.getRequiredFields()) == 2
    assert len(RewardConfig.getOptionalFields()) == 1


def testBadInputsRewardConfig(reward_cfg_dict: dict):
    """Test bad input values to RewardConfig."""
    cfg_dict = deepcopy(reward_cfg_dict)
    cfg_dict["metrics"] = []
    with pytest.raises(ConfigMissingRequiredError):
        RewardConfig(**cfg_dict)

    cfg_dict = deepcopy(reward_cfg_dict)
    cfg_dict["name"] = "Not a reward"
    with pytest.raises(ConfigValueError):
        RewardConfig(**cfg_dict)


@pytest.fixture(name="decision_cfg_dict")
def getDecisionConfig() -> dict:
    """Generate the default DecisionConfig dictionary."""
    return {"name": "MunkresDecision"}


def testCreateDecisionConfig(decision_cfg_dict: dict):
    """Test that DecisionConfig can be created from a dictionary."""
    cfg = DecisionConfig(**decision_cfg_dict)
    assert isinstance(cfg, DecisionConfig)
    assert cfg is not None
    assert cfg.name == "MunkresDecision"
    assert not cfg.parameters
    assert cfg.parameters is not None

    # Ensure the correct amount of req/opt keys
    assert len(DecisionConfig.getRequiredFields()) == 1
    assert len(DecisionConfig.getOptionalFields()) == 1


def testBadInputsDecisionConfig(decision_cfg_dict: dict):
    """Test bad input values to DecisionConfig."""
    cfg_dict = deepcopy(decision_cfg_dict)
    cfg_dict["name"] = "Not a decision"
    with pytest.raises(ConfigValueError):
        DecisionConfig(**cfg_dict)
