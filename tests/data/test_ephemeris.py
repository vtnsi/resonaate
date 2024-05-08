from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
import numpy as np
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.ephemeris import EstimateEphemeris, TruthEphemeris

EXAMPLE_STATE = {
    "eci": [32832.44359, -26125.770428, -4175.978356, 1.920657, 2.399111, 0.090893],
    "covariance": [
        [
            0.00045868865860573414,
            7.077473035630296e-06,
            2.6569219326775983e-06,
            2.8572329061974494e-06,
            7.608865602971146e-08,
            3.148427436402753e-08,
        ],
        [
            7.077473035630296e-06,
            0.0004674186128723682,
            4.744166300030342e-06,
            7.612786387301252e-08,
            2.948885588397417e-06,
            5.552773026893281e-08,
        ],
        [
            2.6569219326775983e-06,
            4.744166300030342e-06,
            0.0004565441207723332,
            3.138196138795943e-08,
            5.531814945587278e-08,
            2.837433422429151e-06,
        ],
        [
            2.8572329061974494e-06,
            7.612786387301252e-08,
            3.138196138795943e-08,
            2.3814900977709134e-08,
            6.340781281444123e-10,
            2.716632627973775e-10,
        ],
        [
            7.608865602971146e-08,
            2.9488855883974173e-06,
            5.531814945587278e-08,
            6.340781281444124e-10,
            2.4570879395801635e-08,
            4.76786127886514e-10,
        ],
        [
            3.148427436402753e-08,
            5.552773026893281e-08,
            2.837433422429151e-06,
            2.716632627973775e-10,
            4.76786127886514e-10,
            2.3661179498536405e-08,
        ],
    ],
}


class TestTruthEphemerisTable:
    """Test class for :class:`.TruthEphemeris` database table class."""

    def testInit(self):
        """Test the init of TruthEphemeris database table."""
        _ = TruthEphemeris()

    def testInitKwargs(self, epoch, target_agent):
        """Test initializing the kewards of the truth ephemeris table."""
        _ = TruthEphemeris(
            epoch=epoch,
            agent=target_agent,
            pos_x_km=32832.44359,
            pos_y_km=-26125.770428,
            pos_z_km=-4175.978356,
            vel_x_km_p_sec=1.920657,
            vel_y_km_p_sec=2.399111,
            vel_z_km_p_sec=0.090893,
        )

    def testFromECIVector(self, epoch, target_agent):
        """Test initializing the kewards of the truth ephemeris table."""
        _ = TruthEphemeris.fromECIVector(epoch=epoch, agent=target_agent, eci=EXAMPLE_STATE["eci"])

    def testReprAndDict(self, epoch, target_agent):
        """Test printing DB table object & making into dict."""
        ephem = TruthEphemeris.fromECIVector(
            epoch=epoch,
            agent=target_agent,
            eci=EXAMPLE_STATE["eci"],
        )
        print(ephem)
        ephem.makeDictionary()

    def testEquality(self, epoch, target_agent):
        """Test equals and not equals operators."""
        ephem1 = TruthEphemeris.fromECIVector(
            epoch=epoch,
            agent=target_agent,
            eci=EXAMPLE_STATE["eci"],
        )

        ephem2 = TruthEphemeris.fromECIVector(
            epoch=epoch,
            agent=target_agent,
            eci=EXAMPLE_STATE["eci"],
        )

        ephem3 = TruthEphemeris.fromECIVector(
            epoch=epoch,
            agent=target_agent,
            eci=np.asarray(EXAMPLE_STATE["eci"]) + np.asarray([0, 0, 1, 2, 3, 4]),
        )

        # Test equality and inequality
        assert ephem1 == ephem2
        assert ephem1 != ephem3

    def testECIProperty(self, epoch, target_agent):
        """Test eci property."""
        ephem = TruthEphemeris.fromECIVector(
            epoch=epoch,
            agent=target_agent,
            eci=EXAMPLE_STATE["eci"],
        )
        assert isinstance(ephem.eci, list)
        assert len(ephem.eci) == 6

    def testInsertWithRelationship(self, database, epoch, target_agent):
        """Test inserting ephemeris with related objects."""
        ephem = TruthEphemeris.fromECIVector(
            epoch=epoch,
            agent=target_agent,
            eci=EXAMPLE_STATE["eci"],
        )

        # Test insert of object
        database.insertData(ephem)

    def testInsertWithForeignKeys(self, database, epoch, target_agent):
        """Test inserting ephemeris with only foreign keys."""
        ephem = TruthEphemeris.fromECIVector(
            julian_date=epoch.julian_date,
            agent_id=target_agent.unique_id,
            eci=EXAMPLE_STATE["eci"],
        )
        # Pre-insert required objects
        database.insertData(epoch)
        database.insertData(target_agent)

        # Test insert of object via FK
        database.insertData(ephem)

    def testManyToOneLazyLoading(self, database, epoch, target_agent):
        """Test many to one lazy-loading attributes."""
        julian_date = epoch.julian_date
        agent_id = target_agent.unique_id
        ephem = TruthEphemeris.fromECIVector(
            epoch=epoch,
            agent=target_agent,
            eci=EXAMPLE_STATE["eci"],
        )
        database.insertData(ephem)

        new_ephem = database.getData(Query(TruthEphemeris), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_ephem.agent.unique_id == agent_id
        assert new_ephem.epoch.julian_date == julian_date

    def testManyToOneQuery(self, database, epoch, target_agent):
        """Test many to one relationship queries."""
        epoch_copy = deepcopy(epoch)
        agent_copy = deepcopy(target_agent)

        ephem = TruthEphemeris.fromECIVector(
            epoch=epoch,
            agent=target_agent,
            eci=EXAMPLE_STATE["eci"],
        )
        database.insertData(ephem)

        # Test querying by Agent
        query = Query(TruthEphemeris).filter(TruthEphemeris.agent == agent_copy)
        new_ephem = database.getData(query, multi=False)
        assert new_ephem.agent == agent_copy

        # Test querying by Epoch
        query = Query(TruthEphemeris).filter(TruthEphemeris.epoch == epoch_copy)
        new_ephem = database.getData(query, multi=False)
        assert new_ephem.epoch == epoch_copy


class TestEstimateEphemerisTable:
    """Test class for :class:`.EstimateEphemeris` database table."""

    def testInit(self):
        """Test init of EstimateEphemeris."""
        _ = EstimateEphemeris()

    def testInitKwargs(self, epoch, target_agent):
        """Test initializing the kewards of the estimate ephemeris table."""
        _ = EstimateEphemeris(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            pos_x_km=32832.44359,
            pos_y_km=-26125.770428,
            pos_z_km=-4175.978356,
            vel_x_km_p_sec=1.920657,
            vel_y_km_p_sec=2.399111,
            vel_z_km_p_sec=0.090893,
            covar_00=1.0,
            covar_01=0.0,
            covar_02=0.0,
            covar_03=0.0,
            covar_04=0.0,
            covar_05=0.0,
            covar_10=0.0,
            covar_11=1.0,
            covar_12=0.0,
            covar_13=0.0,
            covar_14=0.0,
            covar_15=0.0,
            covar_20=0.0,
            covar_21=0.0,
            covar_22=1.0,
            covar_23=0.0,
            covar_24=0.0,
            covar_25=0.0,
            covar_30=0.0,
            covar_31=0.0,
            covar_32=0.0,
            covar_33=1.0,
            covar_34=0.0,
            covar_35=0.0,
            covar_40=0.0,
            covar_41=0.0,
            covar_42=0.0,
            covar_43=0.0,
            covar_44=1.0,
            covar_45=0.0,
            covar_50=0.0,
            covar_51=0.0,
            covar_52=0.0,
            covar_53=0.0,
            covar_54=0.0,
            covar_55=1.0,
        )

    def testFromCovarianceMatrix(self, epoch, target_agent):
        """Test `fromCovarianceMatrix()` in ephemeris.py."""
        _ = EstimateEphemeris.fromCovarianceMatrix(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            eci=EXAMPLE_STATE["eci"],
            covariance=EXAMPLE_STATE["covariance"],
        )

    def testReprAndDict(self, epoch, target_agent):
        """Test printing DB table object & making into dict."""
        ephem = EstimateEphemeris.fromCovarianceMatrix(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            eci=EXAMPLE_STATE["eci"],
            covariance=EXAMPLE_STATE["covariance"],
        )
        print(ephem)
        ephem.makeDictionary()

    def testEquality(self, epoch, target_agent):
        """Test equals and not equals operators."""
        ephem1 = EstimateEphemeris.fromCovarianceMatrix(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            eci=EXAMPLE_STATE["eci"],
            covariance=EXAMPLE_STATE["covariance"],
        )

        ephem2 = EstimateEphemeris.fromCovarianceMatrix(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            eci=EXAMPLE_STATE["eci"],
            covariance=EXAMPLE_STATE["covariance"],
        )

        ephem3 = EstimateEphemeris.fromCovarianceMatrix(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            eci=np.asarray(EXAMPLE_STATE["eci"]) + np.asarray([0, 0, 1, 2, 3, 4]),
            covariance=EXAMPLE_STATE["covariance"],
        )
        assert ephem1 == ephem2
        assert ephem1 != ephem3

    def testECIProperty(self, epoch, target_agent):
        """Test eci property."""
        ephem = EstimateEphemeris.fromCovarianceMatrix(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            eci=EXAMPLE_STATE["eci"],
            covariance=EXAMPLE_STATE["covariance"],
        )
        assert isinstance(ephem.eci, list)
        assert len(ephem.eci) == 6

    def testCovarianceProperty(self, epoch, target_agent):
        """Test covariance property."""
        ephem = EstimateEphemeris.fromCovarianceMatrix(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            eci=EXAMPLE_STATE["eci"],
            covariance=EXAMPLE_STATE["covariance"],
        )
        assert isinstance(ephem.covariance, list)
        assert len(ephem.covariance) == 6
        assert len(ephem.covariance[0]) == 6

    def testInsertWithRelationship(self, database, epoch, target_agent):
        """Test inserting ephemeris with related objects."""
        ephem = EstimateEphemeris.fromCovarianceMatrix(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            eci=EXAMPLE_STATE["eci"],
            covariance=EXAMPLE_STATE["covariance"],
        )

        # Test insert of object
        database.insertData(ephem)

    def testInsertWithForeignKeys(self, database, epoch, target_agent):
        """Test inserting ephemeris with only foreign keys."""
        ephem = EstimateEphemeris.fromCovarianceMatrix(
            julian_date=epoch.julian_date,
            agent_id=target_agent.unique_id,
            source="Propagation",
            eci=EXAMPLE_STATE["eci"],
            covariance=EXAMPLE_STATE["covariance"],
        )
        # Pre-insert required objects
        database.insertData(epoch)
        database.insertData(target_agent)

        # Test insert of object via FK
        database.insertData(ephem)

    def testManyToOneLazyLoading(self, database, epoch, target_agent):
        """Test many to one lazy-loading attributes."""
        julian_date = epoch.julian_date
        agent_id = target_agent.unique_id
        ephem = EstimateEphemeris.fromCovarianceMatrix(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            eci=EXAMPLE_STATE["eci"],
            covariance=EXAMPLE_STATE["covariance"],
        )
        database.insertData(ephem)

        new_ephem = database.getData(Query(EstimateEphemeris), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_ephem.agent.unique_id == agent_id
        assert new_ephem.epoch.julian_date == julian_date

    def testManyToOneQuery(self, database, epoch, target_agent):
        """Test many to one relationship queries."""
        epoch_copy = deepcopy(epoch)
        agent_copy = deepcopy(target_agent)

        ephem = EstimateEphemeris.fromCovarianceMatrix(
            epoch=epoch,
            agent=target_agent,
            source="Propagation",
            eci=EXAMPLE_STATE["eci"],
            covariance=EXAMPLE_STATE["covariance"],
        )
        database.insertData(ephem)

        # Test querying by Agent
        query = Query(EstimateEphemeris).filter(EstimateEphemeris.agent == agent_copy)
        new_ephem = database.getData(query, multi=False)
        assert new_ephem.agent == agent_copy

        # Test querying by Epoch
        query = Query(EstimateEphemeris).filter(EstimateEphemeris.epoch == epoch_copy)
        new_ephem = database.getData(query, multi=False)
        assert new_ephem.epoch == epoch_copy
