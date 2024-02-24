"""Hold common label types for easier importing."""

from __future__ import annotations

# Standard Library Imports
from enum import Enum, unique


@unique
class Explanation(Enum):
    """Enumeration for explanations of why an observation was missed."""

    VISIBLE = "Visible"
    MINIMUM_RANGE = "Minimum Range"
    MAXIMUM_RANGE = "Maximum Range"
    LINE_OF_SIGHT = "Line of Sight"
    AZIMUTH_MASK = "Azimuth Mask"
    ELEVATION_MASK = "Elevation Mask"
    VIZ_MAG = "Visual Magnitude"
    SOLAR_FLUX = "Solar Flux"
    LIMB_OF_EARTH = "Limb of the Earth"
    SPACE_ILLUMINATION = "Space Sensor Illumination"
    GROUND_ILLUMINATION = "Ground Sensor Illumination"
    RADAR_SENSITIVITY = "Radar Sensitivity - Max Range"
    FIELD_OF_VIEW = "Field of View"
    SLEW_DISTANCE = "Slew Rate/Distance to Target"
    GALACTIC_EXCLUSION = "Galactic Exclusion Zone"


class StateLabel:
    """Defines valid labels for state types."""

    ECI: str = "eci"
    """``str``: Earth-centered, inertial (ECI) state type."""

    COE: str = "coe"
    """``str``: classical orbital elements (COE) state type."""

    EQE: str = "eqe"
    """``str``: equinoctial orbital elements (EQE) state type."""

    LLA: str = "lla"
    """``str``: latitude (geodetic), longitude, altitude (LLA) state type."""


class PlatformLabel:
    """Defines valid labels for platform types."""

    GROUND_FACILITY: str = "ground_facility"
    """``str``: ground facility platform type."""

    SPACECRAFT: str = "spacecraft"
    """``str``: spacecraft platform type."""


class SensorLabel:
    """Defines valid labels for sensor types."""

    OPTICAL: str = "optical"
    """``str``: electro-optical sensor type."""

    RADAR: str = "radar"
    """``str``: radar sensor type."""

    ADV_RADAR: str = "adv_radar"
    """``str``: advanced radar sensor type."""


class FoVLabel:
    """Defines valid labels for Field of View types."""

    CONIC: str = "conic"
    """``str``: conic field of view type."""

    RECTANGULAR: str = "rectangular"
    """str: rectangular field of view type."""


class IntegratorLabel:
    """Defines valid labels for integrator methods."""

    RK45: str = "RK45"
    """str: Runge-Kutta integration method of order 5(4)."""

    DOP853: str = "DOP853"
    """``str``: Dormand-Prince integration method of order 8(5)."""


class DynamicsLabel:
    """Defines valid labels for satellite dynamics models."""

    TWO_BODY: str = "two_body"
    """str: two body satellite propagation model."""

    SPECIAL_PERTURBATIONS: str = "special_perturbations"
    """str: special perturbations satellite propagation model."""


class ManeuverDetectionLabel:
    """Defines valid labels for maneuver detection techniques."""

    STANDARD_NIS: str = "standard_nis"
    """``str``: regular normalized innovations squared (NIS) method."""

    SLIDING_NIS: str = "sliding_nis"
    """``str``: sliding normalized innovations squared (NIS) method."""

    FADING_MEMORY_NIS: str = "fading_memory_nis"
    """``str``: fading memory normalized innovations squared (NIS) method."""


class AdaptiveEstimationLabel:
    """Defines valid labels for adaptive estimation techniques."""

    GPB1: str = "gpb1"
    """``str``: generalized pseudo-Bayesian of first order adaptive estimator."""

    SMM: str = "smm"
    """``str``: static multiple module adaptive estimator."""


class SequentialFilterLabel:
    """Defines valid labels for sequential filter types."""

    UKF: str = "ukf"
    """``str``: unscented Kalman filter algorithm."""

    UNSCENTED_KALMAN_FILTER: str = "unscented_kalman_filter"
    """``str``: unscented Kalman filter algorithm."""


class InitialOrbitDeterminationLabel:
    """Defines valid labels for initial orbit determination (IOD) algorithms."""

    LAMBERT_BATTIN: str = "lambert_battin"
    """``str``: Lambert-Battin IOD algorithm."""

    LAMBERT_GAUSS: str = "lambert_gauss"
    """``str``: Lambert-Gauss IOD algorithm."""

    LAMBERT_UNIVERSAL: str = "lambert_universal"
    """``str``: Lambert-Universal IOD algorithm."""


class StackingLabel:
    """Defines valid labels for adaptive estimation state stacking techniques."""

    ECI_STACKING: str = "eci_stack"
    """``str``: ECI state stacking method."""


class NoiseLabel:
    """Defines valid labels for kinematic noise models."""

    CONTINUOUS_WHITE_NOISE: str = "continuous_white_noise"
    """``str``: continuous white noise model."""

    DISCRETE_WHITE_NOISE: str = "discrete_white_noise"
    """``str``: discrete white noise model."""

    SIMPLE_NOISE: str = "simple_noise"
    """``str``: simple noise model."""


class OrbitRegimeLabel:
    """Defines valid labels for orbital regimes."""

    LEO: str = "leo"
    """``str``: low Earth orbit (LEO) regime."""

    HEO: str = "heo"
    """``str``: highly elliptical orbit (HEO) regime."""

    MEO: str = "meo"
    """``str``: medium Earth orbit (MEO) regime."""

    GEO: str = "geo"
    """``str``: geosynchronous Earth orbit (GEO) regime."""


class MetricTypeLabel:
    """Defines valid labels for decision metric types."""

    INFORMATION: str = "information"
    """``str``: information-based metric type."""

    SENSOR: str = "sensor"
    """``str``: sensor metric type."""

    STABILITY: str = "stability"
    """``str``: stability metric type."""

    STATE: str = "state"
    """``str``: state metric type."""

    TARGET: str = "target"
    """``str``: target metric type."""

    UNCERTAINTY: str = "uncertainty"
    """``str``: uncertainty-based metric type."""
