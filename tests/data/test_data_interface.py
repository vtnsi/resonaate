# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from os.path import join, abspath, dirname
# Third Party Imports
import pytest
from sqlalchemy.orm import Query
# RESONAATE Imports
try:
    from resonaate.data.data_interface import DataInterface
    from resonaate.data.ephemeris import TruthEphemeris
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase, FIXTURE_DATA_DIR


EOP_FILE_DIR = join(
    dirname(abspath(__file__)),
    "../../external_data"
)


class TestDataInterface(BaseTestCase):
    """Tests for :class:`.DataInterface` class."""

    # EXAMPLE_TRUTH_FILES = (
    #     '11111-truth.json', '11112-truth.json', '11113-truth.json',
    #     '11114-truth.json', '11115-truth.json', '11116-truth.json'
    # )

    # Only do two to save time
    EXAMPLE_TRUTH_FILES = ('11111-truth.json', '11112-truth.json')

    def testInsertDataOnePosArg(self, shared_db):
        """Insert a single data object."""
        ephem = TruthEphemeris(
            unique_id=38093,
            name="Sat1",
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
            pos_x_km=32832.44359,
            pos_y_km=-26125.770428,
            pos_z_km=-4175.978356,
            vel_x_km_p_sec=1.920657,
            vel_y_km_p_sec=2.399111,
            vel_z_km_p_sec=0.090893
        )

        shared_db.insertData(ephem)

    def testInsertDataMultiPosArg(self, shared_db):
        """Insert multiple data objects."""
        init_args = [
            {
                "julian_date": 2458207.010416667,
                "unique_id": 38093,
                "eci": [32832.44359, -26125.770428, -4175.978356, 1.920657, 2.399111, 0.090893],
                "name": "Sat1"
            },
            {
                "julian_date": 2458207.010416667,
                "unique_id": 41914,
                "eci": [6513.919343, -2250.992903, -533.767127, -0.870101, -0.754543, -7.5112],
                "name": "Sat2"
            },
            {
                "julian_date": 2458207.010416667,
                "unique_id": 27839,
                "eci": [4642.213371, 41904.121624, -480.890384, -3.056102, 0.338368, -0.013438],
                "name": "Sat3"
            }
        ]

        ephems = []
        for arg_set in init_args:
            ephems.append(
                TruthEphemeris.fromECIVector(**arg_set)
            )

        shared_db.insertData(*ephems)

    def testInsertDataBadArgs(self, shared_db):
        """Insert a bad/malformed data object."""
        with pytest.raises(AssertionError):
            shared_db.insertData("this is not an ephemeris")

    def testGetData(self, shared_db):
        """Test getting a data object from the DB."""
        shared_db.insertData(TruthEphemeris(
            unique_id=38093,
            name="Sat1",
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
            pos_x_km=32832.44359,
            pos_y_km=-26125.770428,
            pos_z_km=-4175.978356,
            vel_x_km_p_sec=1.920657,
            vel_y_km_p_sec=2.399111,
            vel_z_km_p_sec=0.090893
        ))

        julian_date_query = Query([TruthEphemeris]).filter(TruthEphemeris.julian_date == 2458207.010416667)

        results = shared_db.getData(julian_date_query, multi=False)

        expected = TruthEphemeris(
            unique_id=38093,
            name="Sat1",
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
            pos_x_km=32832.44359,
            pos_y_km=-26125.770428,
            pos_z_km=-4175.978356,
            vel_x_km_p_sec=1.920657,
            vel_y_km_p_sec=2.399111,
            vel_z_km_p_sec=0.090893
        )
        assert results == expected

    def testDeleteData(self, shared_db):
        """Test deleting objects from DB."""
        shared_db.insertData(TruthEphemeris(
            unique_id=38093,
            name="Sat1",
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
            pos_x_km=32832.44359,
            pos_y_km=-26125.770428,
            pos_z_km=-4175.978356,
            vel_x_km_p_sec=1.920657,
            vel_y_km_p_sec=2.399111,
            vel_z_km_p_sec=0.090893
        ))
        shared_db.insertData(TruthEphemeris(
            unique_id=38093,
            name="Sat1",
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
            pos_x_km=32832.44359,
            pos_y_km=-26125.770428,
            pos_z_km=-4175.978356,
            vel_x_km_p_sec=1.920657,
            vel_y_km_p_sec=2.399111,
            vel_z_km_p_sec=0.090893
        ))

        del_count = shared_db.deleteData(Query([TruthEphemeris]).filter(TruthEphemeris.unique_id == 38093))

        assert del_count == 2

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testInitDatabaseFromJSON(self, shared_db, datafiles):
        """Test initializing DB from JSON truth target files."""
        init_json_files = []
        for file_name in self.EXAMPLE_TRUTH_FILES:
            init_json_files.append(join(datafiles, "json/rso_truth", file_name))
        shared_db.initDatabaseFromJSON(*init_json_files)

    def testSharedDataInterface(self):
        """Test the :meth:`.getSharedInterface()` class method."""
        shared_interface = DataInterface.getSharedInterface()
        shared_interface.insertData(TruthEphemeris(
            unique_id=38093,
            name="Sat1",
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
            pos_x_km=32832.44359,
            pos_y_km=-26125.770428,
            pos_z_km=-4175.978356,
            vel_x_km_p_sec=1.920657,
            vel_y_km_p_sec=2.399111,
            vel_z_km_p_sec=0.090893
        ))
        shared_interface.insertData(TruthEphemeris(
            unique_id=38093,
            name="Sat1",
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
            pos_x_km=32832.44359,
            pos_y_km=-26125.770428,
            pos_z_km=-4175.978356,
            vel_x_km_p_sec=1.920657,
            vel_y_km_p_sec=2.399111,
            vel_z_km_p_sec=0.090893
        ))

        julian_date_query = Query([TruthEphemeris]).filter(TruthEphemeris.julian_date == 2458207.010416667)

        results = shared_interface.getData(julian_date_query, multi=False)

        expected = TruthEphemeris(
            unique_id=38093,
            name="Sat1",
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
            pos_x_km=32832.44359,
            pos_y_km=-26125.770428,
            pos_z_km=-4175.978356,
            vel_x_km_p_sec=1.920657,
            vel_y_km_p_sec=2.399111,
            vel_z_km_p_sec=0.090893
        )
        assert results == expected

        sat_num_query = Query([TruthEphemeris]).filter(TruthEphemeris.unique_id == 38093)
        deleted_count = shared_interface.deleteData(sat_num_query)

        assert deleted_count == 2

    @pytest.mark.datafiles(EOP_FILE_DIR)
    def testInitEOPData(self, datafiles):
        """Test loading EOP data into the DB."""
        shared_db = DataInterface()

        eop_file = join(datafiles, "EOPdata.dat")
        nut_file = join(datafiles, "nut80.dat")

        shared_db.initEOPData(eop_file, nut_file)
