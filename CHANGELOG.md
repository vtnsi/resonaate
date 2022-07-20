# Release History

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## \[Unreleased\]

- Added

  - `getStandardDeviation` and `getConfidenceRegion` functions in `resonaate.physics.statistics`
  - `fov` input variable to `sensorFactory()`
  - EOPs from 06-10-2021 to 17-03-2022
  - `subtendedAngle()` in `physics/math`
  - `observation` variable to `scenario/config/__init__/`
  - `field_of_view` variable to `config/agent_config/`
  - `config/observation_config`
  - `field_of_view` variable to `sensors/sensor_base/` in the `**sensor_args`
  - `collectObservations()`, `checkTargetsInView()`, `inFOV()`, `canSlew()` to `sensors/sensor_base/`
  - `tests/sensor/test_fov`
  - `visual_cross_section`, `mass`, `reflectivity` config options for `Agent` objects
  - `detectable_vismag`, `min_range`, `max_range` sensor config options
  - Default values on a per-sensor basis for sensor `detectable_vismag`, `min_range`, `max_range`
  - `Optical.isVisible()` now checks solar phase angle and apparent vismag
  - Unit tests for `sensor_utils.py`
  - Unit tests for `Sensor`

- Changed

  - `AsyncExecuteTasking()` now calls `collectObservations` instead of `makeNoisyObservation`
  - chi-square test functions now accept `ndarray` as inputs
  - `_getSolarRadiationPressureAcceleration()` is now a class function of `SpecialPerturbations`
  - Metric calculations only take in 1 estimate agent and sensor agent
  - `FilterDebugFlag` is now `FilterFlag` and all filter debugging is handled in `SequentialFilter._debugChecks`

- Deprecated

- Removed

  - `DEFAULT_VIZ_X_SECTION` and all references to it
  - `services` sub-package as well as all corresponding tests, documentation, & references
  - argument `truth` in `EstimateAgent._update()`

- Fixed

  - FOV tests now reliably pass, properly call `updateReductionParameters`
  - Incorrect `Sensor.maximum_range` check, fixes #40 along with other small errors

## \[1.4.0 - 2022-06-06\]

- Added

  - **.vscode/settings.json** for auto-formatting rules
  - configurations for `black`, `isort`, `prettier`, `mdformat`, & `pre-commit`
  - `Manifest.in` for source dist & CI job for checking
  - `pyproject.toml` for build requirements
  - `shutdown()` methods to `Scenario` for gracefully shutting down, fixes bug #106
  - `physics.statistics` with chi-square statistic tests
  - Test coverage pipeline job
  - `FilterDebugFlag` to `SequentialFilter` for tracking debug
  - Debugging logic for filters now directly handled by `EstimateAgent`
  - Unit tests for maneuver detection and `filters` factory
  - `julian_date_start` variable to `StationKeeping.fromInitECI()`
  - Check if initial orbit is eccentric to `KeepLeoUp` Station Keeping class
  - `data.filter_step` for filter property exports to database
  - `getFilterStep` and `saveFilterStep` functions to `agents.estimate_agents`
  - `Jupiter`, `Venus`, and `Saturn` objects to `third_body.py`
  - `estimation` package
  - Unit tests for adaptive `estimation` package
  - Scheduled maneuver events have `planned` attribute, so that the filter does not flag them as a detection

- Changed

  - Format all `.py`, `.md`, `.json`, `.yaml` files
  - Updated `flake8` configs with new extensions
  - Split tool configs from `setup.cfg` into tool-specific config files
  - `nut80.dat` now lives in `physics/data/nutation` directory
  - `physics/data` directories are now packages/modules
  - CI jobs are now more parallel, only waiting on direct `needs`
  - Split `.gitlab-ci.yml` jobs into separate files
  - Converted `pkg_resource` usage to `importlib.resources`
  - Properly catch `KeyboardInterrupt` in `__main__.py` and shutdown
  - Removed `host` attribute from `SequentialFilter` which decouples filters and `EstimateAgent` objects
  - Made the package-level `__init__.py` dynamically create `LABEL` constants for simpler factory methods
  - filter factory function now properly takes a `FilterConfig` object
  - Made maneuver detection language more consistent and direct
  - Adjusted NIS `ManeuverDetection` techniques to account for heterogeneous observations
  - Move `filters.statistics` to `physics.maneuver_detection`
  - `ManeuverDetection` data table to `DetectedManeuver` for better delineation
  - Move `ManeuverDetection` handling to `EstimateAgent`
  - Split testing into parallel jobs, and made them run without requiring passed check stage
  - Improved fixture usage across all tests
  - Modified event handling so it can occur between timesteps
  - Station keeping is now its own section in the target configs

- Deprecated

- Removed

  - `requirements/` directory -> moved deps into `setup.py` for now...
  - `setup.cfg` because it was becoming very hard to manage
  - Support for YAML config files, dropped `pyyaml` dep. See respect library for converter tool
  - `SingularMatrix` filter debugging because it's irrelevant now
  - Removed `Epoch` data dependency from event configs
  - `filter` package for `estimation`

- Fixed

  - Usage of deprecated `pkg_resources`
  - Small bug with how `calcMeasurementMean` corrected for different angular domains
  - GitLab runner, so we can use pipelines again

## \[1.3.0 - 2022-03-04\]

- Added

  - `physics.orbits` package with new `OrbitalElement` class interface
  - Supporting astrodynamics functions, utilities, & algorithms
  - Unit tests for `orbits` package as well as `math` module
  - Valid limits on eccentricity & inclination to properly define singular cases
  - More unit tests for bodies package
  - General relativity acceleration correction for Earth-orbiting satellites
  - Ability to toggle GR & SRP perturbations in the configuration settings
  - Multiple sections to HTML docs: "Getting Started", "Reference Material", "Technical Background", "For Developers"
  - Proper docstrings to all package **__init__.py** files
  - Copy button and bibliography Sphinx extensions
  - Mermaid flowchart/diagram extension that works with MyST
  - Sphinx Gallery extension for examples
  - `IsAngle` enum class to track whether measurements are angles or not
  - `dt_step` to all `Agent` classes
  - Detailed documentation in the `noise.py` module
  - Separate std values in config for initial estimate error
  - Conversions between spherical & cartesian coordinates
  - Conversions to/from Az/El, RaDec and common reference frames
  - Unit tests to cover all functions in `physics.transforms.methods`
  - `flight_path_angle` property to `Orbit`
  - `ObservationTuple` for easier passing of observation
  - Improved filtering documentation to better explain the API
  - **parallel/handlers** directory with various parallel job handlers
  - Simpler architecture for parallel job execution by refactoring
  - `Agent.time` property for easily accessing the current agent's epoch
  - `physics.math.normalizeAngleNegPiPi()` and `physics.math.normalizeAngle2Pi()`
  - `tests/physics.math`
  - Valid config option to use `"DOP853"` as a ODE solver
  - Suite of `ConfigError`s that more verbosely explain configuration issues
  - `data.events` module
  - `TargetAddition`, `SensorAddition`, and `AgentRemoval` events
  - Installation instructions for bare metal installation
  - Instructions for making RESONAATE containers and running them
  - Added sensor time bias event with test cases
  - Added "events" config option to init.json messages
  - Added ""station_keeping", "target_realtime_propagation", "sensor_realtime_propagation" init message options
  - Added continuous state change events: finite maneuvers and finite burns
  - filter/statistics.py file with NIS Class
  - Maneuver Detection inside `update()` step of `UnscentedKalmanFilter`
  - `data.queries` module
  - Unit tests to cover all functions in `data.queries`

- Changed

  - Updated installation and tutorial information in docs
  - Moved to using MyST as the main documentation parser, allowing Markdown rather than reStructuredText
  - API docs to use `autosummary` extension rather than `api-docs`
  - Moved unnecessary re-sampling of sigma points in `predict` step to `forecast()`
  - No longer used the re-sampled predicted estimated on no-observation steps, but instead us the predicted mean (zero-th predicted sigma point)
  - `"initial_error_magnitude"` is now split into separate values: `"init_position_std_km"` and `"init_velocity_std_km_p_sec"`
  - Default config values for noise parameters
  - References of "Observation Vector" to "Slant Range Vector" for clarification
  - Renamed **example_data** to **configs** to clarify usage a bit more.
  - Refactored sigma point generation into function
  - Refactored looping calculations in UKF to use `map()`
  - Simplified how `Scenario` and `CentralizedTaskingEngine` need to use/call parallel job handlers
  - Moved all linting into **setup.cfg**
  - `BehavioralConfig.debugging.DatabaseURL` to `DatabasePath`
  - Moved `createDatabasePath()` into **data** directory
  - Moved `saveDatabase()` to be a `ResonaateDatabase` method
  - Changed `ManualSensorTask` to `TargetTaskingPriority` in the new `data.events` module
  - Changed `Propulsion` events to `ScheduledImpulseEvent`s
  - Updated scenario configuration documentation
  - Passing entire target Agent object into `makeNoisyObservation()`

- Deprecated

  - `"initial_error_magnitude"` key in the `"noise"` config object
  - `"init_estimate_error"` key in `Estimate.fromConfig()` `dict`
  - In-memory database functionality for `ResonaateDatabase`: will be removed completely when we move to PostgreSQL

- Removed

  - old `orbit.py` module
  - `jplephem` as a dependency
  - Use of `Redis` inside `UnscentedKalmanFilter`
  - `::retrogress()` & several unnecessary attributes from `SequentialFilter`
  - Custom parallel logic in **agents**, **scenario**, & **tasking/engines**
  - `physics.math.normalizeAngle()`, replaced with `normalizeAngleNegPiPi()` and `normalizeAngle2Pi()`
  - `--no-db` and `--auto-db` CLI arguments
  - Type assertions, and replaced with `TypeError` exceptions
  - `Scenario.addNode()` method
  - **tests/networks** directory
  - "realtime_propagation" init message option

- Fixed

  - Skipped station-keeping test to pass
  - Converted all `super()` calls to not use arguments, so it's more Python 3 oriented
  - Broken and old style docstrings
  - Deprecated empty `np.ndarray` check in `Celestial.propagate()`
  - Tasking engine unit tests by removing the mocked classes. Pickling mocked objects doesn't behave well.
  - `JobTimeoutError` bug (#103) introduced by !47, fixed by !56

## \[1.2.0\] - 2021-06-14

- Added

  - New sensor network config for dedicated SSN sensors
  - `angularMean()` math function
  - Logging helper functions for one-off logs
  - Skew-symmetric & 1st Chebyshev functions
  - Scenario/Simulation config sub-package for all valid JSON/YAML objects/options under `resonaate.scenario.config`
    - See !27 for details on how this was implemented
  - `Agent` DB table entry object
  - `Epoch` DB table entry object
  - New `build` and `upload` stages to CI pipeline, along with `sast` test job
  - **tasks.json** file for starting/stopping Redis through VS Code tasks
  - `__hash__()` magic method for `JulianDate` and `ScenarioTime` objects
  - `__version__` attribute to top-level **resonaate/__init__.py** for easier version tracking
  - Unit tests for all modules in **resonaate/data**
  - Unit tests for all modules in **resonaate/common**
  - Various **datafiles** for performing unit tests
  - Ability to dump an in-memory database to disk at the end of a simulation
  - Calling `WorkerManager.stopWorkers()` at the end of simulation
  - `EarthOrientationParameter` dataclass object for tracking EOPs outside of DB
  - `dynamics.integration_events` module that includes station keeping and impulsive maneuvers
  - `Celestial` class to `dynamics` module for functionality shared between space based agents

- Changed

  - Change `normalizeAngle()` to `wrapAngle()`
  - Make `Agent::setCallback()` abstract, and define in concrete classes
  - Split database architecture into `ResonaateDatabase` and `ImporterDatabase`
    - `ResonaateDatabase` for produced data
    - `ImporterDatabase` for **read-only** data ingested into RESONAATE
  - Move all DB table objects to use a relational model
    - Reference `Agent` and `Epoch` objects with `ForeignKey` constraint
    - More efficient storage and querying
  - Improve `DataInterface::getSharedInterface()` logic
  - Move `assess()` definition into `TaskingEngine` abstract class
  - Make `ResonaateDatabase` explicitly defined in `Scenario` constructor
  - Add whether to use `ImporterDatabase` to `Scenario` & `PropagateJobHandler` constructors and `TaskingEngine::assess()`
  - Moved CLI functionality into separate module **resonaate/common/cli.py** and added new options for improved DB architecture
  - Improve **resonaate/common/utilities.py** module error handling & added unit tests
  - Move **external_data** to **resonaate/physics/data**
  - Allow proper packaging of RESONAATE by including data files and using `resource_filename`
  - Move nutation parts into separate **resonaate/physics/transforms/nutation.py** module & cache the function call
  - `config.propagation.realtime_propagation` defaults to `True`
  - Refactor imported estimate/observation logic into separate functions `PropagateJobHandler::loadImportedEphemerides()` and `CentralizedTaskingEngine::loadImportedObservations()` respectively
  - Minor improvements to entry-point script in **resonaate/__main__.py**
  - Improvements and clarifications to **README.md** and **CONTRIBUTING.md** for new users
  - Updates to **initialization.md** and **interface.md** for all requisite changes
  - Update **launch.json** to use debugging configurations with and without db saving
  - `Task` objects are now `Jobs` to deconflict with sensor "tasking"
  - `TaskingData` is now called `Task` to be more consistent
  - EOPs are no longer kept in the databases, but are loaded from disk and cached

- Deprecated

  - JSON/YAML config formats to fit new scenario config class
  - Options `PhysicsModelDataPath` and `EphemerisPreLoaded` for config file aren't needed
  - `EarthOrientationParams` is no longer a valid DB table

- Removed

  - **scripts** directory, and put in the SDA Post Processing/SDA Analysis repo
  - `NutationParams` DB table entry object because it is not dynamic data nor is it very large
  - Excess pre-loaded truth data for unit tests
  - `insertData()`, `deleteData()`, & `bulkSave()` from `ImporterDatabase` because it supposed to be **read-only**
  - `ImporterDatabase` initialization from `ScenarioBuilder` constructor
  - `events` module

- Fixed

  - North-facing sensors' azimuth mask was not handled properly causing `isVisible()` to always return false (#78)
  - `TaskingEngine.observations` weren't reset unless `getCurrentObservations()` was called (#79)
  - Config values of `0` were not handled, and so those field were set to the default value (#77)
  - Config `"random_seed": null` was not handled. Changed valid option to `"os"` (#76)
  - No **output** directory caused RESONAATE to crash (#54)
  - `TaskingData` were published to DB with `julian_date_start` rather than `julian_date_epoch` (commit 28ef305c)
  - DB table equality operator (commit 7df42e9a5)
  - Fix issue with `JulianDate` subtraction & comparison operators (commits a1a6f2489 and 31f29420b)

## \[1.1.1\] - 2021-03-25

Fix environment variable reading security issue and change Git workflow docs.

- Changed

  - Documentation on release process and Git workflow

- Removed

  - Feature to read environment variable pointing to config file (#62)

## \[1.1.0\] - 2021-03-24

Update that includes LPAR sensors and multiple sensor networks.

- Added

  - Engine config object
  - Large & medium target config sets
  - Capability to designate separate sensor networks & target sets for different tasking engines
  - `asyncUpdateEstimate()` for separately applying observations _a posteriori_
  - `AllVisibleDecision` class for high-volume sensors like LPAR

- Changed

  - Split `EstimateAgent` update and `executeTasking` parallelization into separate files
  - `sensor_list` passed to `asyncCalculateReward()` for down-selecting this engine's sensors
  - `target_num` passed to `asyncExecuteTasking()`
  - moved parallelization of executing tasks and applying observations to `Scenario`

- Removed

  - `networks` sub-package as it is no longer useful
  - debugging logic in `metrics` sub-package that was leftover

- Fixed

  - new pylint & flake8 errors

## \[1.0.1\] - 2021-01-21

Added new `Scenario` factor methods. Also updated documentation for new formats.

- Added

  - `Scenario.parseConfigFile()` static method for automatically parsing main the scenario configuration file
  - `Scenario.fromConfigFile()` factory method for creating `Scenario` from a given file path

- Changed

  - Added old updates to CHANGELOG for better repo tracking
  - `Scenario.fromConfig()` factory method to accept only properly built JSON objects/dictionaries
  - `scenario` unit tests fixed for new factory methods

- Fixed

  - Outdated scenario configuration documentation in `initialization.md`

## \[1.0.0\] - 2021-01-14

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
  - `safeArcCos()` now properly checks for non-rounding cases when called
  - Small corner-case sign errors in reference frame rotations
  - Incorrect lighting conditions

## \[0.9.0\] - 2020-10-20

Mostly config/refactoring updates since the initial port.

- Added

  - Empty db files for testing

- Changed

  - `UKF` and `TwoBody` perform multiple ODEs at once
  - `SpecialPerturbations` solves multiple ODEs at once
  - Removed "sosat" out of all files.
  - Renamed source code folder to resonaate.

- Fixed

  - `KLDivergence` hotfix
  - `UKF` bugs

## \[0.0.0\] - 2020-05-08

Initial version ported to a new repository.

- Added

  - MunkresDecision & MyopicGreedyDecision functions for optimizing the reward matrix.
  - Multiple reward functions to combine metrics in different ways
  - TimeSinceObservation metric for considering observation frequency
  - KLDivergence metric for comparing information gains
  - Unit test for all modules in the tasking package
  - De-duplication of imported observations
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
