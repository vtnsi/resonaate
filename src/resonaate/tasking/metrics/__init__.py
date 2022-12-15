"""Defines the metrics used to measure tasking performance."""
from __future__ import annotations

# Local Imports
from .information import FisherInformation, KLDivergence, ShannonInformation
from .metric_base import Metric
from .sensor import DeltaPosition, SlewCycle, TimeToTransit
from .stability import LyapunovStability
from .state import Range
from .target import TimeSinceObservation
from .uncertainty import (
    PositionCovarianceDeterminant,
    PositionCovarianceReduction,
    PositionCovarianceTrace,
    PositionMaxEigenValue,
    VelocityCovarianceDeterminant,
    VelocityCovarianceReduction,
    VelocityCovarianceTrace,
    VelocityMaxEigenValue,
)

# Register each metric class to global registry
# Information metrics
Metric.register(FisherInformation)
Metric.register(ShannonInformation)
Metric.register(KLDivergence)

# Uncertainty metrics
Metric.register(PositionCovarianceTrace)
Metric.register(VelocityCovarianceTrace)
Metric.register(PositionCovarianceDeterminant)
Metric.register(VelocityCovarianceDeterminant)
Metric.register(PositionMaxEigenValue)
Metric.register(VelocityMaxEigenValue)
Metric.register(PositionCovarianceReduction)
Metric.register(VelocityCovarianceReduction)

# State Metrics
Metric.register(Range)

# Sensor Metrics
Metric.register(DeltaPosition)
Metric.register(SlewCycle)
Metric.register(TimeToTransit)

# Target Metrics
Metric.register(TimeSinceObservation)

# Stability Metrics
Metric.register(LyapunovStability)

VALID_METRICS: list[str] = list(Metric.REGISTRY.keys())
"""list: List of valid metric labels."""
