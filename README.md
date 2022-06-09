# The Responsive Space Observation Analysis and Autonomous Tasking Engine (RESONAATE)

With the expected resident space object (RSO) population growth and improvements of satellite propulsion capabilities, it has become increasingly apparent that maintaining space domain awareness in future decades will require using human-on-the-loop autonomy as opposed to the current human-in-the-loop methods. 
RESONAATE is a decision making algorithm that creates a tasking strategy for a customizable Space Surveillance Network (SSN). 
The program presents responsive and autonomous sensor network management for tracking multiple maneuvering and non-maneuvering satellites with a diversely populated space object surveillance and identification (SOSI) network. 
The method utilizes a sub-optimal partially observed Markov decision process (POMDP) to task various ground and space-based sensors.
The POMDP implements the largest Lyapunov exponent, the Fisher information gain, and a sensor transportability metric to assess the overall reward for tasking a specific sensor to track a particular satellite. 
The successful measurements from the tasked sensors are combined using an unscented Kalman filter to maintain viable orbit estimates for all targets.

## Table of Contents

- [The Responsive Space Observation Analysis and Autonomous Tasking Engine (RESONAATE)](#the-responsive-space-observation-analysis-and-autonomous-tasking-engine-resonaate)
  - [Table of Contents](#table-of-contents)
  - [Dependencies](#dependencies)
- [Setup](#setup)
  - [Installation](#installation)
  - [RESONAATE Configuration](#resonaate-configuration)
- [Usage](#usage)
  - [CLI Tool](#cli-tool)
  - [Initialization](#initialization)
  - [Database Architecture](#database-architecture)
  - [Python Example](#python-example)
- [Contributing](#contributing)
  - [Linting](#linting)
  - [Testing](#testing)
  - [Generating Documentation](#generating-documentation)
- [Publications](#publications)
- [Authors](#authors)
## Dependencies

These are the software requirements for all versions of RESONAATE.
Packages can be installed at their minimum required versions using `pip install -r requirements/requirements.txt`.
Please see software documentation for best installation practices.

- Python (PIP) Packages
    - [NumPy](http://www.numpy.org/)
    - [SciPy](https://www.scipy.org/scipylib/index.html)
    - [concurrent-log-handler](https://github.com/Preston-Landers/concurrent-log-handler)
    - [SQLAlchemy](https://www.sqlalchemy.org/)
    - [matplotlib](https://matplotlib.org/index.html)
    - [PyYAML](https://pyyaml.org/wiki/PyYAML)
    - [jplephem](https://github.com/brandon-rhodes/python-jplephem)
    - [redis](https://github.com/andymccurdy/redis-py)
    - [munkres](https://github.com/bmc/munkres)
- Software
    - [Python >= 3.7.9](python.org)
    - [Redis server > 5.0](https://redis.io/)

# Setup

## Installation

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

## RESONAATE Configuration

By default, RESONAATE will use the default settings defined in `src/resonaate/common/default_behavior.config`.
These values correspond to how RESONAATE behaves with respect to logging, database, debugging, and parallelization.
To overwrite these settings, please copy the contents of `src/resonaate/common/default_behavior.config` to a new `.config` file to save the default settings.
Edit by un-commenting and changing the required values.

# Usage

Using the RESONAATE tool is the easiest when using the CLI, which is installed along with the Python package.
The reason for this, is that RESONAATE has been designed to be highly reconfigurable between separate simulation runs.
This is accomplished by altering the values of configuration files which makes Monte Carlo & parametric studies easier to accomplish.
Simple instructions for the `resonaate` CLI are described below along with a short definition of the configuration schema.

## CLI Tool

- Get Redis server running

```bash
(resonaate) $ redis-server &
```

- Run example, replacing `<init_file>` and `<number_of_hours>` with appropriate values

```bash
(resonaate) $ resonaate <init_file> -t <number_of_hours>
```

- Command line arguments for `resonaate` entry point:
```bash
(resonaate) $ resonaate -h
usage: resonaate [-h] [-t HOURS] [--debug] [--no-db] [--auto-db] [-d DB_PATH]
                 [-i IMPORTER_DB_PATH]
                 INIT_FILE

RESONAATE Command Line Interface

positional arguments:
  INIT_FILE             Path to RESONAATE initialization message file

optional arguments:
  -h, --help            show this help message and exit
  -t HOURS, --time HOURS
                        Time in hours to simulate. DEFAULT: 1/2 hour
  --debug               Turns on parallel debug mode

Database Files:
  -d DB_PATH, --db-path DB_PATH
                        Path to RESONAATE database
  -i IMPORTER_DB_PATH, --importer-db-path IMPORTER_DB_PATH
                        Path to Importer database

Database Options:
  --no-db               Turns off output database, overriding all other
                        options
  --auto-db             Auto-generate RESONAATE DB path to {cwd}/db/
```

- Users should stop Redis when they are done working running/simulations

```bash
(resonaate) $ redis-cli shutdown
```

## Initialization

The initialization/configuration file structure required to run RESONAATE is described in detail by the [Initialization](https://code.vt.edu/space_at_vt/sda/resonaate/-/wikis/Initialization) documentation on the Wiki.
Currently, example initialization files are located under **example_data/json**.

This Wiki defines the schema required by the different JSON/YAML configuration files:
- Main initialization file
    - File required to be pointed to when using `resonaate` CLI
    - Describes the main `Scenario`-level properties of the simulation
    - Points to files defining `Engine` objects
    - Points to files for `TargetEvent` and `SensorEvent` objects
- Engine configuration file(s)
    - Defines a single `Engine` object, and all required parameters
    - Points to file defining `Target` objects for the engine to be tasked to
    - Points to file defining `Sensor` objects that are taskable by the engine
- Target agent configuration file(s)
    - Defines list of `Target` objects to track/estimate in simulation
    - Only ID, name, and state are currently implemented
- Sensor agent configuration file(s)
    - Defines list of `Sensor` objects to task in simulation
    - Fully-defined agents & their sensors
    - Ground-based & space-based sensor agents are supported
- Target/Sensor event configuration file(s)
    - Not currently implemented

## Database Architecture

When interacting with the `resonaate` CLI, users may specify two separate types of databases: `ResonaateDatabase` (aka internal) and `ImporterDatabase` (aka external).

The internal `ResonaateDatabase` defines where data *produced* by RESONAATE is stored.
The default behavior is to store the database **in memory** which is likely faster, but means that no produced data is guaranteed to be saved if the simulation stops early.
Users may save the database to disk by with the `-d` or `--db-path` CLI options to `resonaate` (recommended) or by changing `DatabaseURL` in **resonaate.config** (not recommended).
The `--db-path` option requires explicit selection of the file location.
However, users may also use the `--auto-db` CLI option to use the default disk file location.
Finally, users can force skip saving any database to disk by using the `--no-db` CLI option.

The external `ImporterDatabase` defines **read-only** data that RESONAATE will ingest during a simulation and mix with produced data, but is protected from alteration by RESONAATE itself.
This provides utility for preloading large sets of pre-computed data (truth, observations, tasks); testing fusion of external estimates or observations with internally generated estimates and observations; and stacking data from simulation runs together.
Users can specify an `ImporterDatabase` with the `-i` or `--importer-db-path` CLI options to `resonaate`.

## Python Example

If users wish to incorporate RESONAATE into a separate tool, they can start with this minimal example that will properly run a simulation.
**NOTE**: Redis will still need to be started before this code is executed (see [RESONAATE CLI](#resonaate-cli)), but that can be performed programmatically if needed.

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

# Contributing

Please see [CONTRIBUTING](CONTRIBUTING.md) for more thorough details.
Using these development tools requires a standalone version of RESONAATE to be installed.

## Linting

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

## Testing

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

## Generating Documentation

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


 # Publications

For additional information on the development of the RESONAATE Tool, see the following publications:
- Dynamically Tracking Maneuvering Spacecraft with a Globally-Distributed, Heterogeneous Wireless Sensor Network
  - AIAA Space, 2017
  - Digital Object Identifier (DOI) : 10.2514/6.2017-5172
- An Autonomous Sensor Management Strategy for Monitoring a Dynamic Space Domain with Diverse Sensors
  - AIAA SciTech, 2018
  - Digital Object Identifier (DOI) : 10.2514/6.2018-0890
- Autonomous Multi-Phenomenology Space Domain Sensor Tasking and Adaptive Estimation
  - IEEE Fusion, 2018
  - Digital Object Identifier (DOI) : 10.23919/ICIF.2018.8455863
- Adaptively Tracking Maneuvering Spacecraft with a Globally Distributed, Diversely Populated Surveillance Network
  - Journal of Guidance, Control, and Dynamics, 2018
  - Digital Object Identifier (DOI) : 10.2514/1.G003743
- Autonomous and Responsive Surveillance Network Management for Adaptive Space Situational Awareness
  - Virginia Tech Dissertation, 2018
  - Digital Object Identifier (DOI) : 10919/84931
- Parametric Analysis of an Autonomous Sensor Tasking Engine for Spacecraft Tracking
  - AIAA SciTech, 2021
  - Digital Object Identifier (DOI) : 10.2514/6.2021-1397

# Authors

- Project Principal Investigators
  - Dr. Jonathan Black: <jonathan.black@vt.edu>
  - Dr. Kevin Schroeder: <kschro1@vt.edu>
- Lead Developers
  - Dylan Thomas: <dylan.thomas@vt.edu>
  - David Kusterer: <kdavid13@vt.edu>
- Developers
  - Jon Kadan: <jkadan@vt.edu>
  - Cameron Harris: <camerondh@vt.edu>
  - Connor Segal: <csegal@vt.edu>
