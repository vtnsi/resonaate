# Standard Library Imports
import argparse
import logging
import os.path
# Third Party Imports
# RESONAATE Imports


def fileChecker(filepath):
    """Checks for valid filepaths passed to the CLI parser.

    Args:
        filepath (``str``): filepath given to CLI parser.

    Raises:
        ValueError: if the file does not exist

    Returns:
        ``str``: fully validated, absolute path to the file
    """
    filepath = os.path.abspath(os.path.realpath(os.path.normpath(filepath)))
    if not os.path.isfile(filepath):
        logging.getLogger("resonaate").error("Bad filepath given to CLI")
        raise ValueError(filepath)
    return filepath


def getCommandLineParser():
    """Create parser for command line arguments.

    Returns
        ``argparse.ArgumentParser``: valid parser object
    """
    parser = argparse.ArgumentParser(description="RESONAATE Command Line Interface")
    db_group = parser.add_argument_group("Database Files")
    db_opts = parser.add_argument_group("Database Options")

    parser.add_argument(
        "init_msg",
        metavar="INIT_FILE",
        type=fileChecker,
        help="Path to RESONAATE initialization message file"
    )

    parser.add_argument(
        "-t",
        "--time",
        dest="sim_time_hours",
        metavar="HOURS",
        default=0.5,
        type=float,
        help="Time in hours to simulate. DEFAULT: 1/2 hour"
    )

    parser.add_argument(
        "--debug",
        dest="debug_mode",
        action="store_true",
        default=False,
        help="Turns on parallel debug mode"
    )

    db_opts.add_argument(
        "--no-db",
        dest="db_save",
        action="store_false",
        default=True,
        help="Turns off output database, overriding all other options"
    )

    db_opts.add_argument(
        "--auto-db",
        dest="auto_db",
        action="store_true",
        default=False,
        help="Auto-generate RESONAATE DB path to {cwd}/db/"
    )

    db_group.add_argument(
        "-d",
        "--db-path",
        dest="db_path",
        metavar="DB_PATH",
        default=None,
        type=str,
        help="Path to RESONAATE database"
    )

    db_group.add_argument(
        "-i",
        "--importer-db-path",
        dest="importer_db_path",
        metavar="IMPORTER_DB_PATH",
        default=None,
        type=fileChecker,
        help="Path to Importer database"
    )

    return parser
