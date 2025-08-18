"""Define implemented prediction functions used to determine sensor task opportunities."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING
from warnings import warn

if TYPE_CHECKING:
    # Local Imports
    from ..agents.estimate_agent import EstimateAgent
    from ..agents.sensing_agent import SensingAgent
    from ..data.observation import Observation


def predictObservation(
    sensing_agent: SensingAgent,
    estimate_agent: EstimateAgent,
) -> Observation | None:
    """Forecasting an observation for reward matrix purposes.

    .. warning::
        This function is deprecated and will be removed in a future version.
        Use `SensingAgent.sensor.predictObservation()` instead.

    Args:
        sensing_agent (SensingAgent): agent performing predicted observation
        estimate_agent (EstimateAgent): agent being observed

    Returns:
        :class:`.Observation` | None : constructed observation if observable
    """
    warn(
        "old_function is deprecated and will be removed in a future version. "
        "Use `SensingAgent.sensor.predictObservation()` instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return sensing_agent.sensor.predictObservation(estimate_agent)
