from __future__ import annotations

# Standard Library Imports
import json
import os

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
import resonaate.common.utilities as utils
from resonaate.common.behavioral_config import BehavioralConfig

# Local Imports
from .. import FIXTURE_DATA_DIR


def testNdarraySerializer():
    """Tests conversion between ndarrays and json strings."""
    q_matrix = np.array([[1, 2, 3], [1, 2, 3], [4, 5, 6]])
    q_matrix_2 = np.array([[0, 1, 0], [1, 1, 1], [2, 4, 2]])

    q_mat_str: str = utils.ndArrayToString(q_matrix)
    q_mat_from_str: np.ndarray = utils.stringToNdarray(q_mat_str)

    q_mat_str_2: str = utils.ndArrayToString(q_matrix_2)
    q_mat_from_str_2: np.ndarray = utils.stringToNdarray(q_mat_str_2)

    assert np.array_equal(q_matrix, q_mat_from_str)
    assert np.array_equal(q_matrix_2, q_mat_from_str_2)
    assert q_mat_str != q_mat_str_2
    assert not np.array_equal(q_mat_from_str, q_mat_from_str_2)


def testGetTypeString():
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
def testLoadJSONFile(datafiles: str):
    """Ensure JSON file loader works properly."""
    # Valid JSON file
    utils.loadJSONFile(os.path.join(datafiles, "json/config/engines/test_engine.json"))
    # Empty JSON file
    with pytest.raises(IOError, match="Empty JSON file:") as io_exc_info:
        utils.loadJSONFile(os.path.join(datafiles, "json/empty.json"))
    err_msg: str = io_exc_info.value.args[0]
    assert err_msg.endswith(".json")
    # Non-existant JSON file
    with pytest.raises(FileNotFoundError):
        utils.loadJSONFile(os.path.join(datafiles, "json/nonexistant.json"))
    # Invalid JSON file
    with pytest.raises(json.decoder.JSONDecodeError):
        utils.loadJSONFile(os.path.join(datafiles, "json/invalid.json"))


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testLoadDatFile(datafiles: str):
    """Ensure dat file loader works properly."""
    # Valid dat file
    utils.loadDatFile(os.path.join(datafiles, "dat/nut80.dat"))
    # Empty dat file
    with pytest.raises(IOError, match="Empty DAT file:") as io_exc_info:
        utils.loadDatFile(os.path.join(datafiles, "dat/empty.dat"))
    err_msg: str = io_exc_info.value.args[0]
    assert err_msg.endswith(".dat")
    # Non-existant dat file
    with pytest.raises(FileNotFoundError):
        utils.loadDatFile(os.path.join(datafiles, "dat/nonexistant.dat"))
    # Invalid dat file
    with pytest.raises(ValueError, match="Parsing error reading DAT file:") as io_exc_info:
        utils.loadDatFile(os.path.join(datafiles, "dat/invalid.dat"), delim=",")
    err_msg: str = io_exc_info.value.args[0]
    assert err_msg.endswith(".dat")


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testMatrixSaving(datafiles: str):
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


@pytest.mark.no_debug()
def testGetTimeout():
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
