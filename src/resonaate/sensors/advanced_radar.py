# Standard Library Imports
# Third Party Imports
from numpy import asarray
# RESONAATE Imports
from .measurements import getAzimuth, getElevation, getRange, getRangeRate
from .radar import Radar


class AdvRadar(Radar):
    """Advanced radar sensor class.

    The Advanced Radar Sensor Class (Radar) is used to model four dimensional radar sensors that
    take range, azimuth, elevation, and range rate measurements for each observation. This is a
    specialization of the :class:`.Radar` class, overriding methods for adding extra measurements
    into the observation.
    """

    @property
    def angle_measurements(self):
        """``np.ndarray``: Returns 4x1 boolean array of which measurements are angles."""
        return asarray([1, 1, 0, 0], dtype=bool)

    def getMeasurements(self, obs_sez_state, noisy=False):
        """Return the measurement state of the measurement.

        Args:
            obs_sez_state (``np.ndarray``): 6x1 SEZ observation vector from sensor to target (km; km/sec)
            noisy (``bool``, optional): whether measurements should include sensor noise. Defaults to ``False``.

        Returns:
            ``dict``: measurements made by the sensor

            :``"azimuth_rad"``: (``float``): azimuth angle measurement (radians)
            :``"elevation_rad"``: (``float``): elevation angle measurement (radians)
            :``"range_km"``: (``float``): range measurement (km)
            :``"range_rate_km_p_sec"``: (``float``): range rate measurement (km/sec)
        """
        measurements = {
            "azimuth_rad": getAzimuth(obs_sez_state),
            "elevation_rad": getElevation(obs_sez_state),
            "range_km": getRange(obs_sez_state),
            "range_rate_km_p_sec": getRangeRate(obs_sez_state),
        }
        if noisy:
            measurements["azimuth_rad"] += self.measurement_noise[0]
            measurements["elevation_rad"] += self.measurement_noise[1]
            measurements["range_km"] += self.measurement_noise[2]
            measurements["range_rate_km_p_sec"] += self.measurement_noise[3]

        return measurements
