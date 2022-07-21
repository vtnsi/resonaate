# pylint: disable=attribute-defined-outside-init, unused-argument
# Standard Library Imports
import os.path
from copy import deepcopy
from dataclasses import fields

# Third Party Imports
import pytest

try:
    # RESONAATE Imports
    from resonaate.common.exceptions import DuplicateSensorError, DuplicateTargetError
    from resonaate.scenario.config import ScenarioConfig
    from resonaate.scenario.scenario_builder import ScenarioBuilder
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import FIXTURE_DATA_DIR, BaseTestCase


@pytest.fixture(name="scenario_config")
def getScenarioTestConfig():
    """Fixture to return a valid scenario config `dict`."""
    return ScenarioConfig.parseConfigFile("configs/json/test_init.json")


class TestScenarioConfig(BaseTestCase):
    """Test the :class:`.ScenarioConfig` class."""

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    @pytest.mark.parametrize("remove", ScenarioConfig.getRequiredFields())
    def testRequiredSection(self, datafiles, remove):
        """Test removing each required sections in config."""
        init_filepath = os.path.join(datafiles, self.json_init_path, "test_init.json")
        scenario_config = ScenarioConfig.parseConfigFile(init_filepath)
        # Remove required key from the config dict
        del scenario_config[remove]
        # Ensure a ConfigMissingRequiredError is raised
        with pytest.raises(TypeError):
            ScenarioConfig(**scenario_config)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    @pytest.mark.parametrize("remove", ScenarioConfig.getOptionalFields())
    def testOptionalSection(self, datafiles, remove):
        """Test removing each optional sections in config."""
        init_filepath = os.path.join(datafiles, self.json_init_path, "test_init.json")
        scenario_config = ScenarioConfig.parseConfigFile(init_filepath)
        # Remove required key from the config dict
        if scenario_config.get(remove):
            del scenario_config[remove]
        # Ensure a valid section was added
        ScenarioConfig(**scenario_config)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    @pytest.mark.parametrize("remove", ScenarioConfig.getRequiredFields())
    def testRequiredFields(self, datafiles, remove):
        """Test removing required fields in each config section."""
        init_filepath = os.path.join(datafiles, self.json_init_path, "test_init.json")
        scenario_config = ScenarioConfig.parseConfigFile(init_filepath)
        section = getattr(ScenarioConfig(**scenario_config), remove)
        for field in fields(section):
            if field in section.getRequiredFields():
                temp_config = deepcopy(scenario_config)
                del temp_config[section.config_label][field.config_label]
                with pytest.raises(TypeError):
                    ScenarioConfig(**temp_config)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    @pytest.mark.parametrize("remove", ScenarioConfig.getOptionalFields())
    def testOptionalFields(self, datafiles, remove):
        """Test removing optional fields in each config section."""
        init_filepath = os.path.join(datafiles, self.json_init_path, "test_init.json")
        scenario_config = ScenarioConfig.parseConfigFile(init_filepath)
        section = getattr(ScenarioConfig(**scenario_config), remove)
        for field in fields(section):
            if field in section.getOptionalFields():
                temp_config = deepcopy(scenario_config)
                if temp_config.get(remove):
                    del temp_config[remove][field.config_label]
                ScenarioConfig(**temp_config)

    def testEmptyConfig(self):
        """Test passing invalid, empty config dict."""
        # Pass an empty dictionary, ensure ConfigMissingRequiredError is raise
        with pytest.raises(TypeError):
            ScenarioConfig(**{})

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testSafeDuplicateTargets(self, datafiles, reset_shared_db):
        """Verify no errors are thrown if two engines are looking at the same target network."""
        init_filepath = os.path.join(datafiles, self.json_init_path, "test_init.json")
        scenario_config = ScenarioConfig.parseConfigFile(init_filepath)
        first_target_network = None
        for engine in scenario_config["engines"]:
            if not first_target_network:
                first_target_network = engine["targets"]
            else:
                engine["targets"] = first_target_network

        config = ScenarioConfig(**scenario_config)
        ScenarioBuilder(config)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testECICOEDuplicateTargets(self, datafiles, reset_shared_db):
        """Verify errors are thrown if two engines are looking at the same target with different initial states."""
        init_filepath = os.path.join(datafiles, self.json_init_path, "test_init.json")
        scenario_config = ScenarioConfig.parseConfigFile(init_filepath)
        first_target_network = None
        for engine in scenario_config["engines"]:
            if not first_target_network:
                first_target_network = deepcopy(engine["targets"])
                first_target_network[0]["init_coe"] = {
                    "sma": 0,
                    "ecc": 0,
                    "inc": 0,
                    "true_long": 0,
                }
                del first_target_network[0]["init_eci"]
            else:
                engine["targets"] = first_target_network

        config = ScenarioConfig(**scenario_config)
        with pytest.raises(DuplicateTargetError):
            ScenarioBuilder(config)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testDiffStateDuplicateTargets(self, datafiles, reset_shared_db):
        """Verify errors are thrown if two engines are looking at the same target with different initial states."""
        init_filepath = os.path.join(datafiles, self.json_init_path, "test_init.json")
        scenario_config = ScenarioConfig.parseConfigFile(init_filepath)
        first_target_network = None
        for engine in scenario_config["engines"]:
            if not first_target_network:
                first_target_network = deepcopy(engine["targets"])
                first_target_network[0]["init_eci"][0] += 0.1
            else:
                engine["targets"] = first_target_network

        config = ScenarioConfig(**scenario_config)
        with pytest.raises(DuplicateTargetError):
            ScenarioBuilder(config)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testDuplicateSensors(self, datafiles, reset_shared_db):
        """Verify errors are thrown if two engines are tasking the same sensors."""
        init_filepath = os.path.join(datafiles, self.json_init_path, "test_init.json")
        scenario_config = ScenarioConfig.parseConfigFile(init_filepath)
        first_sensor_network = None
        for engine in scenario_config["engines"]:
            if not first_sensor_network:
                first_sensor_network = engine["sensors"]
            else:
                engine["sensors"] = first_sensor_network

        config = ScenarioConfig(**scenario_config)
        with pytest.raises(DuplicateSensorError):
            ScenarioBuilder(config)
