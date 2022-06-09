# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from os.path import join, exists, abspath
# Third Party Imports
import pytest
from numpy import allclose
from sqlalchemy import Column, Float, Integer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Query
# RESONAATE Imports
try:
    from resonaate.data.resonaate_database import ResonaateDatabase
    from resonaate.data.importer_database import ImporterDatabase
    from resonaate.data.ephemeris import TruthEphemeris
    from resonaate.data.agent import Agent
    from resonaate.data.epoch import Epoch
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase, FIXTURE_DATA_DIR


EXAMPLE_RSO = [
    {
        "name": "Sat1",
        "unique_id": 38093,
        "eci": [32832.44359, -26125.770428, -4175.978356, 1.920657, 2.399111, 0.090893],
    },
    {
        "name": "Sat2",
        "unique_id": 41914,
        "eci": [6513.919343, -2250.992903, -533.767127, -0.870101, -0.754543, -7.5112],
    },
    {
        "name": "Sat3",
        "unique_id": 27839,
        "eci": [4642.213371, 41904.121624, -480.890384, -3.056102, 0.338368, -0.013438],
    }
]


EXAMPLE_EPOCH = {
    "julian_date": 2458207.010416667,
    "timestampISO": "2019-01-01T00:01:00.000Z",
}


@pytest.fixture(name="ephem")
def getSingleEphemerisData():
    """Create a valid :class:`.TruthEphemeris` object."""
    epoch = Epoch(**EXAMPLE_EPOCH)
    tgt = Agent(
        unique_id=EXAMPLE_RSO[0]["unique_id"],
        name=EXAMPLE_RSO[0]["name"],
    )
    eci = EXAMPLE_RSO[0]["eci"]
    ephem = TruthEphemeris(
        epoch=epoch,
        agent=tgt,
        pos_x_km=eci[0],
        pos_y_km=eci[1],
        pos_z_km=eci[2],
        vel_x_km_p_sec=eci[3],
        vel_y_km_p_sec=eci[4],
        vel_z_km_p_sec=eci[5]
    )

    return ephem


@pytest.fixture(name="ephems")
def getMultipleEphemerisData():
    """Create several valid :class:`.TruthEphemeris` objects."""
    epoch = Epoch(**EXAMPLE_EPOCH)

    ephems = []
    for rso in EXAMPLE_RSO:
        ephems.append(
            TruthEphemeris.fromECIVector(
                epoch=epoch,
                agent=Agent(unique_id=rso["unique_id"], name=rso["name"]),
                eci=rso["eci"])
        )

    return ephems


class TestResonaateDatabase(BaseTestCase):
    """Tests for :class:`.DataInterface` class."""

    @pytest.fixture(scope="function", name="database")
    def getDataInterface(self):
        """Create common, non-shared DB object for all tests.

        Yields:
            :class:`.ResonaateDatabase`: properly constructed DB object
        """
        # Create & yield instance.
        shared_interface = ResonaateDatabase.getSharedInterface(
            db_path=None
        )
        yield shared_interface
        shared_interface.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testInsertDataOnePosArg(self, database, ephem):
        """Insert a single data object."""
        eci = ephem.eci
        database.insertData(ephem)

        # Query the results, check attributes after query
        query = Query(TruthEphemeris)
        result = database.getData(query, multi=False)
        assert result.epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        assert result.epoch.timestampISO == EXAMPLE_EPOCH["timestampISO"]
        assert result.agent_id == EXAMPLE_RSO[0]["unique_id"]
        assert result.agent_id == result.agent.unique_id
        assert result.agent.name == EXAMPLE_RSO[0]["name"]
        assert allclose(result.eci, eci)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testSaveDB(self, datafiles, database, ephems):
        """Test saving database to new file."""
        db_path = join(datafiles, "db/copied.sqlite3")
        database.insertData(*ephems)
        database.saveDatabase(database_path=db_path)
        assert exists(abspath(db_path))

    def testInsertDataMultiPosArg(self, database, ephems):
        """Insert multiple data objects."""
        database.insertData(*ephems)

    def testBulkSave(self, database, ephems):
        """Insert multiple data objects using bulkSave."""
        database.insertData(Epoch(**EXAMPLE_EPOCH))

        ephems = []
        for rso in EXAMPLE_RSO:
            database.insertData(Agent(unique_id=rso["unique_id"], name=rso["name"]))
            ephems.append(
                TruthEphemeris.fromECIVector(
                    julian_date=EXAMPLE_EPOCH["julian_date"],
                    agent_id=rso["unique_id"],
                    eci=rso["eci"])
            )
        database.bulkSave(ephems)

    def testSessionScopeError(self, database):
        """Catches SQLAlchemy error during session scope usage."""
        # Define a new db object class
        class NewEpoch(declarative_base()):
            __tablename__ = "new_epochs"

            id = Column(Integer, primary_key=True)  # noqa: A003

            julian_date = Column(Float, index=True, unique=True, nullable=False)

        # Query for new DB object
        query = Query(NewEpoch).filter(
            NewEpoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        )

        with pytest.raises(SQLAlchemyError):
            database.deleteData(query)

    def testInsertDataBadArgs(self, database):
        """Insert a bad/malformed data object."""
        with pytest.raises(TypeError):
            database.insertData("this is not an ephemeris")

        with pytest.raises(ValueError):
            database.insertData()

    def testGetData(self, database, ephem):
        """Test getting a data object from the DB."""
        database.insertData(ephem)

        julian_date_query = Query(TruthEphemeris).join(Epoch).filter(
            Epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        )
        result = database.getData(julian_date_query, multi=False)

        eci = EXAMPLE_RSO[0]["eci"]
        assert result.epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        assert result.epoch.timestampISO == EXAMPLE_EPOCH["timestampISO"]
        assert result.agent_id == EXAMPLE_RSO[0]["unique_id"]
        assert result.agent_id == result.agent.unique_id
        assert result.agent.name == EXAMPLE_RSO[0]["name"]
        assert allclose(result.eci, eci)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testGetDataError(self, datafiles, ephem):
        """Test getting a data object from the DB."""
        # Define a new db object class
        class NewEpoch(declarative_base()):
            __tablename__ = "new_epochs"

            id = Column(Integer, primary_key=True)  # noqa: A003

            julian_date = Column(Float, index=True, unique=True, nullable=False)

        # Create DB, and insert data
        shared_db_url = "sqlite:///" + join(datafiles, "db/deleted.sqlite3")
        database = ResonaateDatabase(db_path=shared_db_url)
        database.insertData(ephem)

        # Query for new DB object
        query = Query(NewEpoch).filter(
            NewEpoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        )
        with pytest.raises(SQLAlchemyError):
            database.getData(query)

        with pytest.raises(TypeError):
            database.getData("not a query object")

    def testSingleDeleteData(self, database, ephems):
        """Test deleting objects from DB."""
        database.insertData(*ephems)

        query = Query(TruthEphemeris).join(Agent).filter(
            Agent.unique_id == EXAMPLE_RSO[0]["unique_id"]
        )
        del_count = database.deleteData(query)

        assert del_count == 1

        with pytest.raises(TypeError):
            database.deleteData("not a query object")

    def testMultipleDeleteData(self, database, ephems):
        """Test deleting objects from DB."""
        database.insertData(*ephems)

        query = Query(TruthEphemeris).join(Epoch).filter(
            Epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        )
        del_count = database.deleteData(query)

        assert del_count == 3

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testSharedDataInterface(self, datafiles, ephems):
        """Test the :meth:`.getSharedInterface()` class method."""
        # Create DB using API
        shared_db_url = "sqlite:///" + join(datafiles, self.shared_db_path)
        database = ResonaateDatabase.getSharedInterface(shared_db_url)
        database.insertData(*ephems)

        # Query on ID and Julian date
        combined_query = Query(TruthEphemeris).join(Epoch).filter(
            Epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        ).join(Agent).filter(
            Agent.unique_id == EXAMPLE_RSO[1]["unique_id"]
        )
        result = database.getData(combined_query, multi=False)

        # Make sure returned result is correct
        eci = EXAMPLE_RSO[1]["eci"]
        assert result.epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        assert result.epoch.timestampISO == EXAMPLE_EPOCH["timestampISO"]
        assert result.agent_id == EXAMPLE_RSO[1]["unique_id"]
        assert result.agent_id == result.agent.unique_id
        assert result.agent.name == EXAMPLE_RSO[1]["name"]
        assert allclose(result.eci, eci)

        # Delete based on ID
        sat_num_query = Query(TruthEphemeris).join(Agent).filter(
            Agent.unique_id == EXAMPLE_RSO[0]["unique_id"]
        )
        deleted_count = database.deleteData(sat_num_query)
        assert deleted_count == 1

        # Delete based on Julian date
        julian_date_query = Query(TruthEphemeris).join(Epoch).filter(
            Epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        )
        deleted_count = database.deleteData(julian_date_query)
        assert deleted_count == 2

        # Delete DB after finished
        database.resetData(tables=database.VALID_DATA_TYPES)

    def testInit(self, ephems):
        """Test the constructor."""
        # Create DB using API
        database = ResonaateDatabase(None, logger=None, verbose_echo=True)
        database.insertData(*ephems)

        # Query on ID and Julian date
        combined_query = Query(TruthEphemeris).join(Epoch).filter(
            Epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        ).join(Agent).filter(
            Agent.unique_id == EXAMPLE_RSO[1]["unique_id"]
        )
        result = database.getData(combined_query, multi=False)

        # Make sure returned result is correct
        eci = EXAMPLE_RSO[1]["eci"]
        assert result.epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        assert result.epoch.timestampISO == EXAMPLE_EPOCH["timestampISO"]
        assert result.agent_id == EXAMPLE_RSO[1]["unique_id"]
        assert result.agent_id == result.agent.unique_id
        assert result.agent.name == EXAMPLE_RSO[1]["name"]
        assert allclose(result.eci, eci)

        # Delete based on ID
        sat_num_query = Query(TruthEphemeris).join(Agent).filter(
            Agent.unique_id == EXAMPLE_RSO[0]["unique_id"]
        )
        deleted_count = database.deleteData(sat_num_query)
        assert deleted_count == 1

        # Delete based on Julian date
        julian_date_query = Query(TruthEphemeris).join(Epoch).filter(
            Epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        )
        deleted_count = database.deleteData(julian_date_query)
        assert deleted_count == 2

        # Delete DB after finished
        database.resetData(tables=database.VALID_DATA_TYPES)

    def testResetData(self, database, ephems):
        """Test functionality of resetting data."""
        database.insertData(*ephems)
        database.resetData(tables={TruthEphemeris.__tablename__: TruthEphemeris})

    def testResetDataBadArgs(self, database, ephems):
        """Test functionality of resetting data with improper arguments."""
        database.insertData(*ephems)
        # Test a non-existant table
        with pytest.raises(ValueError):
            database.resetData(tables={"ephemeris": TruthEphemeris})


class TestImporterDatabase(BaseTestCase):
    """Tests for Importer DB class."""

    # [TODO]: Write test for importing observations

    # Only do two to save time
    EXAMPLE_TRUTH_FILES = ('11111-truth.json', '11112-truth.json')

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInitDatabaseFromJSON(self, datafiles):
        """Test initializing DB from JSON truth target files."""
        # Create DB using API
        importer_db_url = "sqlite:///" + join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase(importer_db_url)

        importer_db.initDatabaseFromJSON(
            join(datafiles, self.json_rso_truth, self.EXAMPLE_TRUTH_FILES[0]),
            start=2458454.0,
            stop=2458454.0 + 1 / 24,  # one hour later
        )
        ephems = importer_db.getData(
            Query(
                TruthEphemeris
            ).join(
                Agent
            ).filter(
                Agent.unique_id == 11111
            )
        )
        assert len(ephems) == 61

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testReadOnly(self, datafiles, ephems):
        """Test the read only methods."""
        # Create DB using API
        importer_db_url = "sqlite:///" + join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase(importer_db_url)

        # `insertData()`
        with pytest.raises(NotImplementedError):
            importer_db.insertData(*ephems)

        # `deleteData()`
        with pytest.raises(NotImplementedError):
            importer_db.deleteData(
                Query(TruthEphemeris).join(Agent).filter(
                    Agent.unique_id == EXAMPLE_RSO[0]["unique_id"]
                )
            )

        # `bulkSave()`
        with pytest.raises(NotImplementedError):
            importer_db.insertData(ephems)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testSharedDataInterface(self, datafiles, ephems):
        """Test the :meth:`.getSharedInterface()` class method."""
        # Create DB using API
        importer_db_url = "sqlite:///" + join(datafiles, self.importer_db_path)
        database = ImporterDatabase.getSharedInterface(importer_db_url)
        database._insertData(*ephems)  # pylint: disable=protected-access

        # Query on ID and Julian date
        combined_query = Query(TruthEphemeris).join(Epoch).filter(
            Epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        ).join(Agent).filter(
            Agent.unique_id == EXAMPLE_RSO[1]["unique_id"]
        )
        result = database.getData(combined_query, multi=False)

        # Make sure returned result is correct
        eci = EXAMPLE_RSO[1]["eci"]
        assert result.epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        assert result.epoch.timestampISO == EXAMPLE_EPOCH["timestampISO"]
        assert result.agent_id == EXAMPLE_RSO[1]["unique_id"]
        assert result.agent_id == result.agent.unique_id
        assert result.agent.name == EXAMPLE_RSO[1]["name"]
        assert allclose(result.eci, eci)

        # Delete DB after finished
        database.resetData(tables=database.VALID_DATA_TYPES)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInit(self, datafiles, ephems):
        """Test the constructor."""
        # Create DB using API
        importer_db_url = "sqlite:///" + join(datafiles, self.importer_db_path)
        database = ImporterDatabase(importer_db_url, logger=None, verbose_echo=True)
        database._insertData(*ephems)  # pylint: disable=protected-access

        # Query on ID and Julian date
        combined_query = Query(TruthEphemeris).join(Epoch).filter(
            Epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        ).join(Agent).filter(
            Agent.unique_id == EXAMPLE_RSO[1]["unique_id"]
        )
        result = database.getData(combined_query, multi=False)

        # Make sure returned result is correct
        eci = EXAMPLE_RSO[1]["eci"]
        assert result.epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        assert result.epoch.timestampISO == EXAMPLE_EPOCH["timestampISO"]
        assert result.agent_id == EXAMPLE_RSO[1]["unique_id"]
        assert result.agent_id == result.agent.unique_id
        assert result.agent.name == EXAMPLE_RSO[1]["name"]
        assert allclose(result.eci, eci)

        # Delete DB after finished
        database.resetData(tables=database.VALID_DATA_TYPES)
