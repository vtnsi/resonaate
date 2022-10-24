(ref-cfg-top)=

# Config Specification

This document contains the configuration format specification.
Specifically, it defines the format and contents of the scenario configuration file, and what is required versus optional.
RESONAATE simulations are initialized and started via the {class}`.Scenario` class which contains all relevant information and the public API.
There are two main ways to initialize RESONAATE:

1. Pass a fully constructed JSON object (as a Python {class}`dict`) to {func}`.buildScenarioFromConfigDict()`.
1. Pass a filepath to {func}`.buildScenarioFromConfigFile()` which points to a main scenario configuration JSON file.

The filepath method is preferred because it allows engines, targets, and sensors to be defined in separate files from the main configuration file.

______________________________________________________________________

<!-- TOC formatted for sphinx -->

```{contents} Table of Contents
---
depth: 2
backlinks: none
local:
---
```

______________________________________________________________________

```{rubric} Format Changelog
```

- 2022-07-20: RESONAATE v1.4.0
- 2022-06-06: RESONAATE v1.4.0
- 2022-03-04: RESONAATE v1.3.0
- 2021-08-10: RESONAATE v1.1.1
- 2021-01-22: RESONAATE v1.0.0
- 2020-10-16: RESONAATE v0.9.0

______________________________________________________________________

(ref-cfg-sec-file-format)=

## Config File Formats

The main way RESONAATE simulations are configured is by passing JSON configuration files to  {func}`.buildScenarioFromConfigFile()`.
This class method will properly handle parsing the multiple configuration files, combining them into a single configuration dictionary, validating the configuration format and fields, and returning a valid {class}`.Scenario` object.
If users simply wish to construct the formatted configuration dictionary, using the static method {func}`.buildScenarioFromConfigFile()` will properly handle the required logic.
This section describes how the configuration files are expected to be structured, formatted, and organized.

There are four main simulation configuration files that RESONAATE uses:

1. Main configuration file
   - Includes scenario-wide configuration values
   - Points to engine configuration file(s)
1. Tasking engine configuration file
   - Includes definition of tasking algorithm
   - Points to sensor & target set files associated with this engine
1. Target set configuration file
   - Includes target parameters & initial state information
1. Sensor set configuration file
   - Includes sensor parameters & initial state information

(ref-cfg-subsec-main-file)=

### Main Config File

The main JSON configuration file must be defined as follows (see {ref}`ref-cfg-sec-object-defs` for details):

```python
{
    "time": TimeConfig,                     # Req: scenario time properties
    "estimation": EstimationConfig,         # Req: filter types and parameters
    "engines_files": [str, ...],            # Req: relative filepath(s) to tasking engine(s)
    "noise": NoiseConfig,                   # Opt: noise characteristics
    "propagation": PropagationConfig,       # Opt: defines how RSOs are propagated
    "geopotential": GeopotentialConfig,     # Opt: Earth geopotential model
    "perturbations": PerturbationsConfig,   # Opt: orbital perturbations
    "observation": ObservationConfig,       # Opt: observation details
    "events": [EventConfig, ...],           # Opt: discrete events that occur during the scenario
}
```

Separating the tasking engine configurations into separate files improves the organization and flexibility users have with defining configuration files when running many scenarios.
Instead of defining the tasking engine parameters, lists of target objects, and list of sensor objects all in the main file, the new fields point to separate JSON files which include only specifications for that tasking engine.
This allows users to quickly change between different configurations in order to produce different simulation scenarios or test new behavior.

For example, if the configuration below was in `/app/init.json`, it would point to files at `/app/engines/taskable.json` and `/app/engines/all_visible.json`, respectively.

```python
{
    "time": {...},
    "estimation": {...},
    "engines_files": ["engines/taskable.json", "engines/all_visible.json"],
    "noise": {...},
    "propagation": {...},
    "geopotential": {...},
    "perturbations": {...},
    "observation": {...},
    "events": [...],
}
```

If using {func}`.buildScenarioFromConfigDict()` instead, the `"engines"` field needs to be pre-resolved:

```python
{
    "time": {...},
    "estimation": {...},
    "engines": [EngineConfig, ...],
    "noise": {...},
    "propagation": {...},
    "geopotential": {...},
    "perturbations": {...},
    "observation": {...},
    "events": [...],
}
```

The top-level configuration object is defined by {class}`.ScenarioConfig`.

(ref-cfg-subsec-engine-file)=

### Tasking Engine Config File

Only a single tasking engine configuration is required to be specified in the `"engines"` list, but users may include several.
Using more than one tasking engine allows different sensors to be tasked in different manners (and possibly against different target sets).

Passing the example `/app/init.json` main configuration file from {ref}`ref-cfg-subsec-main-file` to {func}`buildScenarioFromConfigFile()` would automatically read the files defined in the `"engines"` field.
Each of those files would then have the following format:

```python
{
    "reward": RewardConfig,         # Req: reward function and its metrics
    "decision": DecisionConfig,     # Req: algorithm used to optimize the reward matrix
    "target_file": str,             # Req: relative path to JSON file defining target agents
    "sensor_file": str,             # Req: relative path to JSON file defining sensor agents
}
```

Where the {class}`.RewardConfig` and {class}`.DecisionConfig` are defined in {ref}`ref-cfg-subsubsec-reward-object` and {ref}`ref-cfg-subsubsec-decision-object`, respectively.
Also, `"target_file"` and `"sensor_file"` refer to JSON files defining the sets of {class}`.TargetAgentConfig` and {class}`.SensingAgentConfig`, respectively.
More detail on the are provided in the {ref}`ref-cfg-subsec-target-object` and {ref}`ref-cfg-subsec-sensor-object` sections.
These filepath definitions are defined relative to the main configuration file (parent of this file).

For example, if the main config file was in `/app/init.json`, and if it pointed to the tasking engine config file defined below (located at `/app/engines/taskable.json`), then the engine config would point to target and sensor files at `/app/targets/leo_only.json` and `/app/sensors/complete_ssn.json`, respectively.

```python
{
    "reward": {...},
    "decision": {...},
    "target_file": "targets/leo_only.json",
    "sensor_file": "sensors/complete_ssn.json",
}
```

If using {func}`.buildScenarioFromConfigDict()` instead, the `"targets"` & `"sensors"` fields need to be pre-resolved:

```python
{
    "reward": {...},
    "decision": {...},
    "targets": [TargetAgentConfig, ...],
    "sensors": [SensingAgentConfig, ...],
}
```

The engine configuration object is defined by {class}`.EngineConfig`, and they are stored in the `"engines"` field as a {class}`.ConfigObjectList`.

(ref-cfg-subsec-target-file)=

### Target Set Config File

Each tasking engine configuration file must point to a target set configuration file for which the engine is tasked to track.
The set of targets is allowed to overlap with target sets of other tasking engines.
The corresponding target set configuration file will have the following format:

```python
[
    TargetAgentConfig,  # Req: object(s) defining target agents
    ...,
]
```

where {class}`.TargetAgentConfig` is a target object as defined in {ref}`ref-cfg-subsec-target-object`.

(ref-cfg-subsec-sensor-file)=

### Sensor Set Config File

Each tasking engine configuration file must point to a sensor set configuration file for which the engine can task.
The set of sensors cannot overlap with sensors from other tasking engines, i.e., engines' sensor sets are mutually exclusive.
The corresponding sensor set configuration file will have the following format:

```python
[
    SensingAgentConfig,  # Req: object(s) defining sensor agents
    ...,
]
```

where {class}`.SensingAgentConfig` is a sensor object as defined in {ref}`ref-cfg-subsec-sensor-object`.

(ref-cfg-sec-object-defs)=

## Config Object Definitions

This section goes over the JSON object definitions that satisfy the RESONAATE configuration specification.

The definition of the main configuration file is as follows:

```python
{
    "time": TimeConfig,                     # Req: scenario time properties
    "estimation": EstimationConfig,         # Req: filter types and parameters
    "engines_files": [str, ...],            # Req: relative filepath(s) to tasking engine(s)
    "noise": NoiseConfig,                   # Opt: noise characteristics
    "propagation": PropagationConfig,       # Opt: defines how RSOs are propagated
    "geopotential": GeopotentialConfig,     # Opt: Earth geopotential model
    "perturbations": PerturbationsConfig,   # Opt: orbital perturbations
    "observation": ObservationConfig,       # Opt: observation details
    "events": [EventConfig, ...],           # Opt: discrete events that occur during the scenario
}
```

(ref-cfg-subsec-time-object)=

### TimeConfig

This is a required field defining global scenario time properties.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.time_config

.. autoclass:: TimeConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"time": {
    "start_timestamp": <ISO 8601 timestamp>,    # Required
    "stop_timestamp": <ISO 8601 timestamp>,     # Required
    "physics_step_sec": int,                    # Optional
    "output_step_sec": int,                     # Optional
}
```

(ref-cfg-subsec-estimation-object)=

### EstimationConfig

This is a required field defining estimation techniques used to track the targets during the simulation.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.estimation_config

.. autoclass:: EstimationConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"estimation": {
    "sequential_filter": SequentialFilterConfig,  # Required
    "adaptive_filter": AdaptiveEstimationConfig,  # Optional
    "initial_orbit_determination": InitialOrbitDeterminationConfig,  # Optional
}
```

#### SequentialFilterConfig

This is a required field in `"estimation"` defining the nominal sequential filter algorithm that tracks the targets during the simulation.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.estimation_config

.. autoclass:: SequentialFilterConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"estimation": {
    "name":                         str,                      # Required
    "dynamics_model":               str,                      # Optional
    "maneuver_detection":           ManeuverDetectionConfig,  # Optional
    "adaptive_estimation":          bool,                     # Optional
    "initial_orbit_determination":  bool,                     # Optional
    "parameters":                   dict,                     # Optional
}
```

##### ManeuverDetectionConfig

This is an optional field in `"sequential_filter"` defining the maneuver detection technique that tests for maneuvers during the estimation algorithm.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.estimation_config

.. autoclass:: ManeuverDetectionConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"maneuver_detection": {
    "name":       str,    # Required
    "threshold":  float,  # Optional
    "parameters": dict,   # Optional
}
```

#### AdaptiveEstimationConfig

This is an optional field in `"estimation"` defining the adaptive estimation technique that is used if a maneuver is detected.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.estimation_config

.. autoclass:: AdaptiveEstimationConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"adaptive_filter": {
    "name":                 str,    # Required
    "orbit_determination":  str,    # Optional
    "stacking_method":      str,    # Optional
    "model_interval":       int,    # Optional
    "observation_window":   int,    # Optional
    "prune_threshold":      float,  # Optional
    "prune_percentage":     float,  # Optional
    "parameters":           dict,   # Optional
}
```

#### InitialOrbitDeterminationConfig

This is an optional field in `"estimation"` defining the initial orbi technique that is used if a maneuver is detected.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.estimation_config

.. autoclass:: InitialOrbitDeterminationConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"initial_orbit_determination": {
    "name":                          str,    # Optional
    "minimum_observation_spacing":   int,    # Optional
}
```

(ref-cfg-subsec-engine-object)=

### EngineConfig

Required list of string paths pointing tasking engine configuration definitions.
The paths in this list are defined relative to the **main** configuration file.

The definition of the tasking engine configuration file is as follows:

```python
{
    "reward": RewardConfig,         # Required
    "decision": DecisionConfig,     # Required
    "target_file": str,             # Required
    "sensor_file": str,             # Required
}
```

If using {func}`.buildScenarioFromConfigDict()` instead, the fields need to pre-resolved:

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.engine_config

.. autoclass:: EngineConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
[
    {
    "reward": RewardConfig,               # Required
    "decision": DecisionConfig,           # Required
    "targets": [TargetConfig, ...],       # Required
    "sensors": [SensingAgentConfig, ...], # Required
    },
    ...
]
```

(ref-cfg-subsubsec-decision-object)=

#### DecisionConfig

Required field in {ref}`ref-cfg-subsec-engine-object` defining the decision algorithm used to optimize the reward matrix for this tasking engine.
It is **highly** recommended that users simply set `"name": "MunkresDecision"` unless they understand the differences.
Please refer to the {mod}`~.tasking.decisions` sub-package for more information.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.decision_config

.. autoclass:: DecisionConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"decision": {
    "name": str,        # Required
    "parameters": dict, # Optional
}
```

(ref-cfg-subsubsec-reward-object)=

#### RewardConfig

Required field in {ref}`ref-cfg-subsec-engine-object` defining the reward algorithm and the metrics it uses for this tasking engine.
It is **highly** recommended that users implement the recommended values unless they understand the differences.
Please refer to the {mod}`~.tasking.rewards` and {mod}`~.tasking.metrics` sub-packages for more information.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.reward_config

.. autoclass:: RewardConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"decision": {
    "name": str,                      # Required
    "metrics": [MetricConfig, ...],   # Required
    "parameters": dict,               # Optional
}
```

(ref-cfg-subsubsec-metric-object)=

#### MetricConfig

Required list of objects to include in the `"metrics"` field of the {ref}`ref-cfg-subsubsec-reward-object`.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.reward_config

.. autoclass:: MetricConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"decision": {
    "name": str,        # Required
    "parameters": dict, # Optional
}
```

(ref-cfg-subsec-noise-object)=

### NoiseConfig

Optional object defining simulation noise characteristics.
See {mod}`~.physics.noise` for details on different types of noise/uncertainty.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.noise_config

.. autoclass:: NoiseConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"noise": {
    "init_position_std_km": float,        # Optional
    "init_velocity_std_km_p_sec": float,  # Optional
    "filter_noise_type": str,             # Optional
    "filter_noise_magnitude": float,      # Optional
    "random_seed": str | int,             # Optional
}
```

(ref-cfg-subsec-propagation-object)=

### PropagationConfig

Optional object defining how RSOs are propagated.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.propagation_config

.. autoclass:: PropagationConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"propagation": {
    "propagation_model": str,             # Optional
    "integration_method": str,            # Optional
    "station_keeping": bool,              # Optional
    "target_realtime_propagation": bool,  # Optional
    "sensor_realtime_propagation": bool,  # Optional
    "truth_simulation_only": bool,        # Optional
}
```

(ref-cfg-subsec-geopotential-object)=

### ObservationConfig

Optional object defining observation behavior preferences.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.observation_config

.. autoclass:: ObservationConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"observation": {
    "background": bool,              # Optional
    "realtime_observation": bool,    # Optional
}
```

### GeopotentialConfig

Optional object defining the Earth geopotential model.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.geopotential_config

.. autoclass:: GeopotentialConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"geopotential": {
    "model": str,   # Optional
    "degree": int,  # Optional
    "order": int,   # Optional
}
```

(ref-cfg-subsec-perturbation-object)=

### PerturbationsConfig

Optional object defining orbital perturbations to include.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.perturbations_config

.. autoclass:: PerturbationsConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"perturbations": {
    "third_bodies": [str, ...],         # Optional
    "solar_radiation_pressure": bool,   # Optional
    "general_relativity": bool,         # Optional
}
```

(ref-cfg-subsec-target-object)=

### TargetAgentConfig

Target agents' initial states are assumed to be defined at the epoch defined by `"start_timestamp"` in {ref}`ref-cfg-subsec-time-object`.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.agent_configs

.. autoclass:: TargetAgentConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
[
    {
        "sat_num": int,                           # Required
        "sat_name": str,                          # Required
        "visual_cross_section": float,            # Optional
        "mass": float,                            # Optional
        "reflectivity": float,                    # Optional
        "station_keeping": StationKeepingConfig,  # Optional
        "init_eci": [float, ...],                 # Optional
        "init_coe": dict,                         # Optional
        "init_eqe": dict,                         # Optional
    },
    ...
]
```

There are multiple ways to define a target agent's initial state (all fields are required for each version):

1. ECI state vector
   ```python
   <target_obj>: {
       ...,
       # J2000 initial state vector defined at "start_timestamp"
       "init_eci": [
           # ECI "x", "y", and "z" positions  (km)
           float, float, float,
           # ECI "x", "y", and "z" velocities (km/sec)
           float, float, float,
       ],
   }
   ```
1. Classical orbital elements (COE), see {ref}`ref-cfg-subsec-coe-object`
   ```python
   <target_obj>: {
       ...,
       # COE object defined at "start_timestamp"
       "init_coe": dict,
   }
   ```
1. Equinoctial orbital elements (EQE), see {ref}`ref-cfg-subsec-eqe-object`
   ```python
   <target_obj>: {
       ...,
       # EQE object defined at "start_timestamp"
       "init_eqe": dict,
   }
   ```

(ref-cfg-subsec-sensor-object)=

### SensingAgentConfig

The default sensor network is defined in "SSN Specifications OpenSource v1.8".
Sensor agents can be defined as `"GroundFacility"` for ground-based sensors or `"Spacecraft"` for space-based sensors. Also, each sensing agents can contain a sensor of the following types: `"Optical"`, `"Radar"`, `"AdvRadar"`.

#### Common Sensor Fields

These are the required fields defined for all types of sensor objects.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.agent_configs

.. autoclass:: SensingAgentConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
[
    {
        "id": int,                                # Required
        "name": str,                              # Required
        "host_type": str,                         # Required
        "sensor_type": str,                       # Required
        "azimuth_range": [float, float],          # Required
        "elevation_range": [float, float],        # Required
        "covariance": [[float, ...], ...],        # Required
        "aperture_area": float,                   # Required
        "efficiency": float,                      # Required
        "slew_rate": float,                       # Required
        "exemplar": list[float, float],           # Required
        "background_observations": bool,                    # Optional
        "detectable_vismag": float,               # Optional
        "minimum_range": float,                   # Optional
        "maximum_range": float,                   # Optional
        "visual_cross_section": float,            # Optional
        "mass": float,                            # Optional
        "reflectivity": float,                    # Optional
        "field_of_view": FieldOfViewConfig,       # Optional
        "station_keeping": StationKeepingConfig,  # Optional
    },
    ...
]
```

#### Field of View

Defines type and parameters of `"field_of_view"` field.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.agent_configs

.. autoclass:: FieldOfViewConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"field_of_view": {
    "fov_shape": str,           # Optional
    "cone_angle": float,        # Optional
    "azimuth_angle": float,     # Optional
    "elevation_angle": float,   # Optional
}
```

#### Sensor Types

Different types of sensors (`"sensor_type"` field) require different extra fields in the sensor object.

1. `"Radar"` and `"AdvRadar"` require:
   ```python
   <sensor_obj>: {
       ...,
       "tx_power": float,      # Required
       "tx_frequency": float,  # Required
   }
   ```

Also, the shape/size of the `"covariance"` field depends on the `"sensor_type"` field:

- `"Optical"`: 2x2 measurement uncertainty
  ```python
  # a: azimuth std in radians  # b: elevation std in radians
  [[a ^ 2, ab], [ab, b ^ 2]]
  ```
- `"Radar"` and `"AdvRadar"`: 4x4 measurement uncertainty
  ```python
  [
      [a ^ 2, ab, ac, ad],  # a: azimuth std in radians
      [ab, b ^ 2, bc, bd],  # b: elevation std in radians
      [ac, bc, c ^ 2, cd],  # c: range std in kilometers
      [ad, bd, cd, d ^ 2],  # d: range rate std in kilometers/seconds
  ]
  ```

#### Sensing Agent Types

Different types of sensor agents (`"host_type"` field) require different extra fields in the sensor object.

1. `"GroundFacility"` requires
   ```python
   <sensor_obj>: {
       ...,
       # Defines sensor's terrestrial location at "start_timestamp"
       "lat": float, # Geodetic latitude, (rad)
       "lon": float, # Geodetic longitude, (rad)
       "alt": float, # Height above ellipsoid, (km)
   }
   ```
1. `"Spacecraft"` requires one of the following options to describe its initial state:
   - `"init_eci"` for defining the state in ECI (J2000) position and velocity
     ```python
     <sensor_obj>: {
         ...,
         # Defines satellite J2000 (ECI) state at "start_timestamp"
         "init_eci": [
             float, float, float, # "x", "y", & "z" positions (km)
             float, float, float, # "x", "y", & "z" velocities (km/sec)
         ]
     }
     ```
   - `"init_coe"` for defining an orbit via COEs, see {ref}`ref-cfg-subsec-coe-object`
     ```python
     <sensor_obj>: {
         ...,
         # COE object defined at "start_timestamp"
         "init_coe": <coe_object>,
     }
     ```
   - `"init_eqe"` for defining an orbit via EQEs, see {ref}`ref-cfg-subsec-eqe-object`
     ```python
     <sensor_obj>: {
         ...,
         # EQE object defined at "start_timestamp"
         "init_eqe": <eqe_object>,
     }
     ```

(ref-cfg-subsec-coe-object)=

### COE Config

Note that there are several realizations of COE sets.
An orbit can be described by any of the sets defined below.

1. Elliptical & Inclined
   ```python
   <coe_object>: {
       "sma": float,       # Semi-major axis (km)
       "ecc": float,       # Eccentricity  (unit-less)
       "inc": float,       # Inclination (degrees)
       "raan": float,      # Right Ascension of the Ascending Node (degrees)
       "arg_p": float,     # Argument of Periapsis/Perigee (degrees)
       "true_anom": float, # True Anomaly (degrees)
   }
   ```
1. Elliptical & Equatorial
   ```python
   <coe_object>: {
       "sma": float,
       "ecc": float,
       "inc": float,
       "long_p": float,    # True Longitude of Periapsis (degrees)
       "true_anom": float,
   }
   ```
1. Circular & Inclined
   ```python
   <coe_object>: {
       "sma": float,
       "ecc": float,
       "inc": float,
       "raan": float,
       "arg_lat": float,  # Argument of Latitude (degrees)
   }
   ```
1. Circular & Equatorial
   ```python
   <coe_object>: {
       "sma": float,
       "ecc": float,
       "inc": float,
       "true_long": float  # True Longitude (degrees)
   }
   ```

(ref-cfg-subsec-eqe-object)=

### EQE Config

Any orbit can be described by the set of EQE defined below.

```python
<eqe_object>: {
    "sma": float,   # Semi-major axis (km)
    "h": float,     # Eccentricity vector component 1 (unit-less)
    "k": float,     # Eccentricity vector component 2 (unit-less)
    "p": float,     # Nodal vector component 1 (unit-less)
    "q": float,     # Nodal vector component 2 (unit-less)
    "lam": float,   # Mean longitude anomaly (degrees)
    "retro": float  # Whether the orbit is defined with retrograde elements. Optional: default is false.
}
```

Note that the `"retro"` field is really only necessary for pure retrograde orbits (i.e., equatorial and retrograde).
Therefore, this field is optional, and it's default setting is `false`.

(ref-cfg-subsec-sk-object)=

### StationKeepingConfig

Object defining station-keeping methods to apply during propagation.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.agent_configs

.. autoclass:: StationKeepingConfig
   :members:
   :noindex:
   :special-members: __init__
```

```{rubric} JSON Definition
```

```python
"station_keeping": {
    "routines": [str, ...],  # Optional
}
```

(ref-cfg-subsec-event-object)=

### EventConfig

**NOTE: This needs to be filled out.**
