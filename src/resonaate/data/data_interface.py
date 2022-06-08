# Standard Library Imports
from contextlib import contextmanager
from traceback import format_exc
from os import listdir
from os.path import isfile, isdir, join, abspath, split, splitext
from json import load
from json.decoder import JSONDecodeError
from datetime import date
# Third Party Imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool
# RESONAATE Imports
from . import Base
from .ephemeris import TruthEphemeris, EstimateEphemeris
from .manual_sensor_task import ManualSensorTask
from .earth_orientation_params import EarthOrientationParams, NutationParams
from .node_addition import NodeAddition
from .observation import Observation
from .tasking_data import TaskingData
from ..common.logger import Logger
from ..common.behavioral_config import BehavioralConfig
from ..physics.time.stardate import JulianDate


class DataInterface:
    """Main generic data interface that is DB agnostic."""

    # pylint: disable=no-member

    VALID_DATA_TYPES = {
        TruthEphemeris.__tablename__: TruthEphemeris,
        EstimateEphemeris.__tablename__: EstimateEphemeris,
        ManualSensorTask.__tablename__: ManualSensorTask,
        EarthOrientationParams.__tablename__: EarthOrientationParams,
        NutationParams.__tablename__: NutationParams,
        NodeAddition.__tablename__: NodeAddition,
        Observation.__tablename__: Observation,
        TaskingData.__tablename__: TaskingData
    }

    __shared_inst = None

    def __init__(self, db_url=None, drop_tables=(), logger=None, verbose_echo=False):
        """Create SQLite database based on :attr:`.VALID_DATA_TYPES` .

        Args:
            db_url (``str``, optional): SQLAlchemy-accepted string denoting what database implementation
                to use and where the database is located. Defaults to default configuration value.
            drop_tables (``iterable``, optional): Iterable of table names to be dropped at time of
                :class:`.DataInterface` construction. This parameter makes sense in the context of
                utilizing a pre-existing database that a user may not want to keep data from.
                Defaults to an empty tuple, resulting in no tables being dropped.
            logger (:class:`.Logger`, optional): Previously instantiated logging object that this
                    :class:`.DataInterface` object should use. Defaults to ``None``, resulting in a
                    new :class:`.Logger` instance being instantiated.
            verbose_echo (``bool``, optional): Flag that if set ``True``, will tell the SQLAlchemy
                engine to output the raw SQL statements it runs. Defaults to ``False``.
        """
        self.logger = logger
        if self.logger is None:
            self.logger = Logger("resonaate", path=BehavioralConfig.getConfig().logging.OutputLocation)

        if not db_url:
            db_url = BehavioralConfig.getConfig().database.DatabaseURL

        if db_url[:6] == 'sqlite':
            # Squash warnings in sqlite about thread safety. The only times that sqlite will be
            # used in a multi-threaded context is read-only (and thus thread safe)
            self.engine = create_engine(
                db_url,
                echo=verbose_echo,
                connect_args={'check_same_thread': False},
                poolclass=StaticPool
            )
        else:
            self.engine = create_engine(db_url, echo=verbose_echo)

        self.resetData(drop_tables)

        self.session_factory = sessionmaker(bind=self.engine)

    @classmethod
    def getSharedInterface(cls, db_url=None, load_eops=True):
        """Return a reference to the singleton shared interface.

        Args:
            db_url (``str``, optional): SQLAlchemy-accepted string denoting what database implementation
                to use and where the database is located. Defaults to ``None``.
            load_eops (``bool``, optional): Whether to auto-load EOP table. Defaults to True.

        Returns:
            :class:`.DataInterface`: reference to singleton shared data interface
        """
        if cls.__shared_inst is None:
            if not db_url:
                # Connect to in-memory database
                cls.__shared_inst = DataInterface()

            else:
                cls.__shared_inst = DataInterface(db_url=db_url)
                # [NOTE][shared-data-resetting] Instantiating the singleton shared interface will no
                # longer result in any of the database's tables being reset. While it makes sense to
                # clean the table(s) holding temporary data (e.g. historical data or user-created
                # manual sensor tasks) before or after each unrelated Resonaate run, it should no
                # longer be done implicitly with shared interface instantiation. The reason for
                # this is the multi-processing context in which Resonaate now performs. Should a
                # separate process utilize the shared interface, the allocation of the singleton
                # shared interface isn't guaranteed depending on when the separate process was
                # forked versus when the shared interface was first utilized.

            # Load database with EOP data
            if load_eops:
                directory = abspath(join(__file__, "../../../../external_data"))
                cls.__shared_inst.initEOPData(join(directory, 'EOPdata.dat'), join(directory, 'nut80.dat'))

        return cls.__shared_inst

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
            self.logger.error("Exception thrown in `DataInterface.getSessionScope()`: \n{0}".format(format_exc()))
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
                err = "No such table: '{0}'".format(table_name)
                raise ValueError(err)

            try:
                data_type.__table__.drop(self.engine)

            except SQLAlchemyError:
                # table probably didn't exist
                self.logger.warning("Couldn't drop table '{0}'".format(table_name))

            else:
                self.logger.warning("Dropped table '{0}'".format(table_name))

        Base.metadata.create_all(self.engine, checkfirst=True)

    def insertData(self, *args):
        """Insert a new data object into the database.

        Positional argument(s) that is(are) already-constructed VALID_DATA_TYPES objects.
        """
        msg = "[DataInterface.insertData()] Positional argument is not an valid data object: '{0}'"
        if args:
            for arg in args:
                assert isinstance(arg, tuple(self.VALID_DATA_TYPES.values())), msg.format(arg)

            with self._getSessionScope() as session:
                session.add_all(args)

        else:
            raise Exception("Cannot call `DataInterface.insertData()` without arguments.")

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
        msg = "[DataInterface.getData()] `query` argument must be a `sqlalchemy.orm.Query` object, not '{0}'"
        assert isinstance(query, Query), msg.format(type(query))

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
            self.logger.error("Exception thrown in `DataInterface.getData()`: \n{0}".format(format_exc()))
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
        msg = "[DataInterface.deleteData()] `query` argument must be a `sqlalchemy.orm.Query` object, not '{0}'"
        assert isinstance(query, Query), msg.format(type(query))

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

    def initDatabaseFromJSON(self, *args, start=None, stop=None):
        """Initialize a database by populating it with data from the JSON files listed in args.

        Args:
            args (``iterable``): list of JSON filenames/directories used to populate the DB.
            start (:class:`.JulianDate`, optional): epoch of the earliest data object to load.
                Defaults to ``None`` which indicates use the earliest in the file.
            stop (:class:`.JulianDate`, optional): epoch of the latest data object to load.
                Defaults to ``None`` which indicates use the latest in the file.
        """
        for path in args:
            if isfile(path):
                name = self._getJSONFilename(path)
                if "truth" in name:
                    self.loadJSONFile(path, start=start, stop=stop)
                elif "observation" in name:
                    self.loadObservationFile(path, start=start, stop=stop)

            elif isdir(path):
                for filename in listdir(path):
                    name = self._getJSONFilename(filename)
                    if "truth" in name:
                        self.loadJSONFile(join(path, filename), start=start, stop=stop)
                    elif "observation" in name:
                        self.loadObservationFile(join(path, filename), start=start, stop=stop)

            else:
                self.logger.error("Argument is not a valid path: {0}".format(path))

    def _getJSONFilename(self, path):
        """Return the filename of a JSON file without the extension.

        Args:
            path (``str``): full file path object

        Returns:
            ``str``: name of the file with no basename or extension
        """
        (filename, extension) = splitext(split(path)[1])
        if extension.lower() != ".json":
            self.logger.error("Error parsing {0}, must be a JSON file.".format(path))
            self.logger.error("{0}".format(split(path)[1]))
            self.logger.error("{0}:{1}".format(filename, extension))
            raise ValueError(filename)
        return filename

    def loadJSONFile(self, filename, start=None, stop=None):
        """Loads ephemeris data from a JSON file into DB.

        Args:
            filename (``iterable``): JSON filename used to populate the DB.
            start (:class:`.JulianDate`, optional): epoch of the earliest data object to load.
                Defaults to ``None`` which indicates use the earliest in the file.
            stop (:class:`.JulianDate`, optional): epoch of the latest data object to load.
                Defaults to ``None`` which indicates use the latest in the file.
        """
        with open(filename, 'r') as json_file:
            try:
                ephemerides = load(json_file)
            except (JSONDecodeError, UnicodeDecodeError):
                self.logger.error("Error parsing {0}: \n{1}".format(filename, format_exc()))
                ephemerides = []

        if ephemerides:
            valid_ephemerides = []
            for ephemeris in ephemerides:
                # Check to make sure ephemerides are in the correct timeframe, if specified
                if start is not None:
                    if JulianDate(ephemeris["julian_date"]) < start:
                        continue
                if stop is not None:
                    if JulianDate(ephemeris["julian_date"]) > stop:
                        self.logger.info("Found ending Julian date: {0}".format(stop))
                        break

                # Retrieve position & velocity. Remove covariance data
                ephemeris["pos_x_km"] = ephemeris["position"][0]
                ephemeris["pos_y_km"] = ephemeris["position"][1]
                ephemeris["pos_z_km"] = ephemeris["position"][2]
                del ephemeris["position"]

                ephemeris["vel_x_km_p_sec"] = ephemeris["velocity"][0]
                ephemeris["vel_y_km_p_sec"] = ephemeris["velocity"][1]
                ephemeris["vel_z_km_p_sec"] = ephemeris["velocity"][2]
                del ephemeris["velocity"]

                ephemeris["unique_id"] = ephemeris.pop("satNum")
                ephemeris["name"] = ephemeris.pop("satName")

                del ephemeris["covariance"]

                # only add valid ephemerides to database
                valid_ephemerides.append(ephemeris)

            self.logger.info("Loading {0} ephemerides from file '{1}'.".format(len(valid_ephemerides), filename))

            with self._getSessionScope() as session:
                session.bulk_insert_mappings(TruthEphemeris, valid_ephemerides)

    def loadObservationFile(self, filename, start=None, stop=None):
        """Loads observation data from a JSON file into DB.

        Args:
            filename (``iterable``): JSON filename used to populate the DB.
            start (:class:`.JulianDate`, optional): epoch of the earliest data object to load.
                Defaults to ``None`` which indicates use the earliest in the file.
            stop (:class:`.JulianDate`, optional): epoch of the latest data object to load.
                Defaults to ``None`` which indicates use the latest in the file.
        """
        with open(filename, 'r') as json_file:
            try:
                observations = load(json_file)
            except (JSONDecodeError, UnicodeDecodeError):
                self.logger.error("Error parsing {0}: \n{1}".format(filename, format_exc()))
                observations = []

        if observations:
            valid_observations = []
            for observation in observations:
                # Check to make sure observations are in the correct timeframe, if specified
                if start is not None:
                    if JulianDate(observation["julian_date"]) < start:
                        continue
                if stop is not None:
                    if JulianDate(observation["julian_date"]) > stop:
                        self.logger.info("Found ending Julian date: {0}".format(stop))
                        break

                # Build new observation entry
                obs_entry = {
                    "julian_date": observation["julian_date"],
                    "timestampISO": observation["timestampISO"],
                    "observer": observation["observer"],
                    "sensor_type": observation["sensorType"],
                    "unique_id": observation["sensorId"],
                    "target_id": observation["satNum"],
                    "target_name": observation["satName"],
                    "azimuth_rad": observation["azimuth"],
                    "elevation_rad": observation["elevation"],
                    "range_km": observation["range"],
                    "range_rate_km_p_sec": observation["rangeRate"],
                    "sez_state_s_km": observation["xSEZ"][0],
                    "sez_state_e_km": observation["xSEZ"][1],
                    "sez_state_z_km": observation["xSEZ"][2],
                    "position_lat_rad": observation["position"][0],
                    "position_long_rad": observation["position"][1],
                    "position_altitude_km": observation["position"][2]
                }

                # only add valid observations to database
                valid_observations.append(obs_entry)

            self.logger.info("Loading {0} observations from file '{1}'.".format(len(valid_observations), filename))

            with self._getSessionScope() as session:
                session.bulk_insert_mappings(Observation, valid_observations)

    def initEOPData(self, eop_filename, nut_filename):
        """Initialize a database with EOP data.

        Args:
            eop_filename (``str``): EOP data file to load into DB.
            nut_filename (``str``): nutation data file to load into DB.
        """
        with open(abspath(join(eop_filename)), 'r') as dat_file:
            eop_data = loadDatFile(dat_file)

        with open(abspath(join(nut_filename)), 'r') as dat_file:
            nut_data = loadDatFile(dat_file)

        if eop_data and nut_data:
            self.loadEOPData(eop_data)
            self.loadNutationData(nut_data)
        else:
            self.logger.error("No data in either `{0}`, or `{1}`".format(eop_filename, nut_filename))

    def loadEOPData(self, eop_data):
        """Load EOP data into DB.

        Args:
            eop_data (``list``): dicts describing the loaded EOP data.
        """
        self.logger.info("Loading {0} days of eop data".format(len(eop_data)))

        eop_list = []
        for eop_set in eop_data:
            # Index 10 & 11 are for different reduction algorithm. # is modified Julian date.
            current_date = date(
                int(eop_set[0]),
                int(eop_set[1]),
                int(eop_set[2])
            )
            params = {
                "eop_date": current_date,
                "x_p": eop_set[4],
                "y_p": eop_set[5],
                "delta_ut1": eop_set[6],
                "length_of_day": eop_set[7],
                "d_delta_psi": eop_set[8],
                "d_delta_eps": eop_set[9],
                "delta_atomic_time": eop_set[12],
            }
            eop_list.append(params)

        with self._getSessionScope() as session:
            session.bulk_insert_mappings(EarthOrientationParams, eop_list)

    def loadNutationData(self, nut_data):
        """Load nutation data into DB.

        Args:
            nut_data (``list``): dicts describing the loaded nutation data.
        """
        self.logger.info("Loading {0} terms of nutation data".format(len(nut_data)))

        coefficients = []
        for terms in nut_data:
            # Index 9 is ignored because order isn't important
            params = {
                "a_n1_i": terms[0],
                "a_n2_i": terms[1],
                "a_n3_i": terms[2],
                "a_n4_i": terms[3],
                "a_n5_i": terms[4],
                "a_i": terms[5],
                "b_i": terms[6],
                "c_i": terms[7],
                "d_i": terms[8],
            }
            coefficients.append(params)

        with self._getSessionScope() as session:
            session.bulk_insert_mappings(NutationParams, coefficients)


def loadDatFile(data_file):
    """Load the corresponding dat file. Assumes space delimeter.

    Args:
        data_file (``str``): file path to dat file.

    Returns:
        ``list``: nested list of float values of each row
    """
    output = []
    for line in data_file:
        output.append([float(x) for x in line.split()])

    return output
