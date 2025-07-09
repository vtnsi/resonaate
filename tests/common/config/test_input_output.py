
# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.common.config.input_output import InputConfig


def test_inputConfig_goodArgs():
    """Validate that input config builds with only init file as input."""
    input_cfg = InputConfig(init_file="path/to/init.json")
    assert isinstance(input_cfg, InputConfig)

def test_inputConfig_missingImporterDetail():
    """Validate that error is thrown if an invalid Importer database configuration is provided."""
    with pytest.raises(ValidationError):
        _ = InputConfig(init_file="path/to/init.json", importer_db_params={"importer_db_driver": "sqlite"})
