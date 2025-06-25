# Release History

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Versioning

This project is currently under *rapid development*, and so our versioning does not necessarily follow Semantic Versioning.
We use a Major, Minor, Patch versioning scheme, but only patch version updates are not supposed to break backwards compatibility.
Minor version updates can (and likely will) break some API assumptions, as they add new features or change the usage of current features.
Major version updates are reserved for changes such as complete redesigns of key packages or changes that require a complete reinstallation.

______________________________________________________________________

<!-- START TOC -->

<!-- TOC Formatted for GitLab -->

<!-- markdownlint-disable MD036 -->

<!-- markdownlint-disable MD049 -->

**Table of Contents**

[[_TOC_]]

<!-- markdownlint-enable MD036 -->

<!-- markdownlint-enable MD049 -->

<!-- END TOC -->

______________________________________________________________________

## [Unreleased][unreleased-diff]

### Added

*for new features*

### Changed

*for changes in existing functionality*

### Deprecated

*for soon-to-be removed features*

### Removed

*for now removed features*

### Fixed

*for any bug fixes*

### Security

*in case of vulnerabilities*

### Test

*for test suite specific improvements*

### Development

*for improving developer tools & environment*

### CI

*related to the continuous integration system*


## [4.1.0][v4.1.0] - 2025-06-24

### Added

- `TLELoader` object into `physics.orbits.tle`.
- `teme2ecef` conversion function into `physics.transforms.methods`.
- `getSmaFromMeanMotion` function into `physics.orbits.utils`.
- TEME to ECEF conversion method
- Ability to update EOP data and select a custom source location.
- Behavioral Config option for your default EOP data location.
- Multiple loader objects for updating EOP data: `DotDatLoader`, `ModuleDotDatLoader`, `LocalDotDatLoader`, `RemoteDotDatLoader`.
- Improved documentation for database schemas in `resonaate.data`.
- Configuration option to save filter step information in `EstimationConfig`.
- Additional columns to the `FilterStep` object.
- `np.ndarray` to JSON string conversion utilities.
- Ability to save `FilterStep` objects to the database.
- `common.labels.GeopotentialModel` enum
- `common.labels.StationKeepingRoutine` enum
- `common.labels.DecisionLabel` enum
- `common.labels.RewardLabel` enum
- `common.labels.MetricLabel` enum
- `physics.orbits.ResidentStratification` class to encapsulate orbit designation information/defaults
- `scenario.config.state_config` orbital elements are now validated based on limits expressed in docstrings
  - **WARNING**: *this could break existing input config files*, but I don't think it's enough of a change to warrant a version bump
- option for multi-level caching of reduction parameters
- `estimation.particle.particle_filter` Support for particle filters with relevant labels and configuration objects
- `estimation.particle.genetic_particle_filter` An initial, simple particle filter implementation with relevant labels and configuration objects
- `dynamics.dynamics_base.DynamicsErrorFlag` enum for controlling certain propagation errors
- `physics.maths.vecResiduals` a numpy vectorized residual calculation
- `physics.maths.vecWrapAngle2Pi` a numpy vectorized angle wrapping funciton
- `physics.maths.vecWrapAngleNeg` a numpy vectorized angle wrapping funciton

### Changed

- replaced custom configuration code (i.e. `ConfigObject`, `ConfigObjectList`, and associated errors) with Pydantic models/validators
- `TargetAgentConfig` now just known as `AgentConfig`
- most `enum.Enum`s now inherit from `str` for easier Pydantic handling
- `ScheduledImpulse` classes and burn methods are now mapped directly to `ThrustFrame` enum via the `impulse` and `thrust` properties respectively
- added `ManeuverType` enum that maps maneuver types to thrust methods via `thrust` property
- replaced `physics.sensor_utils.getFrequencyFromString()` with `.FrequencyBand` enum and `mean` property
- `estimation` module factory method conventions rely more on config objects and mappings, rather than conditionals
- `tasking` module factory method conventions rely more on config objects and mappings, rather than custom registries
- refactored reduction parameters (see `pysics.transforms.reductions.ReductionParams`)
- iteratively store `Agent`s as Ray remote objects to replace centralized `Agent` caching
  - ~~agent caching methodology now available via `agents.agent_cache` module~~
- incorporate `EstimateAgent` rework to remove duplicate 'update' definitions and calls
  - implement formal `Result` hierarchy for `Filter` results
  - reimplement `strmbrkr` `KeyValueStore` using a Ray Actor
- refactor 'importer' paradigm into its own `dynamics` module
- refactor `checkThreeSigmaObs()` -> `checkThreeSigmaObservation()` to reduce dependency on old agent cache implementation
- replace `job_handlers` classes with Ray implementations that abstract away a lot of the old `Job` passing boilerplate code
  - This resulted in lots of changes to...
    - `Scenario` (in particular `::stepForward()`)
    - `CentralizedEngine` (in particular `::assess()`)
  - ...to update how parallel processing is called
- refactor `CentralizedEngine._createLoadedObs()` -> `::_attachObsMetadata()`
- fixed the bulk propagator in `dynamics.celestial.Celestial.propagateBulk`
- dynamics now accept flags for certain stop conditions

### Deprecated

*for soon-to-be removed features*

### Removed

- Removed `resonaate.physics.transforms.eops.DEFAULT_EOP_DATA` constant.
- orbit-dependent platform constants from `agents` module (see `physics.orbits.ResidentStratification` addition)
- reduction parameters are no longer cached due to performance of `strmbrkr` kvs
- remove `createFilterDebugDict()` and `logFilterStep()` debug methods since we save `FilterStep` objects to the database now

### Fixed

*for any bug fixes*

### Security

*in case of vulnerabilities*

### Test

- Added test to ensure proper functionality of the EOP update functionality.
- Added testing for `np.ndarray` to JSON string conversions.
- Added testing for new `FilterStep` properties.
- Modified existing testing for `EstimationConfig` to inlcude new configuration option.
- tests had to be updated to accommodate pydantic migration changes

### Development

- suppress `sphinx` duplicate cross reference warning
- remove `.python-version` because I wanted to use 3.11 and it was messing with my `uv` venv
- change `.gitignore` to ignore timeline files produced by Ray, rather than old `strmbrkr` artifacts
- update license to Apache V2
- fix some outdated readme information
- add project metadata to `pyproject.toml`

### CI

*related to the continuous integration system*

## [4.0.0][v4.0.0] - 2024-05-08

### Added

- add `residual()` and `residuals()` function to `resonaate.maths` (see !245)

### Changed

- EstimateAgent.\_update() logic split into sub-functions (see !164)
- Several logic improvements for MMAE & IOD start and convergence handling (see !164)
- Reordered Optical visibility calculations in increasing complexity (see !191)
- reordered `SequentialFilter.checkManeuverDetection()` to return early (see !245)
- make sigma point resampling an option that is set on UKF creation (see !245)
- organize UKF methods for clarity & refactor into smaller methods (see !245)
- a few names of variables and exceptions to adhere to pep8-naming (see !302)
- refactored `mjolnir` references to `strmbrkr`

### Deprecated

*for soon-to-be removed features*

### Removed

*for now removed features*

### Fixed

- SRP perturbation would not work without setting "sun" third body (see #184)
- `AllVisibleDecision` config sensor type check (see #187)
- Duplicate IOD logging (see !164)
- GPB1 & SMM post-convergence re-initialization (see !164)
- Ability to turn MMAE and IOD on simultaneously (see !164)
- UKF parameter overwritten when `kappa=0` (see !245)
- Sensor boresight and time_last_tasked were not being updated (see #203)
- Properly point RESONAATE at valid `mjolnir` version (see #207 & !299)

### Security

*in case of vulnerabilities*

### Test

- Add tests to cover `EstimateAgent` (see !164)
- Add tests to cover `UnscentedKalmanFilter` (see !245)

### Development

- Migrated to usage of `ruff` for linting, removing `flake8` and all plugins completely as well as most of `pylint` (see #194 & !239)
- Apply various fixes for new linting rules from `ruff` (see !239)
- Develop dependency conflict (see #206 & !298)
- Update `make install` to use new `mjolnir` optional dependency (see !299)
- Added docstring linting back using `ruff` (see #44)
- Remove `pylint` as a dev tool (see #208)
- Add several new ruff rules and apply (see !302)

### CI

- Added 3.12 nightly test job (see !299)
- Allow nightly test jobs to fail once and retry (see !299)

## [3.0.0][v3.0.0] - 2023-04-07

### Breaking Changes

- upgraded the minimum supported Python to 3.9, dropping support for 3.7 and 3.8 (see #148 and !191)
  - switch our custom `methdispatch()` to `singledispatchmethod()`
  - `MagicMock.call_args` includes `kwargs` attribute
  - use walrus operator (`:=`) in several places
  - replaced deprecated `importlib.resources` funcs with newly added ones
  - removed `Optional` and `Union` type hints for new syntax
- moved responsibility for managing the shared DB connection from `DateInterface.getSharedInterface()` to `setDBPath()` and `getDBConnection()` (see #179 and !199)
- split `AgentConfig` into several smaller classes and adjust config specification (see #37 and !163)

### Fixed

- infinite loop catch in `lambertUniversal()` (see commit fe802bd2dd)
- rounding of seconds when converting from `datetime.datetime` to `JulianDate` (see commit 58d032bd)
- `asyncExecuteTasking()` incorrectly calling `collectObservations()` with `EstimateAgents` (see commit bdfc3834, introduced by !2)
- duplicate `isVisible()` calls from within `collectObservations()` (see commit bdfc3834)
- no FoV checks against the tasked `TargetAgent` when background observations aren't being collected (see !83)
- indexing logic of `SensingAgent` objects in `TaskingEngine` causing infeasible tasks (see !90)
- passing only background targets from `asyncExecuteTasking()` to `collectObservations()` (see !84)
- incorrect VCS units in `apparentVisualMagnitude()` (see commit ef241f0f4)
- sun unit vector in `checkSpaceSensorLightingConditions()` (see #161)
- unit test failures due to ZMQ errors in `mjolnir` (see #159)
- SqlAlchemy 2.0 failures due to old API, implemented interim fix (see commit fd63168d)
- incorrect relative state calculation in `eci2rsw()` transformation (see commit e6851c9f7)
- incorrect updating of `delta_boresight` (see #180 and !198)
- overuse of `updateReductionParameters()` since `getReductionParameters()` properly handles if they aren't updated (see #142)
- TeX errors in documentation causing `make latexpdf` to fail (see !213)
- obscure SQLAlchemy bug when creating the database before importing `AgentModel` (see #183 and !212)
- tests hanging when using TCP protocol (see #171 and !217)

### Added

#### `resonaate.common` package

- `labels.py` module for storing options (see !163)

#### `resonaate.data` package

- tracking missed observations via `MissedObservation` table (see #125)
- `Observation` contains sensor ECI state vector columns and `sensor_eci` property (see #46 and !127).
- `db_connection.py` module for handling the shared database interface with `setDBPath()`, `getDBConnection()`, and `clearDBPath()` (see #179 and !199)

#### `resonaate.physics` package

- `eci2lla()`, `eci2rsw()`, `eci2radec()` coordinate frame transformations
- `checkGalacticExclusionZone()` conditional check
- `lambertGauss()` orbit determination algorithm (see !157)

#### `resonaate.scenario` package

- `SensorConfig`, `RadarConfig`, `AdvRadarConfig`, and `OpticalConfig` for handling sensor-specific configuration options (see #36 and !163)
- `PlatformConfig`, `SpacecraftConfig`, and `GroundFacilityConfig` for handling agent 'vehicle' configuration options (see #37 and !163)
- `StateConfig`, `ECIStateConfig`, `LLAStateConfig`, `COEStateConfig`, and `EQEStateConfig` for handling agent's initial state information (see #35 and !163)

#### `resonaate.sensors` package

- `FieldOfView` class for generalizing field of view definitions and constraints (see !92)
- `Measurement` and `MeasurementType` classes to decouple sensor and measurement logic (see #146 and !130)

#### `resonaate.tasking` package

- tasking metric normalization via `calculateRewards()` and `normalizeMetrics()` (see #15)
- `UncertaintyMetric` and `StateMetric` base classes and implementations for covariance/state focused metrics, (see #153 and !136)

### Changed

#### Dependencies

- bump `mjolnir` version to 1.3.1
- removed `concurrent-log-handler` dependency

#### JSON Configs

- default engines use `SimpleSummationReward` and `TimeSinceObservation`
- renamed `cost_constrained_ssn.json` to `summation_ssn.json` and `cost_constrained_space.json` to `summation_space.json`
- all JSON configs with `AgentConfig` objects were converted to support the refactor for #37 and !163

#### `resonaate.data` package

- queries of imported observations and ephemerides use `Epoch.timestampISO` instead of `julian_date`
- added `Measurement` to `Observation` (see #156 and !141)
- renamed `Observation.position_long_rad` to `position_lon_rad`
- renamed `SensorAdditionEvent.host_type` to `platform`
- `SensorAdditionEvent`, `TargetAdditionEvent` attributes `sensor` and `target` renamed to `sensor_agent` and `target_agent` respectively (see !163)

#### `resonaate.dynamics` package

- finite burn and maneuvers take `agent_id` so they can properly log to the `EventStack` (see !191)

#### `resonaate.job_handler` package

- added a `missed_observation` key to the `dict` returned by `asyncExecuteTasking()`
- `asyncCalculateReward()` calculates individual metrics instead of reward to support metric normalization (see !131)

#### `resonaate.physics` package

- `subtendedAngle()` accepts `safe` arg for using `safeArccos()` instead of `np.arccos()`
- updated EOP data included within RESONAATE (see commit 1ec535b7a)
- moved measurement functions (like `getAzimuth()`) to `physics.measurement_utils` module
- added `utc_date` parameter to `updateReductionParameters()` (see #49 and !80)
- added `utc_date` parameter to `getReductionParameters()` (see #49 and !80)
- `getReductionParameters()` caches results and re-calculate if `utc_date` doesn't exist or doesn't match the value in the KVS (see #49 and !80)
- added `utc_date` parameter to coordinate frame transformations which use reductions directly or indirectly (see #49 and !80)
- `determineTransferDirection()` checks orbital period instead of true anomaly, so only a position vector is needed (see #170 and !153)
- renamed `getWavelengthFromString()` to `getFrequencyFromString()`

#### `resonaate.scenario` package

- `Scenario.saveDatabaseOutput()` inserts times into `Epoch` database table if it does not already exist
- moved `PropagationConfig.realtime_observation` to `ObservationConfig` and renamed `ObservationConfig.field_of_view` to `background` (see !83)
- `ScenarioClock` is initialized with a UTC `datetime`, instead of a `JulianDate`
- `SensorConfig.minimum_range` defaults to `None`. The default for optical sensors is `0.0` and for radar sensors is set based on `tx_frequency`
- configs objects assume degrees across the board (see #34 and !163)
- refactored `AgentConfig` into several classes `PlatformConfig`, `StateConfig`, and `SensorConfig` to divide responsibility (see #37 and !163)
- split `ScenarioBuilder` construction into several smaller methods (see #38 and !169)
- renamed `SensorConfig.aperture_area` to `aperture_diameter` (see !185)
- `RadarConfig.min_detectable_power` is required
- `SensorConfig.field_of_view` defaults to `RectangularFoV` (see !163)

#### `resonaate.sensors` package

- `collectObservations()` takes `estimate_eci` state vector instead of `EstimateAgent` object
- `Sensor.isVisible()` returns a `bool` for visibility and an `Explanation` for why the RSO was not visible
- refactored `Sensor.inFOV()` into `FieldOfView` classes (see !92)
- `MeasurementType.calculate()`, `Measurement.calculateMeasurement()`, and `getSlantRangeVector()` take sensor/target ECI states and UTC as parameters (see #158)
- refactored (and validated) `getEarthLimbConeAngle()` into `getBodyLimbConeAngle()` and `checkSpaceSensorEarthLimbObscuration()` (see #155)
- renamed `Sensor.aperture_area` to `effective_aperture_area`
- moved `sensors.measurement` to `physics.measurements` and combined with `physics.measurement_utils` (see #176 and !186)
- refactored `fieldOfViewFactory()` and most of `sensorFactory()` into respective `fromConfig()` class methods (see #176 and !186)
- `Sensor.collectObservations()` slews sensor boresight to target before attempting observations (see !198)

#### `resonaate.tasking` package

- `Decision.calculate()` logically `ANDs` decision and visibility matrices (see #154 and !147)
- `TaskingEngine.assess()` takes `datetime` bounds instead of `JulianDate` bounds
- moved `Metric.METRIC_TYPE` strings to `MetricTypeLabel` constants
- renamed `BehaviorMetric` to `TargetMetric`
- `Decision.calculate()` takes the visibility matrix as a parameter (see #154 and !147)
- rewards no longer must be positive (see #154 and !147)

### Deprecated

- `ImporterDatabase.loadObservationFile()` fails unless the sensor `r_matrix` is passed as an argument

### Removed

- `NoiseConfig.dynamics_noise_magnitude`, `NoiseConfig.dynamics_noise_type`, `TargetAgent.process_noise` because they aren't used (see commit 58f72522)
- `Sensor.exemplar` and corresponding config field for better minimum/maximum range calculations
- `ObservationTuple` and `Sensor.buildSigmaObs()` because logic moved into `Measurement` class (see #156 and !141)
- `DataInterface.getSharedInterface()` the shared connection is managed in `db_connection` module (see #179, !192, and !199)

### Test

- added regression test of the number of obs generated by the `main_init.json` on the first timestep
- added `pytest-cov` as a testing dependency to better manage coverage results
- small typing fix that was incompatible with 3.7
- added back cobertura coverage report for MR coverage gutters (see !85)
- added `MissedObservation` conditional tests
- tests skip flaky event integration tests because it's not reproducible (see #115)
- added default coverage options for easier use of `pytest --cov`
- stop importing from `conftest.py`, move things into `__init__.py` modules (see !192)
- fixed testing bug where DB creation order was incorrect, refactor into easier-to-use fixtures (see #178 and !192)
- moved integration and regression tests into their own test modules (see !192)
- `ImporterDatabase` tests now actually run and check themselves (see !192)

### Development

- added several small documentation clarifications
- attempted to fix `pylint` false positives of `invalid-name` in tests (see #129)
- fixed `flake8` ignores for A001/A003, updated `pre-commit` hook versions (see !151)
- moved `coverage` configs to `pyproject.toml` (see !150)
- added top-level `Makefile` for easily making docs and cleaning files up
- added more `make` targets for common developer commands (see !197)

### CI

- test jobs run against a *properly* installed RESONAATE package, see #32
- only the unit tests are included in coverage statistics
- added scheduled job config for testing against multiple Python versions, see #33
- standard jobs skipped during scheduled jobs

## [2.0.0][v2.0.0] - 2022-09-06

### Added

- Initial state vectors (at the initial `Epoch`) are saved to the DB, see #114

### Changed

- all references to Redis throughout the code have been refactored to use the `mjolnir` package, see #52
- all references to Redis throughout the documentation have been removed, see #52
- stop overuse of `ABC` when no abstract methods declared
- `WorkerManager` instantiation in `Scenario` object now adheres to `debugging.ParallelDebugMode` config option

### Removed

- RESONAATE no longer requires Redis to be running in the background to work, see #52

### Fixed

- null `Observation` objects produced during tasking when not using FoV feature, see !69

### Development

- pylance "unreachable code" false-positive caused by `np.cross()`

### CI

- Changed removed `cobertura` field for `junit` to produce XML test data

## [1.5.2][v1.5.2] - 2022-08-26

### CI

- Fix release notes format for `release-notes` CI job
- Make `publish-pkg` job wait until release stage is complete before running

## [1.5.1][v1.5.1] - 2022-08-26

### Fixed

- Updated `release-notes` job to use an Ubuntu image instead to fix #112

## [1.5.0][v1.5.0] - 2022-08-24

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
- README in `tests` and `.gitlab` folders
- Documentation on the CI system, developer workflows, GitLab labels, style guide & release procedure (see #58 and #59)

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

- Updated merge request & issue templates with better instructions/auto-labels (see #58)

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
[unreleased-diff]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v3.0.0...develop
[v1.0.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/commits/v1.0.0
[v1.0.1]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.0.0...v1.0.1
[v1.1.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.0.1...v1.1.0
[v1.1.1]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.1.0...v1.1.1
[v1.2.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.1.1...v1.2.0
[v1.3.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.2.0...v1.3.0
[v1.4.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.3.0...v1.4.0
[v1.5.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.4.0...v1.5.0
[v1.5.1]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.5.0...v1.5.1
[v1.5.2]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.5.1...v1.5.2
[v2.0.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v1.5.2...v2.0.0
[v3.0.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v2.0.0...v3.0.0
[v4.0.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v3.0.0...v4.0.0
[v4.1.0]: https://code.vt.edu/space-research/resonaate/resonaate/-/compare/v4.0.0...v4.1.0
[`black`]: https://black.readthedocs.io/en/stable/index.html
[`isort`]: https://pycqa.github.io/isort/
[`pre-commit`]: https://pre-commit.com/
[`prettier`]: https://prettier.io/
[`resp3ct`]: https://code.vt.edu/space-research/resonaate/resp3ct
