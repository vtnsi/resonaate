# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from copy import deepcopy
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.scenario.scenario_config import ScenarioConfig
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


@pytest.fixture(name="scenario_config")
def getScenarioTestConfig():
    """Fixture to return a valid scenario config `dict`."""
    return {
        "time": {
            "start_timestamp": "2018-12-01T12:00:00.000Z",
            "physics_step_sec": 60,
            "output_step_sec": 60,
            "stop_timestamp": "2018-12-01T13:00:00.000Z"
        },
        "noise": {
            "initial_error_magnitude": 1e-20,
            "dynamics_noise_type": "simple_noise",
            "dynamics_noise_magnitude": 1e-25,
            "filter_noise_type": "continuous_white_noise",
            "filter_noise_magnitude": 1e-7,
            "random_seed": None
        },
        "reward": {
            "name": "CostConstrainedReward",
            "metrics": [
                {
                    "name": "FisherInformation",
                    "parameters": {}
                },
                {
                    "name": "DeltaPosition",
                    "parameters": {}
                },
                {
                    "name": "LyapunovStability",
                    "parameters": {}
                }
            ],
            "parameters": {}
        },
        "decision": {
            "name": "MyopicNaiveGreedyDecision",
            "parameters": {}
        },
        "propagation": {
            "propagation_model": "special_perturbations",
            "integration_method": "RK45",
            "realtime_propagation": False,
            "realtime_observation": False
        },
        "geopotential": {
            "model": "egm96.txt",
            "degree": 4,
            "order": 4
        },
        "perturbations": {
            "third_bodies": ["sun", "moon"]
        },
        "target_events": "",
        "sensor_events": "",
        "filter": {
            "name": "unscented_kalman_filter"
        },
        "engines": [
            "engines/taskable_engine.json"
        ]
    }


@pytest.fixture(name="minimal_config")
def getMinimalScenarioConfig():
    """Fixture to return the minimal valid scenario config `dict`."""
    return {
        "time": {
            "start_timestamp": "2018-12-01T12:00:00.000Z",
            "stop_timestamp": "2018-12-01T13:00:00.000Z"
        },
        "filter": {
            "name": "unscented_kalman_filter"
        },
        "engines": [
            "engines/taskable_engine.json"
        ]
    }


class TestScenarioConfig(BaseTestCase):
    """Test the :class:`.ScenarioConfig` class."""

    @pytest.mark.parametrize("remove", ScenarioConfig.REQUIRED_SECTIONS)
    def testRequiredSection(self, scenario_config, remove):
        """Test removing each required sections in config."""
        # Remove required key from the config dict
        del scenario_config[remove]
        # Ensure a KeyError is raised
        with pytest.raises(KeyError):
            ScenarioConfig(scenario_config)

    @pytest.mark.parametrize("remove", ScenarioConfig.OPTIONAL_SECTIONS)
    def testOptionalSection(self, scenario_config, remove):
        """Test removing each optional sections in config."""
        # Remove required key from the config dict
        del scenario_config[remove]
        # Ensure a valid section was added
        ScenarioConfig(scenario_config)

    @pytest.mark.parametrize("remove", ScenarioConfig.REQUIRED_SECTIONS)
    def testRequiredFields(self, scenario_config, remove):
        """Test removing required fields in each config section."""
        # Build a list of required keys for this section
        required = []
        for field in ScenarioConfig.CONFIG[remove]:
            field_config = ScenarioConfig.CONFIG[remove][field]
            if "default" in field_config and field_config["default"] is None:
                required.append(field)

        # Remove the required keys for this section, ensure KeyError is raise
        for field in required:
            tmp_config = deepcopy(scenario_config)
            del tmp_config[remove][field]
            with pytest.raises(KeyError):
                ScenarioConfig(tmp_config)

    @pytest.mark.parametrize("remove", ScenarioConfig.OPTIONAL_SECTIONS)
    def testOptionalFields(self, scenario_config, remove):
        """Test removing optional fields in each config section."""
        # Build a list of optional keys for this section
        optional = []
        for field in ScenarioConfig.CONFIG[remove]:
            field_config = ScenarioConfig.CONFIG[remove][field]
            if "default" in field_config and field_config["default"] is not None:
                optional.append(field)

        # Remove the required keys for this section, ensure default keys are applied
        for field in optional:
            tmp_config = deepcopy(scenario_config)
            del tmp_config[remove][field]
            ScenarioConfig(tmp_config)

    def testBadTypes(self, scenario_config):
        """Test bad types for each section."""
        for section, fields in ScenarioConfig.CONFIG.items():
            # These sections are special
            if section in ("filter", "engine"):
                # Grab a copy of the test config
                tmp_config = deepcopy(scenario_config)
                # Overwrite field with an in-compatible type
                tmp_config[section] = 1000
                with pytest.raises(TypeError):
                    ScenarioConfig(tmp_config)
                continue

            for field in fields:
                # Grab a copy of the test config
                tmp_config = deepcopy(scenario_config)
                # Overwrite field with an in-compatible type
                tmp_config[section][field] = set()
                with pytest.raises(TypeError):
                    ScenarioConfig(tmp_config)

    def testEmptyConfig(self):
        """Test passing invalid, empty config dict."""
        # Pass an empty dictionary, ensure KeyError is raise
        with pytest.raises(KeyError):
            ScenarioConfig({})

    def testMinimalConfigFile(self, minimal_config):
        """Test the minimal configuration case."""
        ScenarioConfig(minimal_config)
