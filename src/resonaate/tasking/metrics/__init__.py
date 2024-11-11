"""Defines the metrics used to measure tasking performance."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ...common.labels import MetricLabel
from .information import FisherInformation, KLDivergence, ShannonInformation
from .sensor import (
    SlewDistanceMaximization,
    SlewDistanceMinimization,
    SlewTimeMaximization,
    SlewTimeMinimization,
)
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

if TYPE_CHECKING:
    # Local Imports
    from .metric_base import Metric


_METRIC_MAPPING: dict[MetricLabel, Metric] = {
    MetricLabel.FISHER_INFO: FisherInformation,
    MetricLabel.SHANNON_INFO: ShannonInformation,
    MetricLabel.KL_DIVERGENCE: KLDivergence,
    MetricLabel.POS_COV_TRACE: PositionCovarianceTrace,
    MetricLabel.VEL_COV_TRACE: VelocityCovarianceTrace,
    MetricLabel.POS_COV_DET: PositionCovarianceDeterminant,
    MetricLabel.VEL_COV_DET: VelocityCovarianceDeterminant,
    MetricLabel.POS_MAX_EIGEN: PositionMaxEigenValue,
    MetricLabel.VEL_MAX_EIGEN: VelocityMaxEigenValue,
    MetricLabel.POS_COV_REDUC: PositionCovarianceReduction,
    MetricLabel.VEL_COV_REDUC: VelocityCovarianceReduction,
    MetricLabel.RANGE: Range,
    MetricLabel.SLEW_DIST_MIN: SlewDistanceMinimization,
    MetricLabel.SLEW_DIST_MAX: SlewDistanceMaximization,
    MetricLabel.SLEW_TIME_MIN: SlewTimeMinimization,
    MetricLabel.SLEW_TIME_MAX: SlewTimeMaximization,
    MetricLabel.TIME_SINCE_OBS: TimeSinceObservation,
    MetricLabel.LYAPUNOV_STABILITY: LyapunovStability,
}
"""dict[MetricLabel, Metric]: Maps enumerated metric label to corresponding class.

Used in :meth:`.resonaate.tasking.rewards.rewardsFactory()` but lives here to simplify imports.
"""
