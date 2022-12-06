"""Defines the :class:`.ImporterDatabase` data interface class for pre-canned data."""
# Standard Library Imports
import os

# Third Party Imports
from sqlalchemy.orm import Query

# Local Imports
from ..common.logger import resonaateLogError
from ..common.utilities import loadJSONFile
from ..physics.time.stardate import JulianDate
from .agent import AgentModel
from .data_interface import DataInterface
from .ephemeris import TruthEphemeris
from .epoch import Epoch


class ImporterDatabase(DataInterface):
    """Importer database object for loading external data."""

    __shared_inst = None

    def __init__(self, db_path, drop_tables=(), logger=None, verbose_echo=False):
        """Create SQLite database based on :attr:`.VALID_DATA_TYPES` .

        Args:
            db_path (``str``): SQLAlchemy-accepted string denoting what database implementation
                to use and where the database is located.
            drop_tables (``iterable``, optional): Iterable of table names to be dropped at time of
                :class:`.DataInterface` construction. This parameter makes sense in the context of
                utilizing a pre-existing database that a user may not want to keep data from.
                Defaults to an empty tuple, resulting in no tables being dropped.
            logger (:class:`.Logger`, optional): Previously instantiated logging object to use. Defaults to ``None``,
                resulting in a new :class:`.Logger` instance being instantiated.
            verbose_echo (``bool``, optional): Flag that if set ``True``, will tell the SQLAlchemy
                engine to output the raw SQL statements it runs. Defaults to ``False``.
        """
        # Force users to define db location
        if not db_path:
            resonaateLogError("Importer database requires a valid url path")
            raise ValueError(db_path)

        # Instantiate the data interface object
        super().__init__(db_path, drop_tables, logger, verbose_echo)

    def insertData(self, *args):
        """Override :class:`.DataInterface` implementation.

        Raises:
            NotImplementedError: this is a read-only database
        """
        raise NotImplementedError("ImporterDatabase is read-only, so inserting data is prohibited")

    def deleteData(self, query):
        """Override :class:`.DataInterface` implementation.

        Raises:
            NotImplementedError: this is a read-only database
        """
        raise NotImplementedError("ImporterDatabase is read-only, so deleting data is prohibited")

    def bulkSave(self, data):
        """Override :class:`.DataInterface` implementation.

        Raises:
            NotImplementedError: this is a read-only database
        """
        raise NotImplementedError("ImporterDatabase is read-only, so inserting data is prohibited")

    def _insertData(self, *args):
        """Re-implement :meth:`.DataInterface.insertData` as private method."""
        with self._getSessionScope() as session:
            session.add_all(args)

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
            # Force users to define db location
            if not db_path:
                resonaateLogError("Importer database requires a valid url path")
                raise ValueError(db_path)
            cls.__shared_inst = cls(db_path, drop_tables, logger, verbose_echo)

        return cls.__shared_inst

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
            if os.path.isfile(path):
                name = self._getJSONFilename(path)
                self._loadJSONFile(name, path, start=start, stop=stop)

            elif os.path.isdir(path):
                for filename in os.listdir(path):
                    name = self._getJSONFilename(filename)
                    self._loadJSONFile(name, os.path.join(path, filename), start=start, stop=stop)

            else:
                self.logger.error(f"Argument is not a valid path: {path}")

    def _loadJSONFile(self, name, path, start=None, stop=None):
        """Load a single JSON file.

        Args:
            name (``str``): file base name.
            path (``str``): file path.
            start (:class:`.JulianDate`, optional): minimum date which to load from the file.
                Defaults to None which means no lower bound.
            stop (:class:`.JulianDate`, optional): maximum date which to load from the file.
                Defaults to None which means no upper bound.
        """
        if "truth" in name:
            self.loadEphemerisFile(path, start=start, stop=stop)
        elif "observation" in name:
            self.loadObservationFile(path, start=start, stop=stop)

    def _getJSONFilename(self, path):
        """Return the filename of a JSON file without the extension.

        Args:
            path (``str``): full file path object

        Returns:
            ``str``: name of the file with no basename or extension
        """
        (filename, extension) = os.path.splitext(os.path.split(path)[1])
        if extension.lower() != ".json":
            self.logger.error(f"Error parsing {path}, must be a JSON file.")
            self.logger.error(f"{os.path.split(path)[1]}")
            self.logger.error(f"{filename}:{extension}")
            raise ValueError(filename)
        return filename

    def loadEphemerisFile(self, filename, start=None, stop=None):
        """Loads ephemeris data from a JSON file into DB.

        Args:
            filename (``iterable``): JSON filename used to populate the DB.
            start (:class:`.JulianDate`, optional): epoch of the earliest data object to load.
                Defaults to ``None`` which indicates use the earliest in the file.
            stop (:class:`.JulianDate`, optional): epoch of the latest data object to load.
                Defaults to ``None`` which indicates use the latest in the file.
        """
        ephemerides = loadJSONFile(filename)

        if ephemerides:
            valid_ephemerides = []
            for ephemeris in ephemerides:
                # Check to make sure ephemerides are in the correct time frame, if specified
                if start and JulianDate(ephemeris["julian_date"]) < start:
                    continue
                if stop and JulianDate(ephemeris["julian_date"]) > stop:
                    continue

                # Retrieve position & velocity. Remove covariance data
                ephemeris["pos_x_km"] = ephemeris["position"][0]
                ephemeris["pos_y_km"] = ephemeris["position"][1]
                ephemeris["pos_z_km"] = ephemeris["position"][2]
                del ephemeris["position"]

                ephemeris["vel_x_km_p_sec"] = ephemeris["velocity"][0]
                ephemeris["vel_y_km_p_sec"] = ephemeris["velocity"][1]
                ephemeris["vel_z_km_p_sec"] = ephemeris["velocity"][2]
                del ephemeris["velocity"]

                agent_query = Query(AgentModel).filter(
                    AgentModel.unique_id == ephemeris["sat_num"]
                )
                julian_date_query = Query(Epoch).filter(
                    Epoch.julian_date == ephemeris["julian_date"]
                )

                # Get agent. Insert into DB if it doesn't exist yet
                agent = self.getData(agent_query, multi=False)
                if not agent:
                    self._insertData(
                        AgentModel(
                            unique_id=ephemeris.pop("sat_num"),
                            name=ephemeris.pop("sat_name"),
                        )
                    )
                    agent = self.getData(agent_query, multi=False)
                else:
                    del ephemeris["sat_num"]
                    del ephemeris["sat_name"]

                # Get epoch. Insert into DB if it doesn't exist yet
                epoch = self.getData(julian_date_query, multi=False)
                if not epoch:
                    self._insertData(
                        Epoch(
                            julian_date=ephemeris.pop("julian_date"),
                            timestampISO=ephemeris.pop("timestampISO"),
                        )
                    )
                    epoch = self.getData(julian_date_query, multi=False)
                else:
                    del ephemeris["julian_date"]
                    del ephemeris["timestampISO"]

                if ephemeris.get("covariance"):
                    del ephemeris["covariance"]

                # only add valid ephemerides to database
                valid_ephemerides.append(
                    TruthEphemeris(
                        **ephemeris,
                        agent_id=agent.unique_id,
                        julian_date=epoch.julian_date,
                    )
                )

            self.logger.info(
                f"Loading {len(valid_ephemerides)} ephemerides from file '{filename}'."
            )
            self._insertData(*valid_ephemerides)

    def loadObservationFile(self, filename, start=None, stop=None):
        """Loads observation data from a JSON file into DB.

        Args:
            filename (``iterable``): JSON filename used to populate the DB.
            start (:class:`.JulianDate`, optional): epoch of the earliest data object to load.
                Defaults to ``None`` which indicates use the earliest in the file.
            stop (:class:`.JulianDate`, optional): epoch of the latest data object to load.
                Defaults to ``None`` which indicates use the latest in the file.
        """
        observations = loadJSONFile(filename)

        if observations:
            valid_observations = []
            for observation in observations:
                # Check to make sure observations are in the correct time frame, if specified
                if start and JulianDate(observation["julian_date"]) < start:
                    continue
                if stop and JulianDate(observation["julian_date"]) > stop:
                    self.logger.info(f"Found ending Julian date: {stop}")
                    continue

                # Build new observation entry
                obs_entry = {
                    "julian_date": observation["julian_date"],
                    "timestampISO": observation["timestampISO"],
                    "observer": observation["observer"],
                    "sensor_type": observation["sensor_type"],
                    "unique_id": observation["sensor_id"],
                    "target_id": observation["sat_num"],
                    "target_name": observation["sat_name"],
                    "azimuth_rad": observation["azimuth"],
                    "elevation_rad": observation["elevation"],
                    "range_km": observation["range"],
                    "range_rate_km_p_sec": observation["range_rate"],
                    "sez_state_s_km": observation["sez_state"][0],
                    "sez_state_e_km": observation["sez_state"][1],
                    "sez_state_z_km": observation["sez_state"][2],
                    "position_lat_rad": observation["position"][0],
                    "position_lon_rad": observation["position"][1],
                    "position_altitude_km": observation["position"][2],
                }

                # only add valid observations to database
                valid_observations.append(obs_entry)

            self.logger.info(
                f"Loading {len(valid_observations)} observations from file '{filename}'."
            )
            self._insertData(*observations)
