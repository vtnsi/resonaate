"""Defines the :class:`.DataInterface` abstract base class."""
# Standard Library Imports
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from traceback import format_exc

# Third Party Imports
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query, sessionmaker
from sqlalchemy.pool import StaticPool

# Local Imports
from ..common.behavioral_config import BehavioralConfig
from ..common.logger import Logger
from . import Base
from .agent import AgentModel
from .detected_maneuver import DetectedManeuver
from .ephemeris import EstimateEphemeris, TruthEphemeris
from .epoch import Epoch
from .events import Event
from .filter_step import FilterStep
from .observation import MissedObservation, Observation
from .task import Task


class DataInterface(metaclass=ABCMeta):
    """Common data interface that is DB agnostic.

    This defines the common data model by which all RESONAATE DBs are assumed to adhere to.
    """

    # pylint: disable=no-member
    VALID_DATA_TYPES = {
        AgentModel.__tablename__: AgentModel,
        Epoch.__tablename__: Epoch,
        DetectedManeuver.__tablename__: DetectedManeuver,
        EstimateEphemeris.__tablename__: EstimateEphemeris,
        Event.__tablename__: Event,
        FilterStep.__tablename__: FilterStep,
        MissedObservation.__tablename__: MissedObservation,
        Observation.__tablename__: Observation,
        Task.__tablename__: Task,
        TruthEphemeris.__tablename__: TruthEphemeris,
    }

    SQLITE_PREFIX = "sqlite://"

    def __init__(self, db_path, drop_tables, logger, verbose_echo):
        """Create SQLite database based on :attr:`.VALID_DATA_TYPES` .

        Args:
            db_path (``str``): SQLAlchemy-accepted string denoting what database implementation to
                use and where the database is located.
            drop_tables (``iterable``): Iterable of table names to be dropped at time of construction. This parameter
                makes sense in the context of utilizing a pre-existing database that a user may not want to keep
                data from.
            logger (:class:`.Logger`): Previously instantiated logging object to use.
            verbose_echo (``bool``): Flag that if set ``True``, will tell the SQLAlchemy engine to
                output the raw SQL statements it runs.
        """
        self.logger = logger
        if self.logger is None:
            self.logger = Logger(
                "resonaate", path=BehavioralConfig.getConfig().logging.OutputLocation
            )

        if db_path.startswith(self.SQLITE_PREFIX):
            # Squash warnings in sqlite about thread safety. The only times that sqlite will be
            # used in a multi-threaded context is read-only (and thus thread safe)
            self.engine = create_engine(
                db_path,
                echo=verbose_echo,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self.engine = create_engine(db_path, echo=verbose_echo)

        self.resetData(tables=drop_tables)
        self.session_factory = sessionmaker(bind=self.engine)

    @classmethod
    @abstractmethod
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
        raise NotImplementedError

    @contextmanager
    def _getSessionScope(self, **kwargs):
        """Provide a transactional scope around a series of operations.

        Args:
            kwargs (``dict``): optional arguments to pass to `Session` factory

        Yields:
            :class:`sqlalchemy.orm.session.Session`: establishes all conversations with DB
        """
        current_session = self.session_factory(**kwargs)
        try:
            yield current_session
            current_session.commit()
        except SQLAlchemyError:
            self.logger.error(
                f"Exception thrown in `::getSessionScope()` by {self}: \n{format_exc()}"
            )
            current_session.rollback()
            raise
        finally:
            current_session.close()

    def resetData(self, tables=()):
        """Drop given tables of the database, then make sure all valid tables exist.

        Args:
            tables (``iterable``, optional): Iterable of table names to have data reset (removed).
                Defaults to an empty tuple.
        """
        for table_name in tables:
            data_type = self.VALID_DATA_TYPES.get(table_name)
            if data_type is None:
                err = f"No such table: {table_name!r}"
                raise ValueError(err)

            data_type.__table__.drop(self.engine)
            self.logger.warning(f"Dropped table {table_name!r}")

        Base.metadata.create_all(self.engine, checkfirst=True)

    def insertData(self, *args):
        """Insert a new data object into the database.

        Positional argument(s) that is(are) already-constructed VALID_DATA_TYPES objects.
        """
        if args:
            for arg in args:
                msg = f"[DataInterface.insertData()] Positional argument is not an valid data object: {arg!r}"
                if not isinstance(arg, tuple(self.VALID_DATA_TYPES.values())):
                    self.logger.error(msg)
                    raise TypeError(arg)

            with self._getSessionScope() as session:
                session.add_all(args)

        else:
            raise ValueError("Cannot call `DataInterface.insertData()` without arguments.")

    def getData(self, query, multi=True):
        """Retrieve ephemeris object(s) that match the given Query object.

        Args:
            query (`sqlalchemy.orm.Query`): pre-constructed query that will be used to retrieve
                matching data object(s) from the database.
            multi (``bool``, optional): flag indicating whether to return multiple results.
                Defaults to ``True``.

        Returns:
            ``VALID_DATA_TYPES``: data object or list of data objects matching the query
        """
        msg = f"[DataInterface.getData()] `query` argument must be a `sqlalchemy.orm.Query` object, not {type(query)!r}"
        if not isinstance(query, Query):
            self.logger.error(msg)
            raise TypeError(query)

        if multi:
            retval = []
        else:
            retval = None

        # [NOTE]: The context manager pattern isn't used here because of the lazy loading
        #   functionality of the ORM. Somehow the context manager causes data objects to become detached.
        #   See https://docs.sqlalchemy.org/en/13/errors.html#error-bhk3
        cur_session = self.session_factory()
        try:
            if multi:
                retval = query.with_session(cur_session).all()
            else:
                retval = query.with_session(cur_session).first()

        except SQLAlchemyError as err:
            self.logger.error(f"Exception thrown in `DataInterface.getData()`: \n{format_exc()}")
            raise err

        finally:
            cur_session.close()

        return retval

    def deleteData(self, query):
        """Delete object(s) from DB table.

        Args:
            query (`sqlalchemy.orm.Query`): pre-constructed query that will be used to retrieve
                matching data object(s) from the database.

        Returns:
            ``int``: number of data objects that were successfully deleted.
        """
        msg = f"[DataInterface.deleteData()] `query` argument must be a `sqlalchemy.orm.Query`, not {type(query)!r}"
        if not isinstance(query, Query):
            self.logger.error(msg)
            raise TypeError(query)

        deleted_count = 0
        with self._getSessionScope() as session:
            for result in query.with_session(session).all():
                session.delete(result)
            deleted_count = len(session.deleted)

        return deleted_count

    def bulkSave(self, data):
        """Use a low latency method to make large amounts of updates to the database.

        Warning:
            The bulk save feature allows for a lower-latency INSERT/UPDATE of rows at the
            expense of most other unit-of-work features. Features such as object management,
            relationship handling, and SQL clause support are silently omitted in favor of raw
            INSERT/UPDATES of records.

        See Also:
            <https://docs.sqlalchemy.org/en/latest/orm/session_api.html#sqlalchemy.orm.session.Session.bulk_save_objects>

        Args:
            data (``list``): data objects to be inserted into/updated in the database

        Returns:
            ``int``: number of data objects saved to the database
        """
        save_count = 0
        with self._getSessionScope() as session:
            session.bulk_save_objects(data)
            save_count = len(data)

        return save_count
