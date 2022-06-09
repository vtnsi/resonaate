# RESONAATE Imports
from .metric_base import Metric as _BaseMetric
from .information import FisherInformation, ShannonInformation, KLDivergence
from .stability import LyapunovStability
from .sensor import TimeToTransit, DeltaPosition, SlewCycle
from .behavior import TimeSinceObservation


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
