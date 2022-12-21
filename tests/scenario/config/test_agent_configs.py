# pylint: disable=attribute-defined-outside-init, unused-argument
from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.agents import GROUND_FACILITY_LABEL, SPACECRAFT_LABEL
from resonaate.scenario.config.agent_configs import (
    DEFAULT_VIEWING_ANGLE,
    ConfigError,
    ConfigValueError,
    FieldOfViewConfig,
    SensingAgentConfig,
    StationKeepingConfig,
    TargetAgentConfig,
)
from resonaate.sensors import ADV_RADAR_LABEL, OPTICAL_LABEL, RADAR_LABEL

# Local Imports
from .conftest import EARTH_SENSORS, GEO_TARGETS, LEO_TARGETS, SPACE_SENSORS


class TestTargetConfig:
    """Test the target config object with valid/invalid sets of JSON configs."""

    @pytest.mark.parametrize("tgt_dict", GEO_TARGETS + LEO_TARGETS)
    def testValidConfig(self, monkeypatch, tgt_dict):
        """Test basic construction of TargetAgentConfig & optional attributes."""
        tgt_cfg_obj = TargetAgentConfig(**tgt_dict)
        assert tgt_cfg_obj.sat_num == tgt_dict["sat_num"]
        assert tgt_cfg_obj.sat_name == tgt_dict["sat_name"]
        assert tgt_cfg_obj.station_keeping.routines == tgt_dict["station_keeping"]["routines"]
        if tgt_cfg_obj.eci_set:
            assert tgt_cfg_obj.init_eci == tgt_dict["init_eci"]
        elif tgt_cfg_obj.coe_set:
            assert tgt_cfg_obj.init_coe == tgt_dict["init_coe"]
        elif tgt_cfg_obj.eqe_set:
            assert tgt_cfg_obj.init_eqe == tgt_dict["init_eqe"]

        # Station keeping is optional, so test deleting it
        with monkeypatch.context() as m_patch:
            m_patch.delitem(tgt_dict, "station_keeping")
            _ = TargetAgentConfig(**tgt_dict)

    @pytest.mark.parametrize("tgt_dict", GEO_TARGETS + LEO_TARGETS)
    def testMultiStateConflict(self, monkeypatch, tgt_dict):
        """Test basic construction of TargetAgentConfig & optional attributes."""
        init_eci = [0, 0, 0, 0, 0, 0]
        init_coe = {
            "sma": 0,
            "ecc": 0,
            "inc": 0,
            "true_long": 0,
        }
        init_eqe = {
            "sma": 0,
            "h": 0,
            "k": 0,
            "p": 0,
            "q": 0,
            "lam": 0,
        }
        with monkeypatch.context() as m_patch:
            m_patch.setitem(tgt_dict, "init_eci", init_eci)
            m_patch.setitem(tgt_dict, "init_coe", init_coe)
            m_patch.setitem(tgt_dict, "init_eqe", init_eqe)
            # All three set
            with pytest.raises(ConfigError):
                _ = TargetAgentConfig(**tgt_dict)

            # ECI + COE | EQE
            m_patch.delitem(tgt_dict, "init_eqe")
            with pytest.raises(ConfigError):
                _ = TargetAgentConfig(**tgt_dict)

            m_patch.delitem(tgt_dict, "init_coe")
            m_patch.setitem(tgt_dict, "init_eqe", init_eqe)
            with pytest.raises(ConfigError):
                _ = TargetAgentConfig(**tgt_dict)

            # EQE + COE
            m_patch.delitem(tgt_dict, "init_eci")
            m_patch.setitem(tgt_dict, "init_coe", init_coe)
            with pytest.raises(ConfigError):
                _ = TargetAgentConfig(**tgt_dict)

    @pytest.mark.parametrize("tgt_dict", GEO_TARGETS + LEO_TARGETS)
    def testInvalidStationKeepingConfig(self, monkeypatch, tgt_dict):
        """Test invalid station keeping config."""
        with monkeypatch.context() as m_patch:
            m_patch.setitem(tgt_dict, "station_keeping", {"routines": ["INVALID"]})
            with pytest.raises(ConfigValueError):
                _ = TargetAgentConfig(**tgt_dict)
            m_patch.setitem(tgt_dict, "station_keeping", {"routines": [20]})
            with pytest.raises(ConfigValueError):
                _ = TargetAgentConfig(**tgt_dict)

    @pytest.mark.parametrize("tgt_dict", GEO_TARGETS + LEO_TARGETS)
    def testInvalidStateConfig(self, monkeypatch, tgt_dict):
        """Test invalid states by not giving the require number of items."""
        init_coe = {
            "sma": 0,
            "ecc": 0,
            "inc": 0,
        }
        init_eqe = {
            "sma": 0,
            "h": 0,
            "k": 0,
            "p": 0,
            "q": 0,
        }
        with monkeypatch.context() as m_patch:
            if "init_eci" in tgt_dict:
                m_patch.setitem(tgt_dict, "init_eci", [0, 0, 0, 0, 0])
            elif "init_coe" in tgt_dict:
                m_patch.setitem(tgt_dict, "init_coe", init_coe)
            elif "init_eqe" in tgt_dict:
                m_patch.setitem(tgt_dict, "init_eqe", init_eqe)

            with pytest.raises(ConfigError):
                _ = TargetAgentConfig(**tgt_dict)

    def testInvalidAltitude(self):
        """Test invalid altitude."""
        with pytest.raises(ConfigError):
            _ = TargetAgentConfig(
                sat_num=1,
                sat_name="Test",
                init_eci=[1e9, 0, 0, 0, 0, 0],
            )

    def testNoStateInput(self):
        """Test no state input."""
        with pytest.raises(ConfigError):
            _ = TargetAgentConfig(
                sat_num=1,
                sat_name="Test",
            )


class TestSensorConfig:
    """Test the sensor config object with valid/invalid sets of JSON configs."""

    @pytest.mark.parametrize("sen_dict", EARTH_SENSORS + SPACE_SENSORS)
    def testValidConfig(self, monkeypatch, sen_dict):
        """Test basic construction of TestSensorConfig & optional attributes."""
        sen_cfg_obj = SensingAgentConfig(**sen_dict)
        assert sen_cfg_obj.id == sen_dict["id"]
        assert sen_cfg_obj.name == sen_dict["name"]
        assert sen_cfg_obj.azimuth_range == sen_dict["azimuth_range"]
        assert sen_cfg_obj.elevation_range == sen_dict["elevation_range"]
        assert sen_cfg_obj.covariance == sen_dict["covariance"]
        assert sen_cfg_obj.aperture_area == sen_dict["aperture_area"]
        assert sen_cfg_obj.efficiency == sen_dict["efficiency"]
        assert sen_cfg_obj.aperture_area == sen_dict["aperture_area"]
        assert sen_cfg_obj.host_type == sen_dict["host_type"]
        assert sen_cfg_obj.host_type in (GROUND_FACILITY_LABEL, SPACECRAFT_LABEL)
        if sen_cfg_obj.host_type == SPACECRAFT_LABEL:
            if sen_cfg_obj.eci_set:
                assert sen_cfg_obj.init_eci == sen_dict["init_eci"]
            elif sen_cfg_obj.coe_set:
                assert sen_cfg_obj.init_coe == sen_dict["init_coe"]
            elif sen_cfg_obj.eqe_set:
                assert sen_cfg_obj.init_eqe == sen_dict["init_eqe"]
            # Station keeping is optional, so test deleting it
            with monkeypatch.context() as m_patch:
                m_patch.delitem(sen_dict, "station_keeping")
                _ = SensingAgentConfig(**sen_dict)

        elif sen_cfg_obj.host_type == GROUND_FACILITY_LABEL:
            assert sen_cfg_obj.lla_set
            assert sen_cfg_obj.lat == sen_dict["lat"]
            assert sen_cfg_obj.lon == sen_dict["lon"]
            assert sen_cfg_obj.alt == sen_dict["alt"]

        assert sen_cfg_obj.sensor_type in (OPTICAL_LABEL, RADAR_LABEL, ADV_RADAR_LABEL)
        if sen_cfg_obj.sensor_type in (RADAR_LABEL, ADV_RADAR_LABEL):
            assert sen_cfg_obj.tx_frequency == sen_dict["tx_frequency"]
            assert sen_cfg_obj.tx_power == sen_dict["tx_power"]
            assert sen_cfg_obj.min_detectable_power == sen_dict["min_detectable_power"]

    def testStringTxFrequency(self):
        """Test radar sensor required inputs."""
        sen_dict = deepcopy(EARTH_SENSORS[0])
        sen_dict["tx_frequency"] = "L"
        sen_cfg_obj = SensingAgentConfig(**sen_dict)
        assert sen_cfg_obj.tx_frequency == 1.5 * 1e9

    @pytest.mark.parametrize("sen_dict", SPACE_SENSORS)
    def testMultiStateConflictSpace(self, monkeypatch, sen_dict):
        """Test state conflict for space sensors."""
        init_eci = [0, 0, 0, 0, 0, 0]
        init_coe = {
            "sma": 0,
            "ecc": 0,
            "inc": 0,
            "true_long": 0,
        }
        init_eqe = {
            "sma": 0,
            "h": 0,
            "k": 0,
            "p": 0,
            "q": 0,
            "lam": 0,
        }
        with monkeypatch.context() as m_patch:
            m_patch.setitem(sen_dict, "init_eci", init_eci)
            m_patch.setitem(sen_dict, "init_coe", init_coe)
            m_patch.setitem(sen_dict, "init_eqe", init_eqe)
            # All three set
            with pytest.raises(ConfigError):
                _ = SensingAgentConfig(**sen_dict)

            # ECI + COE | EQE
            m_patch.delitem(sen_dict, "init_eqe")
            with pytest.raises(ConfigError):
                _ = SensingAgentConfig(**sen_dict)

            m_patch.delitem(sen_dict, "init_coe")
            m_patch.setitem(sen_dict, "init_eqe", init_eqe)
            with pytest.raises(ConfigError):
                _ = SensingAgentConfig(**sen_dict)

            # EQE + COE
            m_patch.delitem(sen_dict, "init_eci")
            m_patch.setitem(sen_dict, "init_coe", init_coe)
            with pytest.raises(ConfigError):
                _ = SensingAgentConfig(**sen_dict)

    @pytest.mark.parametrize("sen_dict", EARTH_SENSORS)
    def testMultiStateConflictGround(self, monkeypatch, sen_dict):
        """Test test state conflict for ground sensors."""
        with monkeypatch.context() as m_patch:
            m_patch.setitem(sen_dict, "init_eci", [0, 0, 0, 0, 0])
            # LLA & ECI set
            with pytest.raises(ConfigError):
                _ = SensingAgentConfig(**sen_dict)

            # No State
            m_patch.delitem(sen_dict, "init_eci")
            m_patch.delitem(sen_dict, "lat")
            m_patch.delitem(sen_dict, "lon")
            m_patch.delitem(sen_dict, "alt")
            with pytest.raises(ConfigError):
                _ = SensingAgentConfig(**sen_dict)

    @pytest.mark.parametrize("sen_dict", SPACE_SENSORS)
    def testInvalidStateConfig(self, monkeypatch, sen_dict):
        """Test invalid states by not giving the require number of items."""
        init_coe = {
            "sma": 0,
            "ecc": 0,
            "inc": 0,
        }
        init_eqe = {
            "sma": 0,
            "h": 0,
            "k": 0,
            "p": 0,
            "q": 0,
        }
        with monkeypatch.context() as m_patch:
            if "init_eci" in sen_dict:
                m_patch.setitem(sen_dict, "init_eci", [0, 0, 0, 0, 0])
            elif "init_coe" in sen_dict:
                m_patch.setitem(sen_dict, "init_coe", init_coe)
            elif "init_eqe" in sen_dict:
                m_patch.setitem(sen_dict, "init_eqe", init_eqe)

            with pytest.raises(ConfigError):
                _ = SensingAgentConfig(**sen_dict)

    @pytest.mark.parametrize("sen_dict", SPACE_SENSORS)
    def testInvalidStationKeepingConfig(self, monkeypatch, sen_dict):
        """Test invalid station keeping config."""
        with monkeypatch.context() as m_patch:
            m_patch.setitem(sen_dict, "station_keeping", {"routines": ["INVALID"]})
            with pytest.raises(ConfigValueError):
                _ = SensingAgentConfig(**sen_dict)
            m_patch.setitem(sen_dict, "station_keeping", {"routines": [20]})
            with pytest.raises(ConfigValueError):
                _ = SensingAgentConfig(**sen_dict)

    def testInvalidAltitude(self):
        """Test invalid altitude."""
        sen_dict = deepcopy(SPACE_SENSORS[0])
        sen_dict["init_eci"] = [1e9, 0, 0, 0, 0, 0]
        with pytest.raises(ConfigError):
            _ = SensingAgentConfig(**sen_dict)

    def testStationKeepingForGroundSensors(self):
        """Test station keeping for ground sensors throws an error."""
        sen_dict = deepcopy(EARTH_SENSORS[0])
        sen_dict["station_keeping"] = {"routines": ["LEO"]}
        with pytest.raises(ConfigError):
            _ = SensingAgentConfig(**sen_dict)

        sen_dict = deepcopy(EARTH_SENSORS[0])
        sen_dict["station_keeping"] = {}
        _ = SensingAgentConfig(**sen_dict)

        sen_dict = deepcopy(EARTH_SENSORS[0])
        sen_dict["station_keeping"] = None
        _ = SensingAgentConfig(**sen_dict)

    def testRadarSensorRequiredInputs(self):
        """Test radar sensor required inputs."""
        sen_dict = deepcopy(EARTH_SENSORS[0])
        del sen_dict["tx_frequency"]
        with pytest.raises(ConfigError):
            _ = SensingAgentConfig(**sen_dict)

        sen_dict = deepcopy(EARTH_SENSORS[0])
        del sen_dict["tx_power"]
        with pytest.raises(ConfigError):
            _ = SensingAgentConfig(**sen_dict)

        sen_dict = deepcopy(EARTH_SENSORS[0])
        del sen_dict["min_detectable_power"]
        with pytest.raises(ConfigError):
            _ = SensingAgentConfig(**sen_dict)

    def testInvalidHostType(self):
        """Test invalid host type."""
        with pytest.raises(ConfigError):
            _ = SensingAgentConfig(
                id=11111,
                name="Test",
                host_type="INVALID",
                sensor_type=OPTICAL_LABEL,
                azimuth_range=[0, 360],
                elevation_range=[0, 90],
                covariance=[[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                aperture_area=10.0,
                efficiency=0.99,
                slew_rate=2.0,
                init_eci=[7000.0, 0, 0, 0, 0, 0],
            )

    def testInvalidSensorType(self):
        """Test invalid sensor type."""
        with pytest.raises(ConfigError):
            _ = SensingAgentConfig(
                id=11111,
                name="Test",
                host_type=SPACECRAFT_LABEL,
                sensor_type="INVALID",
                azimuth_range=[0, 360],
                elevation_range=[0, 90],
                covariance=[[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                aperture_area=10.0,
                efficiency=0.99,
                slew_rate=2.0,
                init_eci=[7000.0, 0, 0, 0, 0, 0],
            )


def testFieldOfViewConfig():
    """Test field of view config."""
    cone_cfg = FieldOfViewConfig(fov_shape="conic", cone_angle=DEFAULT_VIEWING_ANGLE)
    assert cone_cfg.CONFIG_LABEL == "field_of_view"
    assert cone_cfg.cone_angle == DEFAULT_VIEWING_ANGLE

    cone_cfg = FieldOfViewConfig(fov_shape="conic")
    assert cone_cfg.CONFIG_LABEL == "field_of_view"
    assert cone_cfg.cone_angle == DEFAULT_VIEWING_ANGLE

    rect_cfg = FieldOfViewConfig(
        fov_shape="rectangular",
        azimuth_angle=DEFAULT_VIEWING_ANGLE,
        elevation_angle=DEFAULT_VIEWING_ANGLE,
    )
    assert rect_cfg.CONFIG_LABEL == "field_of_view"
    assert rect_cfg.azimuth_angle == DEFAULT_VIEWING_ANGLE
    assert rect_cfg.elevation_angle == DEFAULT_VIEWING_ANGLE

    rect_cfg = FieldOfViewConfig(fov_shape="rectangular")
    assert rect_cfg.azimuth_angle == DEFAULT_VIEWING_ANGLE
    assert rect_cfg.elevation_angle == DEFAULT_VIEWING_ANGLE


def testBadInputsFieldOfViewConfig():
    """Test bad inputs for field of view config."""
    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="invalid")

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="conic", cone_angle=0.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="conic", cone_angle=180.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="conic", cone_angle=-1.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="conic", cone_angle=181.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", azimuth_angle=0.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", azimuth_angle=180.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", azimuth_angle=-1.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", azimuth_angle=181.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", elevation_angle=0.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", elevation_angle=180.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", elevation_angle=-1.0)

    with pytest.raises(ConfigValueError):
        _ = FieldOfViewConfig(fov_shape="rectangular", elevation_angle=181.0)


def testStationKeepingConfig():
    """Test station keeping config."""
    cfg = StationKeepingConfig(routines=["LEO"])
    assert cfg.CONFIG_LABEL == "station_keeping"
    assert cfg.routines == ["LEO"]

    assert cfg.toJSON() == {"routines": ["LEO"]}

    cfg = StationKeepingConfig()
    assert cfg.routines is not None
    assert not cfg.routines

    with pytest.raises(ConfigValueError):
        _ = StationKeepingConfig(routines=["INVALID"])
