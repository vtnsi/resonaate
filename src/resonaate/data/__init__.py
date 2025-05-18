"""Defines the database models and classes for persistent data storage.

This module holds common functions and attributes used in many data modules.
"""

from __future__ import annotations

# Standard Library Imports
from os import getcwd, makedirs
from os.path import abspath, dirname, exists, join, normpath

# Local Imports
from ..common import pathSafeTime
from ..common.logger import resonaateLogError
from .agent import AgentModel
from .db_connection import clearDBPath, getDBConnection, setDBPath
from .detected_maneuver import DetectedManeuver
from .ephemeris import EstimateEphemeris, TruthEphemeris
from .epoch import Epoch
from .filter_step import FilterStep, ParticleFilterStep, SequentialFilterStep
from .observation import Observation
from .task import Task

__all__ = [
    "AgentModel",
    "DetectedManeuver",
    "Epoch",
    "EstimateEphemeris",
    "FilterStep",
    "Observation",
    "ParticleFilterStep",
    "SequentialFilterStep",
    "Task",
    "TruthEphemeris",
    "clearDBPath",
    "createDatabasePath",
    "getDBConnection",
    "setDBPath",
]


def createDatabasePath(path, importer=False):
    """Create a valid path for the database.

    Args:
        path (``str``): path-like string to the desired database file location.
        importer (``bool``, optional): whether database file is imported. Defaults to ``False``.

    Returns:
        ``str``: properly formatted database path. Defaults to timestamped path
            in **db** directory if ``None`` is passed.
    """
    if path:
        db_path = f"sqlite:///{normpath(abspath(path))}"
        directory = abspath(dirname(path))
        if not importer:
            if exists(abspath(path)):
                msg = f"Cannot overwrite existing database: {db_path}"
                resonaateLogError(msg)
                raise FileExistsError(path)

            if not exists(directory):
                makedirs(directory)

    else:
        directory = abspath(join(getcwd(), "db"))
        if not exists(directory):
            makedirs(directory)
        db_path = f"sqlite:///{directory}/resonaate_{pathSafeTime()}.sqlite3"

    return db_path
