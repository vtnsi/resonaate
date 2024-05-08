from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from os.path import abspath, exists, join
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from numpy import allclose
from sqlalchemy import Column, Float, Integer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query, declarative_base

# RESONAATE Imports
from resonaate.data import clearDBPath, getDBConnection, setDBPath
from resonaate.data.agent import AgentModel
from resonaate.data.ephemeris import TruthEphemeris
from resonaate.data.epoch import Epoch
from resonaate.data.importer_database import ImporterDatabase
from resonaate.data.queries import fetchTruthByJDInterval
from resonaate.data.resonaate_database import ResonaateDatabase

# Local Imports
from .. import FIXTURE_DATA_DIR, IMPORTER_DB_PATH, JSON_RSO_TRUTH, SHARED_DB_PATH

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

EXAMPLE_RSO: list[dict[str, Any]] = [
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
    },
]


EXAMPLE_EPOCH: dict[str, Any] = {
    "julian_date": 2458207.010416667,
    "timestampISO": "2019-01-01T00:01:00.000Z",
}


@pytest.fixture(name="ephem")
def getSingleEphemerisData() -> TruthEphemeris:
    """Create a valid :class:`.TruthEphemeris` object."""
    epoch = Epoch(**EXAMPLE_EPOCH)
    tgt = AgentModel(
        unique_id=EXAMPLE_RSO[0]["unique_id"],
        name=EXAMPLE_RSO[0]["name"],
    )
    eci = EXAMPLE_RSO[0]["eci"]
    return TruthEphemeris(
        epoch=epoch,
        agent=tgt,
        pos_x_km=eci[0],
        pos_y_km=eci[1],
        pos_z_km=eci[2],
        vel_x_km_p_sec=eci[3],
        vel_y_km_p_sec=eci[4],
        vel_z_km_p_sec=eci[5],
    )


@pytest.fixture(name="ephems")
def getMultipleEphemerisData() -> list[TruthEphemeris]:
    """Create several valid :class:`.TruthEphemeris` objects."""
    epoch = Epoch(**EXAMPLE_EPOCH)

    ephems = []
    for rso in EXAMPLE_RSO:
        ephems.append(
            TruthEphemeris.fromECIVector(
                epoch=epoch,
                agent=AgentModel(unique_id=rso["unique_id"], name=rso["name"]),
                eci=rso["eci"],
            ),
        )

    return ephems


class TestResonaateDatabase:
    """Tests for :class:`.DataInterface` class."""

    def testInsertDataOnePosArg(self, database: ResonaateDatabase, ephem: TruthEphemeris):
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
    def testSaveDB(
        self,
        datafiles: str,
        database: ResonaateDatabase,
        ephems: list[TruthEphemeris],
    ):
        """Test saving database to new file."""
        db_path = join(datafiles, "db/copied.sqlite3")
        database.insertData(*ephems)
        database.saveDatabase(database_path=db_path)
        assert exists(abspath(db_path))

    def testInsertDataMultiPosArg(self, database: ResonaateDatabase, ephems: list[TruthEphemeris]):
        """Insert multiple data objects."""
        database.insertData(*ephems)

    def testBulkSave(self, database: ResonaateDatabase):
        """Insert multiple data objects using bulkSave."""
        database.insertData(Epoch(**EXAMPLE_EPOCH))

        ephems = []
        for rso in EXAMPLE_RSO:
            database.insertData(AgentModel(unique_id=rso["unique_id"], name=rso["name"]))
            ephems.append(
                TruthEphemeris.fromECIVector(
                    julian_date=EXAMPLE_EPOCH["julian_date"],
                    agent_id=rso["unique_id"],
                    eci=rso["eci"],
                ),
            )
        database.bulkSave(ephems)

    def testSessionScopeError(self, database: ResonaateDatabase):
        """Catches SQLAlchemy error during session scope usage."""

        # Define a new db object class
        class NewEpoch(declarative_base()):
            __tablename__ = "new_epochs"

            id = Column(Integer, primary_key=True)

            julian_date = Column(Float, index=True, unique=True, nullable=False)

        # Query for new DB object
        query = Query(NewEpoch).filter(NewEpoch.julian_date == EXAMPLE_EPOCH["julian_date"])

        with pytest.raises(SQLAlchemyError):
            database.deleteData(query)

    def testInsertDataBadArgs(self, database: ResonaateDatabase):
        """Insert a bad/malformed data object."""
        with pytest.raises(TypeError):
            database.insertData("this is not an ephemeris")

        error_msg = r"Cannot call `DataInterface.insertData\(\)` without arguments."
        with pytest.raises(ValueError, match=error_msg):
            database.insertData()

    def testGetData(self, database: ResonaateDatabase, ephem: TruthEphemeris):
        """Test getting a data object from the DB."""
        database.insertData(ephem)

        julian_date_query = (
            Query(TruthEphemeris)
            .join(Epoch)
            .filter(Epoch.julian_date == EXAMPLE_EPOCH["julian_date"])
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
    def testGetDataError(self, datafiles: str, ephem: TruthEphemeris):
        """Test getting a data object from the DB."""

        # Define a new db object class
        class NewEpoch(declarative_base()):
            __tablename__ = "new_epochs"

            id = Column(Integer, primary_key=True)

            julian_date = Column(Float, index=True, unique=True, nullable=False)

        # Create DB, and insert data
        shared_db_url = "sqlite:///" + join(datafiles, "db/deleted.sqlite3")
        database = ResonaateDatabase(db_path=shared_db_url)
        database.insertData(ephem)

        # Query for new DB object
        query = Query(NewEpoch).filter(NewEpoch.julian_date == EXAMPLE_EPOCH["julian_date"])
        with pytest.raises(SQLAlchemyError):
            database.getData(query)

        with pytest.raises(TypeError):
            database.getData("not a query object")

    def testSingleDeleteData(self, database: ResonaateDatabase, ephems: list[TruthEphemeris]):
        """Test deleting objects from DB."""
        database.insertData(*ephems)

        query = (
            Query(TruthEphemeris)
            .join(AgentModel)
            .filter(AgentModel.unique_id == EXAMPLE_RSO[0]["unique_id"])
        )
        del_count = database.deleteData(query)

        assert del_count == 1

        with pytest.raises(TypeError):
            database.deleteData("not a query object")

    def testMultipleDeleteData(self, database: ResonaateDatabase, ephems: list[TruthEphemeris]):
        """Test deleting objects from DB."""
        database.insertData(*ephems)

        query = (
            Query(TruthEphemeris)
            .join(Epoch)
            .filter(Epoch.julian_date == EXAMPLE_EPOCH["julian_date"])
        )
        del_count = database.deleteData(query)

        assert del_count == 3

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testSharedDataInterface(self, datafiles: str, ephems: list[TruthEphemeris]):
        """Test the shared interface version method."""
        # Create DB using API
        shared_db_url = "sqlite:///" + join(datafiles, SHARED_DB_PATH)
        setDBPath(shared_db_url)
        database = getDBConnection()
        database.insertData(*ephems)

        # Query on ID and Julian date
        combined_query = (
            Query(TruthEphemeris)
            .join(Epoch)
            .filter(Epoch.julian_date == EXAMPLE_EPOCH["julian_date"])
            .join(AgentModel)
            .filter(AgentModel.unique_id == EXAMPLE_RSO[1]["unique_id"])
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
        sat_num_query = (
            Query(TruthEphemeris)
            .join(AgentModel)
            .filter(AgentModel.unique_id == EXAMPLE_RSO[0]["unique_id"])
        )
        deleted_count = database.deleteData(sat_num_query)
        assert deleted_count == 1

        # Delete based on Julian date
        julian_date_query = (
            Query(TruthEphemeris)
            .join(Epoch)
            .filter(Epoch.julian_date == EXAMPLE_EPOCH["julian_date"])
        )
        deleted_count = database.deleteData(julian_date_query)
        assert deleted_count == 2

        # Delete DB after finished
        database.resetData(tables=database.VALID_DATA_TYPES)
        clearDBPath()

    def testInit(self, ephems: list[TruthEphemeris]):
        """Test the constructor."""
        # Create DB using API
        database = ResonaateDatabase(None, logger=None, verbose_echo=True)
        database.insertData(*ephems)

        # Query on ID and Julian date
        combined_query = (
            Query(TruthEphemeris)
            .join(Epoch)
            .filter(Epoch.julian_date == EXAMPLE_EPOCH["julian_date"])
            .join(AgentModel)
            .filter(AgentModel.unique_id == EXAMPLE_RSO[1]["unique_id"])
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
        sat_num_query = (
            Query(TruthEphemeris)
            .join(AgentModel)
            .filter(AgentModel.unique_id == EXAMPLE_RSO[0]["unique_id"])
        )
        deleted_count = database.deleteData(sat_num_query)
        assert deleted_count == 1

        # Delete based on Julian date
        julian_date_query = (
            Query(TruthEphemeris)
            .join(Epoch)
            .filter(Epoch.julian_date == EXAMPLE_EPOCH["julian_date"])
        )
        deleted_count = database.deleteData(julian_date_query)
        assert deleted_count == 2

        # Delete DB after finished
        database.resetData(tables=database.VALID_DATA_TYPES)

    def testResetData(self, database: ResonaateDatabase, ephems: list[TruthEphemeris]):
        """Test functionality of resetting data."""
        database.insertData(*ephems)
        database.resetData(tables={TruthEphemeris.__tablename__: TruthEphemeris})

    def testResetDataBadArgs(self, database: ResonaateDatabase, ephems: list[TruthEphemeris]):
        """Test functionality of resetting data with improper arguments."""
        database.insertData(*ephems)
        # Test a non-existant table
        error_msg = r"No such table: '\w+'"
        with pytest.raises(ValueError, match=error_msg):
            database.resetData(tables={"ephemeris": TruthEphemeris})


class TestImporterDatabase:
    """Tests for Importer DB class."""

    # [TODO]: Write test for importing observations

    # Only do two to save time
    EXAMPLE_TRUTH_FILES = ("11111-truth.json", "11112-truth.json")

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInitDatabaseFromJSON(self, datafiles: str):
        """Test initializing DB from JSON truth target files."""
        # Create DB using API
        importer_db_url = "sqlite:///" + join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase(importer_db_url)

        importer_db.initDatabaseFromJSON(
            join(datafiles, JSON_RSO_TRUTH, self.EXAMPLE_TRUTH_FILES[0]),
            start=2458454.0,
            stop=2458454.0 + 1 / 24,  # one hour later
        )
        ephems = importer_db.getData(
            Query(TruthEphemeris).join(AgentModel).filter(AgentModel.unique_id == 11111),
        )
        assert len(ephems) == 61

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testReadOnly(self, datafiles: str, ephems: list[TruthEphemeris]):
        """Test the read only methods."""
        # Create DB using API
        importer_db_url = "sqlite:///" + join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase(importer_db_url)

        # `insertData()`
        with pytest.raises(NotImplementedError):
            importer_db.insertData(*ephems)

        # `deleteData()`
        with pytest.raises(NotImplementedError):
            importer_db.deleteData(
                Query(TruthEphemeris)
                .join(AgentModel)
                .filter(AgentModel.unique_id == EXAMPLE_RSO[0]["unique_id"]),
            )

        # `bulkSave()`
        with pytest.raises(NotImplementedError):
            importer_db.insertData(ephems)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInit(self, datafiles: str, ephems: list[TruthEphemeris]):
        """Test the constructor."""
        # Create DB using API
        importer_db_url = "sqlite:///" + join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase(importer_db_url, logger=None, verbose_echo=True)
        importer_db._insertData(*ephems)

        # Query on ID and Julian date
        combined_query = (
            Query(TruthEphemeris)
            .join(Epoch)
            .filter(Epoch.julian_date == EXAMPLE_EPOCH["julian_date"])
            .join(AgentModel)
            .filter(AgentModel.unique_id == EXAMPLE_RSO[1]["unique_id"])
        )
        result = importer_db.getData(combined_query, multi=False)

        # Make sure returned result is correct
        eci = EXAMPLE_RSO[1]["eci"]
        assert result.epoch.julian_date == EXAMPLE_EPOCH["julian_date"]
        assert result.epoch.timestampISO == EXAMPLE_EPOCH["timestampISO"]
        assert result.agent_id == EXAMPLE_RSO[1]["unique_id"]
        assert result.agent_id == result.agent.unique_id
        assert result.agent.name == EXAMPLE_RSO[1]["name"]
        assert allclose(result.eci, eci)


# SET UP EPOCH ENTRIES
EXAMPLE_JD = [
    2458207.010416667,
    2459304.21527778,
    2459304.21875,
]
EXAMPLE_JD_WITH_PRECISION_ERROR = [
    2458207.010416666,
    2459304.215277778,
    2459304.218750001,
]
EXAMPLE_TIMESTAMPS = [
    "2019-01-01T00:01:00.000",
    "2021-03-30T17:10:00.000",
    "2021-03-30T17:15:00.000",
]
EXAMPLE_EPOCHS = [
    {"julian_date": jd, "timestampISO": ts} for jd, ts in zip(EXAMPLE_JD, EXAMPLE_TIMESTAMPS)
]

# SET UP AGENT ENTRIES
RSO_UNIQUE_ID = 24601
EXAMPLE_RSO_AGENT = {"name": "Sat1", "unique_id": RSO_UNIQUE_ID}

# SET UP TRUTH ENTRIES
EXAMPLE_ECI_STATES = [
    [32832.44359, -26125.770428, -4175.978356, 1.920657, 2.399111, 0.090893],
    [2586.058936, 6348.302803, 3801.942400, -3.304773, -2.193913, 5.915754],
    [1296.645611, -2457.821083, 5721.873513, 0.179231, 0.093705, -0.000365],
]
EXAMPLE_TRUTH = [
    {"julian_date": jd, "agent_id": RSO_UNIQUE_ID, "eci": eci}
    for jd, eci in zip(EXAMPLE_JD, EXAMPLE_ECI_STATES)
]
EXAMPLE_TRUTH_WITH_JD_PRECISION_ERROR = [
    {"julian_date": jd, "agent_id": RSO_UNIQUE_ID, "eci": eci}
    for jd, eci in zip(EXAMPLE_JD_WITH_PRECISION_ERROR, EXAMPLE_ECI_STATES)
]


class TestDatabaseIssues:
    """Write tests that demonstrate tricky issues that can result in lost data in queries."""

    @pytest.fixture(name="epochs")
    def getMultipleEpochs(self) -> list[Epoch]:
        """Create several valid :class:`.Epoch` objects."""
        epochs: list[Epoch] = []
        for epoch in EXAMPLE_EPOCHS:
            epochs.append(Epoch(**epoch))
        return epochs

    @pytest.fixture(name="agent")
    def getAgent(self):
        """Create a valid :class:`.AgentModel` object."""
        return AgentModel(**EXAMPLE_RSO_AGENT)

    @pytest.fixture(name="matched_ephems")
    def getMultipleEphemerisData(self) -> list[TruthEphemeris]:
        """Create several valid :class:`.TruthEphemeris` objects."""
        ephems: list[TruthEphemeris] = []
        for ex_ephem in EXAMPLE_TRUTH:
            ephems.append(TruthEphemeris.fromECIVector(**ex_ephem))
        return ephems

    @pytest.fixture(name="unmatched_ephems")
    def getMultipleRoundedEphemerisData(self) -> list[TruthEphemeris]:
        """Create several valid :class:`.TruthEphemeris` objects."""
        ephems: list[TruthEphemeris] = []
        for ex_ephem in EXAMPLE_TRUTH_WITH_JD_PRECISION_ERROR:
            ephems.append(TruthEphemeris.fromECIVector(**ex_ephem))
        return ephems

    @pytest.fixture(name="matched_epoch_db")
    def createMatchedDB(
        self,
        epochs: list[Epoch],
        agent: AgentModel,
        matched_ephems: list[TruthEphemeris],
    ):
        """Create a DB object where the `TruthEphemeris` table entries have matching julian dates in the `Epoch` table.

        Yields:
            :class:`.ResonaateDatabase`: properly constructed DB object
        """
        # Create & yield instance.
        matched_db = ResonaateDatabase(db_path=None)
        matched_db.insertData(deepcopy(agent))
        matched_db.bulkSave(deepcopy(epochs + matched_ephems))
        yield matched_db
        matched_db.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    @pytest.fixture(name="unmatched_epoch_db")
    def createUnmatchedDB(
        self,
        epochs: list[Epoch],
        agent: AgentModel,
        unmatched_ephems: list[TruthEphemeris],
    ):
        """Create a DB object where the `TruthEphemeris` table entries where julian dates have truncated precision from the `Epoch` table.

        Yields:
            :class:`.ResonaateDatabase`: properly constructed DB object
        """
        # Create & yield instance.
        unmatched_db = ResonaateDatabase(db_path=None)
        unmatched_db.insertData(deepcopy(agent))
        unmatched_db.bulkSave(deepcopy(epochs + unmatched_ephems))
        yield unmatched_db
        unmatched_db.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testBadJDJoin(
        self,
        matched_epoch_db: ResonaateDatabase,
        unmatched_epoch_db: ResonaateDatabase,
    ):
        """Test that ephemeris queries only return the correct number of ephemeris when there is a matching epoch entry in the `Epoch` table.

        This test demonstrates that precision loss in julian date entries can result in lost queries.

        Args:
            matched_epoch_db (ResonaateDatabase): database where julian date entries in `TruthEphemeris` table have matching values in `Epoch` table.
            unmatched_epoch_db (ResonaateDatabase): database where julian date entries in `TruthEphemeris` table do not have matching values in `Epoch` table.
        """
        matched_epoch_truth = fetchTruthByJDInterval(matched_epoch_db, [RSO_UNIQUE_ID])
        unmatched_epoch_truth = fetchTruthByJDInterval(unmatched_epoch_db, [RSO_UNIQUE_ID])
        assert len(matched_epoch_truth) != len(unmatched_epoch_truth)
        assert len(unmatched_epoch_truth) == 0
        assert len(matched_epoch_truth) == len(EXAMPLE_ECI_STATES)
