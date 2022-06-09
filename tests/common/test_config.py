# pylint: disable=attribute-defined-outside-init, import-outside-toplevel, reimported
# Standard Library Imports
import os
from collections import OrderedDict
from logging import DEBUG, INFO

# Third Party Imports
import pytest

# Local Imports
from ..conftest import FIXTURE_DATA_DIR, BaseTestCase


class TestConfig(BaseTestCase):
    """Class to test :mod:`.common.behavioral_config` module."""

    CONFIG_FILE_VALID = (
        "[logging]\n",
        "OutputLocation = ./logs/\n",
        "Level = INFO\n",
        "MaxFileSize = 2048\n",
        "MaxFileCount = 10\n",
    )

    CORRECT_DEFAULTS = OrderedDict(
        {
            "logging": {
                "OutputLocation": "stdout",
                "Level": DEBUG,
                "MaxFileSize": 1048576,
                "MaxFileCount": 50,
                "AllowMultipleHandlers": False,
            },
            "database": {
                "DatabasePath": "sqlite://",
            },
            "parallel": {"RedisHostname": "localhost", "RedisPort": 6379, "WorkerCount": None},
            "debugging": {
                "OutputDirectory": "debugging",
                "NearestPD": False,
                "NearestPDDirectory": "cholesky_failure",
                "EstimateErrorInflation": False,
                "EstimateErrorInflationDirectory": "est_error_inflation",
                "ThreeSigmaObs": False,
                "ThreeSigmaObsDirectory": "three_sigma_obs",
                "SaveSpaceSensors": False,
                "SaveSpaceSensorsDirectory": "space_sensor_truth",
            },
        }
    )

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    @pytest.fixture(name="file_config")
    def mockCustomSettingsFile(self, monkeypatch, datafiles):
        """Automatically delete each environment variable, if set.

        Args:
            monkeypatch (:class:`pytest.monkeypatch.MonkeyPatch`): monkeypatch obj to track changes
            datafiles (str): location of current test data directory

        Yields:
            :class:.`BehavioralConfig`: non-default configuration object

        Note:
            This is used so tests can assume a "blank" configuration, and it won't
            overwrite a user's custom-set environment variables.
        """
        # Write to custom config file, and patch the proper environment variable
        config_path = os.path.join(datafiles, "test.config")
        with open(config_path, "w", encoding="utf-8") as config_file:
            config_file.writelines(self.CONFIG_FILE_VALID)

        with monkeypatch.context() as m_patch:
            # Patch env variable, and yield the new config
            m_patch.setenv("RESONAATE_BEHAVIOR_CONFIG", os.path.join(datafiles, "test.config"))
            # RESONAATE Imports
            from resonaate.common.behavioral_config import BehavioralConfig

            yield BehavioralConfig(os.environ.get("RESONAATE_BEHAVIOR_CONFIG"))

    def testImported(self):
        """Test that importing :class:`._BehavioralConfig` results in the default values."""
        # RESONAATE Imports
        from resonaate.common.behavioral_config import BehavioralConfig

        config = BehavioralConfig.getConfig()
        for section, section_conf in self.CORRECT_DEFAULTS.items():
            for option, value in section_conf.items():
                conf_section = getattr(config, section)
                conf_option = getattr(conf_section, option)
                assert value == conf_option

    def testSinglePattern(self):
        """Test that :class:.`_BehavioralConfig` is a proper Singleton class."""
        # RESONAATE Imports
        from resonaate.common.behavioral_config import BehavioralConfig

        config = BehavioralConfig.getConfig()
        # RESONAATE Imports
        from resonaate.common.behavioral_config import BehavioralConfig as second_config

        assert config is second_config.getConfig()

    def testOverwrite(self):
        """Test overwriting the default :class:`._BehavioralConfig` directly with custom settings."""
        # Import and overwrite default settings
        # RESONAATE Imports
        from resonaate.common.behavioral_config import BehavioralConfig

        custom_config = BehavioralConfig.getConfig()
        custom_config.logging.OutputLocation = "./logs/"
        custom_config.logging.Level = INFO
        custom_config.logging.MaxFileSize = 2048
        custom_config.logging.MaxFileCount = 10

        # Re-import and check the values
        second_config = BehavioralConfig.getConfig()
        assert second_config.logging.OutputLocation == "./logs/"
        assert second_config.logging.Level == INFO
        assert second_config.logging.MaxFileSize == 2048
        assert second_config.logging.MaxFileCount == 10

        # Reset the values to the defaults
        second_config.logging.OutputLocation = self.CORRECT_DEFAULTS["logging"]["OutputLocation"]
        second_config.logging.Level = self.CORRECT_DEFAULTS["logging"]["Level"]
        second_config.logging.MaxFileSize = self.CORRECT_DEFAULTS["logging"]["MaxFileSize"]
        second_config.logging.MaxFileCount = self.CORRECT_DEFAULTS["logging"]["MaxFileCount"]

        # Assert singleton condition
        assert custom_config is second_config

    def testNonDefaultFile(self, test_logger, file_config):
        """Test overwriting the default :class:`._BehavioralConfig` with custom config file.

        Args:
            test_logger (:class:`logging.Logger`): unit test logger object
            file_config (:class:.`BehavioralConfig`): non-default config object

        Note:
            This will not overwrite the :class:`_BehavioralConfig` that all others use because it
            patches the environment variable _after_ the first import, so it only checks that a
            subsequent instantiation uses the environment variable. This mimics if the user had
            it set _before_ calling/importing anything.
        """
        # Patched environment variable
        msg = f'RESONAATE_BEHAVIOR_CONFIG: {os.environ.get("RESONAATE_BEHAVIOR_CONFIG")}'
        test_logger.debug(msg)

        # Check the values
        assert file_config.logging.OutputLocation == "./logs/"
        assert file_config.logging.Level == INFO
        assert file_config.logging.MaxFileSize == 2048
        assert file_config.logging.MaxFileCount == 10

        # Check it change for all imports
        # RESONAATE Imports
        from resonaate.common.behavioral_config import BehavioralConfig

        second_config = BehavioralConfig.getConfig()
        assert second_config.logging.OutputLocation == file_config.logging.OutputLocation
        assert second_config.logging.Level == file_config.logging.Level
        assert second_config.logging.MaxFileSize == file_config.logging.MaxFileSize
        assert second_config.logging.MaxFileCount == file_config.logging.MaxFileCount

        # Reset the values to the defaults
        file_config.logging.OutputLocation = self.CORRECT_DEFAULTS["logging"]["OutputLocation"]
        file_config.logging.Level = self.CORRECT_DEFAULTS["logging"]["Level"]
        file_config.logging.MaxFileSize = self.CORRECT_DEFAULTS["logging"]["MaxFileSize"]
        file_config.logging.MaxFileCount = self.CORRECT_DEFAULTS["logging"]["MaxFileCount"]

        # Assert singleton condition
        assert file_config is second_config

        # Double check config was reset properly
        for section, section_conf in self.CORRECT_DEFAULTS.items():
            for option, value in section_conf.items():
                conf_section = getattr(file_config, section)
                conf_option = getattr(conf_section, option)
                assert value == conf_option
