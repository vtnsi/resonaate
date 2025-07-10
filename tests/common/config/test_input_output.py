
# Standard Library Imports
from pathlib import Path

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.common.config.input_output import AlchemyURL, InputConfig, OutputDbUrlSpec


def test_inputConfig_goodArgs():
    """Validate that input config builds with only init file as input."""
    input_cfg = InputConfig(init_file="path/to/init.json")
    assert isinstance(input_cfg, InputConfig)

def test_inputConfig_missingImporterDetail():
    """Validate that error is thrown if an invalid Importer database configuration is provided."""
    with pytest.raises(ValidationError):
        _ = InputConfig(init_file="path/to/init.json", importer_db_params={"importer_db_driver": "sqlite"})

def test_outputDbUrl_default():
    """Validate that :meth:`.OutputDbUrlSpec.getURL()` works as intended."""
    output_spec = OutputDbUrlSpec()
    db_url = output_spec.getURL()
    assert isinstance(db_url, AlchemyURL)
    # after call to `::getURL()`, default spec should have populated `database` attr
    assert output_spec.database is not None
    db_path = Path(output_spec.database)
    assert db_path.name.startswith("resonaate_")
    assert db_path.suffix == ".sqlite3"
    assert db_path.parent.name == "db"
    assert db_path.parent.exists()

def test_outputDbUrl_user(tmp_path: Path):
    """Validate that specifying an sqlite database works as intended."""
    db_path = tmp_path / "test_db.sqlite3"
    output_spec = OutputDbUrlSpec(output_db_name=str(db_path))
    assert output_spec.getURL()
    db_path.touch()
    with pytest.raises(FileExistsError):
        _ = output_spec.getURL()
