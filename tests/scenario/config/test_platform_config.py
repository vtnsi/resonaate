from __future__ import annotations

# Standard Library Imports
from typing import Optional

# Third Party Imports
import pytest
from pydantic import BaseModel, ValidationError

# RESONAATE Imports
from resonaate.common.labels import PlatformLabel
from resonaate.scenario.config.platform_config import (
    GroundFacilityConfig,
    PlatformConfig,
    SpacecraftConfig,
    StationKeepingConfig,
)


def testStationKeepingConfigDefault():
    """Test an empty station keeping configuration."""
    cfg = StationKeepingConfig()
    assert cfg.routines is not None


def testStationKeepingConfigValid():
    """Test station keeping config with valid keywords."""
    cfg = StationKeepingConfig(routines=["LEO", "GEO EW", "GEO NS"])
    assert cfg.routines == ["LEO", "GEO EW", "GEO NS"]


def testStationKeepingConfigInvalid():
    """Test station keeping config with invalid keyword."""
    with pytest.raises(ValidationError):
        _ = StationKeepingConfig(routines=["INVALID"])


class PlatformWrapper(BaseModel):
    """Test model to make sure different types of platform configurations are parsed correctly."""

    platform_config: PlatformConfig
    """Wrapped platform configuration."""


@pytest.mark.parametrize("platform_type", PlatformLabel)
@pytest.mark.parametrize("mass", [None, 5000.0])
@pytest.mark.parametrize("vcs", [None, 5.0])
@pytest.mark.parametrize("refl", [None, 0.1])
def testPlatformConfigValid(
    platform_type: str,
    mass: Optional[float],  # noqa: UP007
    vcs: Optional[float],  # noqa: UP007
    refl: Optional[float],  # noqa: UP007
):
    """Test valid platform configurations."""
    cfg = PlatformWrapper(
        platform_config={
            "type": platform_type,
            "mass": mass,
            "visual_cross_section": vcs,
            "reflectivity": refl,
        },
    )
    if platform_type == PlatformLabel.SPACECRAFT:
        assert isinstance(cfg.platform_config, SpacecraftConfig)
    elif platform_type == PlatformLabel.GROUND_FACILITY:
        assert isinstance(cfg.platform_config, GroundFacilityConfig)


@pytest.mark.parametrize("platform_type", ["invalid", None, 10])
def testCreationBadType(platform_type: str):
    """Test creating platform config with bad params."""
    with pytest.raises(ValidationError):
        _ = PlatformWrapper(
            platform_config={
                "type": platform_type,
            },
        )
