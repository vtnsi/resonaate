"""Define configuration parameters pertaining to the input and output of RESONAATE."""

# ruff: noqa: UP007

from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Optional

# Third Party Imports
from pydantic import Field, model_validator
from sqlalchemy.engine import URL as AlchemyURL  # noqa: N811
from sqlalchemy.engine import make_url
from typing_extensions import Self

# Local Imports
from .. import pathSafeTime
from .meta import CommandLineOptions, EnvName, UserBaseModel

SQLITE_DRIVER: str = "sqlite"
"""Driver name for using SQLite."""


class AlchemyURLSpec(ABC, UserBaseModel):
    """Specifies required parameters to generate an SQLAlchemy connection to a database."""

    @property
    @abstractmethod
    def drivername(self) -> str:
        """The name of the database backend."""
        raise NotImplementedError

    @property
    @abstractmethod
    def username(self) -> str:
        """The user name used to connect to the database."""
        raise NotImplementedError

    @property
    @abstractmethod
    def password(self) -> str:
        """The password used to connect to the database."""
        raise NotImplementedError

    @property
    @abstractmethod
    def host(self) -> str:
        """The host name of the database."""
        raise NotImplementedError

    @property
    @abstractmethod
    def port(self) -> int:
        """The port number that the database accepts connections on."""
        raise NotImplementedError

    @property
    @abstractmethod
    def database(self) -> str:
        """The name used for the database.

        For an SQLite database, this is the path to the database file.
        """
        raise NotImplementedError

    @database.setter
    @abstractmethod
    def database(self, value: str):
        """Set the name of the database.

        Args:
            value: New database name to use.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def exists_ok(self) -> bool:
        """Flag indicating whether it's ok that the specified SQLite database file already exists."""
        raise NotImplementedError

    def getURL(self) -> AlchemyURL:
        """Build the `sqlalchemy.engine.URL` connection object described by this specification."""
        return AlchemyURL.create(
            drivername=self.drivername,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    def checkExists(self):
        """Verify that instantiating the specified database won't overwrite an existing database.

        Raises:
            FileExistsError: If instantiating the specified database will overwrite an existing database.
        """
        if self.drivername == SQLITE_DRIVER and self.database is not None:
            db_path = Path(self.database)
            if not self.exists_ok:
                if db_path.exists():
                    msg = f"Cannot overwrite existing database: {db_path}"
                    raise FileExistsError(msg)

                if not db_path.parent.exists():
                    db_path.parent.mkdir(parents=True)


class ImporterDbUrlSpec(AlchemyURLSpec):
    """Specifies required parameters to connect to a RESONAATE Importer database via SQLAlchemy."""

    importer_db_driver: Annotated[
        str | None,
        Field(default=SQLITE_DRIVER),
        EnvName("IMPORTER_DB_DRIVER"),
        CommandLineOptions("--importer-db-driver"),
    ]
    """The name of the importer database backend."""

    importer_db_username: Annotated[
        Optional[str],
        Field(default=None),
        EnvName("IMPORTER_DB_USER"),
        CommandLineOptions("--importer-db-user"),
    ]
    """The user name used to connect to the importer database."""

    importer_db_password: Annotated[
        Optional[str],
        Field(default=None),
        EnvName("IMPORTER_DB_PASSWORD"),
        CommandLineOptions("--importer-db-password"),
    ]
    """The password used to connect to the importer database."""

    importer_db_host: Annotated[
        Optional[str],
        Field(default=None),
        EnvName("IMPORTER_DB_HOST"),
        CommandLineOptions("--importer-db-host"),
    ]
    """The host name of the importer database."""

    importer_db_port: Annotated[
        Optional[str],
        Field(default=None),
        EnvName("IMPORTER_DB_PORT"),
        CommandLineOptions("--importer-db-port"),
    ]
    """The port number that the importer database accepts connections on."""

    importer_db_name: Annotated[
        str,
        Field(default=None, validate_default=True),
        EnvName("IMPORTER_DB_NAME"),
        CommandLineOptions("--importer-db-name"),
    ]
    """The name used for the importer database.

    For an SQLite database, this is the path to the database file.
    """

    importer_db_exists_ok: Optional[bool] = True
    """Flag indicating whether it's ok that the specified SQLite database file already exists."""

    @property
    def drivername(self) -> str:
        """The name of the database backend."""
        return self.importer_db_driver

    @property
    def username(self) -> str:
        """The user name used to connect to the database."""
        return self.importer_db_username

    @property
    def password(self) -> str:
        """The password used to connect to the database."""
        return self.importer_db_password

    @property
    def host(self) -> str:
        """The host name of the database."""
        return self.importer_db_host

    @property
    def port(self) -> int:
        """The port number that the database accepts connections on."""
        return self.importer_db_port

    @property
    def database(self) -> str:
        """The name used for the database.

        For an SQLite database, this is the path to the database file.
        """
        return self.importer_db_name

    @database.setter
    def database(self, value: str):
        """Set the name of the database.

        Args:
            value: New database name to use.
        """
        self.importer_db_name = value

    @property
    def exists_ok(self) -> bool:
        """Flag indicating whether it's ok that the specified SQLite database file already exists."""
        return self.importer_db_exists_ok


class OutputDbUrlSpec(AlchemyURLSpec):
    """Specifies required parameters to connect to a RESONAATE output database via SQLAlchemy."""

    output_db_driver: Annotated[
        Optional[str],
        Field(default=SQLITE_DRIVER),
        EnvName("OUTPUT_DB_DRIVER"),
        CommandLineOptions("--output-db-driver"),
    ]
    """The name of the output database backend."""

    output_db_username: Annotated[
        Optional[str],
        Field(default=None),
        EnvName("OUTPUT_DB_USER"),
        CommandLineOptions("--output-db-user"),
    ]
    """The user name used to connect to the output database."""

    output_db_password: Annotated[
        Optional[str],
        Field(default=None),
        EnvName("OUTPUT_DB_PASSWORD"),
        CommandLineOptions("--output-db-password"),
    ]
    """The password used to connect to the output database."""

    output_db_host: Annotated[
        Optional[str],
        Field(default=None),
        EnvName("OUTPUT_DB_HOST"),
        CommandLineOptions("--output-db-host"),
    ]
    """The host name of the output database."""

    output_db_port: Annotated[
        Optional[str],
        Field(default=None),
        EnvName("OUTPUT_DB_PORT"),
        CommandLineOptions("--output-db-port"),
    ]
    """The port number that the output database accepts connections on."""

    output_db_name: Annotated[
        Optional[str],
        Field(default=None),
        EnvName("OUTPUT_DB_NAME"),
        CommandLineOptions("--output-db-name"),
    ]
    """The name used for the output database.

    For an SQLite database (the default used by RESONAATE), this is the path to the database file. If the
    default SQLite driver is used and this field is left unspecified, it will automatically be populated with
    a timestamped file in a "db" directory relative to the current working directory.
    """

    output_db_exists_ok: Optional[bool] = False
    """Flag indicating whether it's ok that the specified SQLite database file already exists."""

    @property
    def drivername(self) -> str:
        """The name of the database backend."""
        return self.output_db_driver

    @property
    def username(self) -> str:
        """The user name used to connect to the database."""
        return self.output_db_username

    @property
    def password(self) -> str:
        """The password used to connect to the database."""
        return self.output_db_password

    @property
    def host(self) -> str:
        """The host name of the database."""
        return self.output_db_host

    @property
    def port(self) -> int:
        """The port number that the database accepts connections on."""
        return self.output_db_port

    @property
    def database(self) -> str:
        """The name used for the database.

        For an SQLite database, this is the path to the database file.
        """
        return self.output_db_name

    @database.setter
    def database(self, value: str):
        """Set the name of the database.

        Args:
            value: New database name to use.
        """
        self.output_db_name = value

    @property
    def exists_ok(self) -> bool:
        """Flag indicating whether it's ok that the specified SQLite database file already exists."""
        return self.output_db_exists_ok

    @model_validator(mode="after")
    def conditional_validate_database(self) -> Self:
        """Generate a default path for an SQLite database, if none was provided."""
        if self.drivername == SQLITE_DRIVER and self.database is None:
            db_path = Path.cwd() / "db" / f"resonaate_{pathSafeTime()}.sqlite3"
            if not db_path.parent.exists():
                db_path.parent.mkdir(parents=True)
            self.database = str(db_path)

        return self


class InMemoryDbSpec(AlchemyURLSpec):
    """Connection parameters for an in-memory SQLite database."""

    @property
    def drivername(self) -> str:
        """The in-memory database is based on SQLite."""
        raise SQLITE_DRIVER

    @property
    def username(self) -> str:
        """No username for in-memory database."""
        return None

    @property
    def password(self) -> str:
        """No password for in-memory database."""
        return None

    @property
    def host(self) -> str:
        """No host for in-memory database."""
        return None

    @property
    def port(self) -> int:
        """No port number for in-memory database."""
        return None

    @property
    def database(self) -> str:
        """No name for in-memory database."""
        return None

    @database.setter
    def database(self, value: str):
        """Set the name of the database.

        Args:
            value: New database name to use.
        """
        raise NotImplementedError

    @property
    def exists_ok(self) -> bool:
        """Assume it's fine if in-memory database already exists."""
        return True

    def getURL(self) -> AlchemyURL:
        """Build the `sqlalchemy.engine.URL` connection object for the in-memory database."""
        return make_url(f"{self.drivername}//")


class InputConfig(UserBaseModel):
    """Configuration section defining how RESONAATE consumes input."""

    init_file: Path
    """Path to RESONAATE initialization message file."""

    importer_db_params: Optional[ImporterDbUrlSpec] = None
    """Connection parameters specifying how to connect to the importer database."""

    sim_duration: Annotated[
        Optional[float],
        Field(default=None),
        CommandLineOptions("-t", "--time"),
        EnvName("SIM_DURATION"),
    ]
    """Optional argument specifying how long (in hours) to run the simulation.

    Useful for shortening sanity check tests. If left unspecified, the simulation will adhere to the end
    time specified in the RESONAATE init message.
    """

    @property
    def sim_duration_timedelta(self) -> timedelta:
        """:attr:`.sim_duration` represented as a ``datetime.timedelta`` object."""
        if self.sim_duration is not None:
            return timedelta(hours=self.sim_duration)
        return None
