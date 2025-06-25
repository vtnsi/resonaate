"""Defines dynamics of agents that can be used in RESONAATE simulations."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ..common.labels import DynamicsLabel
from ..physics.transforms.methods import eci2ecef
from .special_perturbations import SpecialPerturbations, calcSatRatio
from .terrestrial import Terrestrial
from .two_body import TwoBody

if TYPE_CHECKING:
    # Local Imports
    from ..scenario.clock import ScenarioClock
    from ..scenario.config.agent_config import AgentConfig
    from ..scenario.config.geopotential_config import GeopotentialConfig
    from ..scenario.config.perturbations_config import PerturbationsConfig
    from ..scenario.config.propagation_config import PropagationConfig
    from .dynamics_base import Dynamics


def dynamicsFactory(
    agent_cfg: AgentConfig,
    prop_cfg: PropagationConfig,
    geo_cfg: GeopotentialConfig,
    pert_cfg: PerturbationsConfig,
    clock: ScenarioClock,
) -> Dynamics:
    """Build a :class:`.Dynamics` object for propagation.

    Args:
        agent_cfg (:class:`.AgentConfig`): describes config options for an agent
        prop_cfg (:class:`.PropagationConfig`): describes the propagation config options
        geo_cfg (:class:`.GeopotentialConfig`): describes the Earth's geopotential model
        pert_cfg (:class:`.PerturbationsConfig`): describes the dynamics' perturbational accelerations
        clock (:class:`.ScenarioClock`): clock for tracking time

    Raises:
        ValueError: raised if given an invalid "model" argument
        TypeError: raised if given an invalid platform type

    Returns:
        :class:`.Dynamics`: constructed dynamics object
    """
    # Local Imports
    from ..scenario.config.platform_config import GroundFacilityConfig, SpacecraftConfig

    if isinstance(agent_cfg.platform, SpacecraftConfig):
        sat_ratio = calcSatRatio(
            agent_cfg.platform.visual_cross_section,
            agent_cfg.platform.mass,
            agent_cfg.platform.reflectivity,
        )
        if prop_cfg.propagation_model.lower() == DynamicsLabel.TWO_BODY:
            dynamics = TwoBody(method=prop_cfg.integration_method)
        elif prop_cfg.propagation_model.lower() == DynamicsLabel.SPECIAL_PERTURBATIONS:
            dynamics = SpecialPerturbations(
                clock.julian_date_start,
                geo_cfg,
                pert_cfg,
                sat_ratio,
                method=prop_cfg.integration_method,
            )
        else:
            raise ValueError(prop_cfg.propagation_model)

    elif isinstance(agent_cfg.platform, GroundFacilityConfig):
        dynamics = Terrestrial(
            clock.julian_date_start,
            eci2ecef(agent_cfg.state.toECI(clock.datetime_start), clock.datetime_start),
        )

    else:
        raise TypeError(f"Invalid PlatformConfig type: {agent_cfg.platform.type}")

    return dynamics
