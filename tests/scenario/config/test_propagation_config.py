from __future__ import annotations

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.common.labels import DynamicsLabel, IntegratorLabel
from resonaate.scenario.config.propagation_config import PropagationConfig


@pytest.mark.parametrize("prop_model", list(DynamicsLabel))
@pytest.mark.parametrize("integrate_method", list(IntegratorLabel))
def testPropagationConfigCreate(prop_model: DynamicsLabel, integrate_method: IntegratorLabel):
    """Validate that propagation configuration passes validation with all possible dynamics models and integrator methods."""
    assert PropagationConfig(
        propagation_model=prop_model,
        integration_method=integrate_method,
    )


@pytest.mark.parametrize("prop_input", ["not a prop", 123])
def testPropagationConfigBadProp(prop_input):
    """Validate that propagation validation throws an error if the propagation model is invalid."""
    with pytest.raises(ValidationError):
        _ = PropagationConfig(propagation_model=prop_input)


@pytest.mark.parametrize("integrate_input", ["not a method", 123])
def testPropagationConfigBadIntegrator(integrate_input):
    """Validate that propagation validation throws an error if the integrator method is invalid."""
    with pytest.raises(ValidationError):
        _ = PropagationConfig(integration_method=integrate_input)
