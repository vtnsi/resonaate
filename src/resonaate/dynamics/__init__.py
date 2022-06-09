"""Defines dynamics of agents that can be used in RESONAATE simulations."""
# Standard Imports
# Third Party Imports
# RESONAATE Imports
from .special_perturbations import SpecialPerturbations
from .two_body import TwoBody
from .constants import TWO_BODY_LABEL, SPECIAL_PERTURBATIONS_LABEL, RK45_LABEL


def spacecraftDynamicsFactory(model, clock, geopotential, perturbations, method=RK45_LABEL):
    """Build a :class:`.Dynamics` object for RSO propagation.

    Args:
        model (``str``): the dynamics propagation method/class
        clock (:class:`.ScenarioClock`): clock for tracking time
        geopotential (GeopotentialConfig): describes the Earth's geopotential model
        perturbations (PerturbationsConfig): describes the dynamics' perturbational accelerations
        method (``str``, optional): Defaults to ``'RK45'``. Which ODE integration method to use

    Note:
        Valid options for "model" argument:
            - "two_body": :class:`.TwoBody`
            - "special_perturbations": :class:`.SpecialPerturbations`

    Raises:
        ValueError: raised if given an invalid "model" argument

    Returns:
        :class:`.Dynamics`: constructed dynamics object
    """
    # Determine appropriate Dynamics
    if model.lower() == TWO_BODY_LABEL:
        dynamics = TwoBody(method=method)
    elif model.lower() == SPECIAL_PERTURBATIONS_LABEL:
        dynamics = SpecialPerturbations(
            clock.julian_date_start, geopotential, perturbations, method=method
        )
    else:
        raise ValueError(model)

    return dynamics
