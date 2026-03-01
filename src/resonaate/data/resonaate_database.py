"""Defines the :class:`.ResonaateDatabase` shared data interface class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ..common.config import RootConfig
from .data_interface import DataInterface

if TYPE_CHECKING:
    # Local Imports
    from ..common.config.input_output import AlchemyURLSpec
    from ..common.logger import Logger


class ResonaateDatabase(DataInterface):
    """Main generic data interface that is DB agnostic."""

    def __init__(
        self,
        connection_params: AlchemyURLSpec | None = None,
        drop_tables: tuple[str] = (),
        logger: Logger | None = None,
        verbose_echo: bool = False,
    ) -> None:
        """Instantiate an interface that encapsulates common RESONAATE database interactions.

        Args:
            connection_params: Collection of parameters specifying how to connect to the database shared
                across RESONAATE modules.
            drop_tables: Iterable of table names to be dropped at time of construction. In a pre-existing
                database, a user can specify which data that they don't want to keep.
            logger: Previously instantiated logging object to use.
            verbose_echo: Flag indicating whether SQLAlchemy engine should log the raw SQL statements that it
                executes.
        """
        # Last resort, use behavior config for DB
        if connection_params is None:
            root_cfg = RootConfig.LIB.inst()
            connection_params = root_cfg.output_config

        # Instantiate the data interface object
        super().__init__(connection_params, drop_tables, logger, verbose_echo)

    def saveDatabase(self, new_db_params: AlchemyURLSpec):
        """Copy data from an existing instance of :class:`.ResonaateDatabase` to a new instance.

        Args:
            new_db_params: Collection of parameters specifying how to connect to the destination database.
        """
        # Create auto-generated DB path
        self.logger.info(f"Copying database to: {new_db_params.model_dump()}")

        # Get instance of internal DB. Create a different instance to copy to
        new_database = ResonaateDatabase(connection_params=new_db_params)

        # Get raw connections
        raw_connection_memory = self.engine.raw_connection()
        raw_connection_file = new_database.engine.raw_connection()

        # Progress print statement for backup function
        def progress(status, remaining, total):
            print(f"Copied {total - remaining} of {total} pages...")  # noqa: T201

        # Perform backup
        raw_connection_memory.backup(raw_connection_file.driver_connection, progress=progress)

        # Close raw connections
        raw_connection_memory.close()
        raw_connection_file.close()
