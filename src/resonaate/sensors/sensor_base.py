# Standard Library Imports
from abc import ABCMeta, abstractmethod, abstractproperty
# Third Party Imports
from numpy import asarray, matmul, diagflat, sin, cos, arccos, real, fix, random, dot
from scipy.linalg import norm, sqrtm
# RESONAATE Imports
from .measurements import getAzimuth, getElevation, getRange
from ..common.utilities import getTypeString
from ..data.observation import Observation
from ..physics import constants as const
from ..physics.sensor_utils import lineOfSight
from ..physics.transforms.methods import getObservationVector


class Sensor(metaclass=ABCMeta):
    """Abstract base class for a generic Sensor object."""

    def __init__(self, az_mask, el_mask, r_matrix, diameter, efficiency, slew_rate, **sensor_args):
        """Construct a generic `Sensor` object.

        Args:
            az_mask (``list``): azimuth mask for visibility conditions
            el_mask (``list``): elevation mask for visibility conditions
            r_matrix (``np.ndarray``): measurement noise covariance matrix
            diameter (``float``): diameter of sensor dish (m)
            efficiency (``float``): efficiency percentage of the sensor
            slew_rate (``float``): maximum rotational speed of the sensor (deg/sec)
            sensor_args (``dict``): extra key word arguments for easy extension of the `Sensor` interface
        """
        self._az_mask = None
        self._el_mask = None
        self._r_matrix = None
        self.az_mask = const.DEG2RAD * az_mask
        self.el_mask = const.DEG2RAD * el_mask
        self.r_matrix = r_matrix
        self.aperture_area = const.PI * ((diameter / 2.0)**2)
        self.efficiency = efficiency
        self.slew_rate = const.DEG2RAD * slew_rate

        # Derived properties initialization
        self.exemplar = None
        self.time_last_ob = 0.0
        self.delta_boresight = 0.0
        self._host = None
        self.boresight = None
        self._current_target = None
        """``float``: For tracking the current target agent and help with debugging purposes."""
        self.min_detect = None
        self.max_range_aux = None
        self._sensor_args = sensor_args

    @abstractmethod
    def maximumRangeTo(self, viz_cross_section, tgt_eci_state):
        """Calculate the maximum possible range based on a target's visible area.

        Args:
            viz_cross_section (``float``): area of the target facing the sun (m^2)
            tgt_eci_state (``np.ndarray``): 6x1 ECI state vector of the target agent

        Returns:
            ``float``: maximum possible range to target at which this sensor can make valid observations (km)
        """
        raise NotImplementedError

    @abstractmethod
    def getMeasurements(self, obs_sez_state, noisy=False):
        """Return the measurement state of the measurement.

        Args:
            obs_sez_state (``np.ndarray``): 6x1 SEZ observation vector from sensor to target (km; km/sec)
            noisy (``bool``, optional): whether measurements should include sensor noise. Defaults to ``False``.

        Returns:
            ``dict``: measurements made by the sensor
        """
        raise NotImplementedError

    @abstractproperty
    def angle_measurements(self):
        """``np.ndarray``: Returns which measurements are angles as boolean values."""
        raise NotImplementedError

    def makeObservation(self, tgt_id, tgt_eci_state, viz_cross_section, noisy=False, check_viz=True):
        """Calculate the measurement data for a single observation.

        Args:
            tgt_id (``int``): simulation ID associated with current target
            tgt_eci_state (``np.ndarray``): 6x1 ECI state vector of the target (km; km/sec)
            viz_cross_section (``float``): visible cross-sectional area of the target (m^2)
            noisy (``bool``, optional): whether observation should include noisy measurements. Defaults to ``False``.
            check_viz (``bool``, optional): whether to check visibility constraints. Defaults to ``True``.

        Returns:
            ``tuple``: observation tuple

            : :class:`.Observation`: valid observation, or empty list (invalid observation)
            : ``np.ndarray``: boolean array signifying which measurements are angles
        """
        # Calculate common values
        self._current_target = tgt_id
        obs_sez_state = getObservationVector(self.host.ecef_state, tgt_eci_state)
        julian_date = self.host.julian_date_epoch

        # Construct observations
        observation = []
        if noisy:
            # Make a real observation once tasked -> add noise to the measurement
            if self.isVisible(tgt_eci_state, viz_cross_section, obs_sez_state):
                observation = Observation.fromSEZVector(
                    sensor_type=getTypeString(self),
                    sensor_id=self.host.simulation_id,
                    target_id=tgt_id,
                    julian_date=julian_date,
                    sez=obs_sez_state,
                    sensor_position=self.host.lla_state,
                    **self.getNoisyMeasurements(obs_sez_state)
                )
                self.boresight = obs_sez_state[:3] / norm(obs_sez_state[:3])
                self.time_last_ob = self.host.time

        elif check_viz:
            # Forecasting an observation for reward matrix purposes
            if self.isVisible(tgt_eci_state, viz_cross_section, obs_sez_state):
                observation = Observation.fromSEZVector(
                    sensor_type=getTypeString(self),
                    sensor_id=self.host.simulation_id,
                    target_id=tgt_id,
                    julian_date=julian_date,
                    sez=obs_sez_state,
                    sensor_position=self.host.lla_state,
                    **self.getMeasurements(obs_sez_state)
                )

        else:
            # Predicting/estimating observations for filtering
            observation = Observation.fromSEZVector(
                sensor_type=getTypeString(self),
                sensor_id=self.host.simulation_id,
                target_id=tgt_id,
                julian_date=julian_date,
                sez=obs_sez_state,
                sensor_position=self.host.lla_state,
                **self.getMeasurements(obs_sez_state)
            )

        return observation, self.angle_measurements

    def makeNoisyObservation(self, tgt_id, tgt_eci_state, viz_cross_section):
        """Calculate the measurement data for a single observation with noisy measurements.

        Args:
            tgt_id (``int``): simulation ID associated with current target
            tgt_eci_state (``np.ndarray``): 6x1 ECI state vector of the target (km; km/sec)
            viz_cross_section (``float``): visible cross-sectional area of the target (m^2)

        Returns:
            ``tuple``: noisy observation tuple

            : :class:`.Observation`: valid observation, or empty list (invalid observation)
            : ``np.ndarray``: boolean array signifying which measurements are angles
        """
        return self.makeObservation(tgt_id, tgt_eci_state, viz_cross_section, noisy=True)

    def getNoisyMeasurements(self, obs_sez_state):
        """Return noisy measurements.

        Args:
            obs_sez_state (``np.ndarray``): 6x1 SEZ observation vector from sensor to target (km; km/sec)

        Returns:
            ``dict``: noisy measurements made by the sensor
        """
        return self.getMeasurements(obs_sez_state, noisy=True)

    def isVisible(self, tgt_eci_state, viz_cross_section, obs_sez_state):
        """Determine if the target is in view of the sensor.

        Args:
            tgt_eci_state (``np.ndarray``): 6x1 ECI state vector of the target agent
            viz_cross_section (``float``): area of the target facing the sun (m^2)
            obs_sez_state (``np.ndarray``): 6x1 SEZ observation vector from sensor to target (km; km/sec)

        Returns:
            ``bool``: True if target is visible; False if target is not visible
        """
        # Early exit if target not in sensor's range, or a LOS doesn't exist
        if getRange(obs_sez_state) > self.maximumRangeTo(viz_cross_section, tgt_eci_state):
            return False
        elif not lineOfSight(tgt_eci_state[:3], self.host.eci_state[:3]):
            return False

        # Get the azimuth and elevation angles
        # [NOTE]: These are assumed to always be in the following ranges:
        #           - [0, 2*pi]
        #           - [-pi/2, pi/2]
        #   This should suffice to cover all necessary/required conditions
        azimuth = getAzimuth(obs_sez_state)
        elevation = getElevation(obs_sez_state)

        ## [NOTE]: When `obs_sez_state` and `self.boresight` are colinear, lost precision creates a value __slightly__
        ##          larger than 1.0 or smaller than -1.0. This results in domain errors with `numpy::arccos()`.
        ##          This statement ensures to round to either 1 or -1 appropriately.
        arg = dot(obs_sez_state[:3] / norm(obs_sez_state[:3]), self.boresight)
        if abs(arg) - 1.0 > 0.0:
            self.delta_boresight = arccos(fix(arg))
        else:
            self.delta_boresight = arccos(arg)

        # Check if you are able to slew to the new target
        if self.slew_rate * (self.host.time - self.time_last_ob) >= self.delta_boresight:
            # Check if the elevation is within sensor bounds
            if elevation <= self.el_mask[0] or elevation >= self.el_mask[1]:
                return False

            # [NOTE]: Azimuth check requires two versions:
            #   - az_0 <= az_1 for normal situations
            #   - az_0 > az_1 for when mask transits the 360deg/True North line
            if self.az_mask[0] <= self.az_mask[1]:
                if self.az_mask[0] <= azimuth <= self.az_mask[1]:
                    return True
            else:
                if azimuth >= self.az_mask[0] or azimuth <= self.az_mask[1]:
                    return True

        # Default: target satellite is not in view
        return False

    @property
    def az_mask(self):
        """``np.ndarray``: Returns the azimuth visibility mask."""
        return self._az_mask

    @az_mask.setter
    def az_mask(self, new_az_mask):
        """Ensure the azimuth mask is between [0, 2*pi].

        Args:
            az_mask (``np.ndarray``): azimuth mask for a particular sensor
        """
        if isinstance(new_az_mask[0], (float, int)):
            if new_az_mask.all() >= 0 and new_az_mask.all() <= 2 * const.PI:
                self._az_mask = new_az_mask.reshape(2)
            else:
                raise ValueError("Sensor: Invalid shape for az_mask property: {0}".format(new_az_mask.shape))
        else:
            raise TypeError("Sensor: Invalid type for az_mask property: {0}".format(type(new_az_mask[0])))

    @property
    def el_mask(self):
        """``np.ndarray``: Returns the elevation visibility mask."""
        return self._el_mask

    @el_mask.setter
    def el_mask(self, new_el_mask):
        """Ensure the elevation mask is between [-pi, pi].

        Args:
            el_mask (``np.ndarray``): elevation mask for a particular sensor
        """
        if isinstance(new_el_mask[0], (float, int)):
            if new_el_mask.all() >= -const.PI and new_el_mask.all() <= const.PI:
                self._el_mask = new_el_mask.reshape(2)
            else:
                raise ValueError("Sensor: Invalid shape for el_mask property: {0}".format(new_el_mask.shape))
        else:
            raise TypeError("Sensor: Invalid type for el_mask property: {0}".format(type(new_el_mask[0])))

    @property
    def r_matrix(self):
        """``np.ndarray``: Returns the measurement noise covariance matrix."""
        return self._r_matrix

    @r_matrix.setter
    def r_matrix(self, new_specs):
        """Ensure the measurement noise matrix is a square matrix.

        Args:
            ``np.ndarray``: measurement noise matrix for a particular sensor
        """
        if (new_specs.shape[1] == 1 or new_specs.shape[0] == 1):
            self._r_matrix = diagflat(new_specs.ravel())**2.0
        elif new_specs.shape[0] == new_specs.shape[1]:
            self._r_matrix = new_specs
        else:
            raise ValueError("Sensor: Invalid shape for r_matrix property: {0}".format(new_specs.shape))
        # Save the sqrt form of the R matrix to save computation time
        # [FIXME]: not initialized as `None` in `__init__` because variable not overwritten by this line...
        self._sqrt_noise_covar = real(sqrtm(self._r_matrix))  # pylint: disable=attribute-defined-outside-init

    @property
    def host(self):
        """:class:`.Agent`: Returns reference to agent that contains this sensor."""
        return self._host

    @host.setter
    def host(self, new_host):
        """Assign host to an attribute, and sets other relevant properties accordingly.

        Args:
            new_host (:class:`.Agent`): containing :class:`.SensingAgent` object
        """
        self._host = new_host
        self.time_last_ob = new_host.time

        if self.az_mask[0] < self.az_mask[1]:
            mid_az = self.az_mask[0] + (self.az_mask[1] - self.az_mask[0]) / 2.0
        else:
            mid_az = self.az_mask[1] + (self.az_mask[0] - self.az_mask[1]) / 2.0

        if self.el_mask[0] < self.el_mask[1]:
            mid_el = self.el_mask[0] + (self.el_mask[1] - self.el_mask[0]) / 2.0
        else:
            mid_el = self.el_mask[1] + (self.el_mask[0] - self.el_mask[1]) / 2.0

        self.boresight = asarray([cos(mid_el) * cos(mid_az), cos(mid_el) * sin(mid_az), sin(mid_el)])

    @property
    def measurement_noise(self):
        """``np.ndarray``: Returns randomly-generated measurement noise as v_k ~ N(0; r_matrix)."""
        return matmul(self._sqrt_noise_covar, random.randn(self._r_matrix.shape[0]))

    def getSensorData(self):
        """``dict``: Returns a this sensor's formatted information."""
        output_dict = {
            "name": self.host.name,
            "id": self.host.simulation_id,
            "covariance": self.r_matrix.tolist(),
            "slew_rate": self.slew_rate,
            "azimuth_range": self.az_mask.tolist(),
            "elevation_range": self.el_mask.tolist(),
            "efficiency": self.efficiency,
            "aperture_area": self.aperture_area,
            "sensor_type": getTypeString(self),
            "exemplar": self.exemplar.tolist()
        }
        if getTypeString(self.host) == "Spacecraft":
            output_dict["eci_state"] = self.host.truth_state.tolist()
            output_dict["host_type"] = "Spacecraft"
        else:
            latlon = self.host.lla_state
            output_dict["lat"] = latlon[0]
            output_dict["lon"] = latlon[1]
            output_dict["alt"] = latlon[2]
            output_dict["host_type"] = "GroundFacility"
        if getTypeString(self) == "Optical":
            pass
        else:
            output_dict["tx_power"] = self.tx_power  # pylint: disable=no-member
            output_dict["tx_frequency"] = 1 / self.wavelength  # pylint: disable=no-member

        return output_dict
