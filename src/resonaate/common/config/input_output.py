"""Define configuration parameters pertaining to the input and output of RESONAATE."""

from __future__ import annotations

# Standard Library Imports
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Optional

# Third Party Imports
from pydantic import BaseModel, Field
from sqlalchemy.engine import URL as AlchemyURL

# Local Imports
from .. import pathSafeTime
from .meta import CommandLineOptions, EnvName

# ruff: noqa: TCH001, TCH003, UP007

SQLITE_DRIVER: str = "sqlite"
"""Driver name for using SQLite."""


class AlchemyURLSpec(BaseModel):
    """Specifies required parameters to generate an SQLAlchemy connection to a database."""

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

    drivername: Annotated[
        Optional[str],
        Field(
            default=SQLITE_DRIVER,
            description="The name of the importer database backend.",
        ),
        EnvName("IMPORTER_DB_DRIVER"),
        CommandLineOptions("--importer-db-driver"),
    ]

    username: Annotated[
        Optional[str],
        Field(
            default=None,
            description="The user name used to connect to the importer database.",
        ),
        EnvName("IMPORTER_DB_USER"),
        CommandLineOptions("--importer-db-user"),
    ]

    password: Annotated[
        Optional[str],
        Field(
            default=None,
            description="The password used to connect to the importer database.",
        ),
        EnvName("IMPORTER_DB_PASSWORD"),
        CommandLineOptions("--importer-db-password"),
    ]

    host: Annotated[
        Optional[str],
        Field(
            default=None,
            description="The host name of the importer database.",
        ),
        EnvName("IMPORTER_DB_HOST"),
        CommandLineOptions("--importer-db-host"),
    ]

    port: Annotated[
        Optional[str],
        Field(
            default=None,
            description="The port number that the importer database accepts connections on.",
        ),
        EnvName("IMPORTER_DB_PORT"),
        CommandLineOptions("--importer-db-port"),
    ]

    database: Annotated[
        Optional[str],
        Field(
            default=None,
            description=dedent("""\
            The name used for the importer database.

            For an SQLite database (the default used by RESONAATE), this is the path to the database
            file. If the default SQLite driver is used and this field is left unspecified, it will
            automatically be populated with a timestamped file in a "db" directory relative to the
            current working directory."""),
        ),
        EnvName("IMPORTER_DB_NAME"),
        CommandLineOptions("--importer-db-name"),
    ]

    exists_ok: Optional[bool] = True
    """Flag indicating whether it's ok that the specified SQLite database file already exists."""


class OutputDbUrlSpec(AlchemyURLSpec):
    """Specifies required parameters to connect to a RESONAATE output database via SQLAlchemy."""

    drivername: Annotated[
        Optional[str],
        Field(
            default=SQLITE_DRIVER,
            description="The name of the output database backend.",
        ),
        EnvName("OUTPUT_DB_DRIVER"),
        CommandLineOptions("--output-db-driver"),
    ]

    username: Annotated[
        Optional[str],
        Field(
            default=None,
            description="The user name used to connect to the output database.",
        ),
        EnvName("OUTPUT_DB_USER"),
        CommandLineOptions("--output-db-user"),
    ]

    password: Annotated[
        Optional[str],
        Field(
            default=None,
            description="The password used to connect to the output database.",
        ),
        EnvName("OUTPUT_DB_PASSWORD"),
        CommandLineOptions("--output-db-password"),
    ]

    host: Annotated[
        Optional[str],
        Field(
            default=None,
            description="The host name of the output database.",
        ),
        EnvName("OUTPUT_DB_HOST"),
        CommandLineOptions("--output-db-host"),
    ]

    port: Annotated[
        Optional[str],
        Field(
            default=None,
            description="The port number that the output database accepts connections on.",
        ),
        EnvName("OUTPUT_DB_PORT"),
        CommandLineOptions("--output-db-port"),
    ]

    database: Annotated[
        Optional[str],
        Field(
            default=None,
            description=dedent("""\
            The name used for the output database.

            For an SQLite database (the default used by RESONAATE), this is the path to the database
            file. If the default SQLite driver is used and this field is left unspecified, it will
            automatically be populated with a timestamped file in a "db" directory relative to the
            current working directory."""),
        ),
        EnvName("OUTPUT_DB_NAME"),
        CommandLineOptions("--output-db-name"),
    ]

    exists_ok: Optional[bool] = False
    """Flag indicating whether it's ok that the specified SQLite database file already exists."""


class IOConfiguration(BaseModel):
    """Configuration section defining how RESONAATE I/O should work."""

    init_file: Annotated[
        Path,
        Field(
            description="Path to RESONAATE initialization message file.",
        ),
    ]

    import_config: ImporterDbUrlSpec = ImporterDbUrlSpec()

    output_db_parameters: OutputDbUrlSpec = OutputDbUrlSpec()
