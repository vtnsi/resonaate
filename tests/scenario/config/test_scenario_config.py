from __future__ import annotations

# Standard Library Imports
from pathlib import Path

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.scenario.config import ScenarioConfig

# Local Imports
from ... import FIXTURE_DATA_DIR, JSON_INIT_PATH


def testEmptyConfig():
    """Validate that scenario config validation throws an error if specified config is empty."""
    with pytest.raises(ValidationError):
        _ = ScenarioConfig()


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testParseConfigFile(datafiles: str):
    """Test parsing a valid config file."""
    # Pass a valid config file, ensure no errors are raised
    test_init_file = Path(str(datafiles)) / JSON_INIT_PATH / "test_init.json"
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(test_init_file)
    assert isinstance(scenario_cfg_dict, dict)
    assert "engines_files" not in scenario_cfg_dict
    assert isinstance(scenario_cfg_dict.get("engines"), list)
    for engine_cfg_dict in scenario_cfg_dict["engines"]:
        assert "targets_file" not in engine_cfg_dict
        assert "sensors_file" not in engine_cfg_dict
        assert isinstance(engine_cfg_dict.get("targets"), list)
        assert isinstance(engine_cfg_dict.get("sensors"), list)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testFromConfigFile(datafiles: str):
    """Test alt constructor from valid config file."""
    # Pass a valid config file, ensure no errors are raised
    test_init_file = Path(str(datafiles)) / JSON_INIT_PATH / "test_init.json"
    scenario_cfg = ScenarioConfig.fromConfigFile(test_init_file)
    assert isinstance(scenario_cfg, ScenarioConfig)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testInvalidConfigFile(datafiles: str):
    """Test passing invalid, empty config dict."""
    bad_file = Path(str(datafiles)) / JSON_INIT_PATH / "bad_init.json"
    with pytest.raises(FileNotFoundError):
        ScenarioConfig.parseConfigFile(bad_file)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
@pytest.mark.parametrize("remove", ["time", "estimation", "engines"])
def testRequiredSection(datafiles: str, remove: str):
    """Test removing each required sections in config."""
    test_init_file = Path(str(datafiles)) / JSON_INIT_PATH / "test_init.json"
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(test_init_file)
    # Remove required key from the config dict
    del scenario_cfg_dict[remove]
    # Ensure a ConfigMissingRequiredError is raised
    with pytest.raises(ValidationError):
        ScenarioConfig(**scenario_cfg_dict)


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
@pytest.mark.parametrize("remove", ["noise", "propagation", "geopotential", "perturbations", "observation", "events"])
def testOptionalSection(datafiles: str, remove: str):
    """Test removing each optional sections in config."""
    test_init_file = Path(str(datafiles)) / JSON_INIT_PATH / "test_init.json"
    scenario_cfg_dict = ScenarioConfig.parseConfigFile(test_init_file)
    # Remove required key from the config dict
    if scenario_cfg_dict.get(remove):
        del scenario_cfg_dict[remove]
    # Ensure a valid section was added
    ScenarioConfig(**scenario_cfg_dict)
