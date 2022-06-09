"""Defines the metrics used to measure tasking performance."""
# Local Imports
from .behavior import TimeSinceObservation
from .information import FisherInformation, KLDivergence, ShannonInformation
from .metric_base import Metric as _BaseMetric
from .sensor import DeltaPosition, SlewCycle, TimeToTransit
from .stability import LyapunovStability

# Register each metric class to global registry
_BaseMetric.register("TimeSinceObservation", TimeSinceObservation)
_BaseMetric.register("FisherInformation", FisherInformation)
_BaseMetric.register("ShannonInformation", ShannonInformation)
_BaseMetric.register("DeltaPosition", DeltaPosition)
_BaseMetric.register("SlewCycle", SlewCycle)
_BaseMetric.register("TimeToTransit", TimeToTransit)
_BaseMetric.register("LyapunovStability", LyapunovStability)
_BaseMetric.register("KLDivergence", KLDivergence)

VALID_METRICS = list(_BaseMetric.REGISTRY.keys())
"""list: List of valid metric labels."""
