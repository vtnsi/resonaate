"""Define implemented prediction functions used to determine sensor task opportunities."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ..common.utilities import getTypeString
from ..data.observation import Observation
from ..physics.transforms.methods import getSlantRangeVector

if TYPE_CHECKING:
    # Local Imports
    from ..agents.estimate_agent import EstimateAgent
    from ..agents.sensing_agent import SensingAgent


def predictObservation(
    sensing_agent: SensingAgent,
    estimate_agent: EstimateAgent,
) -> Observation | None:
    """Forecasting an observation for reward matrix purposes.

    Args:
        sensing_agent (SensingAgent): agent performing predicted observation
        estimate_agent (EstimateAgent): agent being observed

    Returns:
        :class:`.Observation` | None : constructed observation if observable
    """
    slant_range_sez = getSlantRangeVector(
        sensing_agent.eci_state,
        estimate_agent.eci_state,
        sensing_agent.datetime_epoch,
    )

    # Check if the estimated target is reachable
    if not sensing_agent.sensors.canSlew(slant_range_sez):
        return None

    # Check if the estimated target is observable
    visibility, _ = sensing_agent.sensors.isVisible(
        estimate_agent.eci_state,
        estimate_agent.visual_cross_section,
        estimate_agent.reflectivity,
        slant_range_sez,
    )
    if not visibility:
        return None

    return Observation.fromMeasurement(
        epoch_jd=sensing_agent.julian_date_epoch,
        target_id=estimate_agent.simulation_id,
        tgt_eci_state=estimate_agent.eci_state,
        sensor_id=sensing_agent.simulation_id,
        sensor_eci=sensing_agent.eci_state,
        sensor_type=getTypeString(sensing_agent.sensors),
        measurement=sensing_agent.sensors.measurement,
        noisy=False,  # Don't add noise for prospective observations
    )
