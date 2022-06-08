# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

- [Changelog](#changelog)
  - [[Unreleased]](#unreleased)
  - [[1.0.0] - 2021-01-14](#100---2021-01-14)
  - [[0.9.0] - 2020-10-20](#090---2020-10-20)
  - [[0.0.0] - 2020-01-16](#000---2020-01-16)

## [Unreleased]

N/A

## [1.0.0] - 2021-01-14

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

## [0.9.0] - 2020-10-20

First release to get the process going. Mostly config/refactoring updates since the initial port.

## [0.0.0] - 2020-01-16

Initial scrubbed version ported to code.vt.edu. See Hume GitLab repository for further history.
