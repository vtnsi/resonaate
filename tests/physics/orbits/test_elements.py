from __future__ import annotations

# Third Party Imports
import pytest
from numpy import cos, deg2rad, sin, tan
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.common.labels import StateLabel
from resonaate.physics.orbits import EccentricityError, InclinationError, isEccentric, isInclined
from resonaate.physics.orbits.elements import ClassicalElements, EquinoctialElements
from resonaate.physics.orbits.utils import getEccentricityFromEQE, getInclinationFromEQE
from resonaate.scenario.config import constructFromUnion
from resonaate.scenario.config.state_config import StateConfig

# Local Imports
from . import ANOM, ARGP, ECC, INC, LEO, RAAN, SMA, H, K, P, Q

COE_CONFIGS: list[dict[str, float]] = [
    {
        "semi_major_axis": LEO,
        "eccentricity": ECC[3],
        "inclination": INC[2],
        "right_ascension": RAAN[3],
        "argument_periapsis": ARGP[3],
        "true_anomaly": ANOM[3],
    },
    {
        "semi_major_axis": LEO,
        "eccentricity": ECC[3],
        "inclination": INC[0],
        "true_longitude_periapsis": ARGP[3],
        "true_anomaly": ANOM[3],
    },
    {
        "semi_major_axis": LEO,
        "eccentricity": ECC[0],
        "inclination": INC[2],
        "right_ascension": RAAN[3],
        "argument_latitude": ANOM[3],
    },
    {
        "semi_major_axis": LEO,
        "eccentricity": ECC[0],
        "inclination": INC[0],
        "true_longitude": ANOM[3],
    },
]


EQE_CONFIGS: list[dict[str, float]] = [
    {
        "semi_major_axis": LEO,
        "h": H[3],
        "k": K[3],
        "p": P[2],
        "q": Q[2],
        "mean_longitude": ANOM[3],
        "retrograde": False,
    },
]


COE_SET: tuple[tuple[float, float, float, float, float, float]] = tuple(
    zip(SMA, ECC, INC, RAAN, ARGP, ANOM),
)
EQE_SET: tuple[tuple[float, float, float, float, float, float]] = tuple(zip(SMA, H, K, P, Q, ANOM))

BAD_COES: list[tuple[float, float, float, float, float, float]] = [
    (LEO, -0.001, INC[2], RAAN[2], ARGP[3], ANOM[1]),
    (LEO, 1.0001, INC[2], RAAN[2], ARGP[3], ANOM[1]),
    (LEO, 1.0, INC[2], RAAN[2], ARGP[3], ANOM[1]),
    (LEO, 0.0001, deg2rad(-5), RAAN[2], ARGP[3], ANOM[1]),
    (LEO, 0.0001, deg2rad(181), RAAN[2], ARGP[3], ANOM[1]),
]

BAD_EQES: list[tuple[float, float, float, float, float, float]] = [
    (LEO, 1, 1, 2, 2, ANOM[1]),
    (LEO, 1, 0, 2, 2, ANOM[1]),
    (LEO, 0.1, 0.1, 10e10, 10e10, ANOM[1]),
    (LEO, 0.1, 0.1, 10e10, 2, ANOM[1]),
    (LEO, 0.1, 0.1, 2, 10e10, ANOM[1]),
]


@pytest.mark.parametrize(("sma", "ecc", "inc", "raan", "argp", "anom"), COE_SET)
def testCOE(sma: float, ecc: float, inc: float, raan: float, argp: float, anom: float):
    """Test valid combos of COEs and the class methods."""
    coe = ClassicalElements(sma, ecc, inc, raan, argp, anom)
    inclined, eccentric = isInclined(inc), isEccentric(ecc)
    assert inclined == coe.is_inclined
    assert inclined != coe.is_equatorial
    assert eccentric == coe.is_eccentric
    assert eccentric != coe.is_circular
    assert coe == ClassicalElements(sma, ecc, inc, raan, argp, anom)
    assert coe != ClassicalElements(sma + 1, ecc, inc, raan, argp, anom)

    rv_eci = coe.toECI()
    new_coe = ClassicalElements.fromECI(rv_eci)
    assert coe == new_coe


@pytest.mark.parametrize(("sma", "h", "k", "p", "q", "anom"), EQE_SET)
def testEQE(sma: float, h: float, k: float, p: float, q: float, anom: float):
    """Test valid combos of EQEs and the class methods."""
    eqe = EquinoctialElements(sma, h, k, p, q, anom)
    inc = getInclinationFromEQE(p, q)
    ecc = getEccentricityFromEQE(h, k)
    inclined, eccentric = isInclined(inc), isEccentric(ecc)
    assert inclined == eqe.is_inclined
    assert inclined != eqe.is_equatorial
    assert eccentric == eqe.is_eccentric
    assert eccentric != eqe.is_circular
    assert eqe == EquinoctialElements(sma, h, k, p, q, anom)
    assert eqe != EquinoctialElements(sma + 1, h, k, p, q, anom)

    rv_eci = eqe.toECI()
    new_eqe = EquinoctialElements.fromECI(rv_eci)
    assert eqe == new_eqe


@pytest.mark.parametrize(("sma", "ecc", "inc", "raan", "argp", "anom"), COE_SET)
def testConversions(sma: float, ecc: float, inc: float, raan: float, argp: float, anom: float):
    """Test conversion between element classes."""
    # Classical to Equinoctial
    coe = ClassicalElements(sma, ecc, inc, raan, argp, anom)
    eqe = EquinoctialElements.fromCOE(sma, ecc, inc, raan, argp, anom)
    new_coe = ClassicalElements.fromEQE(eqe.sma, eqe.h, eqe.k, eqe.p, eqe.q, eqe.mean_longitude)
    assert eqe != coe
    assert new_coe == coe

    # Equinoctial to Classical, slightly change values
    h = coe.ecc * sin(coe.argp + coe.raan) + 0.0001
    k = coe.ecc * cos(coe.argp + coe.raan) + 0.0001
    p = tan(coe.inc * 0.5) * sin(coe.raan) + 0.0001
    q = tan(coe.inc * 0.5) * cos(coe.raan) + 0.0001
    anomaly = coe.mean_anomaly + coe.argp + coe.raan + 0.01
    eqe = EquinoctialElements(coe.sma + 1, h, k, p, q, anomaly)
    coe = ClassicalElements.fromEQE(eqe.sma, h, k, p, q, anomaly)
    new_eqe = EquinoctialElements.fromCOE(
        coe.sma,
        coe.ecc,
        coe.inc,
        coe.raan,
        coe.argp,
        coe.true_anomaly,
    )
    assert eqe != coe
    assert new_eqe == eqe


@pytest.mark.parametrize(("sma", "ecc", "inc", "raan", "argp", "anom"), BAD_COES)
def testBadCOE(sma: float, ecc: float, inc: float, raan: float, argp: float, anom: float):
    """Test bad values of COEs."""
    with pytest.raises((InclinationError, EccentricityError)):
        ClassicalElements(sma, ecc, inc, raan, argp, anom)


@pytest.mark.parametrize(("sma", "h", "k", "p", "q", "anom"), BAD_EQES)
def testBadEQE(sma: float, h: float, k: float, p: float, q: float, anom: float):
    """Test bad values of EQEs."""
    with pytest.raises((InclinationError, EccentricityError)):
        EquinoctialElements(sma, h, k, p, q, anom)


@pytest.mark.parametrize("config", COE_CONFIGS)
def testCOEFromConfig(monkeypatch: pytest.MonkeyPatch, config: dict[str, float]):
    """Test valid combos of COEs in a config format."""
    # Nominal
    config["type"] = StateLabel.COE
    _ = ClassicalElements.fromConfig(constructFromUnion(StateConfig, config))

    # Missing required field
    with monkeypatch.context() as m_patch:
        m_patch.delitem(config, "eccentricity")
        with pytest.raises(ValidationError):
            ClassicalElements.fromConfig(constructFromUnion(StateConfig, config))


def testCOEFromConfigBadCOESet(monkeypatch: pytest.MonkeyPatch):
    """Test invalid combos of COEs in a config format."""
    with monkeypatch.context() as m_patch:
        ecc_inc_config = COE_CONFIGS[0]
        ecc_inc_config["type"] = StateLabel.COE
        m_patch.delitem(ecc_inc_config, "right_ascension")
        ecc_eq_config = COE_CONFIGS[1]
        ecc_eq_config["type"] = StateLabel.COE
        m_patch.delitem(ecc_eq_config, "true_longitude_periapsis")
        cir_inc_config = COE_CONFIGS[2]
        cir_inc_config["type"] = StateLabel.COE
        m_patch.delitem(cir_inc_config, "argument_latitude")
        cir_eq_config = COE_CONFIGS[3]
        cir_eq_config["type"] = StateLabel.COE
        m_patch.delitem(cir_eq_config, "true_longitude")
        with pytest.raises(ValidationError):
            ClassicalElements.fromConfig(constructFromUnion(StateConfig, ecc_inc_config))
        with pytest.raises(ValidationError):
            ClassicalElements.fromConfig(constructFromUnion(StateConfig, ecc_eq_config))
        with pytest.raises(ValidationError):
            ClassicalElements.fromConfig(constructFromUnion(StateConfig, cir_inc_config))
        with pytest.raises(ValidationError):
            ClassicalElements.fromConfig(constructFromUnion(StateConfig, cir_eq_config))


@pytest.mark.parametrize("config", EQE_CONFIGS)
def testEQEFromConfig(monkeypatch: pytest.MonkeyPatch, config: dict[str, float]):
    """Test valid combos of EQEs in a config format."""
    # Nominal
    config["type"] = StateLabel.EQE
    _ = EquinoctialElements.fromConfig(constructFromUnion(StateConfig, config))

    # Missing optional retro
    with monkeypatch.context() as m_patch:
        m_patch.setitem(config, "retrograde", True)
        _ = EquinoctialElements.fromConfig(constructFromUnion(StateConfig, config))

    with monkeypatch.context() as m_patch:
        m_patch.delitem(config, "retrograde")
        _ = EquinoctialElements.fromConfig(constructFromUnion(StateConfig, config))

    # Missing required field
    with monkeypatch.context() as m_patch:
        m_patch.delitem(config, "h")
        with pytest.raises(ValidationError):
            EquinoctialElements.fromConfig(constructFromUnion(StateConfig, config))
