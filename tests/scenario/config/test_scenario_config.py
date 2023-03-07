from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.scenario.config import ScenarioConfig

# Local Imports
from ... import FIXTURE_DATA_DIR, JSON_INIT_PATH

# Type Checking Imports
if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.scenario.config import (
        EngineConfig,
        EstimationConfig,
        EventConfigList,
        GeopotentialConfig,
        NoiseConfig,
        ObservationConfig,
        PerturbationsConfig,
        PropagationConfig,
        TimeConfig,
    )


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testParseConfigFile(datafiles: str):
    """Test parsing a valid config file."""
    # Pass a valid config file, ensure no errors are raised
    test_init_file = Path(str(datafiles)) / JSON_INIT_PATH / "test_init.json"
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(test_init_file)
    assert scenario_cfg_dict is not None
    assert "engines_files" not in scenario_cfg_dict
    assert "targets_file" not in scenario_cfg_dict
    assert "sensors_file" not in scenario_cfg_dict
    for field in fields(ScenarioConfig):
        assert field.name in scenario_cfg_dict
        assert scenario_cfg_dict[field.name] is not None


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testFromConfigFile(datafiles: str):
    """Test alt constructor from valid config file."""
    # Pass a valid config file, ensure no errors are raised
    test_init_file = Path(str(datafiles)) / JSON_INIT_PATH / "test_init.json"
    scenario_cfg = ScenarioConfig.fromConfigFile(test_init_file)
    assert scenario_cfg is not None
    for field in fields(ScenarioConfig):
        assert field.name in dir(scenario_cfg)
        assert getattr(scenario_cfg, field.name) is not None


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testInvalidConfigFile(datafiles: str):
    """Test passing invalid, empty config dict."""
    bad_file = Path(str(datafiles)) / JSON_INIT_PATH / "bad_init.json"
    with pytest.raises(FileNotFoundError):
        ScenarioConfig.parseConfigFile(bad_file)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
@pytest.mark.parametrize("remove", ScenarioConfig.getRequiredFields())
def testRequiredSection(datafiles: str, remove: str):
    """Test removing each required sections in config."""
    test_init_file = Path(str(datafiles)) / JSON_INIT_PATH / "test_init.json"
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(test_init_file)
    # Remove required key from the config dict
    del scenario_cfg_dict[remove]
    # Ensure a ConfigMissingRequiredError is raised
    with pytest.raises(TypeError):
        ScenarioConfig(**scenario_cfg_dict)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
@pytest.mark.parametrize("remove", ScenarioConfig.getOptionalFields())
def testOptionalSection(datafiles: str, remove: str):
    """Test removing each optional sections in config."""
    test_init_file = Path(str(datafiles)) / JSON_INIT_PATH / "test_init.json"
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(test_init_file)
    # Remove required key from the config dict
    if scenario_cfg_dict.get(remove):
        del scenario_cfg_dict[remove]
    # Ensure a valid section was added
    ScenarioConfig(**scenario_cfg_dict)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
@pytest.mark.parametrize("remove", ScenarioConfig.getRequiredFields())
def testRequiredFields(datafiles: str, remove: str):
    """Test removing required fields in each config section."""
    test_init_file = Path(str(datafiles)) / JSON_INIT_PATH / "test_init.json"
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(test_init_file)
    section = getattr(ScenarioConfig(**scenario_cfg_dict), remove)
    for field in fields(section):
        if field in section.getRequiredFields():
            temp_config = deepcopy(scenario_cfg_dict)
            del temp_config[section.config_label][field.config_label]
            with pytest.raises(TypeError):
                ScenarioConfig(**temp_config)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
@pytest.mark.parametrize("remove", ScenarioConfig.getOptionalFields())
def testOptionalFields(datafiles: str, remove: str):
    """Test removing optional fields in each config section."""
    test_init_file = Path(str(datafiles)) / JSON_INIT_PATH / "test_init.json"
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(test_init_file)
    section = getattr(ScenarioConfig(**scenario_cfg_dict), remove)
    for field in fields(section):
        if field in section.getOptionalFields():
            temp_config = deepcopy(scenario_cfg_dict)
            if temp_config.get(remove):
                del temp_config[remove][field.config_label]
            ScenarioConfig(**temp_config)


def testEmptyConfig():
    """Test passing invalid, empty config dict."""
    # Pass an empty dictionary, ensure ConfigMissingRequiredError is raise
    with pytest.raises(TypeError):
        ScenarioConfig(**{})


@patch("resonaate.scenario.config.event_configs.EventConfigList", autospec=True)
@patch("resonaate.scenario.config.observation_config.ObservationConfig", autospec=True)
@patch("resonaate.scenario.config.perturbations_config.PerturbationsConfig", autospec=True)
@patch("resonaate.scenario.config.geopotential_config.GeopotentialConfig", autospec=True)
@patch("resonaate.scenario.config.propagation_config.PropagationConfig", autospec=True)
@patch("resonaate.scenario.config.noise_config.NoiseConfig", autospec=True)
@patch("resonaate.scenario.config.engine_config.EngineConfig", autospec=True)
@patch("resonaate.scenario.config.estimation_config.EstimationConfig", autospec=True)
@patch("resonaate.scenario.config.time_config.TimeConfig", autospec=True)
def testScenarioConfigInit(
    mocked_time_config: TimeConfig,
    mocked_est_config: EstimationConfig,
    mocked_engine_config: EngineConfig,
    mocked_noise_config: NoiseConfig,
    mocked_prop_config: PropagationConfig,
    mocked_geopot_config: GeopotentialConfig,
    mocked_perturb_config: PerturbationsConfig,
    mocked_obs_config: ObservationConfig,
    mocked_event_list: EventConfigList,
):
    """Test creating a ScenarioConfig in various ways."""
    # minimal config
    _ = ScenarioConfig(
        time=mocked_time_config,
        estimation=mocked_est_config,
        engines=[mocked_engine_config],
    )
    # full config
    scenario_cfg = ScenarioConfig(
        time=mocked_time_config,
        estimation=mocked_est_config,
        engines=[mocked_engine_config],
        noise=mocked_noise_config,
        propagation=mocked_prop_config,
        geopotential=mocked_geopot_config,
        perturbations=mocked_perturb_config,
        observation=mocked_obs_config,
        events=mocked_event_list,
    )
    assert scenario_cfg is not None
    for field in fields(ScenarioConfig):
        assert field.name in dir(scenario_cfg)
        assert getattr(scenario_cfg, field.name) is not None
