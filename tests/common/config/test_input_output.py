
# Standard Library Imports
from pathlib import Path

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.common.config.input_output import (
    AlchemyURL,
    ImporterDbUrlSpec,
    InputConfig,
    OutputDbUrlSpec,
)


def test_inputConfig_goodArgs():
    """Validate that input config builds with only init file as input."""
    input_cfg = InputConfig(init_file="path/to/init.json")
    assert isinstance(input_cfg, InputConfig)

def test_inputConfig_missingImporterDetail():
    """Validate that error is thrown if an invalid Importer database configuration is provided."""
    with pytest.raises(ValidationError):
        _ = InputConfig(init_file="path/to/init.json", importer_db_params={"importer_db_driver": "sqlite"})

def test_importerDbUrl_getUrl():
    """Validate that :meth:`.InputDbUrlSpec.getURL()` works as intended."""
    importer_params = ImporterDbUrlSpec(importer_db_name="path/to/importer.db")
    assert isinstance(importer_params, ImporterDbUrlSpec)
    importer_url = importer_params.getURL()
    assert "importer.db" in str(importer_url)

def test_outputDbUrl_default():
    """Validate that :meth:`.OutputDbUrlSpec.getURL()` works as intended."""
    output_spec = OutputDbUrlSpec()
    assert output_spec.database is not None
    db_path = Path(output_spec.database)
    assert db_path.name.startswith("resonaate_")
    assert db_path.suffix == ".sqlite3"
    assert db_path.parent.name == "db"
    assert db_path.parent.exists()

    db_url = output_spec.getURL()
    assert isinstance(db_url, AlchemyURL)

def test_outputDbUrl_user(tmp_path: Path):
    """Validate that specifying an sqlite database works as intended."""
    db_path = tmp_path / "test_db.sqlite3"
    output_spec = OutputDbUrlSpec(output_db_name=str(db_path))
    assert output_spec

    db_path.touch()
    with pytest.raises(FileExistsError):
        output_spec.checkExists()

    output_spec = OutputDbUrlSpec(output_db_name=str(db_path), output_db_exists_ok=True)
    output_spec.checkExists()
