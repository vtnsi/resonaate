r"""Defines the Unscented Kalman Filter class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import numpy as np

# import ray
from scipy.linalg import block_diag

# RESONAATE Imports
from resonaate.physics.statistics import chiSquareQuadraticForm

# Local Imports
from ...dynamics.dynamics_base import DynamicsErrorFlag

# from ...parallel.agent_propagation import PropagateSubmission, asyncPropagate
from ...physics.bodies.earth import Earth
from ...physics.maths import vecResiduals
from ...physics.measurements import VALID_ANGULAR_MEASUREMENTS
from ...physics.time.stardate import JulianDate, julianDateToDatetime
from ..results import GPFForecastResult, GPFPredictResult, GPFUpdateResult
from ..sequential_filter import EstimateSource
from .particle_filter import FilterFlag, ParticleFilter

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...data.observation import Observation
    from ...dynamics.dynamics_base import Dynamics
    from ...dynamics.integration_events import ScheduledEventType

    # from ...parallel.agent_propagation import PropagateResult
    from ...physics.time.stardate import ScenarioTime
    from ...scenario.config.estimation_config import ParticleFilterConfig
    from ..maneuver_detection import ManeuverDetection


class GeneticParticleFilter(ParticleFilter):
    r"""Describes necessary equations for state estimation using a Genetic particle evolution algorithm.

    The GPF class provides the framework and functionality for a basic particle filter,
    which propagates the state estimate, and approximates the covariance by combining
    particle point estimates. These particles are frequently modified and resampled according
    to the likelihoods of each estimate given observations. Noise and diffusion are introduced
    through the crossover and mutation steps of the genetic algorithm.

    .. rubric:: Terminology

    The terminology used here refers to the **a** **priori** state estimate and error
    covariance as :attr:`.pred_x` and :attr:`.pred_p`, respectively, and the **a**
    **posteriori** state estimate and error covariance as :attr:`.est_x` and :attr:`.est_p`,
    respectively.

    .. rubric:: Notation

    - :math:`x` refers to the state estimate vector
    - :math:`P` refers to the error covariance matrix
    - :math:`y` refers to the measurement vector
    - :math:`N` is defined as the number of dimensions of the state estimate, :math:`x`, which is constant
    - :math:`M` is defined as the number of dimensions of the measurement, :math:`y`, which can vary with time.
    - :math:`k` is defined as the current timestep of the simulation
    - :math:`k+1` is defined as the future timestep at which the filter is predicting/estimating
    - :math:`S` is defined as the number of particle points generated.

    See Also:
        :class:`.ParticleFilter` for definition of common class attributes

    Attributes:
        population_size (``int``): The number of particles comprising the population.
        population (``ndarray``): A :math:`NxS` matrix where each column is a state vector.
        scores (``ndarray``): A :math:`Sx1` normalized vector of scores for each estimate.
        particle_residuals (``ndarray``): A :math:`MxS` array of particle residuals.

        num_purge (``int``): The number of bottom-performing particles to remove.
        num_keep (``int``): The number of top-performing particles to preserve.
        num_mutate (``int``): The number of particles to mutate.
        num_cross (``int``): The number of particles to create by crossover.

        mutation_strength (``ndarray``): A :math:`Nx1` vector of covariances for mutation strength.

    References:
        TBD
    """

    def __init__(  # noqa: PLR0913
        self,
        tgt_id: int,
        time: ScenarioTime,
        est_x: ndarray,
        est_p: ndarray,
        dynamics: Dynamics,
        maneuver_detection: ManeuverDetection | None = None,
        initial_orbit_determination: bool = False,
        adaptive_estimation: bool = False,
        population_size: int = 100,
        num_purge: int = 10,
        num_keep: int = 10,
        num_mutate: int = 50,
        mutation_strength: list[float] | None = None,
    ):
        r"""Initialize a GPF instance.

        Args:
            tgt_id (int): unique ID of the target associated with this filter object
            time (.ScenarioTime): value for the initial time (sec)
            est_x (ndarray): :math:`N\times 1` initial state estimate
            est_p (ndarray): :math:`N\times N` initial covariance
            dynamics (.Dynamics): dynamics object associated with the filter's target
            q_matrix (ndarray): dynamics error covariance matrix
            maneuver_detection (.ManeuverDetection): ManeuverDetection associated with the filter
            initial_orbit_determination (bool): Indicator that IOD can be flagged by the filter
            adaptive_estimation (bool): Indicator that adaptive estimation can be flagged by the filter
            population_size (int): Number of population members to evolve over time
            num_purge (``int``): The number of bottom-performing particles to remove.
            num_keep (``int``): The number of top-performing particles to preserve.
            num_mutate (``int``): The number of particles to mutate.
            mutation_strength (``list[float]``): A :math:`Nx1` vector of covariances for mutation strength.
        """
        super().__init__(
            tgt_id,
            time,
            est_x,
            est_p,
            dynamics,
            maneuver_detection,
            initial_orbit_determination,
            adaptive_estimation,
            extra_parameters={
                "population_size": population_size,
                "num_purge": num_purge,
                "num_keep": num_keep,
                "num_mutate": num_mutate,
                "mutation_strength": mutation_strength,
            },
        )

        self.population_size = population_size
        self.population = np.random.multivariate_normal(
            mean=est_x,
            cov=est_p,
            size=population_size,
        ).T
        self.scores = np.ones((self.population_size,)) / self.population_size

        self.particle_residuals = np.array([])

        self.num_purge = num_purge
        self.num_keep = num_keep
        self.num_mutate = num_mutate
        self.num_cross = (self.population_size - num_keep - num_purge) // 2

        self.mutation_strength = np.array(
            (
                mutation_strength
                if mutation_strength is not None
                else [0.005, 0.005, 0.005, 0.0001, 0.0001, 0.0001]
            ),
        )

    @property
    def particles(self) -> ndarray:
        """The filter's particles representing its population."""
        return self.population

    @property
    def est_p(self) -> ndarray:
        """Gaussian approximation of the estimation covariance matrix."""
        return np.cov(self.population, aweights=self.scores * self.population_size)

    @est_p.setter
    def est_p(self, _):
        pass

    @property
    def pred_p(self) -> ndarray:
        """Gaussian approximation of the prediction covariance matrix."""
        return np.cov(self.population, aweights=self.scores * self.population_size)

    @pred_p.setter
    def pred_p(self, _):
        pass

    @classmethod
    def fromConfig(
        cls,
        config: ParticleFilterConfig,
        tgt_id: int,
        time: ScenarioTime,
        est_x: ndarray,
        est_p: ndarray,
        dynamics: Dynamics,
        maneuver_detection: ManeuverDetection,
        *args,  # noqa: ARG003
        **kwargs,  # noqa: ARG003
    ) -> ParticleFilter:
        """Build a :class:`.ParticleFilter` object for target state estimation.

        Args:
            config (:class:`.ParticleFilterConfig`): describes the filter to be built
            tgt_id (``int``): unique ID of the associated target agent
            time (:class:`.ScenarioTime`): initial time of scenario
            est_x (``ndarray``): 6x1, initial state estimate
            est_p (``ndarray``): 6x6, initial error covariance matrix
            dynamics (:class:`.Dynamics`): dynamics object to propagate estimate
            maneuver_detection (.ManeuverDetection): ManeuverDetection associated with the filter
            args (``list[Unknown]``): a list of other arguments; may be used by subclasses
            kwargs (``dict[str, Unknown]``): a dictionary of other arguments; may be used by subclasses

        Returns:
            :class:`.ParticleFilter`: constructed filter object
        """
        return cls(
            tgt_id,
            time,
            est_x,
            est_p,
            dynamics,
            maneuver_detection=maneuver_detection,
            initial_orbit_determination=config.initial_orbit_determination,
            adaptive_estimation=config.adaptive_estimation,
            population_size=config.population_size,
            num_purge=config.num_purge,
            num_keep=config.num_keep,
            num_mutate=config.num_mutate,
            mutation_strength=config.mutation_strength,
        )

    def predict(
        self,
        final_time: ScenarioTime,
        scheduled_events: list[ScheduledEventType] | None = None,
    ):
        r"""Propagate the state estimate and error covariance with uncertainty.

        Args:
            final_time (.ScenarioTime): time to propagate to
            scheduled_events (list): scheduled events to apply during propagation which
                can either be implemented :class:`.ContinuousStateChangeEvent` or
                :class:`.DiscreteStateChangeEvent` objects.
        """
        # Reset filter flags
        self._flags = FilterFlag.NONE

        # STEP 1: Propagate the population through their dynamics to t(k) (X(k + 1|k))
        # submissions = [
        #     PropagateSubmission(
        #         agent_id=i,
        #         dynamics=self.dynamics,
        #         init_time=self.time,
        #         final_time=final_time,
        #         init_eci=self.population[:, i].flatten(),
        #         station_keeping=self.station_keeping,
        #         scheduled_events=scheduled_events,
        #         error_flags=DynamicsErrorFlag(0),
        #     )
        #     for i in range(self.population_size)
        # ]
        # results: list[PropagateResult] = ray.get(list(map(asyncPropagate.remote, submissions)))
        # idx = np.array([r.agent_id for r in results])
        # states = np.stack([r.final_eci for r in results]).T
        # states[:, idx] = states
        # self.population = states

        # TODO: is it necessary to insert the results back into place? probably?
        # self.population = np.stack(states).T

        # TODO: Compare performance against propagating locally
        # t = self.time
        # states = np.stack([self.dynamics.propagate(
        #     t,
        #     final_time,
        #     self.population[:,i].flatten(),
        #     station_keeping=self.station_keeping,
        #     scheduled_events=scheduled_events,
        #     error_flags=DynamicsErrorFlag(0),
        # ) for i in range(self.population_size)])
        # self.population = states.T

        states = self.dynamics.propagateBulk(
            [self.time, final_time],
            self.population,
            station_keeping=self.station_keeping,
            scheduled_events=scheduled_events,
            error_flags=DynamicsErrorFlag(0),
        )[..., -1]
        self.population = states

        # STEP 1.1: Check Earth collisions and downweight any particles that
        #           collide, as well as constrain them to the surface
        r_norm_sq = np.einsum("ij->j", self.population[:3, :] ** 2)
        if np.any(r_norm_sq > Earth.radius**2):
            self.scores = np.where(
                r_norm_sq > Earth.radius**2,
                self.scores,
                np.zeros_like(self.scores),
            )
            units = self.population[:3] / np.linalg.norm(self.population[:3], axis=0)
            self.population = np.where(
                r_norm_sq > Earth.radius**2,
                self.population,
                np.concatenate([units * Earth.radius, np.zeros_like(units)], axis=0),
            )

        # STEP 2: Calculate the predicted state
        self.pred_x = np.average(self.population, axis=1, weights=self.scores)

        # STEP 3: Update the time step
        self.time = final_time

    def forecast(self, observations: list[Observation]):
        r"""Update the error covariance with observations.

        Args:
            observations (list): :class:`.Observation` objects associated with the GPF step
        """
        # Reset filter flags
        self._flags = FilterFlag.NONE

        _, res = self.calculateResidualsFromObservations(observations)
        self.r_matrix = block_diag(*[ob.r_matrix for ob in observations])
        new_scores = np.apply_along_axis(
            lambda v: np.exp(
                -0.5 * (v[..., np.newaxis].T @ self.r_matrix @ v[..., np.newaxis]).item(),
            ),
            0,
            res,
        )

        # Set the population scores to the new evaluated scores, but mask out 0 scores
        self.scores = new_scores * (self.scores > 1e-12).astype(self.scores.dtype)
        if np.sum(self.scores) == 0.0:
            self.scores = np.ones_like(self.scores) / len(self.scores)
        else:
            self.scores /= np.sum(self.scores)

    def update(self, observations: list[Observation]):
        r"""Update the state estimate with observations.

        Args:
            observations (list): :class:`.Observation` objects associated with the GPF step
        """
        if not observations:
            self.source = EstimateSource.INTERNAL_PROPAGATION
        else:
            self.source = EstimateSource.INTERNAL_OBSERVATION

            # Performs covariance portion of the update step
            self.forecast(observations)

            if self.particle_residuals.size > 0:
                self.innovation = np.average(
                    self.particle_residuals,
                    axis=-1,
                    weights=self.scores * self.population_size,
                )
                self.nis = chiSquareQuadraticForm(
                    self.innovation,
                    self.innovation @ np.eye(len(self.innovation)) @ self.innovation.T
                    + self.r_matrix,
                )

            # Resample the points
            self.resample()

            # STEP 4: Maneuver detection
            self.checkManeuverDetection()

            self._debugChecks(observations)

        self.est_x = np.average(self.population, axis=1, weights=self.scores)

    def calculateResidualsFromObservations(
        self,
        observations: list[Observation],
    ) -> tuple[ndarray, ndarray]:
        r"""Calculate the stacked observation/measurement matrix for a set of observations.

        Convert the population members into the measurement space, then calculate residuals
        against the true measurement.

        Args:
            observations (list): :class:`.Observation` objects associated with the update step
        """
        # Create observations for each sigma point
        population_obs = np.concatenate(
            [
                np.apply_along_axis(
                    lambda v: list(
                        obs.measurement.calculateMeasurement(  # noqa: B023
                            obs.sensor_eci,  # noqa: B023
                            v,
                            dt,  # noqa: B023
                            noisy=False,
                        ).values(),
                    ),
                    0,
                    self.population,
                )
                for dt, obs in map(  # noqa: C417
                    lambda o: (julianDateToDatetime(JulianDate(o.julian_date)), o),
                    observations,
                )
            ],
            axis=0,
        )

        # Convert to 1-D list of IsAngle values for the combined observation state
        angular_measurements = np.concatenate(
            [ob.measurement.angular_values for ob in observations],
            axis=0,
        )

        # Mx1 array of whether each corresponding measurement was angular or not
        self.is_angular = np.array(
            [a in VALID_ANGULAR_MEASUREMENTS for a in angular_measurements],
            dtype=bool,
        )

        true_y = np.concatenate([o.measurement_states for o in observations], axis=0)

        # Determine the difference between the sigma pt observations and the mean observation
        self.particle_residuals = vecResiduals(
            population_obs,
            true_y[..., np.newaxis],
            self.is_angular[..., np.newaxis],
        )

        return true_y, self.particle_residuals

    def resample(self):
        """Perform the genetic update step to resample filter particles."""
        # Step 0. Sort the population members by their scores
        fitness = np.argsort(self.scores).flatten()

        pop = self.population.copy()
        pop[:, : self.num_keep] = pop[:, -self.num_keep :].copy()
        scores = self.scores.copy()
        scores[: self.num_keep] = scores[-self.num_keep :].copy()
        self.population = pop
        self.scores = scores

        # Step 1. Identify pairs for crossover
        pairs = np.random.choice(
            fitness[self.num_purge :],
            size=(self.num_cross, 2),
            replace=True,  # TODO: Add configuration option
            p=self.scores[self.num_purge :] / self.scores[self.num_purge :].sum(),
        )
        new_members = self.crossover(pairs)
        new_member_scores = self.scores[pairs.ravel()].reshape(-1, 2).mean(axis=1)

        # Step 2. Update the population with the new members
        pop = self.population.copy()
        pop[:, fitness[: self.num_cross]] = new_members
        self.population = pop
        scores = self.scores.copy()
        scores[fitness[: self.num_cross]] = new_member_scores

        if np.sum(scores) == 0.0:
            scores = np.ones_like(scores) / len(scores)
        else:
            scores /= np.sum(scores)
        self.scores = scores

        # Step 3. Identify members for mutation, preserving the top performers.
        #         This is where spread/novelty comes from in our filter
        mutation_indices = np.random.choice(
            fitness[self.num_keep : -self.num_keep],
            size=self.num_mutate - self.num_keep,
            replace=False,
            p=self.scores[self.num_keep : -self.num_keep]
            / self.scores[self.num_keep : -self.num_keep].sum(),
        )
        mutation_indices = np.concatenate([mutation_indices, fitness[: self.num_keep]]).flatten()
        self.mutate(mutation_indices)

    def crossover(self, pairs: ndarray) -> ndarray:
        r"""Performs genetic crossover.

        Args:
            pairs (ndarray): :math:`S\times 2` array of population indices to
                use for crossover

        Returns:
            A :math:`S\timesN` array of the crossover products
        """
        parents = self.population[:, pairs]  # NxSx2
        num_choices = parents.shape[0] * parents.shape[1]
        choice = np.random.randint(2, size=num_choices)
        return parents.reshape(-1, 2)[np.arange(num_choices), choice].reshape(
            parents.shape[0],
            parents.shape[1],
        )

    def mutate(self, indices: ndarray):
        r"""Performs genetic mutation on the specified population members.

        Args:
            indices (ndarray): :math:`S\times1` vector of member indices
        """
        mutations = self.mutation_strength[..., np.newaxis] * np.random.standard_normal(
            (self.population.shape[0], len(indices)),
        )
        pop = self.population.copy()
        pop[:, indices] += mutations
        self.population = pop

    def getPredictionResult(self) -> GPFPredictResult:
        """Compile result message for a predict step.

        Returns:
            Filter results from the 'predict' step.
        """
        return GPFPredictResult.fromFilter(self)

    def getForecastResult(self) -> GPFForecastResult:
        """Compile result message for a forecast step.

        Returns:
            Filter results from the 'forecast' step.
        """
        return GPFForecastResult.fromFilter(self)

    def getUpdateResult(self) -> GPFUpdateResult:
        """Compile result message for an update step.

        Returns:
            Filter results from the 'update' step.
        """
        return GPFUpdateResult.fromFilter(self)
