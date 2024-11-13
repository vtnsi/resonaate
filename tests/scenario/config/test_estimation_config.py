from __future__ import annotations

# Standard Library Imports
from typing import Optional

# Third Party Imports
import pytest
from pydantic import TypeAdapter, ValidationError

# RESONAATE Imports
from resonaate.common.labels import (
    AdaptiveEstimationLabel,
    DynamicsLabel,
    InitialOrbitDeterminationLabel,
    ManeuverDetectionLabel,
    SequentialFilterLabel,
    StackingLabel,
)
from resonaate.scenario.config.estimation_config import (
    DEFAULT_IOD_OBSERVATION_SPACING,
    DEFAULT_MANEUVER_DETECTION_THRESHOLD,
    DEFAULT_MODEL_TIME_INTERVAL,
    DEFAULT_PRUNE_PERCENTAGE,
    DEFAULT_PRUNE_THRESHOLD,
    AdaptiveEstimationConfig,
    EstimationConfig,
    InitialOrbitDeterminationConfig,
    ManeuverDetectionConfig,
    SequentialFilterConfig,
)

AdaptiveEstimationConfigValidator = TypeAdapter(AdaptiveEstimationConfig)
"""TypeAdaptor: Helper class to validate :class:`.AdaptiveEstimationConfig` specification."""


ManeuverDetectionConfigValidator = TypeAdapter(ManeuverDetectionConfig)
"""TypeAdaptor: Helper class to validate :class:`.ManeuverDetectionConfig` specification."""


SequentialFilterConfigValidator = TypeAdapter(SequentialFilterConfig)
"""TypeAdaptor: Helper class to validate :class:`.SequentialFilterConfig` specification."""


def getIODConfigDict(
        name: InitialOrbitDeterminationLabel = InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL,
        minimum_observation_spacing: int = DEFAULT_IOD_OBSERVATION_SPACING,
) -> dict:
    """Return an IOD configuration dictionary based on the specified arguments."""
    return {
        "name": name,
        "minimum_observation_spacing": minimum_observation_spacing,
    }


def getAdaptiveConfigDict(
        name: AdaptiveEstimationLabel = AdaptiveEstimationLabel.SMM,
        orbit_determination: InitialOrbitDeterminationLabel = InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL,
        stacking_method: StackingLabel = StackingLabel.ECI_STACKING,
        model_interval: int = DEFAULT_MODEL_TIME_INTERVAL,
        observation_window: int = DEFAULT_MODEL_TIME_INTERVAL,
        prune_threshold: float = DEFAULT_PRUNE_THRESHOLD,
        prune_percentage: float = DEFAULT_PRUNE_PERCENTAGE,
) -> dict:
    """Return an adaptive estimation configuration dictionary based on the specified arguments."""
    return {
        "name": name,
        "orbit_determination": orbit_determination,
        "stacking_method": stacking_method,
        "model_interval": model_interval,
        "observation_window": observation_window,
        "prune_threshold": prune_threshold,
        "prune_percentage": prune_percentage,
    }


def getManeuverDetectionDict(
        name: ManeuverDetectionLabel = ManeuverDetectionLabel.STANDARD_NIS,
        threshold: float = DEFAULT_MANEUVER_DETECTION_THRESHOLD,
) -> dict:
    """Return a maneuver detection configuration dictionary based on the specified arguments."""
    return {
        "name": name,
        "threshold": threshold,
    }


def getSeqFilterDict(
        name: SequentialFilterLabel = SequentialFilterLabel.UKF,
        dynamics_model: DynamicsLabel = DynamicsLabel.SPECIAL_PERTURBATIONS,
        maneuver_detection: Optional[ManeuverDetectionConfig] = None,  # noqa: UP007
        adaptive_estimation: bool = False,
        initial_orbit_determination: bool = False,
) -> dict:
    """Return a sequential filter configuration dictionary based on the specified arguments."""
    return {
        "name": name,
        "dynamics_model": dynamics_model,
        "maneuver_detection": maneuver_detection,
        "adaptive_estimation": adaptive_estimation,
        "initial_orbit_determination": initial_orbit_determination,
    }


@pytest.mark.parametrize("iod_label", list(InitialOrbitDeterminationLabel))
def testCreateIODConfig(iod_label: InitialOrbitDeterminationLabel):
    """Validate that all IOD labels have a valid configuration."""
    _ = InitialOrbitDeterminationConfig(**getIODConfigDict(name=iod_label))


@pytest.mark.parametrize("iod_input", ["not iod", 123, None])
def testIODConfigBadInput(iod_input):
    """Validate that IOD config validation throws an error on invalid IOD labels."""
    with pytest.raises(ValidationError):
        _ = InitialOrbitDeterminationConfig(**getIODConfigDict(name=iod_input))


@pytest.mark.parametrize("spacing", [0, -1])
def testIODConfigBadSpacing(spacing):
    """Validate that IOD config validation throws an error on invalid observation spacing."""
    with pytest.raises(ValidationError):
        _ = InitialOrbitDeterminationConfig(**getIODConfigDict(minimum_observation_spacing=spacing))


@pytest.mark.parametrize("adaptive_label", list(AdaptiveEstimationLabel))
def testAdaptiveCreate(adaptive_label):
    """Validate that all adaptive estimation labels have a valid configuration."""
    _ = AdaptiveEstimationConfigValidator.validate_python(
        getAdaptiveConfigDict(name=adaptive_label),
    )


@pytest.mark.parametrize("iod_input", ["not iod", 123, None])
def testAdaptiveBadIOD(iod_input):
    """Validate that adaptive estimation config validation throws an error on invalid IOD labels."""
    with pytest.raises(ValidationError):
        _ = AdaptiveEstimationConfigValidator.validate_python(
            getAdaptiveConfigDict(orbit_determination=iod_input),
        )


@pytest.mark.parametrize("stacking_input", ["not stack", 123, None])
def testAdaptiveBadStacking(stacking_input):
    """Validate that adaptive estimation config validation throws an error on invalid stacking labels."""
    with pytest.raises(ValidationError):
        _ = AdaptiveEstimationConfigValidator.validate_python(
            getAdaptiveConfigDict(stacking_method=stacking_input),
        )


@pytest.mark.parametrize("gt0_field", ["model_interval", "observation_window"])
@pytest.mark.parametrize("test_value", [-1, 0])
def testAdaptiveBadGT0Fields(gt0_field, test_value):
    """Validate that adaptive estimation config validation throws and error for bad field values."""
    with pytest.raises(ValidationError):
        _ = AdaptiveEstimationConfigValidator.validate_python(
            getAdaptiveConfigDict(**{gt0_field: test_value}),
        )


@pytest.mark.parametrize("ratio_field", ["prune_threshold", "prune_percentage"])
@pytest.mark.parametrize("test_value", [-1, 0, 1])
def testAdaptiveBadRatioFields(ratio_field, test_value):
    """Validate that adaptive estimation config validation throws and error for bad field values."""
    with pytest.raises(ValidationError):
        _ = AdaptiveEstimationConfigValidator.validate_python(
            getAdaptiveConfigDict(**{ratio_field: test_value}),
        )


@pytest.mark.parametrize("detection_name", list(ManeuverDetectionLabel))
def testManeuverDetectCreate(detection_name: ManeuverDetectionLabel):
    """Validate that all maneuver detection labels have a valid configuration."""
    ManeuverDetectionConfigValidator.validate_python(
        getManeuverDetectionDict(name=detection_name),
    )


@pytest.mark.parametrize("detection_input", ["not detection", 123, None])
def testManeuverDetectBadName(detection_input):
    """Validate that maneuver detection config validation throws an error on invalid detection labels."""
    with pytest.raises(ValidationError):
        _ = ManeuverDetectionConfigValidator.validate_python(
            getManeuverDetectionDict(name=detection_input),
        )


@pytest.mark.parametrize("threshold", [-1, 0, 1])
def testManeuverDetectBadThreshold(threshold):
    """Validate that maneuver detection config validation throws and error for bad threshold."""
    with pytest.raises(ValidationError):
        _ = ManeuverDetectionConfigValidator.validate_python(
            getManeuverDetectionDict(threshold=threshold),
        )


@pytest.mark.parametrize("filter_name", list(SequentialFilterLabel))
def testSeqFilterCreate(filter_name: SequentialFilterLabel):
    """Validate that all sequential filter labels have a valid configuration."""
    SequentialFilterConfigValidator.validate_python(
        getSeqFilterDict(name=filter_name),
    )


@pytest.mark.parametrize("filter_input", ["not a filter", 123, None])
def testSeqFilterBadName(filter_input):
    """Validate that sequential filter config validation throws an error on invalid filter labels."""
    with pytest.raises(ValidationError):
        _ = SequentialFilterConfigValidator.validate_python(
            getSeqFilterDict(name=filter_input),
        )


def testEstimationConfigCreate():
    """Validate that a default estimation config validates properly."""
    cfg_dict = {
        "sequential_filter": getSeqFilterDict(),
    }
    _ = EstimationConfig(**cfg_dict)


def testEstimationAdaptMutex():
    """Validate that estimation config validation throws error when adaptive estimation and IOD are turned on."""
    cfg_dict = {
        "sequential_filter": getSeqFilterDict(
            adaptive_estimation=True,
            initial_orbit_determination=True,
        ),
    }
    with pytest.raises(ValidationError):
        _ = EstimationConfig(**cfg_dict)


def testEstimationAdaptMissing():
    """Validate that estimation config validation throws an error when adaptive estimation is on but no config is provided."""
    cfg_dict = {
        "sequential_filter": getSeqFilterDict(
            adaptive_estimation=True,
        ),
    }
    with pytest.raises(ValidationError):
        _ = EstimationConfig(**cfg_dict)


def testEstimationAdaptConfigOff():
    """Validate that estimation config validation throws a warning when adaptive estimation is off but a config is provided."""
    cfg_dict = {
        "sequential_filter": getSeqFilterDict(),
        "adaptive_filter": getAdaptiveConfigDict(),
    }
    with pytest.warns(UserWarning):
        _ = EstimationConfig(**cfg_dict)


def testEstimationIODMissing():
    """Validate that estimation config validation throws an error when IOD is on but no config is provided."""
    cfg_dict = {
        "sequential_filter": getSeqFilterDict(
            initial_orbit_determination=True,
        ),
    }
    with pytest.raises(ValidationError):
        _ = EstimationConfig(**cfg_dict)


def testEstimationIODConfigOff():
    """Validate that estimation config validation throws a warning when IOD is off but a config is provided."""
    cfg_dict = {
        "sequential_filter": getSeqFilterDict(),
        "initial_orbit_determination": getIODConfigDict(),
    }
    with pytest.warns(UserWarning):
        _ = EstimationConfig(**cfg_dict)
