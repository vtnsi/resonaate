"""Define configuration parameters pertaining to the input and output of RESONAATE."""

from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Annotated, Optional

# Third Party Imports
from pydantic import Field, ValidationError, field_validator
from sqlalchemy.engine import URL as AlchemyURL  # noqa: N811

# Local Imports
from .. import pathSafeTime
from .meta import CommandLineOptions, EnvName, UserBaseModel

# ruff: noqa: TCH001, TCH003, UP007

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

    @property
    @abstractmethod
    def exists_ok(self) -> bool:
        """Flag indicating whether it's ok that the specified SQLite database file already exists."""
        raise NotImplementedError

    def getURL(self) -> AlchemyURL:
        """Build the `sqlalchemy.engine.URL` connection object described by this specification."""
        if self.drivername == SQLITE_DRIVER:
            if self.database:
                db_path = Path(self.database)
                if not self.exists_ok:
                    if db_path.exists():
                        msg = f"Cannot overwrite existing database: {db_path}"
                        raise FileExistsError(msg)

                    if not db_path.parent.exists():
                        db_path.parent.mkdir(parents=True)

            else:  # sqlite database path not provided
                db_path = Path.cwd() / "db" / f"resonaate_{pathSafeTime()}.sqlite3"
                if not db_path.parent.exists():
                    db_path.parent.mkdir(parents=True)
                self.database = str(db_path)

        return AlchemyURL.create(
            drivername=self.drivername,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )


class ImporterDbUrlSpec(AlchemyURLSpec):
    """Specifies required parameters to connect to a RESONAATE Importer database via SQLAlchemy."""

    importer_db_driver: Annotated[
        Optional[str],
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
        Optional[str],
        Field(default=None),
        EnvName("IMPORTER_DB_NAME"),
        CommandLineOptions("--importer-db-name"),
    ]
    """The name used for the importer database.

    For an SQLite database, this is the path to the database file.
    """

    @field_validator("importer_db_name", mode="after")
    @classmethod
    def validateImporterDbName(cls, value) -> str:
        """Make sure importer database name is set.

        Note:
            While it would typically make sense to just _not_ mark the type annotation as `Optional`, it's
            problematic in this case because :meth:`.UserSpec.addToArgParser()` will then interpret
            :attr:`.importer_db_name` as a required positional argument. The :attr:`.importer_db_name` is
            only required when the parent :class:`.ImporterDbUrlSpec` is specified, and so the easiest
            implementation is to validate here in a `field_validator`.

            In the future, should more required sub-attributes be added to the configuration specification,
            perhaps the :meth:`.UserSpec.addToArgParser()` method will need to be revised.
        """
        if value is None:
            err = "User provided importer database specification without a name"
            raise ValidationError(err)
        return value

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

    @property
    def exists_ok(self) -> bool:
        """Flag indicating whether it's ok that the specified SQLite database file already exists."""
        return self.output_db_exists_ok


class InputConfig(UserBaseModel):
    """Configuration section defining how RESONAATE consumes input."""

    init_file: Path
    """Path to RESONAATE initialization message file."""

    importer_db_params: Optional[ImporterDbUrlSpec] = None
    """Connection parameters specifying how to connect to the importer database."""
