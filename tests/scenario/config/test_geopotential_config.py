from __future__ import annotations

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.scenario.config.geopotential_config import GeopotentialConfig, GeopotentialModel


@pytest.fixture(name="test_model")
def getTestModel() -> GeopotentialModel:
    """Model used during testing."""
    return GeopotentialModel.EGM96


@pytest.fixture(name="test_degree")
def getTestDegree() -> int:
    """int: Model degree used during testing."""
    return 4


@pytest.fixture(name="test_order")
def getTestOrder() -> int:
    """int: Model order used during testing."""
    return 4


def testCreateGeopotentialConfig(test_model: GeopotentialModel, test_degree: int, test_order: int):
    """Test that GeopotentialConfig can be created from a dictionary."""
    cfg = GeopotentialConfig(model=test_model, degree=test_degree, order=test_order)
    assert cfg.model == test_model
    assert cfg.degree == test_degree
    assert cfg.order == test_order

    # Test that this can be created from an empty dictionary
    cfg = GeopotentialConfig()
    assert cfg is not None


def testBadModel():
    """Test bad input for :attr:`.GeopotentialConfig.model`."""
    with pytest.raises(ValidationError):
        GeopotentialConfig(
            model="bad",
        )


def testNegativeDegree():
    """Test negative input for :attr:`.GeopotentialConfig.degree`."""
    with pytest.raises(ValidationError):
        GeopotentialConfig(
            degree=-1,
        )


def testTooLargeDegree():
    """Test input that's too large for :attr:`.GeopotentialConfig.degree`."""
    with pytest.raises(ValidationError):
        GeopotentialConfig(
            degree=1000,
        )


def testNegativeOrder():
    """Test negative input for :attr:`.GeopotentialConfig.order`."""
    with pytest.raises(ValidationError):
        GeopotentialConfig(
            order=-1,
        )


def testTooLargeOrder():
    """Test input that's too large for :attr:`.GeopotentialConfig.order`."""
    with pytest.raises(ValidationError):
        GeopotentialConfig(
            order=1000,
        )
