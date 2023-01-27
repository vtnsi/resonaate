"""Defines the :class:`.ResonaateDatabase` shared data interface class."""
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

    @classmethod
    def getSharedInterface(cls, db_path=None, drop_tables=(), logger=None, verbose_echo=False):
        """Return a reference to the singleton shared interface.

        Args:
            db_path (``str``, optional): SQLAlchemy-accepted string denoting what database implementation
                to use and where the database is located. Defaults to default configuration value.
            drop_tables (``iterable``, optional): Iterable of table names to be dropped at time of construction. This
                parameter makes sense in the context of utilizing a pre-existing database that a user may not want to
                keep data from. Defaults to an empty tuple, resulting in no tables being dropped.
            logger (:class:`.Logger`, optional): Previously instantiated logging object to use. Defaults to ``None``,
                resulting in a new :class:`.Logger` instance being instantiated.
            verbose_echo (``bool``, optional): Flag that if set ``True``, will tell the SQLAlchemy
                engine to output the raw SQL statements it runs. Defaults to ``False``.

        Returns:
            :class:`.DataInterface`: reference to singleton shared data interface
        """
        # [NOTE][shared-data-resetting] Instantiating the singleton shared interface will no
        #   longer result in any of the database's tables being reset. While it makes sense to
        #   clean the table(s) holding temporary data (e.g. historical data or user-created
        #   manual sensor tasks) before or after each unrelated Resonaate run, it should no
        #   longer be done implicitly with shared interface instantiation. The reason for
        #   this is the multi-processing context in which Resonaate now performs. Should a
        #   separate process utilize the shared interface, the allocation of the singleton
        #   shared interface isn't guaranteed depending on when the separate process was
        #   forked versus when the shared interface was first utilized.
        if cls.__shared_inst is None:
            cls.__shared_inst = cls(db_path, drop_tables, logger, verbose_echo)

        return cls.__shared_inst

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
        def progress(status, remaining, total):  # pylint: disable=unused-argument
            print(f"Copied {total-remaining} of {total} pages...")

        # Perform backup
        raw_connection_memory.backup(raw_connection_file.driver_connection, progress=progress)

        # Close raw connections
        raw_connection_memory.close()
        raw_connection_file.close()
