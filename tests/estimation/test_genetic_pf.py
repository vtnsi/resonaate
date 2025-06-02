from __future__ import annotations

# Standard Library Imports
import datetime
from unittest.mock import MagicMock, patch

# Third Party Imports
import pytest
from numpy import allclose

# RESONAATE Imports
from resonaate.data.observation import Observation
from resonaate.dynamics import two_body
from resonaate.estimation import GeneticParticleFilter
from resonaate.estimation.particle.particle_filter import FilterFlag
from resonaate.estimation.sequential_filter import EstimateSource
from resonaate.physics.measurements import Measurement
from resonaate.physics.time.stardate import ScenarioTime

# Local Imports
from .ukf_support import (
    GROUND_SENSOR_ECI,
    R_MATRIX_OPTICAL,
    R_MATRIX_RADAR,
    SPACECRAFT_SENSOR_ECI,
    UKF_EST_P,
    UKF_EST_X,
    UKF_MEAN,
    UKF_MEAN_COV,
    UKF_PRED_P,
    UKF_SIGMA_POINTS,
)


# -----------------------------------------------------------------------------
# Define pytest fixtures
# -----------------------------------------------------------------------------
@pytest.fixture(name="gpf")
def createGPF() -> GeneticParticleFilter:
    """Construct a valid GPF object."""
    return GeneticParticleFilter(
        tgt_id=10001,
        time=ScenarioTime(0.0),
        est_x=UKF_MEAN,
        est_p=UKF_MEAN_COV,
        dynamics=two_body.TwoBody(),
        maneuver_detection=False,
        initial_orbit_determination=False,
        adaptive_estimation=False,
    )


@pytest.fixture(name="radar_obs")
def createRadarObservation() -> Observation:
    """Construct a valid radar Observation object."""
    # [NOTE]: Easier to provide actual measurement than mocking...
    radar_measurement = Measurement.fromMeasurementLabels(
        ["azimuth_rad", "elevation_rad", "range_km", "range_rate_km_p_sec"],
        R_MATRIX_RADAR,
    )

    obs: Observation = MagicMock(spec=Observation)
    obs.measurement = radar_measurement
    obs.sensor_eci = SPACECRAFT_SENSOR_ECI
    obs.r_matrix = radar_measurement.r_matrix
    obs.dim = 4
    return obs


@pytest.fixture(name="optical_obs")
def createOpticalObservation() -> Observation:
    """Construct a valid optical Observation object."""
    # [NOTE]: Easier to provide actual measurement than mocking...
    optical_measurement = Measurement.fromMeasurementLabels(
        ["azimuth_rad", "elevation_rad"],
        R_MATRIX_OPTICAL,
    )

    return Observation.fromMeasurement(
        epoch_jd=2459304.443715,
        target_id=42,
        tgt_eci_state=UKF_EST_X,
        sensor_id=1,
        sensor_eci=GROUND_SENSOR_ECI,
        sensor_type="optical",
        measurement=optical_measurement,
        noisy=True,
    )


# -----------------------------------------------------------------------------
# Define test functions
# -----------------------------------------------------------------------------
def testInitialPopulation(gpf: GeneticParticleFilter):
    """Test the population initialization."""
    assert gpf.population.shape == (gpf.x_dim, gpf.population_size)
    assert allclose(gpf.population.mean(axis=1), gpf.est_x, rtol=1e-4)


def testPredict(gpf: GeneticParticleFilter):
    """Test predict() method."""
    final_time = ScenarioTime(300.0)
    assert gpf.time == ScenarioTime(0.0)

    gpf.predict(final_time)

    assert gpf.time == final_time
    assert gpf._flags == FilterFlag.NONE


@patch("resonaate.estimation.particle.genetic_particle_filter.julianDateToDatetime")
def testForecast(mocked_jd2dt: MagicMock, gpf: GeneticParticleFilter, optical_obs: Observation):
    """Test forecast() method."""
    mocked_jd2dt.return_value = datetime.datetime(2021, 10, 21, 11, 26, 13)

    gpf.forecast([optical_obs])
    assert allclose(gpf.est_x, UKF_EST_X, atol=100.0)
    assert allclose(gpf.est_p, UKF_EST_P, rtol=1e-4, atol=1e-6)


def testUpdateNoObservations(gpf: GeneticParticleFilter):
    """Test update() method without any observations."""
    gpf.pred_p = UKF_PRED_P
    gpf.est_p = 2 * UKF_PRED_P
    gpf.forecast = MagicMock()

    gpf.update([])
    assert gpf.source == EstimateSource.INTERNAL_PROPAGATION
    assert allclose(gpf.est_x, UKF_SIGMA_POINTS[:, 0], rtol=1e-4, atol=1e-7)
    assert allclose(gpf.est_p, UKF_PRED_P, rtol=1e-4, atol=1e-6)
    gpf.forecast.assert_not_called()


# @patch("resonaate.estimation.sequential.unscented_kalman_filter.chiSquareQuadraticForm")
# @patch("resonaate.estimation.sequential.unscented_kalman_filter.residuals")
def testUpdate(
    # mocked_residuals: MagicMock,
    # mocked_chi_square: MagicMock,
    gpf: GeneticParticleFilter,
    optical_obs: Observation,
):
    """Test update() method with observations."""
    gpf.forecast = MagicMock()
    gpf.checkManeuverDetection = MagicMock()
    gpf._debugChecks = MagicMock()
    gpf.pred_x = UKF_MEAN

    gpf.update([optical_obs])

    gpf.forecast.assert_called_once()
    gpf.checkManeuverDetection.assert_called_once()
    gpf._debugChecks.assert_called_once()
    # mocked_residuals.assert_called_once()
    assert allclose(gpf.est_x, UKF_EST_X, atol=100.0)
