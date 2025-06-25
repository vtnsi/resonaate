from __future__ import annotations

# Standard Library Imports
from datetime import datetime

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.common.labels import StateLabel
from resonaate.scenario.config.state_config import (
    COEStateConfig,
    ECIStateConfig,
    EQEStateConfig,
    LLAStateConfig,
)


@pytest.fixture(name="test_utc")
def getTestUTC() -> datetime:
    """Date and time used across tests in this module."""
    return datetime(year=2019, month=5, day=22, hour=14)


@pytest.fixture(name="coe_cfg_dict")
def getCoeDict() -> dict:
    """Standard classical orbital element set."""
    return {
        "type": StateLabel.COE,
        "semi_major_axis": 6500.0,
        "eccentricity": 0.001,
        "inclination": 10.1,
        "argument_periapsis": 45.1,
        "right_ascension": 181.0,
        "true_anomaly": 5.5,
    }


@pytest.fixture(name="coe_tl_per_dict")
def getCoeTlPerDict(coe_cfg_dict: dict) -> dict:
    """Classical orbital element set with 'true_longitude_periapsis' element."""
    tl_per = coe_cfg_dict["argument_periapsis"] + coe_cfg_dict["right_ascension"]
    del coe_cfg_dict["argument_periapsis"]
    del coe_cfg_dict["right_ascension"]
    coe_cfg_dict["true_longitude_periapsis"] = tl_per
    return coe_cfg_dict


@pytest.fixture(name="coe_arg_lat_dict")
def getCoeArgLatDict(coe_cfg_dict: dict) -> dict:
    """Classical orbital element set with 'argument_latitude' element."""
    arg_lat = coe_cfg_dict["true_anomaly"] + coe_cfg_dict["argument_periapsis"]
    del coe_cfg_dict["true_anomaly"]
    del coe_cfg_dict["argument_periapsis"]
    coe_cfg_dict["argument_latitude"] = arg_lat
    return coe_cfg_dict


@pytest.fixture(name="coe_true_long_dict")
def getCoeTrueLongDict(coe_cfg_dict: dict) -> dict:
    """Classical orbital element set with 'true_longitude' element."""
    tl_per = coe_cfg_dict["argument_periapsis"] + coe_cfg_dict["right_ascension"]
    true_long = tl_per + coe_cfg_dict["true_anomaly"]
    del coe_cfg_dict["true_anomaly"]
    del coe_cfg_dict["argument_periapsis"]
    del coe_cfg_dict["right_ascension"]
    coe_cfg_dict["true_longitude"] = true_long
    return coe_cfg_dict


@pytest.fixture(name="eci_cfg_dict")
def getECIDict() -> dict:
    """Standard Earth Centered Inertial state config."""
    return {
        "type": StateLabel.ECI,
        "position": [3500.0, -6000.0, 200.0],
        "velocity": [-2.0, 4.3, 0.1],
    }

@pytest.fixture(name="lla_cfg_dict")
def getLLADict() -> dict:
    """Standard Latitude Longitude Altitude state config."""
    return {
        "type": StateLabel.LLA,
        "latitude": 53.1,
        "longitude": -60.0,
        "altitude": 101.0,
    }

@pytest.fixture(name="eqe_cfg_dict", params=[True, False])
def getEQEDict(request) -> dict:
    """Standard EQE state config."""
    return {
        "type": StateLabel.EQE,
        "semi_major_axis": 6500.0,
        "h": 0.1,
        "k": 0.5,
        "p": -0.25,
        "q": 0.25,
        "mean_longitude": 153.0,
        "retrograde": request.param,
    }


def testCOEStandard(coe_cfg_dict: dict, test_utc: datetime):
    """Test a standard COE config."""
    cfg = COEStateConfig(**coe_cfg_dict)
    assert cfg
    assert cfg.type == StateLabel.COE

    eci_state = cfg.toECI(test_utc)
    assert eci_state.shape == (6,)


def testCOETrueLongPer(coe_tl_per_dict: dict, test_utc: datetime):
    """Test a COE config with a 'true_longitude_periapsis' element."""
    cfg = COEStateConfig(**coe_tl_per_dict)
    assert cfg
    assert cfg.type == StateLabel.COE

    eci_state = cfg.toECI(test_utc)
    assert eci_state.shape == (6,)


def testCOEArgLat(coe_arg_lat_dict: dict, test_utc: datetime):
    """Test a COE config with a 'argument_latitude' element."""
    cfg = COEStateConfig(**coe_arg_lat_dict)
    assert cfg
    assert cfg.type == StateLabel.COE

    eci_state = cfg.toECI(test_utc)
    assert eci_state.shape == (6,)


def testCOETrueLong(coe_true_long_dict: dict, test_utc: datetime):
    """Test a COE config with a 'true_longitude' element."""
    cfg = COEStateConfig(**coe_true_long_dict)
    assert cfg
    assert cfg.type == StateLabel.COE

    eci_state = cfg.toECI(test_utc)
    assert eci_state.shape == (6,)


def testCOEBadCombo(coe_cfg_dict: dict):
    """Test a bad COE config with elements missing."""
    del coe_cfg_dict["true_anomaly"]
    del coe_cfg_dict["argument_periapsis"]
    del coe_cfg_dict["right_ascension"]
    with pytest.raises(ValidationError):
        _ = COEStateConfig(**coe_cfg_dict)


def testCOEBadSMA(coe_cfg_dict: dict):
    """Test a bad COE config with a 'semi_major_axis' inside the Earth."""
    coe_cfg_dict["semi_major_axis"] = 6000.0
    with pytest.raises(ValidationError):
        _ = COEStateConfig(**coe_cfg_dict)


def testECIGood(eci_cfg_dict: dict, test_utc: datetime):
    """Test a standard ECI config."""
    cfg = ECIStateConfig(**eci_cfg_dict)
    eci_state = cfg.toECI(test_utc)
    assert cfg
    assert cfg.type == StateLabel.ECI
    assert eci_state.shape == (6,)


def testECILowAlt(eci_cfg_dict: dict, test_utc: datetime):
    """Test an ECI config with an altitude inside the Earth."""
    eci_cfg_dict["position"] = [10.0, 10.0, 10.0]
    with pytest.raises(ValidationError):
        _ = ECIStateConfig(**eci_cfg_dict)


def testLLAGood(lla_cfg_dict: dict, test_utc: datetime):
    """Test a standard LLA config."""
    cfg = LLAStateConfig(**lla_cfg_dict)
    eci_state = cfg.toECI(test_utc)
    assert cfg
    assert cfg.type == StateLabel.LLA
    assert eci_state.shape == (6,)


def testEQEGood(eqe_cfg_dict: dict, test_utc: datetime):
    """Test a standard EQE config."""
    cfg = EQEStateConfig(**eqe_cfg_dict)
    eci_state = cfg.toECI(test_utc)
    assert cfg
    assert cfg.type == StateLabel.EQE
    assert eci_state.shape == (6,)


def testEQELowAlt(eqe_cfg_dict: dict):
    """Test an EQE config with an altitude inside the Earth."""
    eqe_cfg_dict["semi_major_axis"] = 6000.0
    with pytest.raises(ValidationError):
        _ = EQEStateConfig(**eqe_cfg_dict)
