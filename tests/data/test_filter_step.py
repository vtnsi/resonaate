from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
from numpy import array
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.filter_step import FilterStep
from resonaate.data.resonaate_database import ResonaateDatabase


class TestFilterStep:
    """Test class for :class:`.FilterStep` database table class."""

    innovation = array(
        [
            -2.334817207660933e-05,
            -2.0436287793690333e-05,
            -0.0362834239294898,
            -0.000185071151261873,
        ]
    )
    nis = 5.37607495178574
    innovation2 = array([-2.334817207660933e-05, -2.0436287793690333e-05])

    def testInit(self):
        """Test the init of FilterStep database table."""
        _ = FilterStep()

    def testInitKwargs(self, epoch, target_agent):
        """Test initializing the kewards of the truth ephemeris table.

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
        )

    def testrecordFilterStep(self, epoch, target_agent):
        """Test initializing the kewards of the table.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information taken at each call
        """
        _ = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
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
        )

        filt2 = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
        )

        filt3 = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation + self.innovation,
            nis=self.nis,
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
        )
        assert isinstance(filt.innovation, list)
        assert len(filt.innovation) == 2

    def testInsertWithRelationship(self, epoch, target_agent):
        """Test inserting filter values with related objects.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        database = ResonaateDatabase.getSharedInterface()
        filt = FilterStep.recordFilterStep(
            epoch=epoch,
            julian_date=epoch.julian_date,
            target_id=target_agent.unique_id,
            innovation=self.innovation,
            nis=self.nis,
        )

        # Test insert of object
        database.insertData(filt)

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testInsertWithForeignKeys(self, epoch, target_agent):
        """Test inserting observation with only foreign keys.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        database = ResonaateDatabase.getSharedInterface()
        filt = FilterStep.recordFilterStep(
            julian_date=epoch.julian_date,
            target_id=target_agent.unique_id,
            innovation=self.innovation,
            nis=self.nis,
        )
        # Pre-insert required objects
        database.insertData(epoch)
        database.insertData(target_agent)

        # Test insert of object via FK
        database.insertData(filt)

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testManyToOneLazyLoading(self, epoch, target_agent):
        """Test many to one lazy-loading attributes.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        julian_date = epoch.julian_date
        target_id = target_agent.unique_id
        database = ResonaateDatabase.getSharedInterface()
        filt = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
        )
        database.insertData(filt)

        new_filt = database.getData(Query(FilterStep), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_filt.epoch.julian_date == julian_date
        assert new_filt.target.unique_id == target_id

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testManyToOneQuery(self, epoch, target_agent):
        """Test many to one relationship queries.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        epoch_copy = deepcopy(epoch)
        target_copy = deepcopy(target_agent)

        database = ResonaateDatabase.getSharedInterface()
        filt = FilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            innovation=self.innovation,
            nis=self.nis,
        )
        database.insertData(filt)

        # Test querying by Target
        query = Query(FilterStep).filter(FilterStep.target == target_copy)
        new_filt = database.getData(query, multi=False)
        assert new_filt.target == target_copy

        # Test querying by epoch
        query = Query(FilterStep).filter(FilterStep.epoch == epoch_copy)
        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)
