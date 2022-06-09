(ref-service-top)=
# Service Layer

The {mod}`resonaate` application interface (which contains the core operations of RESONAATE) will be contained within a service layer named {class}`.ResonaateService`.
The {class}`.ResonaateService` will handle incoming input messages and outgoing output messages on the testbed.

The general flow of the {class}`.ResonaateService` layer follows a looping paradigm.
Each loop starts with polling incoming messages from other services or the test bed itself.
There are several different types of messages that the service layer is set up to handle, each described below.

-------------------------------------------------
<!-- TOC formatted for sphinx -->
:::{contents} Table of Contents
:depth: 2
:backlinks: none
:local:
:::

-------------------------------------------------

(ref-service-sec-init)=
## Init Message

The {class}`.InitMessage` is used by the {mod}`resonaate` tool to initialize simulation properties, targets, and the sensor network.
The {class}`.InitMessage` input is rigidly defined by Virginia Tech in the {ref}`ref-cfg-top` file.

To construct a {class}`.Scenario` (the interface used to propagate the physics model and generate data), code similar to the following snippet can be used:

```python
# Standard Library Imports
from datetime import timedelta
# RESONAATE Imports
from resonaate.common.logger import Logger
from resonaate.data.resonaate_database import ResonaateDatabase
from resonaate.parallel import isMaster, resetMaster
from resonaate.physics.time.conversions import getTargetJulianDate
from resonaate.scenario import buildScenarioFromConfigFile

# Establish Redis connection
isMaster()

# Points to a valid main configuration file
init_file = "scenarios/main/test1.json"

# Define custom logger object which logs to the console
logger = Logger("resonaate", path="stdout")

# Define internal database instance explicitly
db_path = "db/resonaate.sqlite3"

# Build the Scenario application from the JSON/YAML init
app = buildScenarioFromConfigFile(
    init_file,          # Initialization file/scenario config
    db_path,            # Path to `ResonaateDatabase` file (or `None` for in-memory)
    importer=None,      # No imported data
    start_workers=True  # Starts `WorkerManager` instance
)

# Determine final time as a Julian date
target_date = getTargetJulianDate(
    app.clock.julian_date_start,
    timedelta(hours=sim_time_hours)
)

# Step through simulation to final time
app.propagateTo(target_date)

# Stop workers gracefully
app.worker_mgr.stopWorkers()

# Reset the Redis master key
resetMaster()
```

(ref-service-sec-time)=
## Time Target Message

The {class}`.TimeTargetMessage` should give {class}`.ResonaateService` some indication of a target time to propagate to.
The {class}`.TimeTargetMessage` can be defined by the testbed and {class}`.ResonaateService` will handle any necessary transposition for the {mod}`resonaate` tool to be able to properly ingest the relevant information.

(ref-service-sec-discont)=
## Discontinuation Message

{class}`.ResonaateService` will interpret a {class}`.DiscontinueMessage` as a flag to destroy the current underlying physics model.
This message is an indication that a simulation is over or testing has completed on the current underlying physics model.
The {class}`.DiscontinueMessage` can be defined by the testbed, and {class}`.ResonaateService` will handle any necessary transposition for the {mod}`resonaate` tool to be able to properly ingest the relevant information.

(ref-service-sec-man-task)=
## Manual Sensor Tasking

Currently, {class}`.ManualSensorTaskMessage` supports pre-made directives to designate targets as higher priority during a given time period.
This is achieved by pre-populating the database with messages containing data on how important observations for a given target are during a given time period.

Setting a high priority for collecting observations on a particular target is achieved by injecting the database with a message formatted the following way:

```python
from resonaate.data.resonaate_database import ResonaateDatabase
from resonaate.data.manual_sensor_task import ManualSensorTask

shared_interface = ResonaateDatabase.getSharedInterface()
shared_interface.insertData(
    ManualSensorTask(
        unique_id =34903, # Unique simulation ID for target
        priority=1.25, # Scalar defining how important it is that this target be observed, relative to other targets
        start_time=2458207.0208333335, # Julian Date for when this prioritization should start
        end_time=2458208.0208333335, # Julian Date for when this prioritization should end
        is_dynamic=True, # Whether this task is pre-canned or dynamically created
    )
)
```

The example above would set a 125% precedence for gathering observations on satellite 34903 (STSS ATRR (USA 205)) from 12:30 UTC 29 March 2018 to 12:30 UTC 30 March 2018.

(ref-service-sec-parallel)=
## Parallel Execution

The parallel execution implementation present within {mod}`resonaate` requires that a {mod}`redis` server is running and accepting connections at the host name and port set in {mod}`resonaate`'s {mod}`~.parallel` package configuration.
This presents an extra step to a user running a service layer or test, as {mod}`resonaate` will not start up the {mod}`redis` server on its own.
Information on how to install/run {mod}`redis` can be found here: <https://redis.io/topics/quickstart>

It's important for the {mod}`redis` server to not be persistent as un-handled tasks from previous runs will cause Exceptions to be thrown in {mod}`resonaate`.

(ref-service-sec-output)=
## Output

The {mod}`resonaate` interface currently has three streams of output.
One stream is comprised of observations that are generated during run time, based off of given sensor data and the internal physics model.
The other two streams are comprised of ephemerides.
One of these streams are estimate ephemerides, which are generated at run time based on observations of the target object and estimated propagation based on filters.
The other stream is "truth" ephemerides, which represent the states of each target being simulated internally in the physics model.

To use these output streams effectively, the two data types that are used are described in detail below.

(ref-service-subsec-obs)=
### Observations

{mod}`resonaate` outputs all observations made of the RSOs every `time.physics_step_sec` of simulated clock time, defined in the {class}`.InitMessage`.
These are the observations taken by the autonomously tasked SOSI Network. Additional details of the SOSI network SSN Specifications OpenSource v1.8.

The observations are noisy (i.e., non-exact) measurements of an RSO's state from sensor in the SOSI network.
The measurements are made in a topocentric-horizon coordinate system based on the sensor's location.
The SOSI network is diversely populated with a combination of ground and space based sensors including:
- Electro-optical sensors
- Mechanically steered radars (of various frequencies)
- Electronically steered, phased array radars (of various frequencies)

Within RESONAATE all observations are assumed to be correlated, but must be subject to various constraint to enable a viable observation.
A list of various constraints are listed below for each type of sensor.

Detection thresholds for Radar are constrained by:

- Sensor’s transmit frequency
- Sensor’s transmit power
- Sensor’s aperture size
- Sensor’s overall efficiency
- Slant range to the target
- Target’s radar cross section

Detection thresholds for Electro-Optical/Infrared (EOIR) sensors are constrained by:

- Sensor’s aperture size
- Sensor’s overall efficiency
- Slant range to the target
- Target’s visible cross section
- Target illumination (target must be illuminated by the Sun)
- Sensor illumination (ground-based only – sensor must be in eclipse)
- Earth Limb (line of sight not obstructed by Earth)
- Earth Albedo (space-based only – sensor cannot view target with Earth in the background)

The `range_km` and `range_rate_km_p_sec` may be set to "null" or empty if the particular sensor does not have the capability to measure the respective value

- `target_name `: String
    - Describes satellite associated with NORAD number
    - Corresponds to a valid Space Track "SATNAME" field.
- `target_id  `: Int
    - NORAD Catalog Number
    - Corresponds to a valid Space Track "SATNUM" field.
- `julian_date `: Float in units of days
    - Defines the epoch associated with the given data, i.e. when this data is provided
    - Number of days since 4713 BC
- `timestampISO`: ISO 8601 String
    - Defines the epoch associated with the given data, i.e. when this data is provided
    - ISO 8601 formatted string, UTC
- `unique_id`: Int
    - Indicates the ID number of the corresponding sensor
    - Referenced in the SSN Spec Sheet
- `observer`: String
    - Describes sensor agent associated with `unique_id`
    - Referenced in the SSN Spec Sheet
- `sensor_type `: String
    - Describes the class of sensor
    - Currently three types: `"Optical"`, `"Radar"`, and `"AdvRadar"`
- `sez_state_s_km `: List of floats in km
    - Position of target in SEZ frame
- `azimuth_rad`: Float in radians
    - With respect to the sensor location
    - Azimuth angle of given satellite relative to this sensor.
    - Provided by Optical/Radar/AdvRadar sensors.
- `elevation_rad`: Float in radians
    - With respect to the sensor location
    - Elevation angle of given satellite relative to this sensor.
    - Provided by Optical/Radar/AdvRadar sensors.
- `range_km `: Float in km
    - With respect to the sensor location
    - Distance to given satellite relative to this sensor.
    - Provided by Radar & AdvRadar sensors.
- `range_rate_km_p_sec `: Float in km/s
    - With respect to the sensor location
    - Rate of change of distance to given satellite
    - Provided by AdvRadar sensors.
- `position_lat_rad`: Float in radians
    - Geodetic latitude of the sensor
- `position_long_rad`: Float in radians
    - Geodetic longitude of the sensor
- `position_lat_rad`: Float in km
    - Height above ellipsoid of the sensor

(ref-service-subsec-est)=
### Estimate Ephemerides

{mod}`resonaate` outputs an estimated ephemeris for each RSO every `propagation.OutputTimeStep` of simulated clock time.

These are the estimated ECI (J2000) satellite state vectors, based on the observations and the known dynamics of the RSO.
Estimates are published on 5 minutes intervals.
The ephemeris estimates are the state output from a sequential UKF, using simultaneous observations.

- `name`: String
    - Describes satellite associated with NORAD number
    - Corresponds to a valid Space Track "SATNAME" field.
- `unique_id`: Int
    - NORAD Catalog Number
    - Corresponds to a valid Space Track "SATNUM" field.
- `julian_date`: Float in units of days
    - Defines the epoch associated with the given data, i.e. when this data is provided
    - Number of days since 4713 BC
- `timestampISO`: ISO 8601 String
    - Defines the epoch associated with the given data, i.e. when this data is provided
    - ISO 8601 formatted string, UTC
- `position`: List of floats in km
    - 3x1 cartesian vector
    - J2000 satellite location
- `velocity`: List of floats in km/s
    - 3x1 cartesian vector
    - J2000 satellite velocity
- `covariance`: List of lists (6x6 matrix of floats)
    - Describes the filter's estimated variability/confidence in its state estimates
    - This will be all zeros for truth data because it is exact.
    - Splitting the matrix into four 3x3 sub-matrices
        - units of the upper left 3x3 matrix are km^2
        - units of bottom right 3x3 matrix are km^2/s^2
        - units of upper right/lower left 3x3 matrices are km^2/s.
