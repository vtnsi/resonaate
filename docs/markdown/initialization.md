# 1. RESONAATE Initialization

This document contains the initialization format specification.
Specifically, it defines the format and contents of the scenario configuration file, and what is required versus optional.
RESONAATE simulations are initialized and started via the `Scenario` class which contains all relevant information and the public API.
There are two main ways to intialize RESONAATE:

1. Pass a fully constructed JSON object (as a Python `dict`) to `Scenario.fromConfig()`.
1. Pass a filepath to `Scenario.fromConfigFile()` which points to a main scenario configuration file (JSON or YAML). This option allows targets and sensors to be defined in separate files from the main configuration for easier scenario contruction or tweaking.

Both these options are further explained below.

## Table Of Contents

- [1. RESONAATE Initialization](#1-resonaate-initialization)
    - [Table Of Contents](#table-of-contents)
- [2 JSON Configuration Object Definition](#2-json-configuration-object-definition)
    - [2.1 `"time"` JSON Definition](#21-time-json-definition)
    - [2.2 `"noise"` JSON Definition](#22-noise-json-definition)
    - [2.3 `"propagation"` JSON Definition](#23-propagation-json-definition)
    - [2.4 `"geopotential"` JSON Definition](#24-geopotential-json-definition)
    - [2.5 `"perturbations"` JSON Definition](#25-perturbations-json-definition)
    - [2.6 `"decision"` JSON Definition](#26-decision-json-definition)
    - [2.7 `"reward"` JSON Definition](#27-reward-json-definition)
        - [2.7.1 Metric Object Definition](#271-metric-object-definition)
    - [2.8 Target Object Definition](#28-target-object-definition)
        - [2.8.1 COE Object Definition](#281-coe-object-definition)
    - [2.9 Sensor Object Definition](#29-sensor-object-definition)
        - [2.9.1 Common Sensor Fields](#291-common-sensor-fields)
        - [2.9.2 Sensor Types](#292-sensor-types)
        - [2.9.2 Sensing Agent Types](#292-sensing-agent-types)
    - [2.10 Target Event Definition](#210-target-event-definition)
    - [2.11 Sensor Event Definition](#211-sensor-event-definition)
- [3. Configuration File Format](#3-configuration-file-format)

# 2 JSON Configuration Object Definition

To initialize a scenario, the `Scenario::fromConfig()` method ingests a JSON object (as a Python `dict`) formatted in the following way:

```jsonc
<init_message>: {
    "time": {}, // Required JSON object defining scenario time properties
    "noise": {}, // Optional JSON object defining noise characteristics
    "propagation": {}, // Optional JSON object defining how RSOs are propagated
    "geopotential": {}, // Optional JSON object defining the Earth geopotential model
    "perturbations": {}, // Optional JSON object defining orbital perturbations to include
    "decision": {}, // Required JSON object defining the decision algorithm used to optimize the reward matrix
    "reward": {}, // Required JSON object defining the reward algorithm and the metrics it uses
    "targets": [<target_obj>, ...], // Required list of JSON objects defining target agents
    "sensors": [<sensor_obj>, ...], // Required list of JSON objects defining sensor agents
    "target_events": [<target_event_obj>, ...], // Not currently in use
    "sensor_events": [<sensor_event_obj>, ...] // Not currently in use
}
```

## 2.1 `"time"` JSON Definition

Required JSON object defining scenario time properties

Field Types:
```jsonc
"time": {
    "start_timestamp": <ISO 8601 timestamp>, // Required, no default
    "stop_timestamp": <ISO 8601 timestamp>, // Required, no default
    "physics_step_sec": <integer>, // Optional, default is 60
    "output_step_sec": <integer> // Optional, default is 60
}
```

Field Definitions:
- `"start_timestamp"` is the ISO 8601 UTC time when the scenario starts. It is assumed to be the epoch at which all targets' initial states are defined.
- `"stop_timestamp"` is the ISO 8601 UTC time when the scenario stops.
- `"physics_step_sec"`: is the time step at which the simulation will propagate forwards.
- `"output_step_sec"`: is the time step at which data will be inserted into the database.

Recommended Values:
```jsonc
"time": {
    "physics_step_sec": 60, // (seconds)
    "output_step_sec": 60   // (seconds)
}
```

## 2.2 `"noise"` JSON Definition

Optional JSON object defining noise characteristics.
See `resonaate.physics.noise.py` for details on different types of noise/uncertainty.

Note: `"dynamics_noise_type"` and `"filter_noise_type"` must be set to one of the following options: `"simple_noise"`, `"continuous_white_noise"`, or `"discrete_white_noise"`.

Field Types:
```jsonc
"noise": {
    "initial_error_magnitude": <decimal>, // Optional, default is 0.00005
    "dynamics_noise_type": <string>, // Optional, default is "simple_noise"
    "dynamics_noise_magnitude": <decimal>, // Optional, default is 1e-20
    "filter_noise_type": <string>, // Optional, default is "continuous_white_noise"
    "filter_noise_magnitude": <decimal>, // Optional, default is 1e-7
    "random_seed": <integer or null> // Optional, default is null
}
```

Field Definitions:
- `"initial_error_magnitude"` Assumed variance of initial RSO uncertainty in filter.
- `"dynamics_noise_type"` Assumed noise physics in the dynamics propagation.
- `"dynamics_noise_magnitude"`: Assumed variance of dynamics noise.
- `"filter_noise_type"` Assumed noise physics in the filter/estimation process.
- `"filter_noise_magnitude"`: Assumed variance of filter/estimation noise.
- `"random_seed"`: Seeds the RNG to allow for reproducible results & different noise realizations. Setting to `null` sets the seed based on the system clock.

Recommended Values:
```jsonc
"noise": {
    "initial_error_magnitude": 1e-8,
    "dynamics_noise_type": "simple_noise",
    "dynamics_noise_magnitude": 1e-20,
    "filter_noise_type": "continuous_white_noise",
    "filter_noise_magnitude": 1e-12,
    "random_seed": "os"
}
```

## 2.3 `"propagation"` JSON Definition

Optional JSON object defining how RSOs are propagated.
Note: `"propagation_model"` must be set to one of the following options: `"special_perturbations"` or `"two_body"`.

Field Types:
```jsonc
"propagation": {
    "propagation_model": <string>, // Optional, default is "special_perturbations"
    "integration_method": <string>, // Optional, default is "RK45"
    "realtime_propagation": <boolean>, // Optional, default is false
    "realtime_observation": <boolean> // Optional, default is true
}
```

Field Definitions:
- `"propagation_model"` is the dynamics model to use for RSO propagation.
- `"integration_method"` is the integration method to use with `scipy.integrate.solve_ivp`. See `scipy` documentation for options.
- `"realtime_propagation"`: defines whether to use the internal propagation for the truth model. Will fall back to realtime propagation if pre-loaded ephemerides are not found for an agent in the database.
- `"realtime_observation"`: defines to generate observations during the simulation

Recommended Values:
```jsonc
"propagation": {
    "propagation_model": "special_perturbations",
    "integration_method": "RK45",
    "realtime_propagation": false,
    "realtime_observation": true
}
```

## 2.4 `"geopotential"` JSON Definition

Optional JSON object defining the Earth geopotential model.
Note: `"model"` only officially supports using the `"egm96.txt"` option at this time.

Field Types:
```jsonc
"geopotential": {
    "model": <string>, // Optional, default is `"egm96.txt"`
    "degree": <integer>, // Optional, default is `4`
    "order": <integer> // Optional, default is `4`
}
```

Field Definitions:
- `"model"` is the model file used to define the Earth's gravity model. Only `"egm96.txt"` is officially supported.
- `"degree"` is the degree of the Earth's gravity model.
- `"order"`: is the order of the Earth's gravity model.

Recommended Values:
```jsonc
"geopotential": {
    "model": "egm96.txt",
    "degree": 4,
    "order": 4
}
```

## 2.5 `"perturbations"` JSON Definition

Optional JSON object defining orbital perturbations to include.
Currently, only third body effects from the Sun and the Moon are supported as extra perturbations outside of the non-Spherical Earth model.

Field Types:
```jsonc
"perturbations": {
    "third_bodies": [<string>, ...] // Optional, Default is an empty list
}
```

Field Definitions:
- `"third_bodies"` defines which third bodies to include in perturbations. The only valid options currently are `"Sun"` and `"Moon"`

Recommended Values:
```jsonc
"perturbations": {
    "third_bodies": ["Sun", "Moon"]
}
```

## 2.6 `"decision"` JSON Definition

Required JSON object defining the decision algorithm used to optimize the reward matrix.
It is **highly** recommended that users simply set `"name": "MunkresDecision"` unless they understand the differences.
Please refer to the `resonaate.tasking.decisions` sub-package for more information.

Field Types:
```jsonc
"decision": {
    "name": <string>, // Required, no default
    "parameters": {} // Optional, default is an empty JSON object
}
```

Field Definitions:
- `"name"` defines which decision algorithm to implement when dynamically tasking sensors. The valid options are:
    - `"MyopicNaiveGreedyDecision"` allows for observation saturation
    - `"MunkresDecision"` is the most balanced and robust decision method
    - `"RandomDecision"` is only recommended for comparison studies
- `"parameters"` defines extra arguments taken by each decision algorithm. Only `"RandomDecision"` takes an extra argument, which is `"seed": <integer>` for seeding the RNG.

Recommended Values:
```jsonc
"decision": {
    "name": "MunkresDecision"
}
```

## 2.7 `"reward"` JSON Definition

Required JSON object defining the reward algorithm and the metrics it uses.
It is **highly** recommended that users implement the recommended values unless they understand the differences.
Please refer to the `resonaate.tasking.rewards` and `resonaate.tasking.metrics` sub-packages for more information.

Field Types:
```jsonc
"reward": {
    "name": <string>, // Required, no default
    "metrics": [<metric_obj>, ...], // Required, no default
    "parameters": {} // Optional, default is an empty JSON object
}
```

Field Definitions:
- `"name"` defines which function to calculate the total reward. The valid options are:
    - `"CostConstrainedReward"` constrains the reward by multiplying by the sign of a stability metric and subtracting the sensor metric
    - `"SimpleSummationReward"` simply add an arbitrary number metrics together
    - `"CombinedReward"` similar to `"CostConstrainedReward"` but includes a reward to counteract target "staleness"
- `"metrics"` defines which metrics to include in the reward calculation and their parameters. See [below](#271-metric-object-definition) for more information.
- `"parameters"` defines extra arguments taken by each decision algorithm. `"CostConstrainedReward"` and `"CombinedReward"` can take an optional extra argument `"delta"`. This parameter defines the weighting between the information and sensor metrics. It is `0.85` by default, but is valid in the range `0.0 < delta < 1.0`.

Recommended Values:
```jsonc
"reward": {
    "name": "CostConstrainedReward",
    "metrics": [
        {
            "name": "ShannonInformation",
            "parameters": {} // Leave empty
        },
        {
            "name": "DeltaPosition",
            "parameters": {} // Leave empty
        },
        {
            "name": "LyapunovStability",
            "parameters": {} // Leave empty
        }
    ]
}
```

### 2.7.1 Metric Object Definition

Required JSON objects to include in the `"metrics"` field of the `"reward"` JSON object.

Field Types:
```jsonc
<metric_obj>: {
    "name": <string>, // Required, no default
    "parameters": {} // Required, default is an empty JSON object
}
```

Field Definitions:
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

## 2.8 Target Object Definition

There are two ways to define a target agent:

1. Classical orbital elements (COE)
    ```jsonc
    <target_obj>: {
        "sat_num": <integer>, // NORAD catalog number or unique simulation ID
        "sat_name": <string>, // Unique simulation name, associated with SATCAT name if RSO
        "init_coe": <coe_object> // Classical orbital element object defined at "start_timestamp"
    }
    ```
1. ECI state vector
    ```jsonc
    <target_obj>: {
        "sat_num": <integer>, // NORAD catalog number or unique simulation ID
        "sat_name": <string>, // Unique simulation name, associated with SATCAT name if RSO
        "init_eci": [  // J2000 initial state vector defined at "start_timestamp"
            <decimal>, <decimal>, <decimal>, // ECI "x", "y", and "z" positions  (km)
            <decimal>, <decimal>, <decimal>  // ECI "x", "y", and "z" velocities (km/sec)
        ]
    }
    ```

### 2.8.1 COE Object Definition

Note that there are several iterations of COE sets.
An orbit can be described by any of the iterations defined below.

1.
    ```jsonc
    <coe_object>: {
        "orbitAlt": <decimal>,      // Altitude above the Earth's mean equatorial radius (kilometers)
        "ecc": <decimal>,           // Orbit's eccentricity  (unitless)
        "incl": <decimal>,          // Orbit's inclination (degrees)
        "rightAscension": <decimal>,// Right Ascension of the Ascending Node (degrees)
        "argPeriapsis": <decimal>,  // Argument of Periapsis/Perigee (degrees)
        "trueAnomaly": <decimal>    // True Anomaly (degrees)
    }
    ```
1.
    ```jsonc
    <coe_object>: {
        "orbitAlt": <decimal>,
        "ecc": <decimal>,
        "incl": <decimal>,
        "trueLongPeriapsis": <decimal>, // True Longitude of Periapsis for eccentric,
                                        //     equatorial orbits (degrees)
        "trueAnomaly": <decimal>
    }
    ```
1.
    ```jsonc
    <coe_object>: {
        "orbitAlt": <decimal>,
        "ecc": <decimal>,
        "incl": <decimal>,
        "rightAscension": <decimal>,
        "argLatitude": <decimal> // Argument of Latitude for circular, inclined orbits (degrees)
    }
    ```
4.
    ```jsonc
    <coe_object>: {
        "orbitAlt": <decimal>,
        "ecc": <decimal>,
        "incl": <decimal>,
        "trueLongitude": <decimal> // True Longitude for circular, equatorial orbits (degrees)
    }
    ```

## 2.9 Sensor Object Definition

The default SOSI network is defined in "SSN Specifications OpenSource v1.8".
Sensor agents can be defined as `"GroundFacility"` for ground-based sensors or `"Spacecraft"` for space-based sensors. Also, sensing agents can have multiple types of sensors: `"Optical"`, `"Radar"`, `"AdvRadar"`.

### 2.9.1 Common Sensor Fields

These are fields defined for all types of sensor objects.
```jsonc
<sensor_obj>: {
    "id": <integer>, // NORAD catalog number or unique simulation ID
    "name": <string>, // Unique simulation name, associated with SATCAT name if RSO
    "covariance": [<decimal>, <decimal>, ...], // Sensor measurement uncertainty matrix
    "slew_rate": <decimal>, // Sensor's maximum angular slew speed (rad/sec)
    "efficiency": <decimal>, // Sensor efficiency value
    "aperture_area": <decimal>, // Sensor aperture area (m^2)
    "sensor_type": <string>, // Type of sensor
    "host_type": <string>, // Type of agent
    "azimuth_range": [<decimal>, <decimal>], // Max/min az sensor limits (rad, rad)
    "elevation_range": [<decimal>, <decimal>], // Max/min el sensor limits (rad, rad)
    "exemplar": [<decimal>, <decimal>] // Ideal observation capability defined as target area and range (m^2, km)
}
```

The shape/size of `"covariance"` depends on the `"sensor_type"` field:
- `"Optical"`: 2x2 measurement uncertainty
    ```json
    [
        [a^2, ab], // a: azimuth std in radians
        [ab, b^2]  // b: elevation std in radians
    ]
    ```
- `"Radar"`: 3x3 measurement uncertainty
    ```json
    [
        [a^2, ab, ac], // a: azimuth std in radians
        [ab, b^2, bc], // b: elevation std in radians
        [ac, bc, c^2], // c: range std in kilometers
    ]
    ```
- `"AdvRadar"`: 4x4 measurement uncertainty
    ```json
    [
        [a^2, ab, ac, ad], // a: azimuth std in radians
        [ab, b^2, bc, bd], // b: elevation std in radians
        [ac, bc, c^2, cd], // c: range std in kilometers
        [ad, bd, cd, d^2], // d: range rate std in kilometers/seconds
    ]
    ```

### 2.9.2 Sensor Types

Different types of sensors require different extra fields in the JSON sensor object.

1. `"sensor_type": "Optical"` requires no extra fields
1. `"sensor_type": "Radar"` and `"sensor_type": "AdvRadar"` require:
    ```jsonc
    <sensor_obj>: {
        "tx_power": <decimal>, // Radar transmit power (W)
        "tx_frequency": <decimal> // Radar operational center frequency (Hz)
    }
    ```

### 2.9.2 Sensing Agent Types

Different types of sensing agents require different extra fields in the JSON sensor object.

1. `"host_type": "GroundFacility"` requires
    ```jsonc
    <sensor_obj>: {
        // Defines sensor's terrestrial location at "start_timestamp"
        "lat": <decimal>, // Geodetic latitude, (rad)
        "lon": <decimal>, // Geodetic longitude, (rad)
        "alt": <decimal>  // Height above ellipsoid, (km)
    }
    ```
1. `"host_type": "Spacecraft"` requires:
    ```jsonc
    <sensor_obj>: {
        "eci_state": [
            // Defines satellite ECI state at "start_timestamp"
            <decimal>, <decimal>, <decimal>, // J2000 "x", "y", & "z" positions (km)
            <decimal>, <decimal>, <decimal>  // J2000 "x", "y", & "z" velocities (km/sec)
        ]
    }
    ```

## 2.10 Target Event Definition

**NOTE: This is deprecated and will not be used.**

```jsonc
<target_event_obj>: {
    "affectedTargets": [<string>, ...],         // list of 'satNum's corresponding to targets
    "eventType": "IMPULSE",                     // Describes an impulsive maneuver
    "jDate": <decimal>,                         // Julian Date defining when the maneuver takes place
    "frame": "NTW",                             // Can also be "ECI"
    "deltaV": [<decimal>, <decimal>, <decimal>] // Acceleration vector of impulse
}
```

## 2.11 Sensor Event Definition

**NOTE: This is deprecated and will not be used.**

# 3. Configuration File Format

To initialize a scenario using a JSON file, the `Scenario::fromConfigFile()` method is passed a filepath to a main config JSON file formatted in the following way:

```jsonc
<init_message>: {
    "time": {}, // Required JSON object defining scenario time properties
    "noise": {}, // Optional JSON object defining noise characteristics
    "propagation": {}, // Optional JSON object defining how RSOs are propagated
    "geopotential": {}, // Optional JSON object defining the Earth geopotential model
    "perturbations": {}, // Optional JSON object defining orbital perturbations to include
    "decision": {}, // Required JSON object defining the decision algorithm used to optimize the reward matrix
    "reward": {}, // Required JSON object defining the reward algorithm and the metrics it uses
    "target_set": <string>, // Required relative filepath to JSON file defining target agents
    "sensor_set": <string>, // Required relative filepath to JSON file defining sensor agents
    "target_event_set": <string>, // Not currently in use, defaults to empty string: ""
    "sensor_event_set": <string>  // Not currently in use, defaults to empty string: ""
}
```

A majority of the definitions from [JSON Configuration Object Definition](#2-json-configuration-object-definition) apply here, but the following replacements are required:
- `"targets"` replaced for `"target_set"`
- `"sensors"` replaced for `"sensor_set"`
- `"target_events"` replaced for `"target_event_set"`, but not used so it can be left out
- `"sensor_events"` replaced for `"sensor_event_set"`, but not used so it can be left out

These replacements are to better organize scenario configuration files when running many scenarios.
Instead of defining the lists of target and sensor objects in the main file, the new fields point to separate JSON files which include only the target or sensor objects.

For example, if the config below was in **/app/init.json**, it would point to files at **/app/targets/leo_only.json** and **/app/sensors/complete_ssn.json**, respectively.
```jsonc
{
    "time": {...},
    "noise": {...},
    "propagation": {...},
    "geopotential": {...},
    "perturbations": {...},
    "decision": {...},
    "reward": {...},
    "target_set": "targets/leo_only.json",
    "sensor_set": "sensors/complete_ssn.json"
}
```

Passing **/app/init.json** to `Scenario.fromConfigFile()` would automatically read the files defined by `"target_set"` and `"sensor_set"` above.
Those files would then have the following format:
- Target JSON configuration file
    ```jsonc
    {
        "targets": [
            <target_obj>,
            <target_obj>,
            ...
        ]
    }
    ```
- Sensor JSON configuration file
    ```jsonc
    {
        "sensors": [
            <sensor_obj>,
            <sensor_obj>,
            ...
        ]
    }
    ```
Where the `<target_obj>` and `<sensor_obj>` are defined exactly the same as in [Target Object](#28-target-object-definition) and [Sensor Object](#28-target-object-definition), respectively.
