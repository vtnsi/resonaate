"""Defines the metrics used to measure tasking performance."""
from __future__ import annotations

# Local Imports
from .behavior import TimeSinceObservation
from .information import FisherInformation, KLDivergence, ShannonInformation
from .metric_base import Metric
from .sensor import DeltaPosition, SlewCycle, TimeToTransit
from .stability import LyapunovStability

# Register each metric class to global registry
Metric.register("TimeSinceObservation", TimeSinceObservation)
Metric.register("FisherInformation", FisherInformation)
Metric.register("ShannonInformation", ShannonInformation)
Metric.register("DeltaPosition", DeltaPosition)
Metric.register("SlewCycle", SlewCycle)
Metric.register("TimeToTransit", TimeToTransit)
Metric.register("LyapunovStability", LyapunovStability)
Metric.register("KLDivergence", KLDivergence)


VALID_METRICS: list[str] = list(Metric.REGISTRY.keys())
"""list: List of valid metric labels."""
