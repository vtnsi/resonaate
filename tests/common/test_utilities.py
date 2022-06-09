# pylint: disable=attribute-defined-outside-init
# Standard Library Imports
import json
import os

# Third Party Imports
import numpy as np
import pytest

try:
    # RESONAATE Imports
    import resonaate.common.utilities as utils
    from resonaate.common.behavioral_config import BehavioralConfig
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import FIXTURE_DATA_DIR, BaseTestCase


class TestCommonUtils(BaseTestCase):
    """Test all functions in utilities module."""

    def testGetTypeString(self):
        """Ensure proper type string is returned for parent & child classes."""
        # Dummy classes for testing type string
        class DummyClass1:
            pass

        class DummyClass2(DummyClass1):
            pass

        # Create proper instances
        dummy1 = DummyClass1()
        dummy2 = DummyClass2()

        assert utils.getTypeString(dummy1) == "DummyClass1"
        assert utils.getTypeString(dummy2) == "DummyClass2"

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testLoadJSONFile(self, datafiles):
        """Ensure JSON file loader works properly."""
        # Valid JSON file
        utils.loadJSONFile(os.path.join(datafiles, "json/config/engines/test_engine.json"))
        # Empty JSON file
        error_msg = r"Empty JSON file: \/.*?\.json+"
        with pytest.raises(IOError, match=error_msg):
            utils.loadJSONFile(os.path.join(datafiles, "json/empty.json"))
        # Non-existant JSON file
        with pytest.raises(FileNotFoundError):
            utils.loadJSONFile(os.path.join(datafiles, "json/nonexistant.json"))
        # Invalid JSON file
        with pytest.raises(json.decoder.JSONDecodeError):
            utils.loadJSONFile(os.path.join(datafiles, "json/invalid.json"))

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testLoadDatFile(self, datafiles):
        """Ensure dat file loader works properly."""
        # Valid dat file
        utils.loadDatFile(os.path.join(datafiles, "dat/nut80.dat"))
        # Empty dat file
        error_msg = r"Empty DAT file: \/.*?\.dat+"
        with pytest.raises(IOError, match=error_msg):
            utils.loadDatFile(os.path.join(datafiles, "dat/empty.dat"))
        # Non-existant dat file
        with pytest.raises(FileNotFoundError):
            utils.loadDatFile(os.path.join(datafiles, "dat/nonexistant.dat"))
        # Invalid dat file
        error_msg = r"Parsing error reading DAT file: \/.*?\.dat+"
        with pytest.raises(ValueError, match=error_msg):
            utils.loadDatFile(os.path.join(datafiles, "dat/invalid.dat"), delim=",")

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testMatrixSaving(self, datafiles):
        """Ensure matrix saving functionality works properly."""
        list_matrix = [[0, 2, 1, 0], [2, 5, 1, 7]]
        numpy_matrix = np.asarray(list_matrix)

        # List form of matrix
        print("\nlist")
        file_name = utils.saveMatrix("list", list_matrix, path=datafiles)
        assert os.path.isfile(file_name)

        # Numpy form of matrix
        print("numpy")
        file_name = utils.saveMatrix("numpy", numpy_matrix, path=datafiles)
        assert os.path.isfile(file_name)

        # Check current working directory form
        print("cwd")
        saved_cwd = os.getcwd()
        os.chdir(datafiles)
        file_name = utils.saveMatrix("cwd", numpy_matrix, path=None)
        assert os.path.isfile(file_name)
        os.chdir(saved_cwd)

        # Invalid matrix
        print("invalid")
        with pytest.raises(TypeError):
            utils.saveMatrix("invalid", ((0, 1), (2, 3)), path=datafiles)

    def testGetTimeout(self):
        """Ensure proper timeout values are calculated."""
        # Test debuggin mode
        default = BehavioralConfig.getConfig().debugging.ParallelDebugMode
        BehavioralConfig.getConfig().debugging.ParallelDebugMode = True
        assert utils.getTimeout(0) is None
        assert utils.getTimeout(10) is None
        assert utils.getTimeout(1000) is None
        assert utils.getTimeout(10, multiplier=1) is None
        # Reset debug config value
        BehavioralConfig.getConfig().debugging.ParallelDebugMode = default

        # Various combinations of valid values
        assert utils.getTimeout(0) == 0
        assert utils.getTimeout(1) == 5
        assert utils.getTimeout(3) == 15
        assert utils.getTimeout(3, multiplier=1) == 3
