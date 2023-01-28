# pylint: disable=attribute-defined-outside-init, unused-argument
from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from datetime import datetime
from unittest.mock import patch

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.labels import COE_LABEL, ECI_LABEL, EQE_LABEL, LLA_LABEL
from resonaate.scenario.config.base import ConfigError, ConfigValueError
from resonaate.scenario.config.state_config import (
    COEStateConfig,
    ECIStateConfig,
    EQEStateConfig,
    LLAStateConfig,
    StateConfig,
)


@patch.multiple(StateConfig, __abstractmethods__=set())
class TestStateConfig:
    """Test abstract StateConfig object."""

    # pylint: disable=abstract-class-instantiated

    @pytest.mark.parametrize("state_type", StateConfig.VALID_LABELS)
    def testCreation(self, state_type: str):
        """Test creating state config."""
        _ = StateConfig(type=state_type)

    @pytest.mark.parametrize("state_type", ["invalid", None, 10])
    def testCreationBadType(self, state_type: str):
        """Test creating state config with bad params."""
        with pytest.raises(ConfigValueError):
            _ = StateConfig(
                type=state_type,
            )

        with pytest.raises(ConfigValueError):
            _ = StateConfig.fromDict(
                {"type": state_type},
            )


# @pytest.mark.parametrize("retro", [False, True])
def testCOE():
    """Test COE state config."""
    utc = datetime(year=2019, month=5, day=22, hour=14)
    coe_cfg_dict = {
        "type": COE_LABEL,
        "semi_major_axis": 6500.0,
        "eccentricity": 0.001,
        "inclination": 10.1,
        "argument_periapsis": 45.1,
        "right_ascension": 181.0,
        "true_anomaly": 5.5,
    }

    tl_per = coe_cfg_dict["argument_periapsis"] + coe_cfg_dict["right_ascension"]
    true_long = tl_per + coe_cfg_dict["true_anomaly"]
    arg_lat = coe_cfg_dict["true_anomaly"] + coe_cfg_dict["argument_periapsis"]

    cfg = COEStateConfig(**coe_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == COE_LABEL
    assert eci_state.shape == (6,)

    cfg = COEStateConfig.fromDict(coe_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == COE_LABEL
    assert eci_state.shape == (6,)

    new_cfg_dict = deepcopy(coe_cfg_dict)
    del new_cfg_dict["argument_periapsis"]
    del new_cfg_dict["right_ascension"]
    new_cfg_dict["true_longitude_periapsis"] = tl_per

    cfg = COEStateConfig(**new_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == COE_LABEL
    assert eci_state.shape == (6,)

    cfg = COEStateConfig.fromDict(new_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == COE_LABEL
    assert eci_state.shape == (6,)

    new_cfg_dict = deepcopy(coe_cfg_dict)
    del new_cfg_dict["true_anomaly"]
    del new_cfg_dict["argument_periapsis"]
    new_cfg_dict["argument_latitude"] = arg_lat

    cfg = COEStateConfig(**new_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == COE_LABEL
    assert eci_state.shape == (6,)

    cfg = COEStateConfig.fromDict(new_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == COE_LABEL
    assert eci_state.shape == (6,)

    new_cfg_dict = deepcopy(coe_cfg_dict)
    del new_cfg_dict["true_anomaly"]
    del new_cfg_dict["argument_periapsis"]
    del new_cfg_dict["right_ascension"]
    new_cfg_dict["true_longitude"] = true_long

    cfg = COEStateConfig(**new_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == COE_LABEL
    assert eci_state.shape == (6,)

    cfg = COEStateConfig.fromDict(new_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == COE_LABEL
    assert eci_state.shape == (6,)

    # Check bad combo
    new_cfg_dict = deepcopy(coe_cfg_dict)
    del new_cfg_dict["true_anomaly"]
    del new_cfg_dict["argument_periapsis"]
    del new_cfg_dict["right_ascension"]
    with pytest.raises(ConfigError):
        cfg = COEStateConfig(**new_cfg_dict)
    with pytest.raises(ConfigError):
        cfg = COEStateConfig.fromDict(new_cfg_dict)

    new_cfg_dict = deepcopy(coe_cfg_dict)
    new_cfg_dict["semi_major_axis"] = 6000.0
    with pytest.raises(ConfigError):
        _ = COEStateConfig(**new_cfg_dict)
    with pytest.raises(ConfigError):
        _ = COEStateConfig.fromDict(new_cfg_dict)


def testECI():
    """Test ECI state config."""
    utc = datetime(year=2019, month=5, day=22, hour=14)
    eci_cfg_dict = {
        "type": ECI_LABEL,
        "position": [3500.0, -6000.0, 200.0],
        "velocity": [-2.0, 4.3, 0.1],
    }

    cfg = ECIStateConfig(**eci_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == ECI_LABEL
    assert eci_state.shape == (6,)

    cfg = ECIStateConfig.fromDict(eci_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == ECI_LABEL
    assert eci_state.shape == (6,)

    new_cfg_dict = deepcopy(eci_cfg_dict)
    new_cfg_dict["position"] = [10.0, 10.0, 10.0]
    with pytest.raises(ConfigError):
        _ = ECIStateConfig(**new_cfg_dict)
    with pytest.raises(ConfigError):
        _ = ECIStateConfig.fromDict(new_cfg_dict)


def testLLA():
    """Test LLA state config."""
    utc = datetime(year=2019, month=5, day=22, hour=14)
    lla_cfg_dict = {
        "type": LLA_LABEL,
        "latitude": 53.1,
        "longitude": -60.0,
        "altitude": 101.0,
    }

    cfg = LLAStateConfig(**lla_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == LLA_LABEL
    assert eci_state.shape == (6,)

    cfg = LLAStateConfig.fromDict(lla_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == LLA_LABEL
    assert eci_state.shape == (6,)


@pytest.mark.parametrize("retro", [False, True])
def testEQE(retro: bool):
    """Test EQE state config."""
    utc = datetime(year=2019, month=5, day=22, hour=14)
    eqe_cfg_dict = {
        "type": EQE_LABEL,
        "semi_major_axis": 6500.0,
        "h": 0.1,
        "k": 0.5,
        "p": -0.25,
        "q": 0.25,
        "mean_longitude": 153.0,
        "retrograde": retro,
    }

    cfg = EQEStateConfig(**eqe_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == EQE_LABEL
    assert eci_state.shape == (6,)

    cfg = EQEStateConfig.fromDict(eqe_cfg_dict)
    eci_state = cfg.toECI(utc)
    assert cfg
    assert cfg.type == EQE_LABEL
    assert eci_state.shape == (6,)

    new_cfg_dict = deepcopy(eqe_cfg_dict)
    new_cfg_dict["semi_major_axis"] = 6000.0
    with pytest.raises(ConfigError):
        _ = EQEStateConfig(**new_cfg_dict)
    with pytest.raises(ConfigError):
        _ = EQEStateConfig.fromDict(new_cfg_dict)
