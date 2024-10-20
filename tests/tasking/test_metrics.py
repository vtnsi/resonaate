from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.tasking.metrics.information import (
    FisherInformation,
    KLDivergence,
    ShannonInformation,
)
from resonaate.tasking.metrics.metric_base import Metric
from resonaate.tasking.metrics.sensor import (
    SlewDistanceMaximization,
    SlewDistanceMinimization,
    SlewTimeMaximization,
    SlewTimeMinimization,
)
from resonaate.tasking.metrics.stability import LyapunovStability
from resonaate.tasking.metrics.state import Range
from resonaate.tasking.metrics.target import TimeSinceObservation
from resonaate.tasking.metrics.uncertainty import (
    PositionCovarianceDeterminant,
    PositionCovarianceReduction,
    PositionCovarianceTrace,
    PositionMaxEigenValue,
    VelocityCovarianceDeterminant,
    VelocityCovarianceReduction,
    VelocityCovarianceTrace,
    VelocityMaxEigenValue,
)

# Type Checking Imports
if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.agents.estimate_agent import EstimateAgent
    from resonaate.agents.sensing_agent import SensingAgent


@pytest.fixture(name="mocked_metric_class")
def mockedMetricClass() -> Metric:
    """Return reference to a minimal :class:`.Metric` class."""

    class MockedMetric(Metric):
        def calculate(self, estimate_agent, sensor_agent):
            return 4

    return MockedMetric


class TestMetricsBase:
    """Test the base class of the metrics module."""

    def testCreation(self):
        """Test creating a Metric Object."""
        with pytest.raises(TypeError):
            Metric()

    def testMetricCall(
        self,
        mocked_estimate: EstimateAgent,
        mocked_metric_class: Metric,
        mocked_sensing_agent: SensingAgent,
    ):
        """Test the call function of the Metric base class."""
        metric = mocked_metric_class()
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {"sensor": mocked_sensing_agent}
        sensor_id = "sensor"
        metric.calculate(target_agents[target_id], sensor_agents[sensor_id])


class TestInformationMetric:
    """Test the InformationMetric class of the metrics module."""

    def testCalculateMetric(
        self,
        mocked_estimate: EstimateAgent,
        mocked_sensing_agent: SensingAgent,
    ):
        """Test the calculate metric function."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {1234: mocked_sensing_agent}
        sensor_id = 1234

        shannon_metric = ShannonInformation()
        shannon_value = shannon_metric.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert shannon_value > 0.0

        fisher_metric = FisherInformation()
        fisher_value = fisher_metric.calculate(target_agents[target_id], sensor_agents[sensor_id])
        assert fisher_value > 0.0

        kld_metric = KLDivergence()
        kld_value = kld_metric.calculate(target_agents[target_id], sensor_agents[sensor_id])
        assert kld_value > 0.0


class TestUncertaintyMetric:
    """Test the UncertaintyMetric class of the metrics module."""

    def testCalculateMetric(
        self,
        mocked_estimate: EstimateAgent,
        mocked_sensing_agent: SensingAgent,
    ):
        """Test the calculate metric function."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {1234: mocked_sensing_agent}
        sensor_id = 1234

        position_covar_metric = PositionCovarianceReduction()
        pos_covar_value = position_covar_metric.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert pos_covar_value > 0.0

        position_det = PositionCovarianceDeterminant()
        pos_det_value = position_det.calculate(target_agents[target_id], sensor_agents[sensor_id])
        assert pos_det_value > 0.0

        position_trace = PositionCovarianceTrace()
        pos_trace_value = position_trace.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert pos_trace_value > 0.0

        position_eigen = PositionMaxEigenValue()
        pos_eig_value = position_eigen.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert pos_eig_value > 0.0

        velocity_covar_metric = VelocityCovarianceReduction()
        vel_covar_value = velocity_covar_metric.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert vel_covar_value > 0.0

        velocity_det = VelocityCovarianceDeterminant()
        vel_det_value = velocity_det.calculate(target_agents[target_id], sensor_agents[sensor_id])
        assert vel_det_value > 0.0

        velocity_trace = VelocityCovarianceTrace()
        vel_trace_value = velocity_trace.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert vel_trace_value > 0.0

        velocity_eigen = VelocityMaxEigenValue()
        vel_eig_value = velocity_eigen.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert vel_eig_value > 0.0


class TestStabilityMetric:
    """Test the StabilityMetric class of the metrics module."""

    def testCalculateMetric(
        self,
        mocked_estimate: EstimateAgent,
        mocked_sensing_agent: SensingAgent,
    ):
        """Test the calculate metric function."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {1234: mocked_sensing_agent}
        sensor_id = 1234
        lyapunov_metric = LyapunovStability()
        lyapunov_value = lyapunov_metric.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert lyapunov_value > 0.0

        # Test negative Lyapunov stability
        mocked_estimate.nominal_filter.pred_p = np.array(
            [
                [2.0e-08, 0.0e00, 0.0e00, 0.0e00, 0.0e00, 0.0e00],
                [0.0e00, 2.0e-08, 0.0e00, 0.0e00, 0.0e00, 0.0e00],
                [0.0e00, 0.0e00, 2.0e-08, 0.0e00, 0.0e00, 0.0e00],
                [0.0e00, 0.0e00, 0.0e00, 2.0e-13, 0.0e00, 0.0e00],
                [0.0e00, 0.0e00, 0.0e00, 0.0e00, 2.0e-13, 0.0e00],
                [0.0e00, 0.0e00, 0.0e00, 0.0e00, 0.0e00, 2.0e-13],
            ],
        )
        negative_lyapunov = lyapunov_metric.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert negative_lyapunov < 0.0


class TestSensorMetric:
    """Test the SensorMetric class of the metrics module."""

    def testCalculateMetric(
        self,
        mocked_estimate: EstimateAgent,
        mocked_sensing_agent: SensingAgent,
    ):
        """Test the calculate metric function."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {1234: mocked_sensing_agent}
        sensor_id = 1234

        distance_minimization = SlewDistanceMinimization()
        distance_minimization_value = distance_minimization.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert distance_minimization_value > 0.0

        distance_maximization = SlewDistanceMaximization()
        distance_maximization_value = distance_maximization.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert distance_maximization_value > 0.0
        assert distance_maximization_value > distance_minimization_value

        slew_minimization = SlewTimeMinimization()
        slew_min_value = slew_minimization.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert slew_min_value > 0.0

        slew_maximization = SlewTimeMaximization()
        slew_maximization_value = slew_maximization.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert slew_maximization_value > 0.0
        assert slew_maximization_value > slew_min_value


class TestStateMetric:
    """Test the StateMetric class of the metrics module."""

    def testCalculateMetric(
        self,
        mocked_estimate: EstimateAgent,
        mocked_sensing_agent: SensingAgent,
    ):
        """Test the calculate metric function."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {1234: mocked_sensing_agent}
        sensor_id = 1234

        range_metric = Range()
        range_value = range_metric.calculate(target_agents[target_id], sensor_agents[sensor_id])
        assert range_value > 0.0


class TestTargetMetric:
    """Test the TargetMetric class of the metrics module."""

    def testCalculateMetric(
        self,
        mocked_estimate: EstimateAgent,
        mocked_sensing_agent: SensingAgent,
    ):
        """Test the calculate metric function."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {1234: mocked_sensing_agent}
        sensor_id = 1234

        time_since_observation = TimeSinceObservation()
        staleness_value = time_since_observation.calculate(
            target_agents[target_id],
            sensor_agents[sensor_id],
        )
        assert staleness_value > 0.0
