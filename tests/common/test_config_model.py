
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


def test_buildConfigWithDotEnv(tmp_path: Path):
    custom_db_path = "path/to/output.db"
    temp_dotenv_path = tmp_path / "resonaate.env"
    with open(temp_dotenv_path, "w") as temp_dotenv:
        temp_dotenv.write(f"DB_PATH={custom_db_path}\n")

    init_input = "path/to/config.json"
    config = buildConfig([init_input], dotenv_path=temp_dotenv_path)
    assert config.db_path == custom_db_path


def test_buildConfigWithEnv(monkeypatch):
    custom_db_path = "path/to/output.db"
    monkeypatch.setenv("DB_PATH", custom_db_path)

    init_input = "path/to/config.json"
    config = buildConfig([init_input])
    assert config.db_path == custom_db_path
