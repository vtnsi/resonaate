"""Defines the database models and classes for persistent data storage.

This module holds common functions and attributes used in many data modules.
"""

from __future__ import annotations

# Standard Library Imports
from os import getcwd, makedirs
from os.path import abspath, dirname, exists, join, normpath
from pathlib import Path

# Third Party Imports
from sqlalchemy.engine import URL as AlchemyURL  # noqa: N811

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


SQLITE_DRIVER: str = "sqlite"
"""Driver name for using SQLite."""


def createAlchemyUrl(
    drivername: str | None = None,
    username: str | None = None,
    password: str | None = None,
    host: str | None = None,
    port: int | None = None,
    database: str | None = None,
    exists_ok: bool = False,
) -> AlchemyURL:
    """Create an `sqlalchemy.engine.URL` object used to connect to a database.

    Args:
        drivername: The name of the database backend. This will default to "sqlite".
        username: The user name.
        password: Database password.
        host: The name of the host.
        port: The port number.
        database: The database name. For an SQLite database, this is the path to the database
            file. If using SQLite, this will default to a timestamped file in a "db" directory
            relative to the current working directory.
        exists_ok: Flag indicating whether it's ok that the specified SQLite database file
            already exists.

    Returns:
        `sqlalchemy.engine.URL` object used to connect to a database.

    Raises:
        FileExistsError: Thrown if using SQLite, `exists_ok` is False, and `database` points to
            a file that already exists.
    """
    if not drivername:
        drivername = SQLITE_DRIVER

    if drivername == SQLITE_DRIVER:
        if database:
            db_path = Path(database)
            if not exists_ok:
                if db_path.exists():
                    msg = f"Cannot overwrite existing database: {db_path}"
                    resonaateLogError(msg)
                    raise FileExistsError(db_path)

                if not db_path.parent.exists():
                    db_path.parent.mkdir(parents=True)

        else:  # sqlite database path not provided
            db_path = Path.cwd() / "db" / f"resonaate_{pathSafeTime()}.sqlite3"
            if not db_path.parent.exists():
                db_path.parent.mkdir(parents=True)
            database = str(db_path)

    return AlchemyURL.create(
        drivername=drivername,
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
    )
