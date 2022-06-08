# RESONAATE Initialization

To initialize a scenario, the `RESONAATEApplication::buildFromConfig()` method ingests a JSON message formatted the following way:

## Init JSON Object Definition

```json
<init_message>: {
    "targetList": [<target_obj>, ...],
    "sensorConf": <string>, // Must be configuration string in ("SSN", )
    "jDate": <decimal>,     // Julian Date corresponding to the input data; 
                            //     i.e. when the simulation starts
    "targetEvents": [<target_event_obj>, ...],
    "sensorEvents": [<sensor_event_obj>, ...]
}
```

### Target JSON Object Definition

```json
<target_obj>: {
    "satNum": <integer>, // NORAD catalog number
    "satName": <string>, // Describes satellite associated with NORAD number
    "initCOE": <coe_object>,
    "physicsData":{
        "ballisticCoef": <decimal>, // Measure of sat's ability to overcome air resistance in flight
        "solarCoef": <decimal>,     // Measure of effect of solar radiation on the sat
        "visXSect": <decimal>       // Measure of cross-section visible by sensors
    }
}

<target_obj>: {
    "satNum": <integer>, // NORAD catalog number
    "satName": <string>, // Describes satellite associated with NORAD number
    "initECI": [<decimal>, <decimal>, <decimal>, <decimal>, <decimal>, <decimal>],
    "physicsData":{
        "ballisticCoef": <decimal>, // Measure of sat's ability to overcome air resistance in flight
        "solarCoef": <decimal>,     // Measure of effect of solar radiation on the sat
        "visXSect": <decimal>       // Measure of cross-section visible by sensors
    }
}
```

#### Classical Orbital Elements (COE) JSON Objects Definition

Note that there are several iterations of COE sets.
An orbit can be described by any of the iterations defined below.

```json
<coe_object>: {
    "orbitAlt": <decimal>,      // Altitude above the Earth's mean equatorial radius (kilometers)
    "ecc": <decimal>,           // Orbit's eccentricity  (unitless)
    "incl": <decimal>,          // Orbit's inclination (degrees)
    "rightAscension": <decimal>,// Right Ascension of the Ascending Node (degrees)
    "argPeriapsis": <decimal>,  // Argument of Periapsis/Perigee (degrees)
    "trueAnomaly": <decimal>    // True Anomaly (degrees)
}

<coe_object>: {
    "orbitAlt": <decimal>,
    "ecc": <decimal>,
    "incl": <decimal>,
    "trueLongPeriapsis": <decimal>, // True Longitude of Periapsis for eccentric, 
                                    //     equatorial orbits (degrees)
    "trueAnomaly": <decimal>
}

<coe_object>: {
    "orbitAlt": <decimal>,
    "ecc": <decimal>,
    "incl": <decimal>,
    "rightAscension": <decimal>,
    "argLatitude": <decimal> // Argument of Latitude for circular, inclined orbits (degrees)
}

<coe_object>: {
    "orbitAlt": <decimal>,
    "ecc": <decimal>,
    "incl": <decimal>,
    "trueLongitude": <decimal> // True Longitude for circular, equatorial orbits (degrees)
}
```

## Sensor Configuration JSON Options

The default SOSI network used as defined in "SSN Specifications OpenSource v1.7" is selected by assigning the value "SSN" to the field `"sensorConf"` in the `init_message`. 
Alternatively, customizable SOSI networks can be developed within the `resonaate.network.sosi` submodule by making a new subclass and inheriting the `SOSINetwork` class. 
The new subclass requires a list of instantiated `Facility` and/or `Spacecraft` objects for the desired SOSI network. 
These agents are added to the subclass as follows:

```Python
        self.addNodes([<Facility>, <Facility>, ...])
```

## Target Event JSON Object Definition

```json
<target_event_obj>: {
    "affectedTargets": [<string>, ...],         // list of 'satNum's corresponding to targets
    "eventType": "IMPULSE",                     // Describes an impulsive maneuver
    "jDate": <decimal>,                         // Julian Date defining when the maneuver takes place
    "frame": "NTW",                             // Can also be "ECI"
    "deltaV": [<decimal>, <decimal>, <decimal>] // Acceleration vector of impulse
}
```