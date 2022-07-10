# pylint: disable=attribute-defined-outside-init
# Standard Library Imports
# Third Party Imports
import pytest

try:
    # RESONAATE Imports
    from resonaate.tasking.metrics.behavior import TimeSinceObservation
    from resonaate.tasking.metrics.information import FisherInformation, ShannonInformation
    from resonaate.tasking.metrics.metric_base import Metric
    from resonaate.tasking.metrics.sensor import DeltaPosition, SlewCycle, TimeToTransit
    from resonaate.tasking.metrics.stability import LyapunovStability
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase


@pytest.fixture(name="mocked_metric_class")
def mockedMetricClass():
    """Return reference to a minimal :class:`.Metric` class."""

    class MockedMetric(Metric):
        def _calculateMetric(self, estimate_agent, sensor_agent, **kwargs):
            return 4

    return MockedMetric


class TestMetricsBase(BaseTestCase):
    """Test the base class of the metrics module."""

    def testRegistry(self, mocked_metric_class):
        """Test to make sure the Metric object is registered."""
        test_metric = mocked_metric_class()
        assert test_metric.is_registered is False

        # Register new class and check
        Metric.register("MockedMetric", mocked_metric_class)
        test_metric = mocked_metric_class()
        assert test_metric.is_registered is True

        # Ensure we cannot register objects that are not :class:`.Metric` sub-classes
        with pytest.raises(TypeError):
            Metric.register("MockedMetric", [2, 2])

    def testCreation(self):
        """Test creating a Metric Object."""
        with pytest.raises(TypeError):
            Metric()  # pylint: disable=abstract-class-instantiated

    def testMetricCall(self, mocked_estimate, mocked_metric_class, mocked_sensing_agent):
        """Test the call function of the Metric base class."""
        metric = mocked_metric_class()
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {"sensor": mocked_sensing_agent}
        sensor_id = "sensor"
        metric(target_agents[target_id], sensor_agents[sensor_id])


class TestInformationMetric(BaseTestCase):
    """Test the InformationMetric class of the metrics module."""

    def testCalculateMetric(self, mocked_estimate, mocked_sensing_agent):
        """Test the calculate metric function."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {1234: mocked_sensing_agent}
        sensor_id = 1234
        shannon_metric = ShannonInformation()
        shannon_metric(target_agents[target_id], sensor_agents[sensor_id])
        fisher_metric = FisherInformation()
        fisher_metric(target_agents[target_id], sensor_agents[sensor_id])


class TestStabilityMetric(BaseTestCase):
    """Test the StabilityMetric class of the metrics module."""

    def testCalculateMetric(self, mocked_estimate, mocked_sensing_agent):
        """Test the calculate metric function."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {1234: mocked_sensing_agent}
        sensor_id = 1234
        lyapunov_metric = LyapunovStability()
        lyapunov_metric(target_agents[target_id], sensor_agents[sensor_id])


class TestSensorMetric(BaseTestCase):
    """Test the SensorMetric class of the metrics module."""

    def testCalculateMetric(self, mocked_estimate, mocked_sensing_agent):
        """Test the calculate metric function."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {1234: mocked_sensing_agent}
        sensor_id = 1234
        delta_position = DeltaPosition()
        delta_position(target_agents[target_id], sensor_agents[sensor_id])
        slew_cycle = SlewCycle()
        slew_cycle(target_agents[target_id], sensor_agents[sensor_id])
        time_to_transit = TimeToTransit(norm_factor=10)
        time_to_transit(target_agents[target_id], sensor_agents[sensor_id])


class TestBehaviorMetric(BaseTestCase):
    """Test the BehaviorMetric class of the metrics module."""

    def testCalculateMetric(self, mocked_estimate, mocked_sensing_agent):
        """Test the calculate metric function."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {1234: mocked_sensing_agent}
        sensor_id = 1234
        time_since_observation = TimeSinceObservation()
        time_since_observation(target_agents[target_id], sensor_agents[sensor_id])
