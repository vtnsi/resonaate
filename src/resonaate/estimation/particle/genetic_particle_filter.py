r"""Defines the Unscented Kalman Filter class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import numpy as np
from scipy.linalg import block_diag

# RESONAATE Imports
from resonaate.dynamics.dynamics_base import DynamicsErrorFlag

# Local Imports
from ...physics.maths import angularMean, vecResiduals
from ...physics.measurements import VALID_ANGLE_MAP, VALID_ANGULAR_MEASUREMENTS
from ...physics.time.stardate import JulianDate, julianDateToDatetime
from ..results import GPFForecastResult, GPFPredictResult, GPFUpdateResult
from .particle_filter import FilterFlag, ParticleFilter

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...data.observation import Observation
    from ...dynamics.dynamics_base import Dynamics
    from ...dynamics.integration_events import ScheduledEventType
    from ...physics.measurements import IsAngle
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
        q_matrix: ndarray,
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
            q_matrix,
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
        self.scores = np.ones((self.population_size,))

        self.pop_res = np.array([])

        self.num_purge = num_purge
        self.num_keep = num_keep
        self.num_mutate = num_mutate
        self.num_cross = (self.population_size - num_keep - num_purge) // 2

        self.mutation_strength = (
            np.array(mutation_strength)
            if mutation_strength is not None
            else np.ones((self.x_dim,))
        )

    @classmethod
    def fromConfig(
        cls,
        config: ParticleFilterConfig,
        tgt_id: int,
        time: ScenarioTime,
        est_x: ndarray,
        est_p: ndarray,
        dynamics: Dynamics,
        q_matrix: ndarray,
        maneuver_detection: ManeuverDetection,
    ) -> ParticleFilter:
        """Build a :class:`.ParticleFilter` object for target state estimation.

        Args:
            config (:class:`.ParticleFilterConfig`): describes the filter to be built
            tgt_id (``int``): unique ID of the associated target agent
            time (:class:`.ScenarioTime`): initial time of scenario
            est_x (``ndarray``): 6x1, initial state estimate
            est_p (``ndarray``): 6x6, initial error covariance matrix
            dynamics (:class:`.Dynamics`): dynamics object to propagate estimate
            q_matrix (``ndarray``): process noise covariance matrix
            maneuver_detection (.ManeuverDetection): ManeuverDetection associated with the filter

        Returns:
            :class:`.ParticleFilter`: constructed filter object
        """
        return cls(
            tgt_id,
            time,
            est_x,
            est_p,
            dynamics,
            q_matrix,
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
        self.population = self.dynamics.propagate(
            self.time,
            final_time,
            self.population,
            scheduled_events=scheduled_events,
            error_flags=DynamicsErrorFlag(0),
        )

        # STEP 2: Calculate the predicted state and covariance at t(k) (P(k + 1|k))
        self.pred_x = np.average(self.population, axis=1, weights=self.scores)
        self.pred_p = np.cov(self.population, aweights=self.scores)

        # STEP 3: Update the time step
        self.time = final_time

    def forecast(self, observations: list[Observation]):
        r"""Update the error covariance with observations.

        Args:
            observations (list): :class:`.Observation` objects associated with the GPF step
        """
        # Reset filter flags
        self._flags = FilterFlag.NONE

        mean, res = self.calculateMeasurementMatrix(observations)
        r_matrix = block_diag(*[ob.r_matrix for ob in observations])
        self.scores = np.apply_along_axis(
            lambda x: x.T @ r_matrix @ x,
            0,
            res,
        )
        self.scores = np.nan_to_num(self.scores, nan=1e-12)

    def update(self, observations: list[Observation]):
        r"""Update the state estimate with observations.

        Args:
            observations (list): :class:`.Observation` objects associated with the GPF step
        """
        if not observations:
            self.source = self.INTERNAL_PROPAGATION_SOURCE
        else:
            self.source = self.INTERNAL_OBSERVATION_SOURCE

            # Performs covariance portion of the update step
            self.forecast(observations)

            # Resample the points
            self.resample()

            # STEP 4: Maneuver detection
            self.checkManeuverDetection()

            self._debugChecks(observations)

        self.est_x = np.average(self.population, axis=1, weights=self.scores)
        self.est_p = np.cov(self.population, aweights=self.scores)

    def _calcMeasurementSigmaPoints(self, observations: list[Observation]) -> ndarray:
        r"""Calculate the measurement sigma points by passing sigma points into the measurement function.

        This properly handles disparate measurement types being combined on a single timestep by stacking
        them together into a single measurement with an uncorrelated measurement noise covariance constructed
        as a block diagonal of the individual measurement noise covariances.

        Args:
            observations (list): :class:`.Observation` objects associated with the UKF step

        Returns:
            ``ndarray``: :math:`M\times S` properly configured measurement sigma point set, where
            :math:`M` is the compiled measurement space, and :math:`S` is the number of sigma points.
        """
        obs_vector_list = []
        for sigma_idx in range(self.population_size):
            obs_states = []
            for observation in observations:
                utc_datetime = julianDateToDatetime(JulianDate(observation.julian_date))
                sigma_measurement = observation.measurement.calculateMeasurement(
                    observation.sensor_eci,
                    self.population[:, sigma_idx],
                    utc_datetime,
                    noisy=False,
                )
                obs_states.append(list(sigma_measurement.values()))

            # Add stacked observations to the list
            stacked_obs_state = np.concatenate(obs_states, axis=0)
            stacked_obs_state.shape = (stacked_obs_state.size, 1)
            obs_vector_list.append(stacked_obs_state)

        # Concatenate stacked obs into MxS
        return np.concatenate(obs_vector_list, axis=1)

    def calculateMeasurementMatrix(
        self,
        observations: list[Observation],
    ) -> tuple[ndarray, ndarray]:
        r"""Calculate the stacked observation/measurement matrix for a set of observations.

        The UKF doesn't use an :math:`H` Matrix. Instead, the differences between the predicted state or
        observations, and the associated sigma values are calculated. These are used to
        determine the cross and innovations covariances.

        Args:
            observations (list): :class:`.Observation` objects associated with the UKF step
        """
        # Create observations for each sigma point
        sigma_obs = self._calcMeasurementSigmaPoints(observations)

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

        # Save mean predicted measurement vector
        mean_pred = self.calcMeasurementMean(sigma_obs, angular_measurements)

        # Determine the difference between the sigma pt observations and the mean observation
        self.pop_res = vecResiduals(
            sigma_obs,
            mean_pred[..., np.newaxis],
            self.is_angular[..., np.newaxis],
        )

        return mean_pred, self.pop_res

    def calcMeasurementMean(
        self,
        measurement_sigma_pts: ndarray,
        is_angular: list[IsAngle],
    ) -> ndarray:
        r"""Determine the mean of the predicted measurements.

        This is done generically which allows for measurements to be ordered in any fashion, but
        requires an associated boolean vector to flag for angle measurements. This special
        treatment is required because angles are nonlinear (modular), so calculating the mean is
        not a linear operation.

        Angular mean:

        .. math::

            \bar{\theta} = \arctan \left( \frac{\sum^{N}_{i=1}\sin{\theta_{i}}}{\sum^{N}_{i=1}\cos{\theta_{i}}} \right)

        Normal mean:

        .. math::

            \bar{x} = \frac{1}{N}\sum^{N}_{i=1}{x_i}

        Args:
            measurement_sigma_pts (ndarray): :math:`M\times S` array of predicted measurements, where
                :math:`M` is the compiled measurement space, and :math:`S` is the number of sigma points.
            is_angular (list): :class:`.IsAngle` objects corresponding to type of angular measurement.

        Returns:
            ``ndarray``: :math:`M\times 1` predicted measurement mean
        """
        meas_mean = np.zeros((measurement_sigma_pts.shape[0],))
        for idx, (meas, angular) in enumerate(zip(measurement_sigma_pts, is_angular)):
            if angular in VALID_ANGULAR_MEASUREMENTS:
                low, high = VALID_ANGLE_MAP[angular]
                mean = angularMean(meas, weights=self.scores, low=low, high=high)
            else:
                mean = meas.dot(self.scores)

            meas_mean[idx] = mean

        return meas_mean

    def resample(self):
        """Perform the genetic update step to resample filter particles."""
        # Step 0. Sort the population members by their scores
        fitness = np.argsort(self.scores).flatten()

        # Step 1. Identify pairs for crossover
        pairs = np.random.choice(
            fitness[self.num_purge :],
            size=(self.num_cross, 2),
            replace=False,
        )
        new_members = self.crossover(pairs)
        new_member_scores = self.scores[pairs.ravel()].reshape(-1, 2).mean(axis=1)

        # Step 2. Update the population with the new members
        pop = self.population.copy()
        pop[:, fitness[: self.num_cross]] = new_members
        self.population = pop
        scores = self.scores.copy()
        scores[fitness[: self.num_cross]] = new_member_scores
        self.scores = scores
        # self.scores /= np.linalg.norm(self.scores)

        # Step 3. Identify members for mutation, preserving the top performers.
        #         This is where spread/novelty comes from in our filter
        mutation_indices = np.random.choice(
            fitness[: -self.num_keep],
            size=self.num_mutate,
            replace=False,
        )
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
