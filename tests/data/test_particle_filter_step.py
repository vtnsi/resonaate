from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, array_equal, linspace, ndarray, newaxis
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.common.utilities import ndArrayToString
from resonaate.data.filter_step import ParticleFilterStep
from resonaate.estimation.particle.genetic_particle_filter import GeneticParticleFilter
from resonaate.physics.time.stardate import ScenarioTime

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # RESONAATE Imports
    from resonaate.data.agent import AgentModel
    from resonaate.data.resonaate_database import ResonaateDatabase


class TestParticleFilterStep:
    """Test class for :class:`.ParticleFilterStep` database table class."""

    est_x = array([40_000.0, 10_000.0, 3_000.0, 1.0, 2.0, 3.0])
    est_p = array(
        [
            [100.0, 0.1, 0.1, 0.5, 0.0, 0.0],
            [0.1, 100.0, 0.1, 0.0, 0.5, 0.0],
            [0.1, 0.1, 100.0, 0.0, 0.0, 0.5],
            [0.5, 0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.5, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.5, 0.0, 0.0, 1.0],
        ],
    )
    pop_size = 5
    particles = linspace(0, 30, 30).reshape(6, 5)

    q_matrix = array(
        [[1, 2, 3], [1, 2, 3], [4, 5, 6]],
    )

    _filter: GeneticParticleFilter = None

    @property
    def filter(self):
        """Get a prebuilt filter object."""
        if self._filter is not None:
            return self._filter
        filt = GeneticParticleFilter(
            tgt_id=42,
            time=ScenarioTime(10),
            est_x=self.est_x,
            est_p=self.est_p,
            dynamics=None,
            population_size=5,
        )
        filt.population = self.particles
        filt.scores = linspace(0, 1, len(filt.population))
        filt.pop_res = self.particles - self.est_x[..., newaxis]
        self._filter = filt
        return self._filter

    def testInit(self):
        """Test the init of FilterStep database table."""
        _ = ParticleFilterStep()

    def testInitKwargs(self, epoch, target_agent: AgentModel):
        """Test initializing the keywords of the truth ephemeris table.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        innov = self.filter.pop_res.mean(axis=0)
        _ = ParticleFilterStep(
            epoch=epoch,
            target=target_agent,
            measurement_residual_azimuth=innov[0],
            measurement_residual_elevation=innov[1],
            measurement_residual_range=innov[2],
            measurement_residual_range_rate=innov[3],
            _particles=ndArrayToString(self.filter.population),
            _scores=ndArrayToString(self.filter.scores),
            _particle_residuals=ndArrayToString(self.filter.pop_res),
        )

    def testRecordParticleFilterStep(self, epoch, target_agent):
        """Test initializing the keywords of the table.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information taken at each call
        """
        _ = ParticleFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            filter=self.filter,
        )

    def testReprAndDict(self, epoch, target_agent):
        """Test printing DB table object & making into dict.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = ParticleFilterStep.recordFilterStep(
            julian_date=epoch,
            target=target_agent,
            filter=self.filter,
        )
        print(filt)
        filt.makeDictionary()

    def testEquality(self, epoch, target_agent):
        """Test equals and not equals operators.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt1 = ParticleFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            filter=self.filter,
        )

        filt2 = ParticleFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            filter=self.filter,
        )

        other_filter = deepcopy(self.filter)
        other_filter.population += 1.0
        filt3 = ParticleFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            filter=other_filter,
        )
        # Test equality and inequality
        assert filt1 == filt2
        assert filt1 != filt3

    def testProperties(self, epoch, target_agent):
        """Test ParticleFilterStep Properties.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
        """
        filt = ParticleFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            filter=self.filter,
        )
        assert isinstance(filt.particles, ndarray)
        assert array_equal(filt.particles, self.filter.population)
        assert isinstance(filt.scores, ndarray)
        assert array_equal(filt.scores, self.filter.scores)

    def testInsertWithRelationship(self, epoch, target_agent, database: ResonaateDatabase):
        """Test inserting filter values with related objects.

        Args:
            epoch (class: `.Epoch`): current epoch at which filter information is taken
            target_agent (class: `.TargetAgent`):  Target Agent information recorded at each call
            database (:class:`.ResonaateDatabase`): shared instance of database
        """
        filt = ParticleFilterStep.recordFilterStep(
            epoch=epoch,
            julian_date=epoch.julian_date,
            target_id=target_agent.unique_id,
            filter=self.filter,
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
        filt = ParticleFilterStep.recordFilterStep(
            julian_date=epoch.julian_date,
            target_id=target_agent.unique_id,
            filter=self.filter,
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
        filt = ParticleFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            filter=self.filter,
        )
        database.insertData(filt)

        new_filt = database.getData(Query(ParticleFilterStep), multi=False)
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

        filt = ParticleFilterStep.recordFilterStep(
            epoch=epoch,
            target=target_agent,
            filter=self.filter,
        )
        database.insertData(filt)

        # Test querying by Target
        query = Query(ParticleFilterStep).filter(ParticleFilterStep.target == target_copy)
        new_filt = database.getData(query, multi=False)
        assert new_filt.target == target_copy

        # Test querying by epoch
        query = Query(ParticleFilterStep).filter(ParticleFilterStep.epoch == epoch_copy)
