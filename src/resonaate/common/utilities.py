"""Various helper functions that are used across multiple modules."""
# Standard Library Imports
import json
import os
from datetime import datetime
# Third Party Imports
import numpy as np
import yaml
# RESONAATE Imports
from .behavioral_config import BehavioralConfig


def getTypeString(class_instance):
    """Return the class type as a string without any base class information.

    Args:
        class_instance (generic class instance): instance of a general class

    Returns:
        ``str``: name of the class without base classes

    """
    return class_instance.__class__.__name__


def loadYAMLFile(file_name):
    """Load in a YAML file into a Python dictionary.

    Args:
        file_name (``str``): name of YAML file to load

    Raises:
        ``FileNotFoundError``: helps with debugging bad filenames
        ``yaml.YAMLError``: error parsing YAML file (bad syntax)
        ``IOError``: valid YAML file is empty

    Returns:
        ``dict``: documents loaded from the YAML file
    """
    try:
        with open(file_name, 'r', encoding="utf-8") as input_file:
            yaml_data = yaml.safe_load(input_file)
    except FileNotFoundError as err:
        print(f"Could not find YAML file: {file_name}")
        raise err
    except yaml.YAMLError as err:
        print(f"Parsing error reading YAML file: {file_name}")
        raise err

    if not yaml_data:
        print(f"Empty YAML file: {file_name}")
        raise IOError

    return yaml_data


def loadJSONFile(file_name):
    """Load in a JSON file into a Python dictionary.

    Args:
        file_name (``str``): name of JSON file to load

    Raises:
        ``FileNotFoundError``: helps with debugging bad filenames
        ``json.decoder.JSONDecodeError``: error parsing JSON file (bad syntax)
        ``IOError``: valid JSON file is empty

    Returns:
        ``dict``: documents loaded from the JSON file
    """
    try:
        with open(file_name, 'r', encoding="utf-8") as input_file:
            json_data = json.load(input_file)
    except FileNotFoundError as err:
        print(f"Could not find JSON file: {file_name}")
        raise err
    except json.decoder.JSONDecodeError as err:
        print(f"Decoding error reading JSON file: {file_name}")
        raise err

    if not json_data:
        print(f"Empty JSON file: {file_name}")
        raise IOError

    return json_data


def loadDatFile(file_name, delim=None):
    """Load the corresponding dat file.

    Note:
        Assumes all data is representable by ``float``.

    Args:
        file_name (``str``): name of dat file to load
        delim (``str``, optional): delimiter character to separate data on same line. Defaults to
            ``None``, which removes all whitespace between values.

    Raises:
        ``FileNotFoundError``: helps with debugging bad filenames
        ``ValueError``: error parsing dat file, likely because values are convertable to ``float``
        ``IOError``: valid dat file is empty

    Returns:
        ``list``: nested list of float values of each row
    """
    try:
        with open(file_name, 'r', encoding="utf-8") as data_file:
            data = []
            for line in data_file:
                data.append([float(x) for x in line.split(sep=delim)])
    except FileNotFoundError as err:
        print(f"Could not find DAT file: {file_name}")
        raise err
    except ValueError:
        print(f"Parsing error reading DAT file: {file_name}")
        raise

    if not data:
        print(f"Empty DAT file: {file_name}")
        raise IOError

    return data


def saveMatrix(name, matrix, path=None):
    """Save a given matrix to a file for post processing.

    Args:
        name (``str``): name of matrix, used in the file name, & should adhere to good file-naming conventions.
        matrix (``numpy.ndarray``): matrix to be saved.
        path (``str``, optional): path of where to save the matrix. Defaults to ``None``, which
            means it will use the current working directory.

    Returns:
        ``str``: full path file name of matrix that was saved

    Raises:
        ``TypeError``: notifies when a bad type is passed for `matrix`
    """
    # Normalize path & use CWD if not specified
    if path is None:
        path = os.path.join(os.getcwd(), "matrix")
    path = os.path.realpath(
        os.path.abspath(path)
    )

    # Make directory
    if not os.path.isdir(path):
        os.makedirs(path)

    # Create timestamped filename
    now = datetime.utcnow()
    file_name = os.path.join(
        os.path.realpath(path),
        f"{name}_{now.isoformat()}.json"
    )
    # Save to file, convert to list if `numpy.ndarray`
    with open(file_name, 'w', encoding="utf-8") as out_file:
        if isinstance(matrix, list):
            json.dump(matrix, out_file)
        elif isinstance(matrix, np.ndarray):
            json.dump(matrix.tolist(), out_file)
        else:
            print("saveMatrix() only takes `list` and `np.ndarray` types for 'matrix' argument")
            raise TypeError(type(matrix))

    return file_name


def getTimeout(num_jobs, multiplier=5):
    """Determine the total job timeout length.

    Args:
        num_jobs (``int``): total number of jobs submitted to worker queue.
        multiplier (``int``, Optional): multiplies the timeout length. Defaults to 5.

    Returns:
        ``None | int``: either ``None`` for blocking behavior, or timeout length in seconds
    """
    if BehavioralConfig.getConfig().debugging.ParallelDebugMode:
        return None
    else:
        return multiplier * num_jobs


def checkTypes(_locals, _types):
    """Throw a ``TypeError`` if `_locals` doesn't match `_types`.

    Args:
        _locals (dict): Dictionary of local variables.
        _types (dict): Dictionary where keys are names of variables and values are the expected types.

    Raises:
        TypeError: If `_locals` doesn't match `_types`.
    """
    for var, _type in _types.items():
        val = _locals.get(var)
        if not isinstance(val, _type):
            err = f"Incorrect type for {var} param"
            raise TypeError(err)
