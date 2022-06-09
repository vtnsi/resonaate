(ref-cfg-top)=
# Config Specification

This document contains the configuration format specification.
Specifically, it defines the format and contents of the scenario configuration file, and what is required versus optional.
RESONAATE simulations are initialized and started via the {class}`.Scenario` class which contains all relevant information and the public API.
There are two main ways to initialize RESONAATE:

1. Pass a fully constructed JSON object (as a Python {class}`dict`) to {func}`.buildScenarioFromConfigDict()`.
1. Pass a filepath to {func}`.buildScenarioFromConfigFile()` which points to a main scenario configuration file (JSON or YAML).

The filepath method is preferred because it allows engines, targets, and sensors to be defined in separate files from the main configuration file.
Note that only JSON formatted examples are shown.
YAML is a super-set of JSON, so it should be easy to map JSON formats to YAML if the user wishes.

-------------------------------------------------
<!-- TOC formatted for sphinx -->
:::{contents} Table of Contents
:depth: 2
:backlinks: none
:local:
:::

-------------------------------------------------

:::{rubric} Format Changelog
:::

- 2021-03-04: RESONAATE v1.3.0
- 2021-08-10: RESONAATE v1.1.1
- 2021-01-22: RESONAATE v1.0.0
- 2020-10-16: RESONAATE v0.9.0

-------------------------------------------------

(ref-cfg-sec-file-format)=
## Config File Formats

The main way RESONAATE simulations are configured is by passing JSON or YAML configuration files to  {func}`.buildScenarioFromConfigFile()`.
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
    "time": <time_obj>,                     # Req: scenario time properties
    "noise": <noise_obj>,                   # Opt: noise characteristics
    "propagation": <propagation_obj>,       # Opt: defines how RSOs are propagated
    "geopotential": <geopotential_obj>,     # Opt: Earth geopotential model
    "perturbations": <perturbations_obj>,   # Opt: orbital perturbations
    "filter": <filter_obj>,                 # Req: Kalman filter type and parameters
    "engines": [<string>, ...],             # Req: relative filepath(s) to tasking engine(s)
}
```

Separating the tasking engine configurations into separate files improves the organization and flexibility users have with defining configuration files when running many scenarios.
Instead of defining the tasking engine parameters, lists of target objects, and list of sensor objects all in the main file, the new fields point to separate JSON files which include only specifications for that tasking engine.
This allows users to quickly change between different configurations in order to produce different simulation scenarios or test new behavior.

For example, if the configuration below was in **/app/init.json**, it would point to files at **/app/engines/taskable.json** and **/app/engines/all_visible.json**, respectively.
```python
{
    "time": {...},
    "noise": {...},
    "propagation": {...},
    "geopotential": {...},
    "perturbations": {...},
    "engines": ["engines/taskable.json", "engines/all_visible.json"],
}
```

(ref-cfg-subsec-engine-file)=
### Tasking Engine Config File

Only a single tasking engine configuration is required to be specified in the `"engines"` list, but users may include several.
Using more than one tasking engine allows different sensors to be tasked in different manners (and possibly against different target sets).

Passing the above **/app/init.json** main configuration file to {func}`buildScenarioFromConfigFile()` would automatically read the files defined in the `"engines"` field.
Each of those files would then have the following format:
```python
{
    "reward": <reward_obj>,         # Req: reward function and its metrics
    "decision": <decision_obj>,     # Req: algorithm used to optimize the reward matrix
    "target_set": <string>,         # Req: relative path to JSON file defining target agents
    "sensor_set": <string>          # Req: relative path to JSON file defining sensor agents
}
```

Where the `<reward_obj>` and ` <decision_obj>` are {ref}`ref-cfg-subsubsec-reward-object` and {ref}`ref-cfg-subsubsec-decision-object`, respectively.
Also, `"target_set"` and `"sensor_set"` refer to JSON files defining the sets of {ref}`ref-cfg-subsec-target-object` and {ref}`ref-cfg-subsec-sensor-object` associated with this tasking engine, respectively.
These filepath definitions are defined relative to the main configuration file (parent of this file).

For example, if the main config file was in **/app/init.json**, and if it pointed to the tasking engine config file defined below (located at **/app/engines/taskable.json**), then the engine config would point to target and sensor files at **/app/targets/leo_only.json** and **/app/sensors/complete_ssn.json**, respectively.
```python
{
    "reward": {...},
    "decision": {...},
    "target_set": "targets/leo_only.json",
    "sensor_set": "sensors/complete_ssn.json"
}
```

(ref-cfg-subsec-target-file)=
### Target Set Config File

Each tasking engine configuration file must point to a target set configuration file for which the engine is tasked to track.
The set of targets is allowed to overlap with target sets of other tasking engines.
The corresponding target set configuration file will have the following format:
```python
{
    "targets": [<target_obj>, ...]  # Req: object(s) defining target agents
}
```

where `<target_obj>` is a target object as defined in {ref}`ref-cfg-subsec-target-object`.

(ref-cfg-subsec-sensor-file)=
### Sensor Set Config File

Each tasking engine configuration file must point to a sensor set configuration file for which the engine can task.
The set of sensors cannot overlap with sensors from other tasking engines, i.e., engines' sensor sets are mutually exclusive.
The corresponding sensor set configuration file will have the following format:
```python
{
    "sensors": [<sensor_obj>, ...]  # Req: object(s) defining sensor agents
}
```

where `<sensor_obj>` is a sensor object as defined in {ref}`ref-cfg-subsec-sensor-object`.

(ref-cfg-sec-object-defs)=
## Config Object Definitions

This section goes over the object definitions that satisfy the RESONAATE configuration specification.

The definition of the main configuration file is as follows:
```python
{
    "time": <time_obj>,                     # Req: scenario time properties
    "noise": <noise_obj>,                   # Opt: noise characteristics
    "propagation": <propagation_obj>,       # Opt: defines how RSOs are propagated
    "geopotential": <geopotential_obj>,     # Opt: Earth geopotential model
    "perturbations": <perturbations_obj>,   # Opt: orbital perturbations
    "filter": <filter_obj>,                 # Req: Kalman filter type and parameters
    "engines": [<string>, ...],             # Req: relative filepath(s) to tasking engine(s)
}
```

(ref-cfg-subsec-time-object)=
### Time Object Definition

Required object defining global scenario time properties.

#### Field Types
```python
<time_obj>: {
    "start_timestamp": <ISO 8601 timestamp>,    # Req: no default
    "stop_timestamp": <ISO 8601 timestamp>,     # Req: no default
    "physics_step_sec": <integer>,              # Opt: default is 60
    "output_step_sec": <integer>                # Opt: default is 60
}
```

#### Field Definitions
- `"start_timestamp"` is the ISO 8601 UTC time when the scenario starts. It is assumed to be the epoch at which all targets' initial states are defined.
- `"stop_timestamp"` is the ISO 8601 UTC time when the scenario stops.
- `"physics_step_sec"`: is the time step at which the simulation will propagate forwards.
- `"output_step_sec"`: is the time step at which data will be inserted into the database.

(ref-cfg-subsec-noise-object)=
### Noise Object Definition

Optional object defining noise characteristics.
See {mod}`~.physics.noise` for details on different types of noise/uncertainty.

#### Field Types
```python
<noise_obj>: {
    "initial_error_magnitude": <decimal>,   # Opt: default is 0.00005
    "dynamics_noise_type": <string>,        # Opt: default is "simple_noise"
    "dynamics_noise_magnitude": <decimal>,  # Opt: default is 1e-20
    "filter_noise_type": <string>,          # Opt: default is "continuous_white_noise"
    "filter_noise_magnitude": <decimal>,    # Opt: default is 1e-7
    "random_seed": <integer or null>        # Opt: default is null
}
```

#### Field Definitions
- `"initial_error_magnitude"` Assumed variance of initial RSO uncertainty in filter.
- `"dynamics_noise_type"` Assumed noise physics in the dynamics propagation.
    - `"simple_noise"`
    - `"continuous_white_noise"`
    - `"discrete_white_noise"`
- `"dynamics_noise_magnitude"`: Assumed variance of dynamics noise.
- `"filter_noise_type"` Assumed noise physics in the filter/estimation process.
    - `"simple_noise"`
    - `"continuous_white_noise"`
    - `"discrete_white_noise"`
- `"filter_noise_magnitude"`: Assumed variance of filter/estimation noise.
- `"random_seed"`: Seeds the RNG to allow for reproducible results & different noise realizations. Setting to `null` sets the seed based on the system clock.

(ref-cfg-subsec-propagation-object)=
### Propagation Object Definition

Optional object defining how RSOs are propagated.

#### Field Types
```python
<propagation_obj>: {
    "propagation_model": <string>,      # Opt: default is "special_perturbations"
    "integration_method": <string>,     # Opt: default is "RK45"
    "realtime_propagation": <boolean>,  # Opt: default is false
    "realtime_observation": <boolean>   # Opt: default is true
}
```

#### Field Definitions
- `"propagation_model"` is the dynamics model to use for RSO propagation.
    - `"special_perturbations"`
    - `"two_body"`
- `"integration_method"` is the integration method to use with {func}`scipy.integrate.solve_ivp`. See `scipy` documentation for options.
- `"realtime_propagation"`: defines whether to use the internal propagation for the truth model. Will fall back to realtime propagation if pre-loaded ephemerides are not found for an agent in the database.
- `"realtime_observation"`: defines to generate observations during the simulation

(ref-cfg-subsec-geopotential-object)=
### Geopotential Object Definition

Optional object defining the Earth geopotential model.

#### Field Types
```python
<geopotential_obj>: {
    "model": <string>,      # Opt: default is `"egm96.txt"`
    "degree": <integer>,    # Opt: default is `4`
    "order": <integer>      # Opt: default is `4`
}
```

#### Field Definitions
- `"model"` is the model file used to define the Earth's gravity model. 
    - `"egm96.txt"` is the only officially supported gravity model currently.
- `"degree"` is the degree of the Earth's gravity model.
- `"order"`: is the order of the Earth's gravity model.

(ref-cfg-subsec-perturbation-object)=
### Perturbations Object Definition

Optional object defining orbital perturbations to include.
Currently, only third body effects from the Sun and the Moon are supported as extra perturbations outside of the non-Spherical Earth model.

#### Field Types
```python
<perturbations_obj>: {
    "third_bodies": [<string>, ...] # Opt: default is an empty list
}
```

#### Field Definitions
- `"third_bodies"` defines which third bodies to include in perturbations.
    - `"Sun"`
    - `"Moon"`

(ref-cfg-subsec-filter-object)=
### Filter Object Definition

Required object defining which Kalman filter is used to track RSOs.

#### Field Types
```python
<filter_obj>: {
    "name": <string> # Opt: default is "unscented_kalman_filter"
}
```

#### Field Definitions
- `"name"` defines which Kalman filter class is used to track estimates.
    - `"unscented_kalman_filter"`: nonlinear Kalman filter which uses the Unscented Transform

(ref-cfg-subsec-engine-object)=
### Engine Object Definition

Required list of string paths pointing tasking engine configuration definitions.
The paths in this list are defined relative to the **main** configuration file.

The definition of the tasking engine configuration file is as follows:
```python
{
    "reward": <reward_obj>,         # Req: reward and its metrics
    "decision": <decision_obj>,     # Req: algorithm used to optimize the reward matrix
    "target_set": <string>,         # Req: relative path to JSON file defining target agents
    "sensor_set": <string>          # Req: relative path to JSON file defining sensor agents
}
```

The definitions of the nested objects are defined below.

(ref-cfg-subsubsec-target-set)=
#### Target Set Definition

String filepath pointing to the set of target objects (RSOs) which this tasking engine is tracking.
This filepath is defined relative to the **main** configuration file.
See {ref}`ref-cfg-subsec-target-object` for details on the target set configuration file.

(ref-cfg-subsubsec-sensor-set)=
#### Sensor Set Definition

String filepath pointing to the set of sensor objects which this tasking engine can task.
This filepath is defined relative to the **main** configuration file.
See {ref}`ref-cfg-subsec-sensor-object` for details on the sensor set configuration file.

(ref-cfg-subsubsec-decision-object)=
#### Decision Object Definition

Required object defining the decision algorithm used to optimize the reward matrix for this tasking engine.
It is **highly** recommended that users simply set `"name": "MunkresDecision"` unless they understand the differences.
Please refer to the {mod}`~.tasking.decisions` sub-package for more information.

##### Field Types
```python
<decision_obj>: {
    "name": <string>,   # Req: no default
    "parameters": {}    # Opt: default is an empty JSON object
}
```

##### Field Definitions
- `"name"` defines which decision algorithm to implement when dynamically tasking sensors. The valid options are:
    - `"MyopicNaiveGreedyDecision"` allows for observation saturation
    - `"MunkresDecision"` is the most balanced and robust decision method
    - `"RandomDecision"` is only recommended for comparison studies
    - `"AllVisibleDecision"` allows all targets satisfying the visibility constraints to be tracked
- `"parameters"` defines extra arguments taken by each decision algorithm. Only `"RandomDecision"` takes an extra argument, which is `"seed": <integer>` for seeding the RNG.

(ref-cfg-subsubsec-reward-object)=
#### Reward Object Definition

Required object defining the reward algorithm and the metrics it uses for this tasking engine.
It is **highly** recommended that users implement the recommended values unless they understand the differences.
Please refer to the {mod}`~.tasking.rewards` and {mod}`~.tasking.metrics` sub-packages for more information.

##### Field Types
```python
<reward_obj>: {
    "name": <string>,               # Req: no default
    "metrics": [<metric_obj>, ...], # Req: no default
    "parameters": {}                # Opt: default is an empty JSON object
}
```

##### Field Definitions
- `"name"` defines which function to calculate the total reward. The valid options are:
    - `"CostConstrainedReward"` constrains the reward by multiplying by the sign of a stability metric and subtracting the sensor metric
    - `"SimpleSummationReward"` simply add an arbitrary number metrics together
    - `"CombinedReward"` similar to `"CostConstrainedReward"` but includes a reward to counteract target "staleness"
- `"metrics"` defines which metrics to include in the reward calculation and their parameters. See {ref}`ref-cfg-subsubsec-metric-object` for more information.
- `"parameters"` defines extra arguments taken by each reward function. `"CostConstrainedReward"` and `"CombinedReward"` can take an optional extra argument `"delta"`. This parameter defines the weighting between the information and sensor metrics. It is `0.85` by default, but is valid in the range `0.0 < delta < 1.0`.

(ref-cfg-subsubsec-metric-object)=
#### Metric Object Definition

Required objects to include in the `"metrics"` field of the `<reward_obj>`.

##### Field Types
```python
<metric_obj>: {
    "name": <string>,   # Req: no default
    "parameters": {}    # Req: default is an empty JSON object
}
```

##### Field Definitions
- `"name"` defines which metric function to call. The valid options are:
    - Behavior metrics:
        - `"TimeSinceObservation"` observation "staleness" metric that increases the reward for observing a target as the time since the last observation of it increases.
    - Information gain metrics:
        - `"FisherInformation"` fisher information gain for observing the target
        - `"FisherInformation"` shannon information gain for observing the target
        - `"KLDivergence"` KL Divergence information gain for observing the target
    - Sensor constraint metrics
        - `"DeltaPosition"` required change in angular position to make an observation
        - `"SlewCycle"` required slew frequency to make an observation
        - `"TimeToTransit"` time to slew to the target to make an observation. Takes extra parameter `"norm_factor"` which is usually equal to `"physics_step_sec"`
    - Stability metrics
        - `"LyapunovStability"` scalar maximal Lyapunov exponent approximation
- `"parameters"` defines extra arguments taken by each decision algorithm

(ref-cfg-subsec-target-object)=
### Target Object Definition

Target agents' initial states are assumed to be defined at the epoch defined by `"start_timestamp"` in {ref}`ref-cfg-subsec-time-object`. There are two ways to define a target agent (all fields are required for each version):

1. ECI state vector
    ```python
    <target_obj>: {
        "sat_num": <integer>, # NORAD catalog number or unique simulation ID
        "sat_name": <string>, # Unique simulation name or SATCAT name
        "init_eci": [         # J2000 initial state vector defined at "start_timestamp"
            # ECI "x", "y", and "z" positions  (km)
            <decimal>, <decimal>, <decimal>,
            # ECI "x", "y", and "z" velocities (km/sec)
            <decimal>, <decimal>, <decimal>
        ]
    }
    ```
1. Classical orbital elements (COE), see {ref}`ref-cfg-subsec-target-coe-object`
    ```python
    <target_obj>: {
        "sat_num": <integer>,    # NORAD catalog number or unique simulation ID
        "sat_name": <string>,    # Unique simulation name, or SATCAT name
        "init_coe": <coe_object> # COE object defined at "start_timestamp"
    }
    ```
1. Equinoctial orbital elements (EQE), see {ref}`ref-cfg-subsec-target-eqe-object`
    ```python
    <target_obj>: {
        "sat_num": <integer>,    # NORAD catalog number or unique simulation ID
        "sat_name": <string>,    # Unique simulation name, or SATCAT name
        "init_eqe": <eqe_object> # EQE object defined at "start_timestamp"
    }
    ```

(ref-cfg-subsec-target-coe-object)=
#### COE Object Definition

Note that there are several realizations of COE sets.
An orbit can be described by any of the sets defined below.

1. Elliptical & Inclined
    ```python
    <coe_object>: {
        "sma": <decimal>,       # Semi-major axis (km)
        "ecc": <decimal>,       # Eccentricity  (unit-less)
        "inc": <decimal>,       # Inclination (degrees)
        "raan": <decimal>,      # Right Ascension of the Ascending Node (degrees)
        "arg_p": <decimal>,     # Argument of Periapsis/Perigee (degrees)
        "true_anom": <decimal>  # True Anomaly (degrees)
    }
    ```
1. Elliptical & Equatorial
    ```python
    <coe_object>: {
        "sma": <decimal>,
        "ecc": <decimal>,
        "inc": <decimal>,
        "long_p": <decimal>,    # True Longitude of Periapsis (degrees)
        "true_anom": <decimal>
    }
    ```
1. Circular & Inclined
    ```python
    <coe_object>: {
        "sma": <decimal>,
        "ecc": <decimal>,
        "inc": <decimal>,
        "raan": <decimal>,
        "arg_lat": <decimal>    # Argument of Latitude (degrees)
    }
    ```
4. Circular & Equatorial
    ```python
    <coe_object>: {
        "sma": <decimal>,
        "ecc": <decimal>,
        "inc": <decimal>,
        "true_long": <decimal>  # True Longitude (degrees)
    }
    ```

(ref-cfg-subsec-target-eqe-object)=
#### EQE Object Definition

Any orbit can be described by the set of EQE defined below.
```python
<eqe_object>: {
    "sma": <decimal>,   # Semi-major axis (km)
    "h": <decimal>,     # Eccentricity vector component 1 (unit-less)
    "k": <decimal>,     # Eccentricity vector component 2 (unit-less)
    "p": <decimal>,     # Nodal vector component 1 (unit-less)
    "q": <decimal>,     # Nodal vector component 2 (unit-less)
    "lam": <decimal>,   # Mean longitude anomaly (degrees)
    "retro": <boolean>  # Whether the orbit is defined with retrograde elements. Optional: default is false.
}
```
Note that the `"retro"` field is really only necessary for pure retrograde orbits (i.e., equatorial and retrograde).
Therefore, this field is optional, and it's default setting is `false`.

(ref-cfg-subsec-sensor-object)=
### Sensor Object Definition

The default SOSI network is defined in "SSN Specifications OpenSource v1.8".
Sensor agents can be defined as `"GroundFacility"` for ground-based sensors or `"Spacecraft"` for space-based sensors. Also, each sensing agents can contain a sensor of the following types: `"Optical"`, `"Radar"`, `"AdvRadar"`.

#### Common Sensor Fields

These are the required fields defined for all types of sensor objects.
```python
<sensor_obj>: {
    "id": <integer>,                            # Unique simulation ID
    "name": <string>,                           # Unique simulation name
    "covariance": [<decimal>, <decimal>, ...],  # Measurement uncertainty matrix
    "slew_rate": <decimal>,                     # Sensor maximum angular slew speed (rad/sec)
    "efficiency": <decimal>,                    # Sensor efficiency value
    "aperture_area": <decimal>,                 # Sensor aperture area (m^2)
    "sensor_type": <string>,                    # Type of sensor
    "host_type": <string>,                      # Type of agent
    "azimuth_range": [<decimal>, <decimal>],    # Min/max az sensor limits (rad, rad)
    "elevation_range": [<decimal>, <decimal>],  # Min/max el sensor limits (rad, rad)
    "exemplar": [<decimal>, <decimal>]          # Ideal target area & range (m^2, km)
}
```

#### Sensor Types

Different types of sensors (`"sensor_type"` field) require different extra fields in the sensor object.

1. `"Optical"` requires no extra fields
1. `"Radar"` and `"AdvRadar"` require:
    ```python
    <sensor_obj>: {
        ...
        "tx_power": <decimal>,      # Transmit power (W)
        "tx_frequency": <decimal>   # Operational center frequency (Hz)
    }
    ```

Also, the shape/size of the `"covariance"` field depends on the `"sensor_type"` field:
- `"Optical"`: 2x2 measurement uncertainty
    ```python
    [
        [a^2, ab],          # a: azimuth std in radians
        [ab, b^2]           # b: elevation std in radians
    ]
    ```
- `"Radar"` and `"AdvRadar"`: 4x4 measurement uncertainty
    ```python
    [
        [a^2, ab, ac, ad],  # a: azimuth std in radians
        [ab, b^2, bc, bd],  # b: elevation std in radians
        [ac, bc, c^2, cd],  # c: range std in kilometers
        [ad, bd, cd, d^2],  # d: range rate std in kilometers/seconds
    ]
    ```

#### Sensing Agent Types

Different types of sensor agents (`"host_type"` field) require different extra fields in the sensor object.

1. `"GroundFacility"` requires
    ```python
    <sensor_obj>: {
        ...
        # Defines sensor's terrestrial location at "start_timestamp"
        "lat": <decimal>, # Geodetic latitude, (rad)
        "lon": <decimal>, # Geodetic longitude, (rad)
        "alt": <decimal>  # Height above ellipsoid, (km)
    }
    ```
1. `"Spacecraft"` requires one of the following options to describe its initial state:
    - `"init_eci"` for defining the state in ECI (J2000) position and velocity
        ```python
        <sensor_obj>: {
            ...
            "init_eci": [
                # Defines satellite J2000 (ECI) state at "start_timestamp"
                <decimal>, <decimal>, <decimal>, # "x", "y", & "z" positions (km)
                <decimal>, <decimal>, <decimal>  # "x", "y", & "z" velocities (km/sec)
            ]
        }
        ```
    - `"init_coe"` for defining an orbit via COEs, see {ref}`ref-cfg-subsec-target-coe-object`
        ```python
        <sensor_obj>: {
            ...
            "init_coe": <coe_object> # COE object defined at "start_timestamp"
        }
        ```
    - `"init_eqe"` for defining an orbit via EQEs, see {ref}`ref-cfg-subsec-target-eqe-object`
        ```python
        <sensor_obj>: {
            ...
            "init_eqe": <eqe_object> # EQE object defined at "start_timestamp"
        }
        ```

(ref-cfg-subsec-event-object)=
### Event Object Definition

**NOTE: This needs to be filled out.**
