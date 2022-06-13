"""Module that defines the objects stored in the 'targets' and 'sensors' configuration sections."""

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
from numpy.linalg import norm

# Local Imports
from ...agents.sensing_agent import GROUND_FACILITY_LABEL, SPACECRAFT_LABEL
from ...agents.target_agent import (
    GEO_DEFAULT_MASS,
    GEO_DEFAULT_VCS,
    LEO_DEFAULT_MASS,
    LEO_DEFAULT_VCS,
    MEO_DEFAULT_MASS,
    MEO_DEFAULT_VCS,
)
from ...dynamics.integration_events.station_keeping import (
    VALID_STATION_KEEPING_ROUTINES,
    StationKeeper,
)
from ...sensors import ADV_RADAR_LABEL, OPTICAL_LABEL, RADAR_LABEL, VALID_SENSOR_FOV_LABELS
from .base import (
    NO_SETTING,
    ConfigError,
    ConfigObject,
    ConfigOption,
    ConfigSection,
    ConfigValueError,
)


def validateStationKeepingConfigs(conf_str_list):
    """Throw an exception if there's an invalid station keeping configuration string in `conf_str_list`.

    Args:
        conf_str_list (list(str)): List of station keeping configuration strings to be validated.

    Raises:
        ValueError: If there's an invalid station keeping configuration string in `conf_str_list`.
    """
    for conf_str in conf_str_list:
        if conf_str not in StationKeeper.validConfigs():
            raise ConfigValueError("station_keeping", conf_str, StationKeeper.validConfigs())


class TargetConfigObject(ConfigObject):
    """Defines the structure for an object defined in the 'targets' configuration section."""

    @staticmethod
    def getFields():
        """Return a tuple of defining required :class:`.ConfigOption` objects for a :class:`.TargetConfigObject`.

        References:
            :cite:t:`montenbruck_2012_orbits`, Eqn 3.75 - 3.76, Table 3.5
        """
        return (
            ConfigOption("sat_num", (int,)),
            ConfigOption("sat_name", (str,)),
            ConfigOption("init_eci", (list,), default=NO_SETTING),
            ConfigOption("init_coe", (dict,), default=NO_SETTING),
            ConfigOption("init_eqe", (dict,), default=NO_SETTING),
            ConfigOption("visual_cross_section", (float, int), default=NO_SETTING),
            ConfigOption("mass", (float, int), default=NO_SETTING),
            ConfigOption("reflectivity", (float,), default=0.21),  # Solar Panel Reflectivity
            StationKeepingConfig(),
        )

    def __init__(self, object_config):
        """Construct an instance of a :class:`.TargetConfigObject`.

        Args:
            object_config (dict): Configuration dictionary defining this
                :class:`.TargetConfigObject`.
        """
        super().__init__(object_config)

        states_set = (self.eci_set, self.coe_set, self.eqe_set)
        if not any(states_set):
            err = f"Target {self.sat_num}: State not specified: {object_config}"
            raise ConfigError(self.__class__.__name__, err)

        if sum(states_set) > 1:
            err = f"Target {self.sat_num}: Duplicate state specified: {object_config}"
            raise ConfigError(self.__class__.__name__, err)

        if self.eci_set:
            if len(self.init_eci) != 6:
                err = f"Target {self.sat_num}: ECI vector should have 6 elements, not {len(self.init_eci)}"
                raise ConfigError(self.__class__.__name__, err)

            altitude = norm(self.init_eci[:3]) - Earth.radius

        if self.eqe_set:
            if len(self.init_eqe) != 6:
                err = f"Target {self.sat_num}: EQE set should have 6 elements, not {len(self.init_eqe)}"
                raise ConfigError(self.__class__.__name__, err)

            altitude = norm(eqe2eci(self.init_eqe)[:3]) - Earth.radius

        if self.coe_set:
            if len(self.init_coe) < 4:
                err = f"Target {self.sat_num}: COE set should have at least 4 elements, not {len(self.init_coe)}"
                raise ConfigError(self.__class__.__name__, err)

            altitude = norm(coe2eci(self.init_coe)[:3]) - Earth.radius

        if self.mass is NO_SETTING:
            if altitude <= LEO_ALTITUDE_LIMIT:
                self.mass = LEO_DEFAULT_MASS
            elif altitude <= MEO_ALTITUDE_LIMIT:
                self.mass = MEO_DEFAULT_MASS
            elif altitude <= GEO_ALTITUDE_LIMIT:
                self.mass = GEO_DEFAULT_MASS
            else:
                err = "RSO altitude above GEO, unable to set a default mass value"
                raise ValueError(self.__class__.__name__, err)

        if self.visual_cross_section is NO_SETTING:
            if altitude <= LEO_ALTITUDE_LIMIT:
                self.visual_cross_section = LEO_DEFAULT_VCS
            elif altitude <= MEO_ALTITUDE_LIMIT:
                self.visual_cross_section = MEO_DEFAULT_VCS
            elif altitude <= GEO_ALTITUDE_LIMIT:
                self.visual_cross_section = GEO_DEFAULT_VCS
            else:
                err = "RSO altitude above GEO, unable to set a default visual cross section value"
                raise ValueError(self.__class__.__name__, err)

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

        See :meth:`.ClassicalElements.fromConfig()` for rules on defining a set of classical orbital elements.
        """
        return self._init_coe.setting  # pylint: disable=no-member

    @property
    def init_eqe(self):
        """dict: Set of equinoctial orbital elements (EQE) describing the target's orbit.

        See :meth:`.EquinoctialElements.fromConfig()` for rules on defining a set of equinoctial orbital elements.
        """
        return self._init_eqe.setting  # pylint: disable=no-member

    @property
    def mass(self):
        """float: Mass of RSO."""
        return self._mass.setting

    @mass.setter
    def mass(self, new_mass):
        """float: Set Mass of RSO."""
        self._mass = new_mass

    @property
    def visual_cross_section(self):
        """float: visual_cross_section of RSO."""
        return self._visual_cross_section.setting

    @visual_cross_section.setter
    def visual_cross_section(self, new_visual_cross_section):
        """float: Set visual cross section of RSO."""
        self._visual_cross_section = new_visual_cross_section

    @property
    def reflectivity(self):
        """float: reflectivity of RSO."""
        return self._reflectivity.setting

    @property
    def station_keeping(self):
        """str: listing what type of station keeping this RSO is doing."""
        return self._station_keeping  # pylint: disable=no-member

    @property
    def eci_set(self):
        """bool: Indication of whether an ECI vector is available for this target configuration."""
        return self.init_eci != NO_SETTING

    @property
    def coe_set(self):
        """bool: Indication of whether COEs are available for this target configuration."""
        return self.init_coe != NO_SETTING

    @property
    def eqe_set(self):
        """bool: Indication of whether EQEs are available for this target configuration."""
        return self.init_eqe != NO_SETTING


class SensorConfigObject(ConfigObject):  # pylint: disable=too-many-public-methods
    """Defines the structure for an object defined in the 'sensors' configuration section."""

    @staticmethod
    def getFields():
        """Return a tuple of defining required :class:`.ConfigOption` objects for a :class:`.SensorConfigObject`."""
        return (
            ConfigOption("id", (int,)),
            ConfigOption("name", (str,)),
            ConfigOption(
                "host_type",
                (str,),
                valid_settings=(
                    GROUND_FACILITY_LABEL,
                    SPACECRAFT_LABEL,
                ),
            ),
            ConfigOption("lat", (float,), default=NO_SETTING),
            ConfigOption("lon", (float,), default=NO_SETTING),
            ConfigOption("alt", (float,), default=NO_SETTING),
            ConfigOption("init_eci", (list,), default=NO_SETTING),
            ConfigOption("init_coe", (dict,), default=NO_SETTING),
            ConfigOption("init_eqe", (dict,), default=NO_SETTING),
            ConfigOption("azimuth_range", (list,)),
            ConfigOption("elevation_range", (list,)),
            ConfigOption("covariance", (list,)),
            ConfigOption("aperture_area", (float,)),
            ConfigOption("efficiency", (float,)),
            ConfigOption("slew_rate", (float,)),
            ConfigOption("exemplar", (list,)),
            FieldOfViewConfig(),
            ConfigOption("calculate_fov", (bool,), default=NO_SETTING),
            ConfigOption("detectable_vismag", (float, int), default=NO_SETTING),
            ConfigOption("minimum_range", (float, int), default=NO_SETTING),
            ConfigOption("maximum_range", (float, int), default=NO_SETTING),
            ConfigOption(
                "sensor_type",
                (str,),
                valid_settings=(
                    OPTICAL_LABEL,
                    RADAR_LABEL,
                    ADV_RADAR_LABEL,
                ),
            ),
            ConfigOption("tx_power", (float,), default=NO_SETTING),
            ConfigOption("tx_frequency", (float,), default=NO_SETTING),
            ConfigOption("visual_cross_section", (float, int), default=25.0),
            ConfigOption("mass", (float, int), default=500.0),
            ConfigOption("reflectivity", (float,), default=0.21),  # Solar Panel Reflectivity
            StationKeepingConfig(),
        )

    def __init__(self, object_config):
        """Construct an instance of a :class:`.SensorConfigObject`.

        Args:
            object_config (dict): Configuration dictionary defining this
                :class:`.SensorConfigObject`.
        """
        super().__init__(object_config)

        states_set = (self.lla_set, self.eci_set, self.coe_set, self.eqe_set)
        if not any(states_set):
            err = f"Sensor {self.id}: State not specified: {object_config}"
            raise ConfigError(self.__class__.__name__, err)

        if sum(states_set) > 1:
            err = f"Sensor {self.id}: Duplicate state specified: {object_config}"
            raise ConfigError(self.__class__.__name__, err)

        if self.eci_set:
            if len(self.init_eci) != 6:
                err = f"Sensor {self.id}: ECI vector should have 6 elements, not {len(self.init_eci)}"
                raise ConfigError(self.__class__.__name__, err)

        if self.eqe_set:
            if len(self.init_eqe) != 6:
                err = f"Target {self.id}: EQE set should have 6 elements, not {len(self.init_eqe)}"
                raise ConfigError(self.__class__.__name__, err)

        if self.coe_set:
            if len(self.init_coe) < 4:
                err = f"Target {self.id}: COE set should have at least 4 elements, not {len(self.init_coe)}"
                raise ConfigError(self.__class__.__name__, err)

        is_radar = self.sensor_type in (RADAR_LABEL, ADV_RADAR_LABEL)
        tx_not_set = self.tx_power is NO_SETTING or self.tx_frequency is NO_SETTING
        if is_radar and tx_not_set:
            err = f"Sensor {self.id}: Radar transmit parameters not set: {object_config}"
            raise ConfigError(self.__class__.__name__, err)

        if self.host_type is GROUND_FACILITY_LABEL and self.station_keeping.routines:
            err = "Ground based sensors cannot perform station keeping"
            raise ConfigError(self.__class__.__name__, err)

    @property  # noqa: A003
    def id(self):  # noqa: A003 pylint: disable=invalid-name
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
    def lla_set(self):
        """bool: Boolean indication of whether this sensor has LLA settings."""
        return all((self.lat != NO_SETTING, self.lon != NO_SETTING, self.alt != NO_SETTING))

    @property
    def init_eci(self):
        """list: Six element list representing this target's initial ECI state vector."""
        return self._init_eci.setting  # pylint: disable=no-member

    @property
    def eci_set(self):
        """bool: Boolean indication of whether this sensor has ECI settings."""
        return self.init_eci != NO_SETTING

    @property
    def init_coe(self):
        """dict: Set of classical orbital elements (COE) describing the target's orbit.

        See :meth:`.ClassicalElements.fromConfig()` for rules on defining a set of classical orbital elements.
        """
        return self._init_coe.setting  # pylint: disable=no-member

    @property
    def coe_set(self):
        """bool: Indication of whether COEs are available for this target configuration."""
        return self.init_coe != NO_SETTING

    @property
    def init_eqe(self):
        """dict: Set of equinoctial orbital elements (EQE) describing the target's orbit.

        See :meth:`.EquinoctialElements.fromConfig()` for rules on defining a set of equinoctial orbital elements.
        """
        return self._init_eqe.setting  # pylint: disable=no-member

    @property
    def eqe_set(self):
        """bool: Indication of whether EQEs are available for this target configuration."""
        return self.init_eqe != NO_SETTING

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
    def field_of_view(self):
        """FieldOfViewConfig: visibility of this sensor."""
        return self._field_of_view  # pylint: disable=no-member

    @property
    def calculate_fov(self):
        """bool: decision to do FoV calcs with this sensor."""
        return self._calculate_fov.setting  # pylint: disable=no-member

    @calculate_fov.setter
    def calculate_fov(self, new_calc_fov: bool):
        """Set new Field of View.

        Args:
            new_calc_fov (``bool``): global FoV setting
        """
        self._calculate_fov = new_calc_fov

    # @field_of_view.setter
    # def field_of_view(self, new_field_of_view):
    #     """float: Set field of view of this sensor."""
    #     self._field_of_view = new_field_of_view

    @property
    def minimum_range(self):
        """float, int: minimum range visibility of this sensor."""
        return self._minimum_range.setting  # pylint: disable=no-member

    # @minimum_range.setter
    # def minimum_range(self, new_minimum_range):
    #     """float, int: Set minimum range visibility of this sensor."""
    #     self._minimum_range = new_minimum_range

    @property
    def maximum_range(self):
        """float, int: maximum range visibility of this sensor."""
        return self._maximum_range.setting  # pylint: disable=no-member

    # @maximum_range.setter
    # def maximum_range(self, new_maximum_range):
    #     """float, int: Set maximum range visibility of this sensor."""
    #     self._maximum_range = new_maximum_range

    @property
    def detectable_vismag(self):
        """float, int: maximum detectable visual magnitude of this sensor."""
        return self._detectable_vismag.setting  # pylint: disable=no-member

    # @detectable_vismag.setter
    # def detectable_vismag(self, new_detectable_vismag):
    #     """float, int: Set maximum detectable visual magnitude of this sensor."""
    #     self._detectable_vismag = new_detectable_vismag

    @property
    def tx_power(self):
        """float: Transmit power of radar sensor.

        Will only be set if :attr:`~.Observation.sensor_type` is `RADAR_LABEL` or `ADV_RADAR_LABEL`.
        """
        return self._tx_power.setting  # pylint: disable=no-member

    @property
    def tx_frequency(self):
        """float: Transmit frequency of radar sensor.

        Will only be set if :attr:`~.Observation.sensor_type` is `RADAR_LABEL` or `ADV_RADAR_LABEL`.
        """
        return self._tx_frequency.setting  # pylint: disable=no-member

    @property
    def mass(self):
        """float: Mass of RSO."""
        return self._mass.setting

    @property
    def visual_cross_section(self):
        """float: visual_cross_section of RSO."""
        return self._visual_cross_section.setting

    @property
    def reflectivity(self):
        """float: reflectivity of RSO."""
        return self._reflectivity.setting

    @property
    def station_keeping(self):
        """string: list of station keeping checks to perform.

        Default to type(None), asserted to be None if host_type is `GROUND_FACILITY_LABEL`.
        """
        return self._station_keeping  # pylint: disable=no-member


class FieldOfViewConfig(ConfigSection):
    """Field of View config class."""

    CONFIG_LABEL = "field_of_view"

    def __init__(self) -> None:
        """Initialize FieldOfViewConfig."""
        self._fov_shape = ConfigOption(
            "fov_shape",
            (str,),
            default="conic",
            valid_settings=(NO_SETTING,) + VALID_SENSOR_FOV_LABELS,
        )
        self._cone_angle = ConfigOption("cone_angle", (float,), default=1.0)  # degrees
        self._azimuth_angle = ConfigOption("azimuth_angle", (float,), default=1.0)  # degrees
        self._elevation_angle = ConfigOption("elevation_angle", (float,), default=1.0)  # degrees

    @property
    def nested_items(self):
        """``list``: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [self._fov_shape, self._cone_angle, self._azimuth_angle, self._elevation_angle]

    @property
    def fov_shape(self):
        """String: Type of Field of View being used."""
        return self._fov_shape.setting

    @property
    def cone_angle(self):
        """float: cone angle for `conic` Field of View (degrees)."""
        return self._cone_angle.setting

    @property
    def azimuth_angle(self):
        """float: horizontal angular resolution for `rectangular` Field of View (degrees)."""
        return self._azimuth_angle.setting

    @property
    def elevation_angle(self):
        """float: vertical angular resolution for `rectangular` Field of View (degrees)."""
        return self._elevation_angle.setting


class StationKeepingConfig(ConfigSection):
    """Configuration setting defining station keeping options."""

    CONFIG_LABEL = "station_keeping"
    """``str``: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.StationKeepingConfig`."""
        self._routines = ConfigOption(
            "routines",
            (list,),
            default=[],
            valid_settings=(NO_SETTING,) + VALID_STATION_KEEPING_ROUTINES,
        )

    @property
    def routines(self):
        """Return settings for routines."""
        return self._routines.setting

    @property
    def nested_items(self):
        """``list``: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [self._routines]

    def toJSON(self):
        """Convert station keeping config section to JSON-serializable format."""
        return {"routines": self.routines}
