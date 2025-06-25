from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, array_equal, ndarray
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.common.utilities import ndArrayToString
from resonaate.data.filter_step import SequentialFilterStep

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # RESONAATE Imports
    from resonaate.data.resonaate_database import ResonaateDatabase


class TestFilterStep:
    """Test class for :class:`.SequentialFilterStep` database table class."""

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

    q_matrix = array(
        [[1, 2, 3], [1, 2, 3], [4, 5, 6]],
    )  # TODO: This should test functionality just fine, but it might be a good idea to put realistic values at some point.
    q_matrix_2 = array([[0, 1, 0], [1, 1, 1], [2, 4, 2]])

    sigma_x_res = array([[1, 4, 2, 1], [2, 4, 2, 1]])
    sigma_y_res = array([[1, 4, 8, 8], [69, 4, 2, 0]])
    cross_cvr = array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    innov_cvr = array([[69, 69, 69], [69, 69, 69], [69, 69, 69]])
    kalman_gain = array([[3, 3, 3], [1, 1, 1], [5, 2, 6]])

    def testInit(self):
        """Test the init of FilterStep database table."""
        _ = SequentialFilterStep()

    def testInitKwargs(self, epoch, target_agent):
        """Test initializing the keywords of the truth ephemeris table.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        _ = SequentialFilterStep(
            epoch=epoch,
            target=target_agent,
            measurement_residual_azimuth=self.innovation[0],
            measurement_residual_elevation=self.innovation[1],
            measurement_residual_range=self.innovation[2],
            measurement_residual_range_rate=self.innovation[3],
            _q_matrix=ndArrayToString(self.q_matrix),
            _sigma_x_res=ndArrayToString(self.sigma_x_res),
            _sigma_y_res=ndArrayToString(self.sigma_y_res),
            _cross_cvr=ndArrayToString(self.cross_cvr),
            _innov_cvr=ndArrayToString(self.innov_cvr),
            _kalman_gain=ndArrayToString(self.kalman_gain),
        )

    def testRecordSequentialFilterStep(self, epoch, target_agent):
        """Test initializing the keywords of the table.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information taken at each call
        """
        _ = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )

    def testReprAndDict(self, epoch, target_agent):
        """Test printing DB table object & making into dict.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = SequentialFilterStep.recordFilterStep(
            julian_date=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        print(filt)
        filt.makeDictionary()

    def testEquality(self, epoch, target_agent):
        """Test equals and not equals operators.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt1 = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )

        filt2 = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )

        filt3 = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation + self.innovation,
            nis=self.nis,
            q_matrix=self.q_matrix_2,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        # Test equality and inequality
        assert filt1 == filt2
        assert filt1 != filt3

    def testQMatrixProperty(self, epoch, target_agent):
        """Test Q-Matrix Property.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        assert isinstance(filt.q_matrix, ndarray)
        assert array_equal(filt.q_matrix, self.q_matrix)

    def testSigmaXResProperty(self, epoch, target_agent):
        """Test the sigma_x_res property.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        assert isinstance(filt.sigma_x_res, ndarray)
        assert array_equal(filt.sigma_x_res, self.sigma_x_res)

    def testSigmaYResProperty(self, epoch, target_agent):
        """Test the sigma_y_res property.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        assert isinstance(filt.sigma_y_res, ndarray)
        assert array_equal(filt.sigma_y_res, self.sigma_y_res)

    def testCrossCvrProperty(self, epoch, target_agent):
        """Test the cross_cvr property.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        assert isinstance(filt.cross_cvr, ndarray)
        assert array_equal(filt.cross_cvr, self.cross_cvr)

    def testInnovCvrProperty(self, epoch, target_agent):
        """Test the innov_cvr property.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        assert isinstance(filt.innov_cvr, ndarray)
        assert array_equal(filt.innov_cvr, self.innov_cvr)

    def testKalmanGainProperty(self, epoch, target_agent):
        """Test the kalman_gain property.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        assert isinstance(filt.kalman_gain, ndarray)
        assert array_equal(filt.kalman_gain, self.kalman_gain)

    def testInnovationProperty(self, epoch, target_agent):
        """Test Innovation Property.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        assert isinstance(filt.innovation, list)
        assert len(filt.innovation) == 4

    def testInnovationProperty2(self, epoch, target_agent):
        """Test Innovation property with different innovations length.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation2,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
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
        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            julian_date=epoch.julian_date,
            target_id=target_agent.unique_id,
            innovation=self.innovation,
            nis=self.nis,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
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
        filt = SequentialFilterStep.recordFilterStep(
            julian_date=epoch.julian_date,
            target_id=target_agent.unique_id,
            innovation=self.innovation,
            nis=self.nis,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
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
        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        database.insertData(filt)

        new_filt = database.getData(Query(SequentialFilterStep), multi=False)
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

        filt = SequentialFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
            q_matrix=self.q_matrix,
            sigma_x_res=self.sigma_x_res,
            sigma_y_res=self.sigma_y_res,
            cross_cvr=self.cross_cvr,
            innov_cvr=self.innov_cvr,
            kalman_gain=self.kalman_gain,
        )
        database.insertData(filt)

        # Test querying by Target
        query = Query(SequentialFilterStep).filter(SequentialFilterStep.target == target_copy)
        new_filt = database.getData(query, multi=False)
        assert new_filt.target == target_copy

        # Test querying by epoch
        query = Query(SequentialFilterStep).filter(SequentialFilterStep.epoch == epoch_copy)
