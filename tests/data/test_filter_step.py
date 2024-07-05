from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, array_equal
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.filter_step import FilterStep, ndArrayToString, stringToNdarray

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # RESONAATE Imports
    from resonaate.data.resonaate_database import ResonaateDatabase


class TestFilterStep:
    """Test class for :class:`.FilterStep` database table class."""

    innovation = array(
        [
            -2.334817207660933e-05,
            -2.0436287793690333e-05,
            -0.0362834239294898,
            -0.000185071151261873,
        ],
    )
    nis = 5.37607495178574
    innovation2 = array([-2.334817207660933e-05, -2.0436287793690333e-05])

    eci_state = array([6900, 6900, 6900, -10.0, -2.03, 8.0])
    q_matrix = array([[1, 2, 3], [1, 2, 3], [4, 5, 6]])

    eci_state_2 = array([6900, -6900, 6900, 10.0, -2.03, 8.0])
    q_matrix_2 = array([[0, 1, 0], [1, 1, 1], [2, 4, 2]])

    def testInit(self):
        """Test the init of FilterStep database table."""
        _ = FilterStep()

    def testInitKwargs(self, epoch, target_agent):
        """Test initializing the keywords of the truth ephemeris table.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        _ = FilterStep(
            epoch=epoch,
            target=target_agent,
            measurement_residual_azimuth=self.innovation[0],
            measurement_residual_elevation=self.innovation[1],
            measurement_residual_range=self.innovation[2],
            measurement_residual_range_rate=self.innovation[3],
            truth_eci=ndArrayToString(self.eci_state),
            q_matrix=ndArrayToString(self.q_matrix),
        )

    def testJSONSerializer(self):
        """Test the conversions between :class:`ndarray` and json string."""
        q_mat_str: str = ndArrayToString(self.q_matrix)
        q_mat_from_str: ndarray = stringToNdarray(q_mat_str)

        eci_str: str = ndArrayToString(self.eci_state)
        eci_from_str: ndarray = stringToNdarray(eci_str)

        assert array_equal(self.q_matrix, q_mat_from_str)
        assert array_equal(self.eci_state, eci_from_str)

    def testRecordFilterStep(self, epoch, target_agent):
        """Test initializing the keywords of the table.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information taken at each call
        """
        _ = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            truth_eci=self.eci_state,
            q_matrix=self.q_matrix,
        )

    def testReprAndDict(self, epoch, target_agent):
        """Test printing DB table object & making into dict.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = FilterStep.recordFilterStep(
            julian_date=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            truth_eci=self.eci_state,
            q_matrix=self.q_matrix,
        )
        print(filt)
        filt.makeDictionary()

    def testEquality(self, epoch, target_agent):
        """Test equals and not equals operators.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt1 = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            truth_eci=self.eci_state,
            q_matrix=self.q_matrix,
        )

        filt2 = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            truth_eci=self.eci_state,
            q_matrix=self.q_matrix,
        )

        filt3 = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation + self.innovation,
            nis=self.nis,
            truth_eci=self.eci_state_2,
            q_matrix=self.q_matrix_2,
        )
        # Test equality and inequality
        assert filt1 == filt2
        assert filt1 != filt3

    def testInnovationProperty(self, epoch, target_agent):
        """Test Innovation Property.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            truth_eci=self.eci_state,
            q_matrix=self.q_matrix,
        )
        assert isinstance(filt.innovation, list)
        assert len(filt.innovation) == 4

    def testInnovationProperty2(self, epoch, target_agent):
        """Test Innovation property with different innovations length.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation2,
            truth_eci=self.eci_state,
            q_matrix=self.q_matrix,
        )
        assert isinstance(filt.innovation, list)
        assert len(filt.innovation) == 2

    def testInsertWithRelationship(self, epoch, target_agent, database: ResonaateDatabase):
        """Test inserting filter values with related objects.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
            database (:class:`.ResonaateDatabase`): shared instance of database
        """
        filt = FilterStep.recordFilterStep(
            epoch=epoch,
            julian_date=epoch.julian_date,
            target_id=target_agent.unique_id,
            innovation=self.innovation,
            nis=self.nis,
            truth_eci=self.eci_state,
            q_matrix=self.q_matrix,
        )

        # Test insert of object
        database.insertData(filt)

    def testInsertWithForeignKeys(self, epoch, target_agent, database: ResonaateDatabase):
        """Test inserting observation with only foreign keys.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
            database (:class:`.ResonaateDatabase`): shared instance of database
        """
        filt = FilterStep.recordFilterStep(
            julian_date=epoch.julian_date,
            target_id=target_agent.unique_id,
            innovation=self.innovation,
            nis=self.nis,
            truth_eci=self.eci_state,
            q_matrix=self.q_matrix,
        )
        # Pre-insert required objects
        database.insertData(epoch)
        database.insertData(target_agent)

        # Test insert of object via FK
        database.insertData(filt)

    def testManyToOneLazyLoading(self, epoch, target_agent, database: ResonaateDatabase):
        """Test many to one lazy-loading attributes.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
            database (:class:`.ResonaateDatabase`): shared instance of database
        """
        julian_date = epoch.julian_date
        target_id = target_agent.unique_id
        filt = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            truth_eci=self.eci_state,
            q_matrix=self.q_matrix,
        )
        database.insertData(filt)

        new_filt = database.getData(Query(FilterStep), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_filt.epoch.julian_date == julian_date
        assert new_filt.target.unique_id == target_id

    def testManyToOneQuery(self, epoch, target_agent, database: ResonaateDatabase):
        """Test many to one relationship queries.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
            database (:class:`.ResonaateDatabase`): shared instance of database
        """
        epoch_copy = deepcopy(epoch)
        target_copy = deepcopy(target_agent)

        filt = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            truth_eci=self.eci_state,
            q_matrix=self.q_matrix,
        )
        database.insertData(filt)

        # Test querying by Target
        query = Query(FilterStep).filter(FilterStep.target == target_copy)
        new_filt = database.getData(query, multi=False)
        assert new_filt.target == target_copy

        # Test querying by epoch
        query = Query(FilterStep).filter(FilterStep.epoch == epoch_copy)
