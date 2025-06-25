"""Various helper functions that are used across multiple modules."""

from __future__ import annotations

# Standard Library Imports
import json
import os
from json import JSONEncoder

# Third Party Imports
import numpy as np

# Local Imports
from . import pathSafeTime
from .behavioral_config import BehavioralConfig
from .logger import resonaateLogError


class NumpyArrayEncoder(JSONEncoder):
    """Handles serialization of a numpy array."""

    def default(self, obj):
        """Serializes a numpy array and returns it as a json.

        Args:
            obj (np.ndarray): Numpy array you wish to serialize

        Returns:
            list, Any: Serialized json.
        """
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)


def ndArrayToString(obj: np.ndarray) -> str:
    """Converts an instance of :class:`np.ndarray` to a json string.

    Args:
        obj (np.ndarray): The array you wish to convert.

    Returns:
        str: The array represented as a json string.
    """
    return json.dumps(obj, cls=NumpyArrayEncoder)


def stringToNdarray(json_string: str) -> np.ndarray:
    """Converts a serialized json string to a :class:`np.ndarray`.

    Args:
        json_string (str): The serialized json string you wish to convert.

    Returns:
        np.ndarray: Converted numpy array.
    """
    obj = json.loads(json_string)
    return np.array(obj)


def serializeArrayKwarg(name: str, kwargs: dict) -> dict:
    """Checks the kwargs if a specific name is present, then converts that parameter into a json string.

    It will also add a '_" prefix to the kwarg to indicate that it is supposed to be a private attribute.
    This is used primarily for handling ndarray to json string conversions within some db classes that
    contain array-based values.

    Args:
        name (str): The name of the keyword argument you are modifying. If it is not found in kwargs,
        this function will just return the original kwargs table.
        kwargs (dict): The keyword arguments.

    Returns:
        dict: The modified keyword arguments.
    """
    if name in kwargs:
        private_name: str = f"_{name}"
        arr: np.ndarray = kwargs[name]
        kwargs.pop(name)
        arr_str: str = ndArrayToString(arr)
        kwargs[private_name] = arr_str
    return kwargs


def getTypeString(class_instance):
    """Return the class type as a string without any base class information.

    Args:
        class_instance (generic class instance): instance of a general class

    Returns:
        ``str``: name of the class without base classes

    """
    return class_instance.__class__.__name__


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
        with open(file_name, encoding="utf-8") as input_file:
            json_data = json.load(input_file)
    except FileNotFoundError as err:
        msg = f"Could not find JSON file: {file_name}"
        resonaateLogError(msg)

        raise err
    except json.decoder.JSONDecodeError as err:
        msg = f"Decoding error reading JSON file: {file_name}"
        resonaateLogError(msg)

        raise err

    if not json_data:
        msg = f"Empty JSON file: {file_name}"
        resonaateLogError(msg)
        raise OSError(msg)

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
        ``ValueError``: error parsing dat file, likely because values are convertible to ``float``
        ``IOError``: valid dat file is empty

    Returns:
        ``list``: nested list of float values of each row
    """
    try:
        with open(file_name, encoding="utf-8") as data_file:
            data = [[float(x) for x in line.split(sep=delim)] for line in data_file]
    except FileNotFoundError as err:
        msg = f"Could not find DAT file: {file_name}"
        resonaateLogError(msg)
        raise err
    except ValueError as err:
        msg = f"Parsing error reading DAT file: {file_name}"
        resonaateLogError(msg)
        raise ValueError(msg) from err

    if not data:
        msg = f"Empty DAT file: {file_name}"
        resonaateLogError(msg)
        raise OSError(msg)

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
    path = os.path.realpath(os.path.abspath(path))

    # Make directory
    if not os.path.isdir(path):
        os.makedirs(path)

    # Create timestamped filename
    file_name = os.path.join(
        os.path.realpath(path),
        f"{name}_{pathSafeTime()}.json",
    )
    # Save to file, convert to list if `numpy.ndarray`
    with open(file_name, "w", encoding="utf-8") as out_file:
        if isinstance(matrix, list):
            json.dump(matrix, out_file)
        elif isinstance(matrix, np.ndarray):
            json.dump(matrix.tolist(), out_file)
        else:
            resonaateLogError(
                "saveMatrix() only takes `list` and `np.ndarray` types for 'matrix' argument",
            )
            raise TypeError(type(matrix))

    return file_name


def getTimeout(num_jobs, multiplier=5):
    """Determine the total job timeout length.

    Args:
        num_jobs (``int``): total number of jobs submitted to worker queue.
        multiplier (``int``, optional): multiplies the timeout length. Defaults to 5.

    Returns:
        ``None | int``: either ``None`` for blocking behavior, or timeout length in seconds
    """
    if BehavioralConfig.getConfig().debugging.ParallelDebugMode:
        return None

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
