"""Submodule defining the 'propagation' configuration section."""

from __future__ import annotations

# Third Party Imports
from pydantic import BaseModel

# Local Imports
from ...common.labels import DynamicsLabel, IntegratorLabel


class PropagationConfig(BaseModel):
    """Configuration section defining several propagation-based options."""

    propagation_model: DynamicsLabel = DynamicsLabel.SPECIAL_PERTURBATIONS
    """``str``: model with which to propagate RSOs."""

    integration_method: IntegratorLabel = IntegratorLabel.RK45
    """``str``: method with which to numerically integrate RSOs."""

    station_keeping: bool = False
    """``bool``: whether to use the station keeping for the truth model.

    Note:
        This turns station-keeping on or off, globally. So this must be ``True`` for agents with
        a :attr:`~.TargetAgent.station_keeping` to use the routines.
    """

    target_realtime_propagation: bool = True
    """``bool``: whether to use the internal propagation for the truth model."""

    sensor_realtime_propagation: bool = True
    """``bool``: whether to use the internal propagation for the truth model."""

    truth_simulation_only: bool = False
    """``bool``: whether to skip estimation and tasking during the simulation."""
