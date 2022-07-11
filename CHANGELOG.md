# Release History

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Versioning

This project is currently under *rapid development*, and so our versioning does not necessarily follow Semantic Versioning.
We use a Major, Minor, Patch versioning scheme, but only patch version updates are not supposed to break backwards compatibility.
Minor version updates can (and likely will) break some API assumptions, as they add new features or change the usage of current features.
Major version updates are reserved for changes such as complete redesigns of key packages or changes that require a complete reinstallation.

______________________________________________________________________

<!-- Start TOC -->

**Table of Contents**

- [Release History](#release-history)
  - [\[Unreleased\]](#unreleased)
  - [\[1.4.0 - 2022-06-06\]](#140---2022-06-06)
  - [\[1.3.0 - 2022-03-04\]](#130---2022-03-04)
  - [\[1.2.0\] - 2021-06-14](#120---2021-06-14)
  - [\[1.1.1\] - 2021-03-25](#111---2021-03-25)
  - [\[1.1.0\] - 2021-03-24](#110---2021-03-24)
  - [\[1.0.1\] - 2021-01-21](#101---2021-01-21)
  - [\[1.0.0\] - 2021-01-14](#100---2021-01-14)
  - [\[0.9.0\] - 2020-10-20](#090---2020-10-20)
  - [\[0.0.0\] - 2020-05-08](#000---2020-05-08)

______________________________________________________________________

<!-- END TOC -->

______________________________________________________________________

## [Unreleased][unreleased-diff]

### Added

- `getStandardDeviation()` and `getConfidenceRegion()` functions in `physics.statistics`
- EOPs from 06-10-2021 to 17-03-2022
- `subtendedAngle()` in `physics.math` module
- `observation` field to `ScenarioConfig`
- `field_of_view` field to `SensingAgentConfig`
- `ObservationConfig` class
- `field_of_view` argument to `Sensor.__init__()` base class
- `collectObservations()`, `checkTargetsInView()`, `inFOV()`, `canSlew()` to `Sensor` base class
- `visual_cross_section`, `mass`, `reflectivity` config options for `Agent` objects
- `detectable_vismag`, `min_range`, `max_range` sensor config options
- Default values on a per-sensor basis for sensor `detectable_vismag`, `min_range`, `max_range`
- `Optical.isVisible()` now checks solar phase angle and apparent visual magnitude
- Add a `ParallelMixin` class that requires a `shutdown()` method be overwritten, inherited by parallel classes (see !39)
- Replaced all `__del__()` with `shutdown()` for parallel classes (see !39)
- `estimation.initial_orbit_determination` module for IOD during a scenario (see !1)
- `physics.orbit_determination.lambert` for classical algorithms of orbit determination (see !1)
- `EstimateAgent._attemptInitialOrbitDetermination` to handle application of IOD (see !1)
- `initialOrbitDeterminationFactory()` function (see !1)
- `initial_orbit_determination` config option for setting IOD, defaults to NO_SETTING (see !1)
- `lambertBattin()` orbit determination method (see !1)
- docs `make serve` target for serving the HTML documentation (see #57)

### Changed

- `asyncExecuteTasking()` now calls `collectObservations()` instead of `makeNoisyObservation()`
- chi-square test functions now accept `ndarray` as inputs
- `_getSolarRadiationPressureAcceleration()` is now a class function of `SpecialPerturbations`
- Metric calculations only take in 1 estimate agent and sensor agent
- `FilterDebugFlag` is now `FilterFlag` and all filter debugging is handled in `SequentialFilter._debugChecks()`
- `ConfigObject` classes are now `dataclasses`, reducing boilerplate code (#27 & !31)
- Renamed `data.agent.Agent` to `AgentModel` to reduce doc conflicts

### Deprecated

### Removed

- `DEFAULT_VIZ_X_SECTION` and all references to it
- `services` sub-package as well as all corresponding tests, documentation, & references
- argument `truth` in `EstimateAgent._update()`
- all (for real this time) `__del__()` (see !39)
- `lambertMinEnergy()` and `lambertGauss()` orbit determination methods (see !1)

### Fixed

- Incorrect `Sensor.maximum_range` check, fixes #40 along with other small errors
- `Decision`, `Reward`, & `Metric` subclasses register themselves with their own class name, directly (see !39)
- `TaskingEngine` now auto-sorts the sensors/targets to prevent undefined behavior on insertion/deletion (see !39)
- Testing bug (#64) where `ScenarioClock` created a DB and didn't reset the tables

### Security

### Test

- FOV tests now reliably pass, properly call `updateReductionParameters()`
- Unit tests for `sensor_utils.py`
- Unit tests for `Sensor`
- Unit tests for Sensor FOV
- Improve coverage of `tasking.engine` & fix slow test case (see !39)
- Remove all `try` import statements in the test modules to address #31 (see !39)
- Improve unit test mocking code by making it more uniform: mainly `create_autospec()` in **most** places (see !39)
- Reduce usage of global mocking fixtures (see !39)
- Add type annotation support to test modules (see !39)

### Development

### CI

- Automated release job for creating release notes and publishing a release on GitLab (see #24)
- Improved CI pipeline/job organization into more reuseable portions

## [1.4.0][v1.4.0] - 2022-06-06

### Added

- `.vscode/settings.json` for auto-formatting rules
- configurations for [`black`], [`isort`], [`prettier`], & [`pre-commit`]
- `Manifest.in` for source dist & CI job for checking
- Initial `pyproject.toml` for build requirements
- `Scenario.shutdown()` for gracefully shutting down, fixes bug [#106][old - #106]
- `physics.statistics` module with $\chi^2$ statistic tests
- `FilterDebugFlag` to `SequentialFilter` for tracking debug
- `julian_date_start` argument to `StationKeeping.fromInitECI()`
- initial orbit eccentricity check to `KeepLeoUp` station-keeping
- `FilterStep` DB table for saving filter properties
- `EstimateAgent.getFilterStep` and `EstimateAgent.saveFilterStep`
- `Jupiter`, `Venus`, and `Saturn` objects to `third_body.py`
- `planned` attribute to "Scheduled" maneuver events, so that the filter does not flag them as a detection

### Changed

- Debugging logic for filters now handled by `EstimateAgent`
- Renamed `filters` sub-package to `estimation`
- Format all `.py`, `.md`, `.json`, `.yaml` files with [`black`], [`isort`], [`prettier`], & [`pre-commit`]
- `physics/data` directories are now sub-packages
- `nut80.dat` now lives in `physics.data.nutation` sub-package
- CI jobs are now more parallel, only waiting on direct `needs`
- Split `.gitlab-ci.yml` jobs into separate files
- Converted instances of `pkg_resource` to use `importlib.resources`
- Properly catch `KeyboardInterrupt` in `runResonaate()` and shutdown
- Removed `host` attribute from `SequentialFilter` which decouples filters and `EstimateAgent` objects
- filter factory function now takes a `FilterConfig` object
- Made maneuver detection language more consistent and direct
- Adjusted NIS `ManeuverDetection` techniques to account for heterogeneous observations
- Rename `filters.statistics` module to `estimation.maneuver_detection`
- `ManeuverDetection` data table to `DetectedManeuver` for better delineation
- Move `ManeuverDetection` handling to `EstimateAgent`
- Modified event handling to occur between time steps
- Add `"station_keeping"` field to `TargetConfig`

### Removed

- Official support for YAML config files, dropped `pyyaml` dep. See [`resp3ct`] library for converter tool
- `SingularMatrix` filter debugging
- `Epoch` data dependency from base class `EventConfig`
- `filters` sub-package

### Fixed

- Small bug with how `calcMeasurementMean()` corrected for different angular domains

## [1.3.0][v1.3.0] - 2022-03-04

### Added

- `physics.orbits` sub-package with new `OrbitalElement` class interface
- Valid limits on eccentricity & inclination to properly define singular cases
- General relativity acceleration correction for Earth-orbiting satellites
- Ability to toggle general relativity & solar radiation pressure perturbations via the config
- "Getting Started", "Reference Material", "Technical Background", "For Developers" documentation sections
- Copy button and bibliography Sphinx extensions
- Mermaid flowchart/diagram extension that works with MyST
- Sphinx Gallery extension for examples
- `IsAngle` class to track whether measurements are angles or not
- `dt_step` to all `Agent` classes
- Separate *std* values in config for initial estimate error
- Conversions between spherical & Cartesian coordinates
- Conversions to/from Azimuth/Elevation, Right Ascension/Declination coordinates and common reference frames
- `ObservationTuple` to contain related data used multiple places
- `parallel.handlers` sub-package with various parallel job handlers
- `Agent.time` property for easily accessing the current agent's epoch
- `physics.math.normalizeAngleNegPiPi()` and `physics.math.normalizeAngle2Pi()`
- Config option to use `"DOP853"` as a ODE solver
- Suite of `ConfigError` exceptions that more verbosely explain configuration issues
- `data.events` module for tracking discrete `Event` in the simulation
- `TargetAddition`, `SensorAddition`, `AgentRemoval`, & `SensorTimeBias` events
- `ContinuousStateChangeEvent` maneuvers: `ScheduledFiniteThrust`, `ScheduledFiniteManeuver`, & `ScheduledFiniteBurn`
- Installation instructions for bare metal installation
- Instructions for making RESONAATE containers and running them
- `"events"` config field to main JSON config definition
- `"station_keeping"`, `"target_realtime_propagation"`, `"sensor_realtime_propagation"` config options
- `filters.statistics` module with functions for normalized innovations squared definitions
- Maneuver detection logic in `UnscentedKalmanFilter.update()`
- `data.queries` module for easily generating common DB queries

### Changed

- Update installation and tutorial documentation
- Use MyST as the main documentation parser, allowing Markdown rather than reStructuredText
- API docs use `autosummary` extension rather than `api-docs`
- Moved re-sampling of sigma points in `predict` step to `forecast()`, was re-sampling too often
- Use the predicted mean (first predicted sigma point) on no-observation filter steps
- `"initial_error_magnitude"` is now split into separate values: `"init_position_std_km"` and `"init_velocity_std_km_p_sec"`
- Default config values for noise parameters
- References of "Observation Vector" to "Slant Range Vector"
- Renamed `example_data` to `configs`
- Refactored sigma point generation into separate function
- Refactored looping calculations in UKF to use `map()`
- Simplified `Scenario` and `CentralizedTaskingEngine` calls to parallel job handlers
- `BehavioralConfig.debugging.DatabaseURL` to `BehavioralConfig.debugging.DatabasePath`
- Moved `createDatabasePath()` into `data` sub-package
- Moved `saveDatabase()` to be a method of `ResonaateDatabase`
- `ManualSensorTask` to `TargetTaskingPriority` in the new `data.events` sub-package
- `Propulsion` events to `ScheduledImpulseEvent`
- Passing `TargetAgent` into `makeNoisyObservation()`
- Converted all `super()` calls to not use arguments, Python 3 style
- Replace type `assert` statements with `TypeError` exceptions
- `physics.math.normalizeAngle()`, replaced with `normalizeAngleNegPiPi()` and `normalizeAngle2Pi()`

### Deprecated

- In-memory database functionality for `ResonaateDatabase`: will be removed completely when we move to PostgreSQL

### Removed

- `"initial_error_magnitude"` key in the `"noise"` config object
- `"init_estimate_error"` key in `Estimate.fromConfig()` argument `dict`
- old `orbit` module
- `jplephem` dependency
- Use of `Redis` inside `UnscentedKalmanFilter`
- `retrogress()` & several unnecessary attributes from `SequentialFilter`
- Custom parallel logic in `agents`, `scenario`, & `tasking.engines` sub-packages
- `--no-db` and `--auto-db` CLI arguments
- `Scenario.addNode()` method
- `tests/networks` directory
- `"realtime_propagation"` JSON config option

### Fixed

- `JobTimeoutError` bug ([#103][old - #103]) introduced by [!47][old - !47], fixed by [!56][old - !56]
- Empty `np.ndarray` check in `Celestial.propagate()`

## [1.2.0][v1.2.0] - 2021-06-14

### Added

- Sensor network config for dedicated SSN sensors
- `angularMean()` function for calculating the circular mean with and without weights
- Logging helper functions for one-off log calls
- Skew-symmetric & 1st Chebyshev functions
- Scenario/Simulation config sub-package for all valid JSON/YAML objects/options under `resonaate.scenario.config`
  - See [!27][old - !27] for details on how this was implemented
- `Agent` & `Epoch` DB table entry object
- New `build` and `upload` stages to CI pipeline
- `tasks.json` file for starting/stopping Redis through VS Code tasks
- `__hash__()` method for `JulianDate` and `ScenarioTime` objects
- `__version__` attribute to top-level `resonaate/__init__.py`
- Function to dump an in-memory database to disk at the end of a simulation
- `EarthOrientationParameter` dataclass object for tracking EOP outside of DB
- `dynamics.integration_events` which includes station-keeping and impulsive maneuvers
- `Celestial` class to `dynamics` for common interface shared between space dynamics models

### Changed

- `Agent.setCallback()` is abstract, and defined in concrete classes
- Split database architecture into `ResonaateDatabase` and `ImporterDatabase`
  - `ResonaateDatabase` for data produced during simulations
  - `ImporterDatabase` for **read-only** data ingested into the simulation
- DB table objects use a proper relational model
- Move `assess()` definition into `TaskingEngine` abstract class
- `ResonaateDatabase` explicitly defined in `Scenario` constructor
- Moved CLI functionality into separate module `common.cli` and added new options for improved DB usage
- `common.utilities` module error handling
- Move `external_data` to `resonaate/physics/data` directory
- Proper packaging of RESONAATE by including data files and using `resource_filename`
- Move nutation calculations into separate `physics.transforms.nutation` & cache the data
- `config.propagation.realtime_propagation` defaults to `True`
- Refactor imported estimate/observation logic into separate functions `PropagateJobHandler.loadImportedEphemerides()` and `CentralizedTaskingEngine.loadImportedObservations()`
- Minor improvements to entry-point script in `resonaate/__main__.py`
- `launch.json` debugging configurations with and without db saving
- `Task` objects are now `Jobs` to prevent a naming conflict with sensor tasking
- `TaskingData` is now named `Task`, see above
- Earth orientation parameters are no longer kept in the databases, but are loaded from disk and cached
- JSON/YAML config to fit new `ScenarioConfig` class

### Removed

- `EarthOrientationParams` & `NutationParams` are no longer a valid DB table, can be cached
- Options `PhysicsModelDataPath` and `EphemerisPreLoaded` for behavioral config file
- `scripts` directory, and put in a separate project
- Large fraction of the preloaded truth data for unit tests
- `insertData()`, `deleteData()`, & `bulkSave()` from `ImporterDatabase` because it is **read-only**
- `ImporterDatabase` initialization from `ScenarioBuilder` constructor
- `events` module

### Fixed

- Properly call `WorkerManager.stopWorkers()` at the end of simulation
- North-facing sensors' azimuth mask was not handled properly causing `isVisible()` to always return false ([#78][old - #78])
- `TaskingEngine.observations` weren't reset unless `getCurrentObservations()` was called ([#79][old - #79] & [!39][old - !39])
- Config values of `0` were not handled, and so those field were set to the default value ([#76][old - #76] & [!37][old - !37])
- Config `"random_seed": null` was not handled. Changed valid option to `"os"` ([#77][old - #77] & [!38][old - !38])
- No `output` directory caused RESONAATE to crash ([#54][old - #54])
- `TaskingData` were published to DB with `julian_date_start` rather than `julian_date_epoch`
- DB table equality operator
- `JulianDate` subtraction & comparison operators

## [1.1.1][v1.1.1] - 2021-03-25

Fix environment variable reading security issue and change Git workflow docs.

### Changed

- Documentation on release process and Git workflow

### Security

- Feature to read environment variable pointing to config file (see [#62][old - #62])

## [1.1.0][v1.1.0] - 2021-03-24

Update that includes multiple sensor networks.

### Added

- `EngineConfig` object
- Large & medium target config sets
- Designate separate sensor networks & target sets for different tasking engines
- `asyncUpdateEstimate()` for separately applying observations _a posteriori_
- `AllVisibleDecision` class for high-volume sensors like large phased array radars

### Changed

- Split `EstimateAgent` update and `executeTasking()` parallelization into separate files
- `sensor_list` passed to `asyncCalculateReward()` for down-selecting this engine's sensors
- `target_num` passed to `asyncExecuteTasking()` for down-selecting this engine's targets
- moved parallelization of executing tasks and applying observations to `Scenario`

### Removed

- `networks` sub-package
- debugging logic in `metrics` sub-package

## [1.0.1][v1.0.1] - 2021-01-21

Added new `Scenario` factor methods. Also updated documentation for new formats.

### Added

- `Scenario.parseConfigFile()` for automatically parsing main the scenario configuration file
- `Scenario.fromConfigFile()` for creating `Scenario` from a given file path

### Changed

- `Scenario.fromConfig()` factory method accepts only proper JSON objects/dictionaries
- `scenario` unit tests fixed for new factory methods

### Fixed

- Outdated scenario configuration documentation in `initialization.md`

## [1.0.0][v1.0.0] - 2021-01-14

Large update to a "Version 1.0" of the RESONAATE tool. This is to make a hard stop where main architectural changes and major features were completed and introduced bugs were fixed.

### Added

- CI/CD integration for automated testing/linting
- Support for YAML scenario configuration files
- Debug mode for runs, including a CLI argument. Allows blocking behavior in the workers
- Warning and logging for de-orbiting satellites at 0 km & 100 km altitude, resp.
- `sensor_utils.py` module for common sensor-related calculations
- `scenario` sub-package for holding modules directly related to the `Scenario` class
- Integration method attribute in scenario configuration
- `Reward` type combining cost-constrained & staleness metric
- Redis password is retrievable via an environment variable `REDIS_PASSWORD`, or `None`

### Changed

- Updated `requirements.txt`, and split out development tool requirements
- Moved factory methods into their respective class definitions
- `BehavioralConfig` is settable. It requires `getConfig()` to be called
- `DataInterface` now uses a context manager for the DB session object
- Filter debugging logic is now its own module
- `Clock` class now associated with `scenario` sub-package
- Streamlined the `Scenario` factory pattern & `Sensor` class
- `Decision` callable interface no longer accepts `visibility_matrix` as an argument

### Removed

- `TaskingEngine` being an attribute of `Network` objects
- Duplicate `sensors.observation.Observation` class because it can be handled by the DB table class
- `observation_factory.py` module

### Fixed

- `safeArcCos()` now properly checks for non-rounding cases when called
- Small corner-case sign errors in reference frame rotations
- Incorrect lighting conditions

## 0.9.0 - 2020-10-20

Mostly config/refactoring updates since the initial port.

### Added

- Empty db files for testing

### Changed

- `SpecialPerturbations` and `TwoBody` propagate multiple ODE at once, reflected in `UKF` as well
- Renamed source code folder to `resonaate`.

### Fixed

- `KLDivergence` hotfix
- `UKF` bugs

## 0.0.0 - 2020-05-08

Initial version ported to a new repository.

### Added

- Multiple reward & decision `callable` classes for tasking
- `TimeSinceObservation` metric for considering observation frequency
- `KLDivergence` metric for comparing information gains
- Deduplicate of imported observations
- Database interface for outputting data, rather than writing to JSON files
- New DB table `Task` for storing tasking information

### Changed

- Moved `metrics`, `rewards`, `core`, `decisions` packages into a combined `tasking` sub-package
- `tasking` package is now modular, and can be customized from a JSON configuration file
- `async_functions.py` logic for new tasking API
- JSON config file format, added many more options for propagation, noise, target set, sensor set, time span, etc.
- Module/package structure and names for better organization
- Refactored parallel processing logic into its own sub-package `parallel`
- Renamed `Config` to `BehavioralConfig` to separate from `ScenarioConfig`
- `Agent` API by creating `TargetAgent`, `SensingAgent`, and `EstimateAgent` classes

### Removed

- Old JSON config file format no longer works
- `central_core_30.py` and `central_core_40.py` modules
- `user_interface.py` module
- `copyable.py` module

### Fixed

- Streamlined visibility calculations

<!-- Links to issues & merge requests-->

[old - !27]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/merge_requests/27
[old - !37]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/merge_requests/37
[old - !38]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/merge_requests/38
[old - !39]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/merge_requests/39
[old - !47]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/merge_requests/47
[old - !56]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/merge_requests/56
[old - #103]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/issues/103
[old - #106]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/issues/106
[old - #54]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/issues/54
[old - #62]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/issues/62
[old - #76]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/issues/76
[old - #77]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/issues/77
[old - #78]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/issues/78
[old - #79]: https://gitlab.hume.vt.edu/sda/resonaate-group/resonaate/-/issues/79
[unreleased-diff]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.4.0...develop
[v1.0.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/commits/v1.0.0
[v1.0.1]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.0.0...v1.0.1
[v1.1.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.0.1...v1.1.0
[v1.1.1]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.1.0...v1.1.1
[v1.2.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.1.1...v1.2.0
[v1.3.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.2.0...v1.3.0
[v1.4.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.3.0...v1.4.0
[`black`]: https://black.readthedocs.io/en/stable/index.html
[`isort`]: https://pycqa.github.io/isort/
[`pre-commit`]: https://pre-commit.com/
[`prettier`]: https://prettier.io/
[`resp3ct`]: https://code.vt.edu/space-research/resonaate/resp3ct
