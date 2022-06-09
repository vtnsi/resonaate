# pylint: disable=attribute-defined-outside-init, no-self-use, unused-argument
# Standard Library Imports
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.scenario.config.agent_configs import (
        ConfigError, ConfigValueError, SensorConfigObject, TargetConfigObject,
    )
    from resonaate.agents.sensing_agent import GROUND_FACILITY_LABEL, SPACECRAFT_LABEL
    from resonaate.sensors import OPTICAL_LABEL, RADAR_LABEL, ADV_RADAR_LABEL
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ...conftest import BaseTestCase
from .conftest import GEO_TARGETS, LEO_TARGETS, EARTH_SENSORS, SPACE_SENSORS


class TestTargetConfig(BaseTestCase):
    """Test the target config object with valid/invalid sets of JSON configs."""

    @pytest.mark.parametrize("tgt_dict", GEO_TARGETS + LEO_TARGETS)
    def testValidConfig(self, monkeypatch, tgt_dict):
        """Test basic construction of TargetConfigObject & optional attributes."""
        tgt_cfg_obj = TargetConfigObject(tgt_dict)
        assert tgt_cfg_obj.sat_num == tgt_dict["sat_num"]
        assert tgt_cfg_obj.sat_name == tgt_dict["sat_name"]
        assert tgt_cfg_obj.station_keeping == tgt_dict["station_keeping"]
        if tgt_cfg_obj.eci_set:
            assert tgt_cfg_obj.init_eci == tgt_dict["init_eci"]
        elif tgt_cfg_obj.coe_set:
            assert tgt_cfg_obj.init_coe == tgt_dict["init_coe"]
        elif tgt_cfg_obj.eqe_set:
            assert tgt_cfg_obj.init_eqe == tgt_dict["init_eqe"]

        # Station keeping is optional, so test deleting it
        with monkeypatch.context() as m_patch:
            m_patch.delitem(tgt_dict, "station_keeping")
            _ = TargetConfigObject(tgt_dict)

    @pytest.mark.parametrize("tgt_dict", GEO_TARGETS + LEO_TARGETS)
    def testMultiStateConflict(self, monkeypatch, tgt_dict):
        """Test basic construction of TargetConfigObject & optional attributes."""
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
                _ = TargetConfigObject(tgt_dict)

            # ECI + COE | EQE
            m_patch.delitem(tgt_dict, "init_eqe")
            with pytest.raises(ConfigError):
                _ = TargetConfigObject(tgt_dict)

            m_patch.delitem(tgt_dict, "init_coe")
            m_patch.setitem(tgt_dict, "init_eqe", init_eqe)
            with pytest.raises(ConfigError):
                _ = TargetConfigObject(tgt_dict)

            # EQE + COE
            m_patch.delitem(tgt_dict, "init_eci")
            m_patch.setitem(tgt_dict, "init_coe", init_coe)
            with pytest.raises(ConfigError):
                _ = TargetConfigObject(tgt_dict)

    @pytest.mark.parametrize("tgt_dict", GEO_TARGETS + LEO_TARGETS)
    def testInvalidStationKeepingConfig(self, monkeypatch, tgt_dict):
        """Test invalid station keeping config."""
        with monkeypatch.context() as m_patch:
            m_patch.setitem(tgt_dict, "station_keeping", ["INVALID"])
            with pytest.raises(ConfigValueError):
                _ = TargetConfigObject(tgt_dict)
            m_patch.setitem(tgt_dict, "station_keeping", [20])
            with pytest.raises(ConfigValueError):
                _ = TargetConfigObject(tgt_dict)

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
                _ = TargetConfigObject(tgt_dict)


class TestSensorConfig(BaseTestCase):
    """Test the sensor config object with valid/invalid sets of JSON configs."""

    @pytest.mark.parametrize("sen_dict", EARTH_SENSORS + SPACE_SENSORS)
    def testValidConfig(self, monkeypatch, sen_dict):
        """Test basic construction of TestSensorConfig & optional attributes."""
        sen_cfg_obj = SensorConfigObject(sen_dict)
        assert sen_cfg_obj.id == sen_dict["id"]
        assert sen_cfg_obj.name == sen_dict["name"]
        assert sen_cfg_obj.azimuth_range == sen_dict["azimuth_range"]
        assert sen_cfg_obj.elevation_range == sen_dict["elevation_range"]
        assert sen_cfg_obj.covariance == sen_dict["covariance"]
        assert sen_cfg_obj.aperture_area == sen_dict["aperture_area"]
        assert sen_cfg_obj.efficiency == sen_dict["efficiency"]
        assert sen_cfg_obj.exemplar == sen_dict["exemplar"]
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
                _ = SensorConfigObject(sen_dict)

        elif sen_cfg_obj.host_type == GROUND_FACILITY_LABEL:
            assert sen_cfg_obj.lla_set
            assert sen_cfg_obj.lat == sen_dict["lat"]
            assert sen_cfg_obj.lon == sen_dict["lon"]
            assert sen_cfg_obj.alt == sen_dict["alt"]

        assert sen_cfg_obj.sensor_type in (OPTICAL_LABEL, RADAR_LABEL, ADV_RADAR_LABEL)
        if sen_cfg_obj.sensor_type in (RADAR_LABEL, ADV_RADAR_LABEL):
            assert sen_cfg_obj.tx_frequency == sen_dict["tx_frequency"]
            assert sen_cfg_obj.tx_power == sen_dict["tx_power"]

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
                _ = SensorConfigObject(sen_dict)

            # ECI + COE | EQE
            m_patch.delitem(sen_dict, "init_eqe")
            with pytest.raises(ConfigError):
                _ = SensorConfigObject(sen_dict)

            m_patch.delitem(sen_dict, "init_coe")
            m_patch.setitem(sen_dict, "init_eqe", init_eqe)
            with pytest.raises(ConfigError):
                _ = SensorConfigObject(sen_dict)

            # EQE + COE
            m_patch.delitem(sen_dict, "init_eci")
            m_patch.setitem(sen_dict, "init_coe", init_coe)
            with pytest.raises(ConfigError):
                _ = SensorConfigObject(sen_dict)

    @pytest.mark.parametrize("sen_dict", EARTH_SENSORS)
    def testMultiStateConflictGround(self, monkeypatch, sen_dict):
        """Test test state conflict for ground sensors."""
        with monkeypatch.context() as m_patch:
            m_patch.setitem(sen_dict, "init_eci", [0, 0, 0, 0, 0])
            # LLA & ECI set
            with pytest.raises(ConfigError):
                _ = SensorConfigObject(sen_dict)

            # No State
            m_patch.delitem(sen_dict, "init_eci")
            m_patch.delitem(sen_dict, "lat")
            m_patch.delitem(sen_dict, "lon")
            m_patch.delitem(sen_dict, "alt")
            with pytest.raises(ConfigError):
                _ = SensorConfigObject(sen_dict)

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
                _ = SensorConfigObject(sen_dict)

    @pytest.mark.parametrize("sen_dict", SPACE_SENSORS)
    def testInvalidStationKeepingConfig(self, monkeypatch, sen_dict):
        """Test invalid station keeping config."""
        with monkeypatch.context() as m_patch:
            m_patch.setitem(sen_dict, "station_keeping", ["INVALID"])
            with pytest.raises(ConfigValueError):
                _ = SensorConfigObject(sen_dict)
            m_patch.setitem(sen_dict, "station_keeping", [20])
            with pytest.raises(ConfigValueError):
                _ = SensorConfigObject(sen_dict)
