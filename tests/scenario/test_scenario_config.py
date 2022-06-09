# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from copy import deepcopy
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.scenario.config import ScenarioConfig
    from resonaate.scenario.scenario_builder import ScenarioBuilder
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


@pytest.fixture(name="scenario_config")
def getScenarioTestConfig():
    """Fixture to return a valid scenario config `dict`."""
    return ScenarioConfig.parseConfigFile("example_data/json/test_init.json")


class TestScenarioConfig(BaseTestCase):
    """Test the :class:`.ScenarioConfig` class."""

    @pytest.mark.parametrize("remove", ScenarioConfig().required_sections)
    def testRequiredSection(self, scenario_config, remove):
        """Test removing each required sections in config."""
        # Remove required key from the config dict
        del scenario_config[remove]
        # Ensure a KeyError is raised
        with pytest.raises(KeyError):
            ScenarioConfig().readConfig(scenario_config)

    @pytest.mark.parametrize("remove", ScenarioConfig().optional_sections)
    def testOptionalSection(self, scenario_config, remove):
        """Test removing each optional sections in config."""
        # Remove required key from the config dict
        del scenario_config[remove]
        # Ensure a valid section was added
        ScenarioConfig().readConfig(scenario_config)

    @pytest.mark.parametrize("remove", ScenarioConfig().required_sections)
    def testRequiredFields(self, scenario_config, remove):
        """Test removing required fields in each config section."""
        section = getattr(ScenarioConfig(), remove)
        for field in section.nested_items:
            if field.isRequired():
                temp_config = deepcopy(scenario_config)
                del temp_config[section.config_label][field.config_label]
                with pytest.raises(KeyError):
                    ScenarioConfig().readConfig(temp_config)

    @pytest.mark.parametrize("remove", ScenarioConfig().optional_sections)
    def testOptionalFields(self, scenario_config, remove):
        """Test removing optional fields in each config section."""
        section = getattr(ScenarioConfig(), remove)
        for field in section.nested_items:
            if not field.isRequired():
                temp_config = deepcopy(scenario_config)
                del temp_config[remove][field.config_label]
                ScenarioConfig().readConfig(temp_config)

    def testEmptyConfig(self):
        """Test passing invalid, empty config dict."""
        # Pass an empty dictionary, ensure KeyError is raise
        with pytest.raises(KeyError):
            ScenarioConfig().readConfig({})

    def testSafeDuplicateTargets(self, scenario_config):
        """Verify no errors are thrown if two engines are looking at the same target network."""
        first_target_network = None
        for engine in scenario_config["engines"]:
            if not first_target_network:
                first_target_network = engine["targets"]
            else:
                engine["targets"] = first_target_network

        config = ScenarioConfig()
        config.readConfig(scenario_config)
        ScenarioBuilder(config)

    def testECICOEDuplicateTargets(self, scenario_config):
        """Verify errors are thrown if two engines are looking at the same target with different initial states."""
        first_target_network = None
        for engine in scenario_config["engines"]:
            if not first_target_network:
                first_target_network = deepcopy(engine["targets"])
                first_target_network[0]["init_coe"] = {}
                del first_target_network[0]["init_eci"]
            else:
                engine["targets"] = first_target_network

        config = ScenarioConfig()
        config.readConfig(scenario_config)

        with pytest.raises(Exception):
            ScenarioBuilder(config)

    def testDiffStateDuplicateTargets(self, scenario_config):
        """Verify errors are thrown if two engines are looking at the same target with different initial states."""
        first_target_network = None
        for engine in scenario_config["engines"]:
            if not first_target_network:
                first_target_network = deepcopy(engine["targets"])
                first_target_network[0]["init_eci"][0] += 0.1
            else:
                engine["targets"] = first_target_network

        config = ScenarioConfig()
        config.readConfig(scenario_config)

        with pytest.raises(Exception):
            ScenarioBuilder(config)

    def testDuplicateSensors(self, scenario_config):
        """Verify errors are thrown if two engines are tasking the same sensors."""
        first_sensor_network = None
        for engine in scenario_config["engines"]:
            if not first_sensor_network:
                first_sensor_network = engine["sensors"]
            else:
                engine["sensors"] = first_sensor_network

        config = ScenarioConfig()
        config.readConfig(scenario_config)

        with pytest.raises(Exception):
            ScenarioBuilder(config)
