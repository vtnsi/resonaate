"""Defines the database models and classes for persistent data storage.

This module holds common functions and attributes used in many data modules.
"""
# Standard Library Imports
from datetime import datetime
from os import getcwd, makedirs
from os.path import abspath, dirname, exists, join, normpath

# Third Party Imports
from sqlalchemy.ext.declarative import declarative_base

# Local Imports
from ..common.logger import resonaateLogError

# Base declarative class used by SQLAlchemy to track ORM's
Base = declarative_base()  # pylint: disable=invalid-name


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
        right_now = datetime.now().isoformat().replace(":", "-").replace(".", "-")
        directory = abspath(join(getcwd(), "db"))
        if not exists(directory):
            makedirs(directory)
        db_path = f"sqlite:///{directory}/resonaate_{right_now}.sqlite3"

    return db_path


class _DataMixin:
    """Base class for objects that get stored via SQLAlchemy."""

    MUTABLE_COLUMN_NAMES = tuple()
    """tuple: Tuple of mutable column names."""

    def __repr__(self):
        """Define how :class:`.DataMixin` objects are represented as a ``str`` object.

        Returns:
            str: String representation of this :class:`.DataMixin` object.
        """
        if self.__class__.__name__ == "AgentModel":
            rep_str = f"{self.__class__}("
        else:
            rep_str = f"{self.__class__}(id={self.id}, "
        for field in self.MUTABLE_COLUMN_NAMES:
            rep_str += f"{field}={getattr(self, field)}, "
        rep_str += ")"

        return rep_str

    def __eq__(self, other):
        """Define how :class:`.DataMixin` objects can be compared to other objects (i.e. `==`, `!=`).

        Args:
            other (object): Object to compare this :class:`.DataMixin` object to.

        Returns:
            bool: Indicates if the two objects are equal.
        """
        if not isinstance(self, other.__class__):
            raise TypeError(f"Can't compare {type(self)} object to {type(other)} object.")

        return not any(
            getattr(self, attr) != getattr(other, attr) for attr in self.MUTABLE_COLUMN_NAMES
        )

    def makeDictionary(self):
        """Return a dictionary representation of this :class:`.DataMixin` object.

        Returns:
            dict: Dictionary representation of this :class:`.DataMixin` object.
        """
        retval = {}
        for field in self.MUTABLE_COLUMN_NAMES:
            retval[field] = getattr(self, field)

        return retval
