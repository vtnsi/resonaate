from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.tasking.metrics.behavior import TimeSinceObservation
from resonaate.tasking.metrics.information import FisherInformation, ShannonInformation
from resonaate.tasking.metrics.metric_base import Metric
from resonaate.tasking.metrics.sensor import DeltaPosition, SlewCycle, TimeToTransit
from resonaate.tasking.metrics.stability import LyapunovStability

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

    def testRegistry(self, mocked_metric_class: Metric):
        """Test to make sure the Metric object is registered."""
        test_metric = mocked_metric_class()
        assert test_metric.is_registered is False

        # Register new class and check
        Metric.register(mocked_metric_class)
        test_metric = mocked_metric_class()
        assert test_metric.is_registered is True

        # Ensure we cannot register objects that are not :class:`.Metric` sub-classes
        with pytest.raises(TypeError):
            Metric.register([2, 2])

    def testCreation(self):
        """Test creating a Metric Object."""
        with pytest.raises(TypeError):
            Metric()  # pylint: disable=abstract-class-instantiated

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
        shannon_metric.calculate(target_agents[target_id], sensor_agents[sensor_id])
        fisher_metric = FisherInformation()
        fisher_metric.calculate(target_agents[target_id], sensor_agents[sensor_id])


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
        lyapunov_metric.calculate(target_agents[target_id], sensor_agents[sensor_id])


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
        delta_position = DeltaPosition()
        delta_position.calculate(target_agents[target_id], sensor_agents[sensor_id])
        slew_cycle = SlewCycle()
        slew_cycle.calculate(target_agents[target_id], sensor_agents[sensor_id])
        time_to_transit = TimeToTransit(norm_factor=10)
        time_to_transit.calculate(target_agents[target_id], sensor_agents[sensor_id])


class TestBehaviorMetric:
    """Test the BehaviorMetric class of the metrics module."""

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
        time_since_observation.calculate(target_agents[target_id], sensor_agents[sensor_id])
