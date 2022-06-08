# Standard Library Imports
import argparse
import json
from datetime import datetime
# Third Party Imports
import yaml
# RESONAATE Imports
from .behavioral_config import BehavioralConfig


def getTypeString(class_instance):
    """Return the class type as a string without any base class information.

    Args:
        class_instance (generic class instance): instance of a general class

    Returns:
        str: name of the class without base classes

    """
    return class_instance.__class__.__name__


def loadYAMLFile(file_name):
    """Load in a YAML file into a Python dictionary.

    Args:
        file_name (str): name of YAML file to load

    Raises:
        IOError: helps with debugging bad filenames

    Returns:
        dict: documents loaded from the YAML file
    """
    try:
        with open(file_name, 'r') as input_file:
            yaml_data = yaml.safe_load(input_file)
    except IOError:
        print("Error reading YAML file: {0}".format(file_name))
        raise

    if not yaml_data:
        print("Empty YAML file: {0}".format(file_name))
        raise IOError

    return yaml_data


def loadJSONFile(file_name):
    """Load in a JSON file into a Python dictionary.

    Args:
        file_name (str): name of JSON file to load

    Raises:
        IOError: helps with debugging bad filenames

    Returns:
        dict: documents loaded from the JSON file
    """
    try:
        with open(file_name, 'r') as input_file:
            json_data = json.load(input_file)
    except json.decoder.JSONDecodeError:
        print("Error reading JSON file: {0}".format(file_name))
        raise

    if not json_data:
        print("Empty JSON file: {0}".format(file_name))
        raise IOError

    return json_data


def parseCommandLineArguments():
    """Parse command line parameters.

    Returns
        (:class:`argparse.Namespace`): return Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="RESONAATE Command Line Interface")
    message_i = "Path to RESONAATE initialization message file"
    parser.add_argument("init_msg", metavar="INIT_FILE", help=message_i, type=str)
    message_t = "Time in hours to simulate. DEFAULT: 1/2 hour."
    parser.add_argument("-t", dest="sim_time_hours", metavar="HOURS", default=0.5, type=float, help=message_t)
    message_no_output = "Turns off output database."
    parser.add_argument("--no-db", dest="output_db", action="store_false", default=True, help=message_no_output)
    message_db_path = "Path to desired output database"
    parser.add_argument("-o", dest="output_db_path", metavar="DB_PATH", default=None, help=message_db_path)
    message_debug_mode = "Turns on parallel debug mode."
    parser.add_argument("--debug", dest="debug_mode", action="store_true", default=False, help=message_debug_mode)

    return parser.parse_args()


def saveMatrix(name, matrix):
    """Save a given matrix to a file for post processing.

    Args:
        name (str): Name of matrix, used in the file name, & should adhere to good file-naming conventions.
        matrix (``numpy.ndarray``): Matrix to be saved.
    """
    now = datetime.utcnow()
    file_name = "matrices/{0}_{1}.json".format(name, now.isoformat())
    with open(file_name, 'w') as out_file:
        json.dump(matrix.tolist(), out_file)


def getTimeout(sequence, multiplier=5):
    """Determine the worker task timeout length.

    Args:
        sequence (``list``): sequence object for determining timeout length
        multiplier (``int``, Optional): multiplies the timeout length. Defaults to 5.

    Returns:
        ``None | int``: either ``None`` for blocking behavior, or timeout length in seconds
    """
    if BehavioralConfig.getConfig().debugging.ParallelDebugMode:
        return None
    else:
        return multiplier * len(sequence)
