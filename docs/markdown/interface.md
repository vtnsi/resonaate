# Interface 

The `resonaate` application interface (which contains the core operations of RESONAATE) will be contained within a service layer named `resonaate_service.py`. 
The `resonaate_service` will handle incoming input messages and outgoing output messages on the testbed. 

The general flow of the `resonaate_service` layer follows a looping paradigm. 
Each loop starts with polling incoming messages from other services or the test bed itself. 
There are several different types of messages that the service layer is set up to handle, each described below. 

## Init Message 

The init message input is used by the `resonaate` tool to initialize a particular physics model and sensor network. 
The init message input is rigidly defined by Virginia Tech in the [RESONAATE Initialization](#resonaate-initialization) section (and following subsections). 
Any necessary init messages (for testing or for OpSits) will be generated and provided by Virginia Tech.

To construct a scenario (the interface used to propagate the physics model and generate data), code similar to the following snippet can be used: 

```python
from json import loads 
from resonaate.factories.json_scenario_factory import JSONScenarioFactory  

scenario_factory = JSONScenarioFactory(loads(init_msg))
scenario = scenario_factory.buildScenarioFromJSON(loads(init_msg))
```

## Time Target Message 

The time target message should give `resonaate_service` some indication of a target time to propagate to.
The time target message can be defined by the testbed and `resonaate_service` will handle any necessary transposition for the `resonaate` tool to be able to properly ingest the relevant information.

To propagate a constructed physics model and generate data, code similar to the following snippet can be used (assuming the 'init' snippet was used): 

```python 
from resonaate.physics.stardate import JulianDate 
from resonaate.config import Config

OUTPUT_TIME_STEP = 900 # Time step of 900 seconds (15 minutes)
target_jdate = JulianDate(2458207.0624999334) # Corresponds to 13:30 UTC 29 March 2018

for output_burst in scenario.propagateTo(target_jdate, output_time_step=OUTPUT_TIME_STEP):
    # Data is output in a loop here, because updated data is provided every `OUTPUT_TIME_STEP` of time. 
    #   E.g. If the current model time is 2458207, and the target time is 2458208 (a day later), then 
    #   there will be 96 output bursts (24 hours / 15 minute time steps). 
    
    for truth_ephem in output_burst["truthEphemeris"]:
        # Truth ephemeris data available for each RSO in the scenario 

    for est_ephem in output_burst["estimateEphemeris"]:
        # Estimate ephemeris data available for each RSO in the scenario 

    for observation in output_burst["observations"]: 
        # Each observation used to generate estimates 
```

## Discontinuation Message

`resonaate_service` will interpret a discontinuation message as a flag to destroy the current underlying physics model. 
This message is an indication that an OpSit is over or testing has completed on the current underlying physics model. 
The discontinuation message can be defined by the testbed, and `resonaate_service` will handle any necessary transposition for the `resonaate` tool to be able to properly ingest the relevant information.

## Manual Sensor Tasking 

Currently, manual sensor tasking supports pre-made directives to designate targets as higher priority during a given time period. 
This is achieved by pre-populating the database with messages containing data on how important observations for a given target are during a given time period. 

Setting a high priority for collecting observations on a particular target is achieved by injecting the database with a message formatted the following way: 

```python 
from resonaate.data.data_interface import DataInterface 
from resonaate.data.manual_sensor_task import ManualSensorTask 

shared_interface = DataInterface.getSharedInterface()
shared_interface.insertData(
    ManualSensorTask(
        target_id=34903, # Satellite Number for target 
        priority=1.25,   # Scalar that indicates how important it is that this target be observed 
        start_time=2458207.0208333335, # Julian Date for when this prioritization should start 
        end_time=2458208.0208333335    # Julian Date for when this prioritization should end
    )
)
```

The example above would set a 125% precedence for gathering observations on satellite 34903 (STSS ATRR (USA 205)) from 12:30 UTC 29 March 2018 to 12:30 UTC 30 March 2018. 

### Parallel Execution 

The parallel execution implementation present within `resonaate` requires that a `redis` server is running and accepting connections at the host name and port set in `resonaate`'s `parallel` configuration. 
This presents an extra step to a user running a service layer or test, as `resonaate` will not start up the `redis` server on its own. 
Information on how to install/run `redis` can be found here: https://redis.io/topics/quickstart 

It's important for the `redis` server to not be persistent as un-handled tasks from previous runs will cause Exceptions to be thrown in `resonaate`.  

## Output

The `resonaate` interface currently has three streams of output. 
One stream is comprised of observations that are generated during run time, based off of given sensor data and the internal physics model. 
The other two streams are comprised of ephemerides. 
One of these streams are estimate ephemerides, which are generated at run time based on observations of the target object and estimated propagation based on filters. 
The other stream is "truth" ephemerides, which represent the states of each target being simulated internally in the physics model.

Accessing these output streams in Python is showcased in the code snippet in the [Time Target Message](#time-target-message) section above. 
To use these output streams effectively, the two data types that are used are described in detail below. 

### Observations 

`resonaate` outputs all observations made of the RSOs every `propagation.OutputTimeStep` of simulated clock time. 
These are the observations taken by the autonomously tasked SOSI Network. Additional details of the SOSI network SSN Specifications OpenSource v1.7

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

The "range" and "rangeRate" may be set to "null" or empty if the particular sensor does not have the capability to measure the respective value

- `satName`: String
    - Describes satellite associated with NORAD number
    - Corresponds to a valid Space Track "SATNAME" field.
- `satNum`: Int
    - NORAD Catalog Number
    - Corresponds to a valid Space Track "SATNUM" field.
- `julianDate`: Float in units of days
    - Defines the epoch associated with the given data, i.e. when this data is provided
    - Number of days since 4713 BC
- `observer`: Int
    - Indicates the ID number of the corresponding sensor
    - Referenced in the SSN Spec Sheet
- `sensorType`: String
    - Describes the class of sensor
    - Currently three types: "Optical", "Radar", and "AdvRadar"
- `xSEZ`: List of floats in km and km/s
    - 6x1 state vector of the given satellite
    - SEZ coordinate frame
        - With respect to the sensor location
        - First three values describe the relative position
        - Next three describe relative velocity
- `azimuth`: Float in radians
    - With respect to the sensor location
    - Azimuth angle of given satellite relative to this sensor.
    - Provided by Optical/Radar/AdvRadar sensors.
- `elevation`: Float in radians
    - With respect to the sensor location
    - Elevation angle of given satellite relative to this sensor.
    - Provided by Optical/Radar/AdvRadar sensors.
- `range`: Float in km
    - With respect to the sensor location
    - Distance to given satellite relative to this sensor.
    - Provided by Radar & AdvRadar sensors.
- `rangeRate`: Float in km/s
    - With respect to the sensor location
    - Rate of change of distance to given satellite
    - Provided by AdvRadar sensors.
- `state`: List of floats
    - Concatenated measurement state vector
    - Can either be a 2x1, 3x1, or 4x1: Optical, Radar, AdvRadar respectively. Correspond directly to azimuth, elevation, range, rangeRate (same order) 

### Estimate Ephemerides

`resonaate` outputs an estimated ephemeris for each RSO every `propagation.OutputTimeStep` of simulated clock time.

These are the estimated ECI (J2000) satellite state vectors, based on the observations and the known dynamics of the RSO. 
Estimates are published on 5 minutes intervals. 
The ephemeris estimates are the state output from a sequential UKF, using simultaneous observations.

- `satName`: String
    - Describes satellite associated with NORAD number
    - Corresponds to a valid Space Track "SATNAME" field.
- `satNum`: Int
    - NORAD Catalog Number
    - Corresponds to a valid Space Track "SATNUM" field.
- `julianDate`: Float in units of days
    - Defines the epoch associated with the given data, i.e. when this data is provided
    - Number of days since 4713 BC
- `position`: List of floats in km
    - 3x1 cartesian vector
    - Inertial satellite location
- `velocity`: List of floats in km/s
    - 3x1 cartesian vector
    - Inertial satellite velocity
- `covariance`: List of lists (6x6 matrix of floats)
    - Describes the filter's estimated variability/confidence in its state estimates
    - This will be all zeros for truth data because it is exact.
    - Splitting the matrix into four 3x3 sub-matrices
        - units of the upper left 3x3 matrix are km^2
        - units of bottom right 3x3 matrix are km^2/s^2
        - units of upper right/lower left 3x3 matrices are km^2/s.