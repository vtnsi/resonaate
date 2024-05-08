"""Functions to support stacking MMAE models in various coordinate systems."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ...common.labels import StackingLabel

if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..sequential.sequential_filter import SequentialFilter


def eciStack(models: list[SequentialFilter], model_weights: ndarray) -> tuple[ndarray, ndarray]:
    """Stack ECI states.

    Args:
        models (``list``): :class:`.SequentialFilter` models to be stacked
        model_weights (``ndarray``): weights of each model

    Returns:
        ``ndarray``: 6x1 ECI predicted state vector, (km; km/sec)
        ``ndarray``: 6x1 ECI estimated state vector, (km; km/sec)
    """
    pred_x = 0
    est_x = 0
    for model, weight in zip(models, model_weights):
        pred_x += model.pred_x * weight
        est_x += model.est_x * weight
    return pred_x, est_x


VALID_STACKING_LABELS = (StackingLabel.ECI_STACKING,)
"""``tuple``: Collection of valid entries for "stacking_method" key in adaptive estimation configuration dictionary."""


def stackingFactory(
    method: str,
) -> Callable[[list[SequentialFilter], ndarray], tuple[ndarray, ndarray]]:
    """MMAE model stacking factory method.

    Args:
        method (``str``): the function used to generate the stacking

    Returns:
        ``callable``: Coordinate system specific stacking function for `.AdaptiveEstimation` init
    """
    if method == StackingLabel.ECI_STACKING:
        return eciStack

    raise ValueError(method)
