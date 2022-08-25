"""Defines the metrics used to measure tasking performance."""
from __future__ import annotations

# Local Imports
from .behavior import TimeSinceObservation
from .information import FisherInformation, KLDivergence, ShannonInformation
from .metric_base import Metric
from .sensor import DeltaPosition, SlewCycle, TimeToTransit
from .stability import LyapunovStability

# Register each metric class to global registry
Metric.register(TimeSinceObservation)
Metric.register(FisherInformation)
Metric.register(ShannonInformation)
Metric.register(DeltaPosition)
Metric.register(SlewCycle)
Metric.register(TimeToTransit)
Metric.register(LyapunovStability)
Metric.register(KLDivergence)


VALID_METRICS: list[str] = list(Metric.REGISTRY.keys())
"""list: List of valid metric labels."""
