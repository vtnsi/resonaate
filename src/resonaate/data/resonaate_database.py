"""Defines the :class:`.ResonaateDatabase` shared data interface class."""

from __future__ import annotations

# Local Imports
from ..common.behavioral_config import BehavioralConfig
from . import createDatabasePath
from .data_interface import DataInterface


class ResonaateDatabase(DataInterface):
    """Main generic data interface that is DB agnostic."""

    __shared_inst = None

    def __init__(self, db_path=None, drop_tables=(), logger=None, verbose_echo=False):
        """Create SQLite database based on :attr:`.VALID_DATA_TYPES` .

        Args:
            db_path (``str``, optional): SQLAlchemy-accepted string denoting what database implementation
                to use and where the database is located. Defaults to default configuration value.
            drop_tables (``iterable``, optional): Iterable of table names to be dropped at time of
                :class:`.DataInterface` construction. This parameter makes sense in the context of
                utilizing a pre-existing database that a user may not want to keep data from.
                Defaults to an empty tuple, resulting in no tables being dropped.
            logger (:class:`.Logger`, optional): Previously instantiated logging object to use. Defaults to ``None``,
                resulting in a new :class:`.Logger` instance being instantiated.
            verbose_echo (``bool``, optional): Flag that if set ``True``, will tell the SQLAlchemy
                engine to output the raw SQL statements it runs. Defaults to ``False``.
        """
        # Last resort, use behavior config for DB
        if not db_path:
            db_path = BehavioralConfig.getConfig().database.DatabasePath

        # Instantiate the data interface object
        super().__init__(db_path, drop_tables, logger, verbose_echo)

        # [NOTE][force-db-path]: Log the location here so it is obvious if the intended DB path
        #    is not being used.
        self.logger.debug(f"Database path: {db_path}")

    def saveDatabase(self, database_path=None):
        """Copy data from an existing instance of :class:`.ResonaateDatabase` to a new instance.

        Args:
            database_path (``str``): desired path to the new database. Default is `None`, which
                results in auto-generating a DB in the current directory.
        """
        # Create auto-generated DB path
        db_path = createDatabasePath(database_path)
        self.logger.info(f"Copying database to: {db_path}")

        # Get instance of internal DB. Create a different instance to copy to
        new_database = ResonaateDatabase(db_path=db_path)

        # Get raw connections
        raw_connection_memory = self.engine.raw_connection()
        raw_connection_file = new_database.engine.raw_connection()

        # Progress print statement for backup function
        def progress(status, remaining, total):
            print(f"Copied {total-remaining} of {total} pages...")  # noqa: T201

        # Perform backup
        raw_connection_memory.backup(raw_connection_file.driver_connection, progress=progress)

        # Close raw connections
        raw_connection_memory.close()
        raw_connection_file.close()
