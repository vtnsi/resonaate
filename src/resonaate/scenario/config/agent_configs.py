"""Module that defines the objects stored in the 'targets' and 'sensors' configuration sections."""
from .base import ConfigOption, ConfigObject, NO_SETTING
from ...sensors import OPTICAL_LABEL, RADAR_LABEL, ADV_RADAR_LABEL
from ...agents.sensing_agent import GROUND_FACILITY_LABEL, SPACECRAFT_LABEL
from ...dynamics.integration_events.station_keeping import StationKeeper


def validateStationKeepingConfigs(conf_str_list):
    """Throw an exception if there's an invalid station keeping configuration string in `conf_str_list`.

    Args:
        conf_str_list (list(str)): List of station keeping configuration strings to be validated.

    Raises:
        ValueError: If there's an invalid station keeping configuration string in `conf_str_list`.
    """
    for conf_str in conf_str_list:
        if conf_str not in StationKeeper.validConfigs():
            err = f"{conf_str} is not a valid station keeping configuration."
            raise ValueError(err)


class TargetConfigObject(ConfigObject):
    """Defines the structure for an object defined in the 'targets' configuration section."""

    @staticmethod
    def getFields():
        """Return a tuple of defining required :class:`.ConfigOption`s for a :class:`.TargetConfigObject`."""
        return (
            ConfigOption("sat_num", (int, )),
            ConfigOption("sat_name", (str, )),
            ConfigOption("init_eci", (list, ), default=NO_SETTING),
            ConfigOption("init_coe", (dict, ), default=NO_SETTING),
            ConfigOption("station_keeping", (list, ), default=list())
        )

    def __init__(self, object_config):
        """Construct an instance of a :class:`.TargetConfigObject`.

        Args:
            object_config (dict): Configuration dictionary defining this
                :class:`.TargetConfigObject`.
        """
        super(TargetConfigObject, self).__init__(object_config)

        if not self.eci_set and not self.coe_set:
            err = "Target {0}: State not specified: {1}".format(self.sat_num, object_config)
            raise ValueError(err)

        if self.eci_set and self.coe_set:
            err = "Target {0}: Duplicate state specified: {1}".format(self.sat_num, object_config)
            raise ValueError(err)

        if self.eci_set:
            if len(self.init_eci) != 6:
                err = "ECI vector should have 6 elements, not {0}".format(len(self.init_eci))
                raise ValueError(err)

        validateStationKeepingConfigs(self.station_keeping)

    @property
    def sat_num(self):
        """int: Unique identifier for this target.

        Typically corresponds to a NORAD catalogue ID number.
        """
        return self._sat_num.setting  # pylint: disable=no-member

    @property
    def sat_name(self):
        """str: Human recognizable name for this target."""
        return self._sat_name.setting  # pylint: disable=no-member

    @property
    def init_eci(self):
        """list: Six element list representing this target's initial ECI state vector."""
        return self._init_eci.setting  # pylint: disable=no-member

    @property
    def init_coe(self):
        """dict: Set of classical orbital elements (COE) describing the target's orbit.

        See :meth:`.Orbit.buildFromCOEConfig()` for rules on defining a set of classical orbital
        elements.
        """
        return self._init_coe.setting  # pylint: disable=no-member

    @property
    def station_keeping(self):
        """str: listing what type of station keeping this RSO is doing."""
        return self._station_keeping.setting  # pylint: disable=no-member

    @property
    def eci_set(self):
        """bool: Indication of whether an ECI vector is available for this target configuration."""
        return self.init_eci != NO_SETTING

    @property
    def coe_set(self):
        """bool: Indication of whether COEs are available for this target configuration."""
        return self.init_coe != NO_SETTING


class SensorConfigObject(ConfigObject):
    """Defines the structure for an object defined in the 'sensors' configuration section."""

    @staticmethod
    def getFields():
        """Return a tuple of defining required :class:`.ConfigOption`s for a :class:`.SensorConfigObject`."""
        return (
            ConfigOption("id", (int, )),
            ConfigOption("name", (str, )),
            ConfigOption("host_type", (str, ), valid_settings=(GROUND_FACILITY_LABEL, SPACECRAFT_LABEL, )),
            ConfigOption("lat", (float, ), default=NO_SETTING),
            ConfigOption("lon", (float, ), default=NO_SETTING),
            ConfigOption("alt", (float, ), default=NO_SETTING),
            ConfigOption("eci_state", (list, ), default=NO_SETTING),
            ConfigOption("azimuth_range", (list, )),
            ConfigOption("elevation_range", (list, )),
            ConfigOption("covariance", (list, )),
            ConfigOption("aperture_area", (float, )),
            ConfigOption("efficiency", (float, )),
            ConfigOption("slew_rate", (float, )),
            ConfigOption("exemplar", (list, )),
            ConfigOption("sensor_type", (str, ), valid_settings=(OPTICAL_LABEL, RADAR_LABEL, ADV_RADAR_LABEL, )),
            ConfigOption("tx_power", (float, ), default=NO_SETTING),
            ConfigOption("tx_frequency", (float, ), default=NO_SETTING),
            ConfigOption("station_keeping", (list, ), default=list())
        )

    def __init__(self, object_config):
        """Construct an instance of a :class:`.SensorConfigObject`.

        Args:
            object_config (dict): Configuration dictionary defining this
                :class:`.SensorConfigObject`.
        """
        super(SensorConfigObject, self).__init__(object_config)

        lla_set = all((self.lat != NO_SETTING, self.lon != NO_SETTING, self.alt != NO_SETTING))
        eci_set = self.eci_state != NO_SETTING
        if not lla_set and not eci_set:
            err = "Sensor {0}: State not specified: {1}".format(self.id, object_config)
            raise ValueError(err)

        if lla_set and eci_set:
            err = "Sensor {0}: Duplicate state specified: {1}".format(self.id, object_config)
            raise ValueError(err)

        if eci_set:
            if len(self.eci_state) != 6:
                err = "Sensor {0}: ECI vector should have 6 elements, not {1}".format(
                    self.id,
                    len(self.eci_state)
                )
                raise ValueError(err)

        is_radar = self.sensor_type in (RADAR_LABEL, ADV_RADAR_LABEL)
        tx_not_set = self.tx_power is NO_SETTING or self.tx_frequency is NO_SETTING
        if is_radar and tx_not_set:
            err = "Sensor {0}: Radar transmit parameters not set: {1}".format(
                self.id,
                object_config
            )
            raise ValueError(err)

        if self.host_type is GROUND_FACILITY_LABEL and self.station_keeping is not None:
            err = "Ground based sensors cannot perform station keeping"
            raise ValueError(err)

        validateStationKeepingConfigs(self.station_keeping)

    @property  # noqa: A003
    def id(self):  # pylint: disable=invalid-name
        """int: Unique identifier for this sensor."""
        return self._id.setting  # pylint: disable=no-member

    @property
    def name(self):
        """str: Human recognizable name for this sensor."""
        return self._name.setting  # pylint: disable=no-member

    @property
    def host_type(self):
        """str: Label for type of sensing agent this sensor is."""
        return self._host_type.setting  # pylint: disable=no-member

    @property
    def lat(self):
        """float: Latitude (in radians) of this sensor.

        Will only be set if :attr:`.host_type` is set to `GROUND_FACILITY_LABEL`.
        """
        return self._lat.setting  # pylint: disable=no-member

    @property
    def lon(self):
        """float: Longitude (in radians) of this sensor.

        Will only be set if :attr:`.host_type` is set to `GROUND_FACILITY_LABEL`.
        """
        return self._lon.setting  # pylint: disable=no-member

    @property
    def alt(self):
        """float: Height (in km) above ellipsoid.

        Will only be set if :attr:`.host_type` is set to `GROUND_FACILITY_LABEL`.
        """
        return self._alt.setting  # pylint: disable=no-member

    @property
    def eci_state(self):
        """list: Six element list representing this sensor's initial ECI state vector.

        Will only be set if :attr:`.host_type` is set to `SPACECRAFT_LABEL`.
        """
        return self._eci_state.setting  # pylint: disable=no-member

    @property
    def covariance(self):
        """list: Measurement noise covariance matrix."""
        return self._covariance.setting  # pylint: disable=no-member

    @property
    def slew_rate(self):
        """float: Rate (radians/sec) at which this sensor can slew to acquire new targets."""
        return self._slew_rate.setting  # pylint: disable=no-member

    @property
    def azimuth_range(self):
        """list: Range of motion (radians) that this sensor has in the azimuth plane."""
        return self._azimuth_range.setting  # pylint: disable=no-member

    @property
    def elevation_range(self):
        """list: Range of motion (radians) that this sensor has in the elevation plane."""
        return self._elevation_range.setting  # pylint: disable=no-member

    @property
    def efficiency(self):
        """float: Efficiency percentage of the sensor."""
        return self._efficiency.setting  # pylint: disable=no-member

    @property
    def aperture_area(self):
        """float: Size (meters^2) of the sensor."""
        return self._aperture_area.setting  # pylint: disable=no-member

    @property
    def sensor_type(self):
        """str: Label for type of sensor this sensor is."""
        return self._sensor_type.setting  # pylint: disable=no-member

    @property
    def exemplar(self):
        """list: Two element list of exemplar capabilities, used in min detectable power calculation.

        Example/units: [cross sectional area (m^2), range (km)]
        """
        return self._exemplar.setting  # pylint: disable=no-member

    @property
    def tx_power(self):
        """float: Transmit power of radar sensor.

        Will only be set if :attr:`.sensor_type` is `RADAR_LABEL` or `ADV_RADAR_LABEL`.
        """
        return self._tx_power.setting  # pylint: disable=no-member

    @property
    def tx_frequency(self):
        """float: Transmit frequency of radar sensor.

        Will only be set if :attr:`.sensor_type` is `RADAR_LABEL` or `ADV_RADAR_LABEL`.
        """
        return self._tx_frequency.setting  # pylint: disable=no-member

    @property
    def station_keeping(self):
        """string: list of station keeping checks to perform.

        Default to type(None), asserted to be None if host_type is `GROUND_FACILITY_LABEL`.
        """
        return self._station_keeping.setting  # pylint: disable=no-member
