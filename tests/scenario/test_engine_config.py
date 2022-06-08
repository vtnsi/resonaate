# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from copy import deepcopy
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.scenario.engine_config import EngineConfig
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


@pytest.fixture(name="engine_config")
def getEngineTestConfig():
    """Fixture to return a valid scenario config `dict`."""
    return {
        "reward": {
            "name": "CostConstrainedReward",
            "metrics": [
                {
                    "name": "ShannonInformation",
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
            "name": "MunkresDecision",
            "parameters": {}
        },
        "target_set": "../target_sets/ISS_target_set.json",
        "sensor_set": "../sensor_sets/basic_network.json"
    }


class TestEngineConfig(BaseTestCase):
    """Test the :class:`.EngineConfig` class."""

    @pytest.mark.parametrize("remove", EngineConfig.REQUIRED_SECTIONS)
    def testRequiredSection(self, engine_config, remove):
        """Test removing each required sections in config."""
        # Remove required key from the config dict
        del engine_config[remove]
        # Ensure a KeyError is raised
        with pytest.raises(KeyError):
            EngineConfig(engine_config)

    @pytest.mark.parametrize("remove", EngineConfig.OPTIONAL_SECTIONS)
    def testOptionalSection(self, engine_config, remove):
        """Test removing each optional sections in config."""
        # Remove required key from the config dict
        del engine_config[remove]
        # Ensure a valid section was added
        EngineConfig(engine_config)

    @pytest.mark.parametrize("remove", EngineConfig.REQUIRED_SECTIONS)
    def testRequiredFields(self, engine_config, remove):
        """Test removing required fields in each config section."""
        # Build a list of required keys for this section
        required = []
        for field in EngineConfig.CONFIG[remove]:
            field_config = EngineConfig.CONFIG[remove][field]
            if "default" in field_config and field_config["default"] is None:
                required.append(field)

        # Remove the required keys for this section, ensure KeyError is raise
        for field in required:
            tmp_config = deepcopy(engine_config)
            del tmp_config[remove][field]
            with pytest.raises(KeyError):
                EngineConfig(tmp_config)

    def testBadTypes(self, engine_config):
        """Test bad types for each section."""
        for section, fields in EngineConfig.CONFIG.items():
            # These sections are special
            if section in ("reward", "decision"):
                # Grab a copy of the test config
                tmp_config = deepcopy(engine_config)
                # Overwrite field with an in-compatible type
                tmp_config[section] = 1000
                with pytest.raises(TypeError):
                    EngineConfig(tmp_config)
                continue

            for field in fields:
                # Grab a copy of the test config
                tmp_config = deepcopy(engine_config)
                # Overwrite field with an in-compatible type
                tmp_config[section][field] = set()
                with pytest.raises(TypeError):
                    EngineConfig(tmp_config)

    def testEmptyConfig(self):
        """Test passing invalid, empty config dict."""
        # Pass an empty dictionary, ensure KeyError is raise
        with pytest.raises(KeyError):
            EngineConfig({})
