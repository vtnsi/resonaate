"""Submodule defining the 'noise' configuration section.

To Do:
    - make sure valid settings for different types of noise are correct

"""
# Local Imports
from ...physics.noise import (
    CONTINUOUS_WHITE_NOISE_LABEL,
    DISCRETE_WHITE_NOISE_LABEL,
    SIMPLE_NOISE_LABEL,
)
from .base import ConfigOption, ConfigSection, ConfigValueError


class NoiseConfig(ConfigSection):
    """Configuration section defining several noise-based options."""

    CONFIG_LABEL = "noise"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    RNG_SEED_OS = "os"
    """str: Value to set :attr:`._random_seed.setting` to that indicates seeding the PRNG with the OS's entropy."""

    def __init__(self):
        """Construct an instance of a :class:`.NoiseConfig`."""
        self._init_position_std_km = ConfigOption("init_position_std_km", (float,), default=1e-3)
        self._init_velocity_std_km_p_sec = ConfigOption(
            "init_velocity_std_km_p_sec", (float,), default=1e-6
        )
        self._dynamics_noise_type = ConfigOption(
            "dynamics_noise_type",
            (str,),
            default=SIMPLE_NOISE_LABEL,
            valid_settings=(
                CONTINUOUS_WHITE_NOISE_LABEL,
                DISCRETE_WHITE_NOISE_LABEL,
                SIMPLE_NOISE_LABEL,
            ),
        )
        self._dynamics_noise_magnitude = ConfigOption(
            "dynamics_noise_magnitude", (float,), default=1e-20
        )
        self._filter_noise_type = ConfigOption(
            "filter_noise_type",
            (str,),
            default=CONTINUOUS_WHITE_NOISE_LABEL,
            valid_settings=(
                CONTINUOUS_WHITE_NOISE_LABEL,
                DISCRETE_WHITE_NOISE_LABEL,
                SIMPLE_NOISE_LABEL,
            ),
        )
        self._filter_noise_magnitude = ConfigOption(
            "filter_noise_magnitude", (float,), default=3.0e-14
        )
        self._random_seed = ConfigOption(
            "random_seed",
            (
                int,
                str,
            ),
            default=1,
        )

    def readConfig(self, raw_config):
        """Validate random seed value.

        Extend :meth:`.ConfigItem.readConfig()`
        """
        super().readConfig(raw_config)

        if isinstance(self._random_seed.setting, str):
            if self._random_seed.setting != self.RNG_SEED_OS:
                raise ConfigValueError(
                    self._random_seed.config_label,
                    self._random_seed.setting,
                    (self.RNG_SEED_OS, "or any int"),
                )

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [
            self._init_position_std_km,
            self._init_velocity_std_km_p_sec,
            self._dynamics_noise_type,
            self._dynamics_noise_magnitude,
            self._filter_noise_type,
            self._filter_noise_magnitude,
            self._random_seed,
        ]

    @property
    def init_position_std_km(self):
        """float: Standard deviation of initial RSO position estimate (km)."""
        return self._init_position_std_km.setting

    @property
    def init_velocity_std_km_p_sec(self):
        """float: Standard deviation of initial RSO velocity estimate (km/sec)."""
        return self._init_velocity_std_km_p_sec.setting

    @property
    def dynamics_noise_type(self):
        """str: String describing noise used in dynamics propagation."""
        return self._dynamics_noise_type.setting

    @property
    def dynamics_noise_magnitude(self):
        """float: 'Variance' of noise added in dynamics propagation."""
        return self._dynamics_noise_magnitude.setting

    @property
    def filter_noise_type(self):
        """str: String describing noise used in filter propagation."""
        return self._filter_noise_type.setting

    @property
    def filter_noise_magnitude(self):
        """float: 'Variance' of noise added in filter propagation."""
        return self._filter_noise_magnitude.setting

    @property
    def random_seed(self):
        """int|None: Psuedo-random number generator (PRNG) seed value.

        Setting this value to :attr:`.RNG_SEED_OS` will seed the PRNG with the OS's entropy.
        """
        if self._random_seed.setting == self.RNG_SEED_OS:
            return None
        return self._random_seed.setting
