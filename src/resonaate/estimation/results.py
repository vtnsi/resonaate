"""Module describing different result objects produced by various filters."""

from __future__ import annotations

# Standard Library Imports
from abc import ABC
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..physics.time.stardate import ScenarioTime


class FilterResult(ABC):  # noqa: B024
    """Abstract base class describing functionality common across all filter results."""

    @classmethod
    def fromFilter(cls, _filter):
        """Convenience method to collect relevant data from specified `filter`.

        Args:
            _filter: Filter object to collect data from.

        Returns:
            An instance of this :class:`.FilterResult`.
        """
        _dict = {}
        for field in fields(cls):
            _dict[field.name] = getattr(_filter, field.name)
        return cls(**_dict)

    def apply(self, _filter):
        """Apply the results contained in this :class:`.FilterResult` to the specified `filter`.

        Args:
            _filter: Filter object to apply this :class:`.FilterResult` to.
        """
        for field in fields(self):
            setattr(_filter, field.name, getattr(self, field.name))


@dataclass
class SeqFilterPredictResult(FilterResult):
    """Object encapsulating data from a 'predict' step of a sequential filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.SequentialFilter`.
    """

    time: Union[ScenarioTime, float]  # noqa: UP007
    """float | ScenarioTime: Current timestep of the simulation (:math:`k`)."""

    est_x: ndarray
    """State estimate (:math:`N\times 1`) before 'predict' step."""

    est_p: ndarray
    """State covariance (:math:`N\times N`) before 'predict' step."""

    pred_x: ndarray
    """Predicted state estimate (:math:`N\times 1`) after 'predict' step."""

    pred_p: ndarray
    """Predicted state covariance (:math:`N\times N`) after 'predict' step."""


@dataclass
class SeqFilterForecastResult(FilterResult):
    """Object encapsulating data from a 'forecast' step of a sequential filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.SequentialFilter`.
    """

    is_angular: ndarray
    """Integer array (:math:`M\times 1`) indicating measurement dimension bounds."""

    mean_pred_y: ndarray
    """:math:`M\times 1` predicted mean measurement vector."""

    r_matrix: ndarray
    """:math:`M\times M` measurement error covariance matrix."""

    cross_cvr: ndarray
    """:math:`N\times M` cross covariance matrix."""

    innov_cvr: ndarray
    """:math:`M\times M` innovation (aka measurement prediction) covariance matrix."""

    kalman_gain: ndarray  # TODO: should this be an attribute of the base result class?
    """:math:`N\times M` Kalman gain matrix."""

    est_p: ndarray
    """:math:`N\times N` estimated error covariance."""


@dataclass
class SeqFilterUpdateResult(SeqFilterForecastResult):
    """Object encapsulating data from an 'update' step of a sequential filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.SequentialFilter`.
    """

    est_x: ndarray
    """:math:`N\times 1` estimated (**posteriori**) state estimate at :math:`k+1`."""

    innovation: ndarray
    """:math:`M\times 1` innovation (aka measurement residual) vector."""

    nis: float
    """Normalized innovations squared values."""

    source: str  # TODO: this should probably reference an enum
    """Indication of whether observation(s) were used during an update."""

    maneuver_metric: Union[float, None]  # noqa: UP007
    """Result of the hypothesis testing function used to determine whether a maneuver occurred or not."""

    maneuver_detected: bool
    """Boolean indication of whether a maneuver occurred or not."""


@dataclass
class UKFPredictResult(SeqFilterPredictResult):
    """Object encapsulating data from a 'predict' step of an unscented Kalman filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.UnscentedKalmanFilter`.
    """

    sigma_points: ndarray
    """:math:`S` sigma point :math:`N\times 1` vectors combined into single matrix."""

    sigma_x_res: ndarray
    """:math:`N\times S` state sigma point residuals."""


@dataclass
class UKFForecastResult(SeqFilterForecastResult):
    """Object encapsulating data from a 'forecast' step of an unscented Kalman filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.UnscentedKalmanFilter`.
    """

    sigma_points: ndarray
    """:math:`S` sigma point :math:`N\times 1` vectors combined into single matrix."""

    sigma_y_res: ndarray
    """:math:`M\times S` measurement sigma point residuals."""


@dataclass
class UKFUpdateResult(SeqFilterUpdateResult, UKFForecastResult):
    """Object encapsulating data from an 'update' step of an unscented Kalman filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.UnscentedKalmanFilter`.
    """


@dataclass
class AdaptivePredictResult(SeqFilterPredictResult):
    """Object encapsulating data from a 'predict' step of an adaptive filter."""

    models: list
    """List of :class:`.SequentialFilter` instances describing the models after the 'predict' step."""

    model_weights: ndarray
    """Scalar weights associated with each model."""


@dataclass
class AdaptiveForecastResult(SeqFilterForecastResult):
    """Object encapsulating data from a 'forecast' step of an adaptive filter."""

    models: list
    """List of :class:`.SequentialFilter` instances describing the models after the 'forecast' step."""

    model_weights: ndarray
    """Scalar weights associated with each model."""


@dataclass
class AdaptiveUpdateResult(SeqFilterUpdateResult, AdaptiveForecastResult):
    """Object encapsulating data from an 'update' step of an adaptive filter."""

    true_y: ndarray
    """TODO: something to do with the measurement used during the 'update' step"""


# ------------------
# PARTICLE FILTER
# ------------------
@dataclass
class ParticleFilterPredictResult(FilterResult):
    """Object encapsulating data from a 'predict' step of a particle filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.SequentialFilter`.
    """

    time: Union[ScenarioTime, float]  # noqa: UP007
    """float | ScenarioTime: Current timestep of the simulation (:math:`k`)."""

    est_x: ndarray
    """State estimate (:math:`N\times 1`) before 'predict' step."""

    est_p: ndarray
    """State covariance (:math:`N\times N`) before 'predict' step."""

    pred_x: ndarray
    """Predicted state estimate (:math:`N\times 1`) after 'predict' step."""

    pred_p: ndarray
    """Predicted state covariance (:math:`N\times N`) after 'predict' step."""


@dataclass
class ParticleFilterForecastResult(FilterResult):
    """Object encapsulating data from a 'forecast' step of a sequential filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.SequentialFilter`.
    """

    num_particles: int
    """Number of particles used during forecasting"""


@dataclass
class ParticleFilterUpdateResult(ParticleFilterForecastResult):
    """Object encapsulating data from an 'update' step of a particle filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.ParticleFilter`.
    """

    est_x: ndarray
    """:math:`N\times 1` estimated (**posteriori**) state estimate at :math:`k+1`."""

    source: str  # TODO: this should probably reference an enum
    """Indication of whether observation(s) were used during an update."""

    maneuver_metric: Union[float, None]  # noqa: UP007
    """Result of the hypothesis testing function used to determine whether a maneuver occurred or not."""

    maneuver_detected: bool
    """Boolean indication of whether a maneuver occurred or not."""


@dataclass
class GPFPredictResult(ParticleFilterPredictResult):
    """Object encapsulating data from a 'predict' step of a genetic particle filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.GeneticParticleFilter`.
    """

    population: ndarray
    """:math:`S` sigma point :math:`N\times 1` vectors combined into single matrix."""

    particle_residuals: ndarray
    """:math:`M\times S` particle residuals."""


@dataclass
class GPFForecastResult(ParticleFilterForecastResult):
    """Object encapsulating data from a 'forecast' step of a genetic particle filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.GeneticParticleFilter`.
    """

    population: ndarray
    """:math:`S` sigma point :math:`N\times 1` vectors combined into single matrix."""

    particle_residuals: ndarray
    """:math:`M\times S` particle residuals."""


@dataclass
class GPFUpdateResult(ParticleFilterUpdateResult, GPFForecastResult):
    """Object encapsulating data from an 'update' step of a genetic particle filter.

    More detailed descriptions of attributes can be found in the primary docstring of
    :class:`.GeneticParticleFilter`.
    """
