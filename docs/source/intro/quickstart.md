(intro-quick-top)=

# Quickstart

This is a basic example showing how the CLI {command}`resonaate` command works, and demonstrate a typical simulation run.
Also, this will document the Python logic behind the command.

______________________________________________________________________

<!-- TOC formatted for sphinx -->

```{contents} Table of Contents
---
depth: 2
backlinks: none
local:
---
```

______________________________________________________________________

(intro-quick-cli)=

## Command Line Tool

Typically, users start simulations by using the provided CLI command {command}`resonaate`, which is installed along with the Python package.
To change simulation settings or features, users can alter the values of configuration files which makes Monte Carlo & parametric studies simple to accomplish.
Instructions for the {command}`resonaate` CLI are described below ({ref}`intro-quick-cli`) along with a short definition of the configuration schema ({ref}`intro-quick-init`).

Start simulation using {command}`resonaate` command

```bash
resonaate <init_file> -t <number_of_hours>
```

Replace `<init_file>` with the location of a main scenario configuration file.
There are example scenario configuration files in the `configs/json` directory.
Replace `<number_of_hours>` with a decimal for the number of hours to simulate during the scenario.
If this argument is omitted, it will run the full scenario length defined in the configuration file.

Invoke the `-h` option to get help with the CLI arguments for the {command}`resonaate` command:

```bash
resonaate -h
usage: resonaate [-h] [-t HOURS] [--debug] [-d DB_PATH]
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
```

To run a simulation using the `configs/json/main_init.json` config file for an hour of simulated time:

```bash
resonaate configs/json/main_init.json -t 1
```

The log output should look something like:

```bash
2022-02-01 20:28:50,798 - resonaate_database - DEBUG - Database path: sqlite:////path/to/resonaate/db/resonaate_2022-02-01T20-28-50-257612.sqlite3
2022-02-01 20:28:50,948 - scenario_builder - INFO - Reward function: CostConstrainedReward
2022-02-01 20:28:50,948 - scenario_builder - INFO - Decision function: MunkresDecision
2022-02-01 20:28:50,949 - producer - INFO - Registered job queue: job_queue_b910c761-e41b-4dea-a7e4-7cd2c01689bc
2022-02-01 20:28:50,950 - producer - INFO - Registered job queue: job_queue_2b2d9086-419d-469d-9260-1834cdab183b
2022-02-01 20:28:50,951 - scenario_builder - INFO - Successfully built tasking engine: CentralizedTaskingEngine
2022-02-01 20:28:53,799 - scenario_builder - INFO - Successfully loaded 69 target agents
2022-02-01 20:28:55,400 - scenario_builder - INFO - Successfully loaded 39 sensor agents
...
2022-02-01 20:28:55,627 - scenario - DEBUG - TicToc
2022-02-01 20:29:04,389 - scenario - DEBUG - Assess
...
2022-02-01 20:32:15,805 - __main__ - INFO - Simulation complete
```

When the simulation is complete, you can query the SQLite database by running the {command}`sqlite` command:

```bash
sqlite db/resonaate_2022-02-01T20-28-50-257612.sqlite3
SQLite version 3.36.0 2021-06-18 18:36:39
Enter ".help" for usage hints.
sqlite>
```

Then use the appropriate SQL query. Here is an example getting positions for a specific agent ID number:

```sql
sqlite> SELECT agent_id, julian_date, pos_x_km, pos_y_km, pos_z_km FROM estimate_ephemerides WHERE agent_id = 12309 ;
12309|2459304.17013889|38441.7764672795|-17240.0776023789|144.753940349412
12309|2459304.17361111|38799.2684529112|-16416.529678603|359.412396830475
12309|2459304.17708333|39138.1480246743|-15585.1057018969|573.898695818384
12309|2459304.18055556|39458.2522154527|-14746.206648433|788.109013385852
12309|2459304.18402778|39759.4280081821|-13900.2336956309|1001.94133795875
12309|2459304.1875|40041.5311591791|-13047.592358574|1215.29340901332
12309|2459304.19097222|40304.4263737407|-12188.6926481105|1428.06239752209
12309|2459304.19444444|40547.9878171375|-11323.945814358|1640.14645518262
12309|2459304.19791667|40772.0987875567|-10453.767560872|1851.44618748607
12309|2459304.20138889|40976.6520564418|-9578.57416055657|2061.85263920182
12309|2459304.20486111|41161.5497426757|-8698.78483469221|2271.26939321229
12309|2459304.20833333|41326.7033562135|-7814.82399048219|2479.59823250741
```

(intro-quick-python)=

## Python Example

This example goes over a small Python script that emulates the behavior of the {command}`resonaate` command.
This will show the necessary steps required to execute a RESONAATE simulation.

```python
import os

# Points to a valid main configuration file
init_file = os.path.abspath(
    os.path.join(os.getcwd(), "./resonaate/configs/json/main_init.json")
)

# Define number of hours to simulate
sim_time_hours = 0.1
```

Build the {class}`.Scenario` object using the JSON config using the factory function.
Also, convert the simulation time to a final simulation epoch.

```python
from datetime import timedelta
from resonaate.physics.time.conversions import getTargetJulianDate
from resonaate.scenario import buildScenarioFromConfigFile

# Build the Scenario from the JSON init.
scenario = buildScenarioFromConfigFile(
    init_file,  # Initialization file/scenario config
)

# Determine final time as a Julian date
target_date = getTargetJulianDate(
    scenario.clock.julian_date_start, timedelta(hours=sim_time_hours)
)
```

```{tip}
If you are not using {func}`.buildScenarioFromConfigFile()`, you must call {func}`.setDBPath()`
before any database queries are required.
```

Using the built {class}`.Scenario` object, propagate the simulation to the target scenario epoch.

```python
# Step through simulation to final time
try:
    scenario.propagateTo(target_date)
except KeyboardInterrupt:
    # Notification simulation stopped via KeyboardInterrupt
    scenario.logger.warning("Simulation terminated")
else:
    # Notification simulation stopped gracefully
    scenario.logger.info("Simulation complete")
finally:
    # Gracefully shutdown the simulation
    scenario.shutdown()
```

The simulation will log information to `stdout`, unless otherwise specified, and it should look similar to the CLI example above.
Once the simulation completes, you can directly query the database from Python.

```python
from sqlalchemy.orm.query import Query
from resonaate.data.ephemeris import TruthEphemeris
from resonaate.data import getDBConnection

# To show that the simulation completed, we will query the DB and count how many
# :class:`.Ephemeris` objects were created.
db = getDBConnection()
print(len(db.getData(Query(TruthEphemeris))))
```

(intro-quick-init)=

## Initialization

The initialization/configuration file structure required to run RESONAATE is described in detail by the {ref}`ref-cfg-top`.
Currently, example initialization files are located under `configs/json`.

The documentation defines the schema required by the different JSON configuration files:

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

(intro-quick-config)=

## Standalone Behavior Configuration

By default, RESONAATE will use the default settings defined in `src/resonaate/common/default_behavior.config`.
To overwrite these settings, please copy the contents of `src/resonaate/common/default_behavior.config` to a new `.config` file to another file to save the default settings.
Edit by uncommenting and changing the required values.
