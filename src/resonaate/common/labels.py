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


class StateLabel(str, Enum):
    """Defines valid labels for state types."""

    ECI: str = "eci"
    """``str``: Earth-centered, inertial (ECI) state type."""

    COE: str = "coe"
    """``str``: classical orbital elements (COE) state type."""

    EQE: str = "eqe"
    """``str``: equinoctial orbital elements (EQE) state type."""

    LLA: str = "lla"
    """``str``: latitude (geodetic), longitude, altitude (LLA) state type."""


class PlatformLabel(str, Enum):
    """Defines valid labels for platform types."""

    GROUND_FACILITY: str = "ground_facility"
    """``str``: ground facility platform type."""

    SPACECRAFT: str = "spacecraft"
    """``str``: spacecraft platform type."""


class SensorLabel(str, Enum):
    """Defines valid labels for sensor types."""

    OPTICAL: str = "optical"
    """``str``: electro-optical sensor type."""

    RADAR: str = "radar"
    """``str``: radar sensor type."""

    ADV_RADAR: str = "adv_radar"
    """``str``: advanced radar sensor type."""


class FoVLabel(str, Enum):
    """Defines valid labels for Field of View types."""

    CONIC: str = "conic"
    """``str``: conic field of view type."""

    RECTANGULAR: str = "rectangular"
    """str: rectangular field of view type."""


class IntegratorLabel(str, Enum):
    """Defines valid labels for integrator methods."""

    RK45: str = "RK45"
    """str: Runge-Kutta integration method of order 5(4)."""

    DOP853: str = "DOP853"
    """``str``: Dormand-Prince integration method of order 8(5)."""


class DynamicsLabel(str, Enum):
    """Defines valid labels for satellite dynamics models."""

    TWO_BODY: str = "two_body"
    """str: two body satellite propagation model."""

    SPECIAL_PERTURBATIONS: str = "special_perturbations"
    """str: special perturbations satellite propagation model."""


class GeopotentialModel(str, Enum):
    """Enumeration of geopotential models mapped to their corresponding filename."""

    EGM2008 = "egm2008.txt"
    """str: Filename corresponding to the Earth Gravitational Model 2008."""

    EGM96 = "egm96.txt"
    """str: Filename corresponding to the Earth Gravitational Model 1996."""

    GGM03S = "GGM03S.txt"
    """str: Filename corresponding to the GRACE Gravity Model 03."""

    JGM3 = "jgm3.txt"
    """str: Filename corresponding to the Joint Gravity Model 3."""


class ManeuverDetectionLabel(str, Enum):
    """Defines valid labels for maneuver detection techniques."""

    STANDARD_NIS: str = "standard_nis"
    """``str``: regular normalized innovations squared (NIS) method."""

    SLIDING_NIS: str = "sliding_nis"
    """``str``: sliding normalized innovations squared (NIS) method."""

    FADING_MEMORY_NIS: str = "fading_memory_nis"
    """``str``: fading memory normalized innovations squared (NIS) method."""


class AdaptiveEstimationLabel(str, Enum):
    """Defines valid labels for adaptive estimation techniques."""

    GPB1: str = "gpb1"
    """``str``: generalized pseudo-Bayesian of first order adaptive estimator."""

    SMM: str = "smm"
    """``str``: static multiple module adaptive estimator."""


class SequentialFilterLabel(str, Enum):
    """Defines valid labels for sequential filter types."""

    UKF: str = "ukf"
    """``str``: unscented Kalman filter algorithm."""

    UNSCENTED_KALMAN_FILTER: str = "unscented_kalman_filter"
    """``str``: unscented Kalman filter algorithm."""

    GPF: str = "gpf"
    """``str``: genetic particle filter algorithm."""

    GENETIC_PARTICLE_FILTER: str = "genetic_particle_filter"
    """``str``: genetic particle filter algorithm."""


class InitialOrbitDeterminationLabel(str, Enum):
    """Defines valid labels for initial orbit determination (IOD) algorithms."""

    LAMBERT_BATTIN: str = "lambert_battin"
    """``str``: Lambert-Battin IOD algorithm."""

    LAMBERT_GAUSS: str = "lambert_gauss"
    """``str``: Lambert-Gauss IOD algorithm."""

    LAMBERT_UNIVERSAL: str = "lambert_universal"
    """``str``: Lambert-Universal IOD algorithm."""


class StackingLabel(str, Enum):
    """Defines valid labels for adaptive estimation state stacking techniques."""

    ECI_STACKING: str = "eci_stack"
    """``str``: ECI state stacking method."""


class NoiseLabel(str, Enum):
    """Defines valid labels for kinematic noise models."""

    CONTINUOUS_WHITE_NOISE: str = "continuous_white_noise"
    """``str``: continuous white noise model."""

    DISCRETE_WHITE_NOISE: str = "discrete_white_noise"
    """``str``: discrete white noise model."""

    SIMPLE_NOISE: str = "simple_noise"
    """``str``: simple noise model."""


class OrbitRegimeLabel(str, Enum):
    """Defines valid labels for orbital regimes."""

    LEO: str = "leo"
    """``str``: low Earth orbit (LEO) regime."""

    HEO: str = "heo"
    """``str``: highly elliptical orbit (HEO) regime."""

    MEO: str = "meo"
    """``str``: medium Earth orbit (MEO) regime."""

    GEO: str = "geo"
    """``str``: geosynchronous Earth orbit (GEO) regime."""


class StationKeepingRoutine(str, Enum):
    """Defines valid labels for station keeping routines."""

    GEO_NS = "GEO NS"
    """``str``: Station keeping routine to keep GEO orbit stable in north-south direction."""

    GEO_EW = "GEO EW"
    """``str``: Station keeping routine to keep GEO orbit stable in east-west direction."""

    LEO = "LEO"
    """``str``: Station keeping routine to keep LEO orbit stable."""


class DecisionLabel(str, Enum):
    """Defines valid labels for decision making algorithms."""

    MUNKRES: str = "MunkresDecision"
    """``str``: :class:`.MunkresDecision` decision making algorithm.

    See Also:
        :class:`.resonaate.tasking.decisions.MunkresDecision`
    """

    MYOPIC_NAIVE_GREEDY: str = "MyopicNaiveGreedyDecision"
    """``str``: :class:`.MyopicNaiveGreedyDecision` decision making algorithm.

    See Also:
        :class:`.resonaate.tasking.decisions.MyopicNaiveGreedyDecision`
    """

    RANDOM: str = "RandomDecision"
    """``str``: :class:`.RandomDecision` decision making algorithm.

    See Also:
        :class:`.resonaate.tasking.decisions.RandomDecision`
    """

    ALL_VISIBLE: str = "AllVisibleDecision"
    """``str``: :class:`.AllVisibleDecision` decision making algorithm.

    See Also:
        :class:`.resonaate.tasking.decisions.AllVisibleDecision`
    """


class RewardLabel(str, Enum):
    """Defines valid labels for metric-based reward computation."""

    COST_CONSTRAINED: str = "CostConstrainedReward"
    """``str``: :class:`.CostConstrainedReward` reward computation class.

    See Also:
        :class:`.resonaate.tasking.rewards.CostConstrainedReward`
    """

    SIMPLE_SUM: str = "SimpleSummationReward"
    """``str``: :class:`.SimpleSummationReward` reward computation class.

    See Also:
        :class:`.resonaate.tasking.rewards.SimpleSummationReward`
    """

    COMBINED: str = "CombinedReward"
    """``str``: :class:`.CombinedReward` reward computation class.

    See Also:
        :class:`.resonaate.tasking.rewards.CombinedReward`
    """


class MetricTypeLabel(str, Enum):
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


class MetricLabel(str, Enum):
    """Defines valid labels for reward metric instances."""

    FISHER_INFO: str = "FisherInformation"
    """``str``: :class:`.FisherInformation` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.FisherInformation`
    """

    SHANNON_INFO: str = "ShannonInformation"
    """``str``: :class:`.ShannonInformation` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.ShannonInformation`
    """

    KL_DIVERGENCE: str = "KLDivergence"
    """``str``: :class:`.KLDivergence` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.KLDivergence`
    """

    POS_COV_TRACE: str = "PositionCovarianceTrace"
    """``str``: :class:`.PositionCovarianceTrace` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.PositionCovarianceTrace`
    """

    VEL_COV_TRACE: str = "VelocityCovarianceTrace"
    """``str``: :class:`.VelocityCovarianceTrace` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.VelocityCovarianceTrace`
    """

    POS_COV_DET: str = "PositionCovarianceDeterminant"
    """``str``: :class:`.PositionCovarianceDeterminant` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.PositionCovarianceDeterminant`
    """

    VEL_COV_DET: str = "VelocityCovarianceDeterminant"
    """``str``: :class:`.VelocityCovarianceDeterminant` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.VelocityCovarianceDeterminant`
    """

    POS_MAX_EIGEN: str = "PositionMaxEigenValue"
    """``str``: :class:`.PositionMaxEigenValue` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.PositionMaxEigenValue`
    """

    VEL_MAX_EIGEN: str = "VelocityMaxEigenValue"
    """``str``: :class:`.VelocityMaxEigenValue` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.VelocityMaxEigenValue`
    """

    POS_COV_REDUC: str = "PositionCovarianceReduction"
    """``str``: :class:`.PositionCovarianceReduction` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.PositionCovarianceReduction`
    """

    VEL_COV_REDUC: str = "VelocityCovarianceReduction"
    """``str``: :class:`.VelocityCovarianceReduction` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.VelocityCovarianceReduction`
    """

    RANGE: str = "Range"
    """``str``: :class:`.Range` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.Range`
    """

    SLEW_DIST_MIN: str = "SlewDistanceMinimization"
    """``str``: :class:`.SlewDistanceMinimization` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.SlewDistanceMinimization`
    """

    SLEW_DIST_MAX: str = "SlewDistanceMaximization"
    """``str``: :class:`.SlewDistanceMaximization` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.SlewDistanceMaximization`
    """

    SLEW_TIME_MIN: str = "SlewTimeMinimization"
    """``str``: :class:`.SlewTimeMinimization` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.SlewTimeMinimization`
    """

    SLEW_TIME_MAX: str = "SlewTimeMaximization"
    """``str``: :class:`.SlewTimeMaximization` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.SlewTimeMaximization`
    """

    TIME_SINCE_OBS: str = "TimeSinceObservation"
    """``str``: :class:`.TimeSinceObservation` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.TimeSinceObservation`
    """

    LYAPUNOV_STABILITY: str = "LyapunovStability"
    """``str``: :class:`.LyapunovStability` reward metric class.

    See Also:
        :class:`.resonaate.tasking.metrics.LyapunovStability`
    """
