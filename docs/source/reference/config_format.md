(ref-cfg-top)=

# Config Specification

This document contains the configuration format specification.
Specifically, it defines the format and contents of the scenario configuration file, and what is required versus optional.
RESONAATE simulations are initialized and started via the {class}`.Scenario` class which contains all relevant information and the public API.
There are two main ways to initialize RESONAATE:

1. Pass a fully constructed JSON object (as a Python {class}`dict`) to {func}`.buildScenarioFromConfigDict()`.
1. Pass a file path to {func}`.buildScenarioFromConfigFile()` which points to a main scenario configuration JSON file.

The file path method is preferred because it allows engines, targets, and sensors to be defined in separate files from the main configuration file.

______________________________________________________________________

<!-- TOC formatted for sphinx -->

```{contents} Table of Contents
---
depth: 3
backlinks: none
local:
---
```

______________________________________________________________________

```{rubric} Format Changelog
```

- 2023-04-07: RESONAATE v3.0.0
- 2023-02-02: RESONAATE v2.0.0
- 2022-09-06: RESONAATE v2.0.0
- 2022-08-26: RESONAATE v1.5.2
- 2022-08-26: RESONAATE v1.5.1
- 2022-08-24: RESONAATE v1.5.0
- 2022-07-20: RESONAATE v1.4.0
- 2022-06-06: RESONAATE v1.3.0
- 2022-03-04: RESONAATE v1.2.0
- 2021-08-10: RESONAATE v1.1.1
- 2021-01-22: RESONAATE v1.0.0
- 2020-10-16: RESONAATE v0.9.0

______________________________________________________________________

(ref-cfg-sec-file-format)=

## Config File Formats

The main way RESONAATE simulations are configured is via passing JSON configuration files to {func}`.buildScenarioFromConfigFile()`.
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
Also, `"target_file"` and `"sensor_file"` refer to JSON files defining the sets of {class}`.AgentConfig` and {class}`.SensingAgentConfig`, respectively.
More detail on {class}`AgentConfig` classes the are provided in the {ref}`ref-cfg-subsec-agent-object` section.
These file path definitions are defined relative to the main configuration file (parent of this file).

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
    "targets": [AgentConfig, ...],
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
    AgentConfig,  # Req: object(s) defining target agents
    ...,
]
```

where {class}`.AgentConfig` is a target object as defined in {ref}`ref-cfg-subsec-agent-object`.

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

where {class}`.SensingAgentConfig` is a sensor object as defined in {ref}`ref-cfg-subsubsec-sensing-agent-object`.

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

### Top-Level Configuration

(ref-cfg-subsec-time-object)=

#### TimeConfig

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

#### EstimationConfig

This is a required field defining estimation techniques used to track the targets during the simulation.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.estimation_config

.. autoclass:: EstimationConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"estimation": {
    "sequential_filter": SequentialFilterConfig,  # Optional
    "particle_filter": ParticleFilterConfig,  # Optional
    "adaptive_filter": AdaptiveEstimationConfig,  # Optional
    "initial_orbit_determination": InitialOrbitDeterminationConfig,  # Optional
}
```

##### SequentialFilterConfig

This is an optional field in `"estimation"` defining the nominal sequential filter algorithm that tracks the targets during the simulation.
One of either `"sequential_filter"` or `"particle_filter"` must be set.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.estimation_config

.. autoclass:: SequentialFilterConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"sequential_filter": {
    "name":                         str,                      # Required
    "dynamics_model":               str,                      # Optional
    "maneuver_detection":           ManeuverDetectionConfig,  # Optional
    "adaptive_estimation":          bool,                     # Optional
    "initial_orbit_determination":  bool,                     # Optional
    "save_filter_steps":            bool,                     # Optional
    "parameters":                   dict,                     # Optional
}
```

###### ManeuverDetectionConfig

This is an optional field in `"sequential_filter"` defining the maneuver detection technique that tests for maneuvers during the estimation algorithm.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.estimation_config

.. autoclass:: ManeuverDetectionConfig
   :members:
   :noindex:
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

##### AdaptiveEstimationConfig

This is an optional field in `"estimation"` defining the adaptive estimation technique that is used if a maneuver is detected.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.estimation_config

.. autoclass:: AdaptiveEstimationConfig
   :members:
   :noindex:
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

##### InitialOrbitDeterminationConfig

This is an optional field in `"estimation"` defining the initial orbit determination technique that is used if a maneuver is detected.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.estimation_config

.. autoclass:: InitialOrbitDeterminationConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"initial_orbit_determination": {
    "name":                          str,    # Optional
    "minimum_observation_spacing":   int,    # Optional
}
```

(ref-cfg-subsec-noise-object)=

#### NoiseConfig

Optional object defining simulation noise characteristics.
See {mod}`~.physics.noise` for details on different types of noise/uncertainty.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.noise_config

.. autoclass:: NoiseConfig
   :members:
   :noindex:
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

#### PropagationConfig

Optional object defining how RSOs are propagated.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.propagation_config

.. autoclass:: PropagationConfig
   :members:
   :noindex:
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

#### ObservationConfig

Optional object defining observation behavior preferences.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.observation_config

.. autoclass:: ObservationConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"observation": {
    "background": bool,              # Optional
    "realtime_observation": bool,    # Optional
}
```

#### GeopotentialConfig

Optional object defining the Earth geopotential model.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.geopotential_config

.. autoclass:: GeopotentialConfig
   :members:
   :noindex:
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

#### PerturbationsConfig

Optional object defining orbital perturbations to include.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.perturbations_config

.. autoclass:: PerturbationsConfig
   :members:
   :noindex:
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

(ref-cfg-subsec-engine-object)=

### Tasking Engine Configuration

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
```

```{rubric} JSON Definition
```

```python
"decision": {
    "name": str,        # Required
    "parameters": dict, # Optional
}
```

(ref-cfg-subsec-agent-object)=

### Agent Configuration

Agents' initial states are assumed to be defined at the epoch defined by `"start_timestamp"` in {ref}`ref-cfg-subsec-time-object`.
The agent's initial state is defined by a `StateConfig` object and its platform is defined by a `PlatformConfig` object, defined in {ref}`ref-cfg-subsec-state-object` and {ref}`ref-cfg-subsec-platform-object` respectively.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.agent_config

.. autoclass:: AgentConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
[
    {
        "id": int,                  # Required
        "name": str,                # Required
        "state": StateConfig,       # Required
        "platform": PlatformConfig, # Required
    },
    ...
]
```

(ref-cfg-subsubsec-sensing-agent-object)=

#### SensingAgentConfig

The `SensingAgentConfig` adds a `SensorConfig` field for defining the contained sensor object which is defined in {ref}`ref-cfg-subsec-sensor-object`.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.agent_config

.. autoclass:: SensingAgentConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
[
    {
        "id": int,                  # Required
        "name": str,                # Required
        "state": StateConfig,       # Required
        "platform": PlatformConfig, # Required
        "sensor": SensorConfig,     # Required
    },
    ...
]
```

(ref-cfg-subsec-state-object)=

#### StateConfig

User's can describe an agent's initial state in a simulation via several `StateConfig` types: `"eci"`, `"lla"`, `"coe"`, and `"eqe"`.
However, the type of `StateConfig` must be valid for the agent's corresponding `PlatformConfig` type.
Each `StateConfig` description below mentions the platforms for which they are valid.

##### ECIStateConfig

The `ECIStateConfig` class defines initial states in Earth-centered inertial coordinates in position (kilometers) and velocity (kilometers per second).
It is a valid option for `GroundFacilityConfig` and `SpacecraftConfig` platforms.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.state_config

.. autoclass:: ECIStateConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"state": {
    "type": "eci",                      # Required
    "position": [float, float, float],  # Required
    "velocity": [float, float, float],  # Required
}
```

##### LLAStateConfig

The `LLAStateConfig` class defines initial states in latitude (degrees), longitude (degrees), altitude (kilometers) coordinates.
It is a valid option only for `GroundFacilityConfig` platforms.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.state_config

.. autoclass:: LLAStateConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"state": {
    "type": "lla",          # Required
    "latitude": float,      # Required
    "longitude": float,     # Required
    "altitude": float,      # Required
}
```

##### COEStateConfig

The `COEStateConfig` class defines initial states in classical orbital elements.
It is a valid option only for `SpacecraftConfig` platforms.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.state_config

.. autoclass:: COEStateConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"state": {
    "type": "coe",                      # Required
    "semi_major_axis": float,           # Required
    "eccentricity": float,              # Required
    "inclination": float,               # Required
    "true_anomaly": float,              # Optional
    "right_ascension": float,           # Optional
    "argument_periapsis": float,        # Optional
    "true_longitude_periapsis": float,  # Optional
    "argument_latitude": float,         # Optional
    "true_longitude": float,            # Optional
}
```

Note that there are several realizations of COE sets based on the fields defined.
An orbit can be described by any of the sets defined below.

1. Elliptical & Inclined
   ```python
    "state": {
        "type": "coe",                      # Required
        "semi_major_axis": float,           # Required
        "eccentricity": float,              # Required
        "inclination": float,               # Required
        "right_ascension": float,           # Required
        "argument_periapsis": float,        # Required
        "true_anomaly": float,              # Required
    }
   ```
1. Elliptical & Equatorial
   ```python
    "state": {
        "type": "coe",                      # Required
        "semi_major_axis": float,           # Required
        "eccentricity": float,              # Required
        "inclination": float,               # Required
        "true_longitude_periapsis": float,  # Required
        "true_anomaly": float,              # Required
    }
   ```
1. Circular & Inclined
   ```python
    "state": {
        "type": "coe",                      # Required
        "semi_major_axis": float,           # Required
        "eccentricity": float,              # Required
        "inclination": float,               # Required
        "right_ascension": float,           # Required
        "argument_latitude": float,         # Required
    }
   ```
1. Circular & Equatorial
   ```python
    "state": {
        "type": "coe",                      # Required
        "semi_major_axis": float,           # Required
        "eccentricity": float,              # Required
        "inclination": float,               # Required
        "true_longitude": float,            # Required
    }
   ```

##### EQEStateConfig

The `EQEStateConfig` class defines initial states in equinoctial orbital elements.
It is a valid option only for `SpacecraftConfig` platforms.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.state_config

.. autoclass:: EQEStateConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"state": {
    "type": "eqe",              # Required
    "semi_major_axis": float,   # Required
    "h": float,                 # Required
    "k": float,                 # Required
    "p": float,                 # Required
    "q": float,                 # Required
    "mean_longitude": float,    # Required
    "retrograde": bool,         # Optional
}
```

Note that the `"retrograde"` field is really only necessary for pure retrograde orbits (i.e., equatorial and retrograde).
Therefore, this field is optional, and its default setting is `false`.

(ref-cfg-subsec-platform-object)=

#### PlatformConfig

Users can define an agent's kinematic behavior in a simulation via different `PlatformConfig` types: `"spacecraft"` and `"ground_facility"`.
Platforms share multiple common fields:

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.platform_config

.. autoclass:: PlatformConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"platform": {
    "type": str,                    # Required
    "mass": float,                  # Optional
    "visual_cross_section": float,  # Optional
    "reflectivity": float,          # Optional
}
```

It is important to note that each `PlatformConfig` type is only able to be defined with a subset of `StateConfig` types.
This information is defined by each class' `valid_states` property.
See {ref}`ref-cfg-subsec-state-object` for which platform types are valid for each state type.

##### GroundFacilityConfig

A ground facility platform defines an agent that is stationary on the Earth's surface.
This platform has no extra fields on top of the common ones defined by `PlatformConfig`.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.platform_config

.. autoclass:: GroundFacilityConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"platform": {
    "type": "ground_facility",      # Required
    "mass": float,                  # Optional
    "visual_cross_section": float,  # Optional
    "reflectivity": float,          # Optional
}
```

##### SpacecraftConfig

A spacecraft platform defines an agent which is an Earth orbiting artificial satellite.
This platform has an extra field for defining station-keeping behaviors, which is defined in {ref}`ref-cfg-subsec-sk-object`.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.platform_config

.. autoclass:: SpacecraftConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"platform": {
    "type": "spacecraft",                       # Required
    "mass": float,                              # Optional
    "visual_cross_section": float,              # Optional
    "reflectivity": float,                      # Optional
    "station_keeping": StationKeepingConfig,    # Optional
}
```

(ref-cfg-subsec-sk-object)=

##### StationKeepingConfig

Object defining station-keeping methods to apply during propagation.
Valid routines are: `"LEO"`, `"GEO EW"`, `"GEO NS"`.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.platform_config

.. autoclass:: StationKeepingConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
"station_keeping": {
    "routines": [str, ...],  # Optional
}
```

(ref-cfg-subsec-sensor-object)=

#### SensorConfig

Sensors can be defined as `"optical"`, `"radar"`, `"adv_radar"`.
All `SensorConfig` types share several common fields.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.sensor_config

.. autoclass:: SensorConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
[
    {
        "type": str,                              # Required
        "azimuth_range": [float, float],          # Required
        "elevation_range": [float, float],        # Required
        "covariance": [[float, ...], ...],        # Required
        "aperture_diameter": float,               # Required
        "efficiency": float,                      # Required
        "slew_rate": float,                       # Required
        "background_observations": bool,          # Optional
        "minimum_range": float,                   # Optional
        "maximum_range": float,                   # Optional
        "field_of_view": FieldOfViewConfig,       # Optional
    },
    ...
]
```

##### OpticalConfig

Electro-optical sensors have an extra, optional field:

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.sensor_config

.. autoclass:: OpticalConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
[
    {
        "detectable_vismag": float,               # Optional
    },
    ...
]
```

##### RadarConfig

Radar sensors have several extra, required fields:

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.sensor_config

.. autoclass:: RadarConfig
   :members:
   :noindex:
```

```{rubric} JSON Definition
```

```python
[
    {
        "tx_power": float,              # Required
        "tx_frequency": float,          # Required
        "min_detectable_power": float,  # Required
    },
    ...
]
```

##### AdvRadarConfig

Advanced Radar sensors have the exact same configuration spec as Radar sensors.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.sensor_config

.. autoclass:: AdvRadarConfig
   :members:
   :noindex:
```

##### Field of View

Defines type and parameters of `"field_of_view"` field.

```{rubric} Python Definition
```

```{eval-rst}
.. currentmodule:: resonaate.scenario.config.sensor_config

.. autoclass:: FieldOfViewConfig
   :members:
   :noindex:
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

(ref-cfg-subsec-event-object)=

### Event Configuration

**NOTE: This needs to be filled out.**
