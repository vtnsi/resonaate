# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

- [Changelog](#changelog)
    - [[Unreleased]](#unreleased)
    - [[1.0.1] - 2021-01-21](#101---2021-01-21)
    - [[1.0.0] - 2021-01-14](#100---2021-01-14)
    - [[0.9.0] - 2020-10-20](#090---2020-10-20)
    - [[0.0.0] - 2020-05-08](#000---2020-05-08)

### [Unreleased]

N/A

### [1.0.1] - 2021-01-21

Small fixes to the `ResonaateService` class and supporting API. Also updated documentation for new formats.

- Added
  - `Scenario.parseConfigFile()` static method for automatically parsing main the scenario configuration file
  - `Scenario.fromConfigFile()` factory method for creating `Scenario` from a given filepath

- Changed
  - Added old updates to CHANGELOG for better repo tracking
  - `Scenario.fromConfig()` factory method to accept only properly built JSON objects/dictionaries
  - `scenario` & `services` unit tests fixed for new factory methods

- Fixed
  - Outdated scenario configuration documentation in `initialization.md`
  - Outdated RESONAATE service ICD in `interface.md`

### [1.0.0] - 2021-01-14

Large update to a "Version 1.0" of the RESONAATE tool. This is to make a hard stop where main architectural changes and major features were completed and introduced bugs were fixed.

- Added
  - CI/CD integration for automated testing/linting
  - Added support for YAML scenario configuration files
  - Debug mode for runs, including a CLI argument. Allows blocking behavior in the workers
  - Warning and logging for de-orbiting satellites at 0km & 100km altitude, resp.
  - `sensor_utils.py` module for common sensor-related calculations
  - New `scenario` sub-package for holding modules directly related to building `Scenario` objects
  - Integration method for ODE propagation in scenario configuration
  - Reward class combining cost-constrained & staleness metric

- Changed
  - Updated requirements.txt, and split out development tool requirements
  - Moved factory methods into their respective class definitions for a simpler interface
  - Made `BehavioralConfig` able to be properly set, requires `getConfig()` to be called
  - `DataInterface` now uses a context manager for the DB session object
  - Move Kalman filter debugging logic into own module for common usage purposes
  - Cleaned the `parallel` module
  - `Clock` class now associated with `scenario` sub-package
  - Streamlined the `Scenario` factory pattern greatly
  - Clarified and fixed the `Sensor` classes to make a lot more sense
  - Small updates to repo boilerplate: requirements.txt, linting config
  - Made unit tests directory more organized

- Deprecated
  - `Decision` objects callable interface no longer accepts `visibility_matrix` as an argument
  - `ObservationData` DB table objects are now `Observation` DB table objects. DBs are incompatible

- Removed
  - `TaskingEngine` being an attribute of `Network` objects
  - Duplicate `sensors.observation.Observation` class because it can be handled by the DB table class
  - `observation_factory.py` module

- Fixed
  - Redis password is now retrieved via an environment variable `REDIS_PASSWORD`, or `None`
  - `safeArgCos()` now properly checks for non-rounding cases when called
  - Small corner-case sign errors in reference frame rotations
  - Incorrect lighting conditions

### [0.9.0] - 2020-10-20

Mostly config/refactoring updates since the initial port.

- Added
  - Unit tests for `resonaate_service` sub-package
  - Empty db files for testing

- Changed
  - `UKF` and `TwoBody` perform multiple ODEs at once
  - `SpecialPerturbations` solves multiple ODEs at once
  - Removed "sosat" out of all files.
  - Renamed source code folder to resonaate.

- Fixed
  - `KLDivergence` hotfix
  - `UKF` bugs

### [0.0.0] - 2020-05-08


- Added
  - MunkresDecision & MyopicGreedyDecision functions for optimizing the reward matrix.
  - Multiple reward functions to combine metrics in different ways
  - TimeSinceObservation metric for considering observation frequency
  - KLDivergence metric for comparing information gains
  - Unit test for all modules in the tasking package
  - De-duplication of imported observations
  - `services` package for various service-layer related modules
  - Database interface for outputting data, rather than writing to JSON files
  - Tasking information to a new DB table

- Changed
  - Moved metrics, rewards, core, decisions packages into a combined tasking package
  - The tasking package is now modular in the algorithms chosen, and can be specified from a JSON configuration file
  - Simplified tasking engine API
  - `async_functions.py` logic for new tasking API
  - Multiple updates/fixes to factory methods & `ScenarioConfig`
  - JSON config file format, added many more options for propagation, noise, target set, sensor set, time span, etc.
  - Various updates to module/package structure and names for better organization
  - Refactored parallel processing logic into its own module
  - Many Updates associated with `agents` package API changes
  - Renamed `Config` to `BehavioralConfig` to separate from `ScenarioConfig`

- Deprecated
  - Old JSON init file format no longer works

- Removed
  - `central_core_30.py` and `central_core_40.py` modules
  - `user_interface.py` module
  - `copyable.py` module
  - Various deprecated folders and files that are no longer relevant

- Fixed
  - Clarified the `Agent` API by creating `TargetAgent`, `SensingAgent`, and `EstimateAgent` classes. This allows for easier variation in sensor vs. target agent types.
  - Streamlined visibility calculations
