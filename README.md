# The Responsive Space Observation Analysis and Autonomous Tasking Engine (RESONAATE)

With the expected resident space object (RSO) population growth and improvements of satellite propulsion capabilities, it has become increasingly apparent that maintaining space domain awareness in future decades will require using human-on-the-loop autonomy as opposed to the current human-in-the-loop methods. 
RESONAATE is a decision making algorithm that creates a tasking strategy for a customizable Space Surveillance Network (SSN). 
The program presents responsive and autonomous sensor network management for tracking multiple maneuvering and non-maneuvering satellites with a diversely populated space object surveillance and identification (SOSI) network. 
The method utilizes a sub-optimal partially observed Markov decision process (POMDP) to task various ground and space-based sensors.
The POMDP implements the largest Lyapunov exponent, the Fisher information gain, and a sensor transportability metric to assess the overall reward for tasking a specific sensor to track a particular satellite. 
The successful measurements from the tasked sensors are combined using an unscented Kalman filter to maintain viable orbit estimates for all targets.

For additional information on the development of the RESONAATE Tool, see the following publications:
- Dynamically Tracking Maneuvering Spacecraft with a Globally-Distributed, Heterogeneous Wireless Sensor Network
    - Digital Object Identifier (DOI) : 10.2514/6.2017-5172
- An Autonomous Sensor Management Strategy for Monitoring a Dynamic Space Domain with Diverse Sensors
    - Digital Object Identifier (DOI) : 10.2514/6.2018-0890
- Autonomous and Responsive Surveillance Network Management for Adaptive Space Situational Awareness
    - Digital Object Identifier (DOI) : 10919/84931

## Features

### Current [2018-12-31]

RESONAATE tasks the customizable SSN to make measurements (observations) of orbiting satellites. 
Each measurement is combined with the previous estimate of a satellite to find the current state estimate of the satellite (EstimateAgent Ephemeris).

#### Input Data

- Satellites
    - Each satellite in the simulation must be provided a priori along with properties of that satellite.
    - Identification: satellite name and NORAD catalog number.
    - Initial State: either as Cartesian position and velocity vectors or as Classical Orbital Elements (COEs).
    - Physical Parameters: including the visual cross section as well as ballistic and solar coefficients (in SI units).
- SOSI Network
    - The SOSI network used as defined in "SSN Specifications OpenSource v1.7" is set as the default.
- Manual sensor tasking
    - Low-level interface for operator to designate RSO(s) as high-priority for a given time.
    - Optimal sensor tasking will take this into account and output more observations for the designated RSO(s).

#### Propagation Methods

Two methods of acquiring actual subsequent states of a satellite (commonly referred to as truth data or truth ephemerides) are allowed. 
RESONAATE has its own numerical propagator which will read in the initial state of an RSO and numerically propagate it forward in time including J2, J3, & J4 perturbations. 
Alternatively, ephemerides can be imported from an external source and used as truth data.

 - "Special Perturbations" real time propagation of a given set of RSOs.
    - Internally tracks current simulated time. 
    - Accepts a time delta message that drives propagation to given time. 
    - Propagates "truth" ephemerides for every RSO on a configurable timestep (`propagation.PhysicsTimeStep`).
    - Outputs generated "truth" ephemerides for every RSO on a configurable timestep (`propagation.OutputTimeStep`).
 - "Importer" model propagation of a given set of RSOs. 
    - Uses pre-populated (SQLite) database to keep track of RSOs states. 
    - Is almost twice as fast as "Special Perturbations" real time propagation.

#### Output Data

 - Observation generation of a given set of RSOs and sensors.
    - Tasked sensors provide optimal observational coverage of RSOs over a single timestep. 
    - Generates observational data based on the type of sensor used and the measured values of "truth" data.
    - Generates and outputs observations for set of RSOs for each timestep. 
 - EstimateAgent ephemeris generation of a given set of RSOs.
    - Bases estimate off of generated observations
    - Generates and outputs estimated ephemerides for a set of RSOs in step with the observation generation.
    - Contains the covariance matrix, which is the uncertainty of the estimate ephemeris. Note that the covariance assumes the satellite has not maneuvered. Thus the satellites true position (reflected in truth data) will be outside the covariance if the satellite has recently maneuvered.

### Planned

 - Real time manual sensor tasking 
    - Current implementation of manual sensor tasking requires that priorities be set before running a scenario. 
    - It is planned to provide an interface to operators to be able to set priorities in real time. 
 - Maneuver generation for maneuvering RSOs.
    - Generates and outputs manuevers in step with observation generation.
    - Maneuver output will _not_ be provided at exact time of maneuver, but delayed until the RSO is observed to be maneuvering.  

## Dependencies

- Python (PIP) Packages
    - [NumPy](http://www.numpy.org/)
    - [SciPy](https://www.scipy.org/scipylib/index.html)
    - [concurrent-log-handler](https://github.com/Preston-Landers/concurrent-log-handler)
    - [SQLAlchemy](https://www.sqlalchemy.org/)
    - [matplotlib](https://matplotlib.org/index.html)
    - [PyYAML](https://pyyaml.org/wiki/PyYAML)
    - [jplephem](https://github.com/brandon-rhodes/python-jplephem)
    - [redis](https://github.com/andymccurdy/redis-py)
- Software 
    - [redis server](https://redis.io/)

Packages can be installed at their required versions using `pip install -r requirements/requirements.txt`.
Please see software documentation for best installation practices. 

## Setup

### Installation

- Clone this repository
- Install [Anaconda](https://docs.anaconda.com/anaconda)
    - See their [Installation Guide](https://docs.anaconda.com/anaconda/install/linux/) for help
- Setup anaconda environment

```bash
$ conda create -n resonaate python=3.7 redis
$ conda activate resonaate
```

- Install the package "in-place"

```bash
(resonaate) $ pip install -e .
```

### Running RESONAATE

- Get Redis server running

```bash
(resonaate) $ redis-server &
```

- Run example

```bash
(resonaate) $ resonaate <init_file> -t <number_of_hours>
```

### Behavior

By default, RESONAATE will use the default settings defined in **src/resonaate/common/behavior_config.py**.
To overwrite these settings, please copy the contents of **src/resonaate/common/default_behavior.config** to a new **.config** file.
Edit by un-commenting and changing the required values.
After, set the following environment variable to the absolute path to the new config file:

```bash
(resonaate) $ export RESONAATE_BEHAVIOR_CONFIG=<config_file_path>
```

Alternatively, you can add the above command to your **~/.bashrc** (or equivalent).

## Contributing

Please see [CONTRIBUTING](CONTRIBUTING.md) for more thorough details.

### Linting

- Install linting libraries:

```bash
(resonaate) $ pip install -r requirements/development.txt
```

- Running `flake8` linter:

```bash
(resonaate) $ flake8 --config=.flake8 *.py tests src/resonaate
```

- Running `pylint` linter:

```bash
(resonaate) $ pylint --rcfile=.pylintrc *.py tests src/resonaate
```

### Testing

- Install pytest

```bash
(resonaate) $ pip install -r requirements/development.txt
```

- Get Redis server running

```bash
(resonaate) $ redis-server &
```

- Run unit tests

```bash
(resonaate) $ pytest
```

### Generating Documentation

1. Install required packages:
   ```shell
   (resonaate) $ pip install -r requirements/development.txt
   ```
1. Navigate into the **docs** directory:
   ```shell
   (resonaate) $ cd docs
   ```
1. Create Sphinx source files for entire package
   ```shell
   (resonaate) $ sphinx-apidoc -MPTefo source/modules ../src/resonaate
   ```
   - `-M`: module documentation written above sub-module documentation
   - `-P`: include "private" members in documentation
   - `-T`: don't create a table of contents file using `sphinx-apidoc`
   - `-e`: separate each module's documentation onto it's own page
   - `-f`: force overwriting of Sphinx source files
   - `-o`: where to output the Sphinx source files, created if it doesn't exist
1. Build the documentation
   ```shell
   (resonaate) $ make clean; make html
   ```
1. Open **docs/build/html/index.html** in a browser to view the documentation
