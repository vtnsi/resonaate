
# Standard Library Imports
from pathlib import Path

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.config_model import BehavioralConfig, buildConfig, getCommandLineParser


def test_configModelGood():
    init_input = "path/to/config.json"
    config = BehavioralConfig(init_file=init_input)
    assert config.init_file == Path(init_input)
    assert config.db_path is not None
    assert config.importer_db_path is None


def test_argParserMissingRequired():
    parser = getCommandLineParser()
    with pytest.raises(SystemExit):
        _ = parser.parse_args([])


def test_buildConfig():
    init_input = "path/to/config.json"
    config = buildConfig([init_input])
    assert config.init_file == Path(init_input)
