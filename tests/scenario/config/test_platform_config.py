# pylint: disable=attribute-defined-outside-init, unused-argument
from __future__ import annotations

# Standard Library Imports
from unittest.mock import MagicMock, create_autospec, patch

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.labels import PlatformLabel, StateLabel
from resonaate.scenario.config.base import ConfigError, ConfigValueError
from resonaate.scenario.config.platform_config import (
    GroundFacilityConfig,
    PlatformConfig,
    SpacecraftConfig,
    StationKeepingConfig,
)
from resonaate.scenario.config.state_config import StateConfig


def testStationKeepingConfig():
    """Test station keeping config."""
    cfg = StationKeepingConfig(routines=["LEO", "GEO EW", "GEO NS"])
    assert cfg.CONFIG_LABEL == "station_keeping"
    assert cfg.routines == ["LEO", "GEO EW", "GEO NS"]

    assert cfg.toJSON() == {"routines": ["LEO", "GEO EW", "GEO NS"]}

    cfg = StationKeepingConfig()
    assert cfg.routines is not None
    assert not cfg.routines

    with pytest.raises(ConfigValueError):
        _ = StationKeepingConfig(routines=["INVALID"])


@patch.multiple(PlatformConfig, __abstractmethods__=set())
class TestPlatformConfig:
    """Test abstract PlatformConfig object."""

    # pylint: disable=abstract-class-instantiated

    @pytest.mark.parametrize("platform_type", PlatformConfig.VALID_LABELS)
    @pytest.mark.parametrize("mass", [None, 5000.0])
    @pytest.mark.parametrize("vcs", [None, 5.0])
    @pytest.mark.parametrize("refl", [None, 0.1])
    def testCreation(
        self,
        monkeypatch: pytest.MonkeyPatch,
        platform_type: str,
        mass: float,
        vcs: float,
        refl: float,
    ):
        """Test creating platform config."""
        mock_state = MagicMock()
        mock_state.type = StateLabel.ECI
        mock_state.position = [7000.0, 0.0, 0.0]

        with monkeypatch.context() as m_patch:
            m_patch.setattr(PlatformConfig, "valid_states", [StateLabel.ECI])
            _ = PlatformConfig(
                type=platform_type,
                mass=mass,
                reflectivity=refl,
                visual_cross_section=vcs,
                state=mock_state,
            )

        cfg_dict = {
            "type": platform_type,
            "mass": mass,
            "reflectivity": refl,
            "visual_cross_section": vcs,
        }
        with monkeypatch.context() as m_patch:
            m_patch.setattr(PlatformConfig, "valid_states", [StateLabel.ECI])
            _ = PlatformConfig.fromDict(cfg_dict, state=mock_state)

    @pytest.mark.parametrize("platform_type", ["invalid", None, 10])
    def testCreationBadType(self, platform_type: str):
        """Test creating platform config with bad params."""
        with pytest.raises(ConfigValueError):
            _ = PlatformConfig(
                type=platform_type,
                state=None,
            )

        with pytest.raises(ConfigValueError):
            _ = PlatformConfig.fromDict(
                {"type": platform_type},
                state=None,
            )

    def testCreationMismatchStateType(self, monkeypatch: pytest.MonkeyPatch):
        """Test a mismatch of the StateConfig.type and PlatformConfig.valid_states."""
        mock_state = MagicMock()
        mock_state.type = StateLabel.LLA
        with monkeypatch.context() as m_patch:
            m_patch.setattr(PlatformConfig, "valid_states", [StateLabel.ECI])
            with pytest.raises(ConfigValueError):
                _ = PlatformConfig(type=PlatformLabel.SPACECRAFT, state=mock_state)


class TestSpacecraftConfig:
    """Test spacecraft platform type."""

    @pytest.mark.parametrize("state_type", [StateLabel.ECI, StateLabel.EQE, StateLabel.COE])
    @pytest.mark.parametrize("altitude", [7000.0, 20000.0, 45000.0])
    def testCreation(self, state_type: str, altitude: float):
        """Test creating spacecraft config."""
        # Mock the state config object
        mock_state = create_autospec(StateConfig)
        mock_state.type = state_type
        mock_state.position = [altitude, 0.0, 0.0]
        mock_state.semi_major_axis = altitude

        _ = SpacecraftConfig(
            type=PlatformLabel.SPACECRAFT,
            state=mock_state,
        )

        _ = SpacecraftConfig.fromDict(
            {"type": PlatformLabel.SPACECRAFT, "station_keeping": {"routines": []}},
            state=mock_state,
        )

    @pytest.mark.parametrize("altitude", [60000.0, 10.0, 6400.0])
    def testCreationBadAltitude(self, altitude: float):
        """Test creating spacecraft config."""
        # Mock the state config object
        mock_state = create_autospec(StateConfig)
        mock_state.type = StateLabel.ECI
        mock_state.position = [altitude, 0.0, 0.0]
        mock_state.semi_major_axis = altitude

        with pytest.raises(ConfigError):
            _ = SpacecraftConfig(
                type=PlatformLabel.SPACECRAFT,
                state=mock_state,
            )

    def testValidStates(self):
        """Test valid states property."""
        mock_state = MagicMock()
        mock_state.type = StateLabel.ECI
        mock_state.position = [7000.0, 0.0, 0.0]
        cfg = SpacecraftConfig(
            type=PlatformLabel.SPACECRAFT,
            state=mock_state,
        )
        assert cfg.valid_states == [StateLabel.ECI, StateLabel.COE, StateLabel.EQE]


class TestGroundFacilityConfig:
    """Test ground facility platform type."""

    @pytest.mark.parametrize("state_type", [StateLabel.ECI, StateLabel.LLA])
    def testCreation(self, state_type: str):
        """Test creating ground facility config."""
        mock_state = create_autospec(StateConfig)
        mock_state.type = state_type
        _ = GroundFacilityConfig(
            type=PlatformLabel.GROUND_FACILITY,
            state=mock_state,
        )

        _ = GroundFacilityConfig.fromDict(
            {"type": PlatformLabel.GROUND_FACILITY}, state=mock_state
        )

    def testValidStates(self):
        """Test valid states property."""
        mock_state = MagicMock()
        mock_state.type = StateLabel.ECI
        cfg = GroundFacilityConfig(
            type=PlatformLabel.GROUND_FACILITY,
            state=mock_state,
        )
        assert cfg.valid_states == [StateLabel.ECI, StateLabel.LLA]
