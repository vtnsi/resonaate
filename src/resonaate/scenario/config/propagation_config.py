"""Submodule defining the 'propagation' configuration section."""

from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import ClassVar

# Local Imports
from ...common.labels import DynamicsLabel, IntegratorLabel
from .base import ConfigObject, ConfigValueError

VALID_PROPAGATION_METHODS: tuple[str] = (
    DynamicsLabel.SPECIAL_PERTURBATIONS,
    DynamicsLabel.TWO_BODY,
)
"""``tuple``: Valid propagation methods."""

VALID_INTEGRATION_METHODS: tuple[str] = (
    IntegratorLabel.RK45,
    IntegratorLabel.DOP853,
)
"""``tuple``: Valid integration methods."""


@dataclass
class PropagationConfig(ConfigObject):
    """Configuration section defining several propagation-based options."""

    CONFIG_LABEL: ClassVar[str] = "propagation"
    """``str``: Key where settings are stored in the configuration dictionary."""

    propagation_model: str = DynamicsLabel.SPECIAL_PERTURBATIONS
    """``str``: model with which to propagate RSOs."""

    integration_method: str = IntegratorLabel.RK45
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

    def __post_init__(self):
        """Runs after the object is initialized."""
        if self.propagation_model not in VALID_PROPAGATION_METHODS:
            raise ConfigValueError(
                "propagation_model", self.propagation_model, VALID_PROPAGATION_METHODS
            )

        if self.integration_method not in VALID_INTEGRATION_METHODS:
            raise ConfigValueError(
                "integration_method", self.integration_method, VALID_INTEGRATION_METHODS
            )
