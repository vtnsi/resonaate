# Docker Instructions

These are instructions for loading RESONAATE Docker images, creating the containers, and running them via `docker-compose`.

```{warning} This documentation is not currently kept up-to-date because we don't officially support a working Docker configuration. User beware!
```

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

## Setup

### Requirements

- **Docker** >= 18.06.0
- **Docker Compose** >= 1.27.0

### Installation

Download the RESONAATE docker image file, navigate to the file location, and run:

```shell
docker load < resonaate-v1.2.0.tar.gz
```

Run the following command to show the Docker images:

```shell
docker images
REPOSITORY   TAG             IMAGE ID       CREATED          SIZE
resonaate    v1.2.0          9c31555933ce   30 minutes ago   459MB
```

## Usage

To run the container, you must use the included Compose file (**docker-compose-external.yml**) to properly configure the containers.
Create a working directory containing the Compose file, navigate there, and run the following command:

```shell
docker-compose -f docker-compose-external.yml up
```

You should see an short example simulation run.

Users can remove the containers and the images with the following commands:

```shell
docker-compose -f docker-compose-external.yml down
docker image rm resonaate:<tag>
```

Make sure to replace `<tag>` with the appropriate version number (e.g. `resonaate:v1.2.0`).

### CLI options

You can specify CLI arguments to RESONAATE by pre-pending the command as follows:

```shell
RESONAATE_ARGS="configs/main_init.json -t 0.5" docker-compose -f docker-compose-external.yml up
```

This allows users to change the config file, simulation run time, etc without changing the Docker image itself.
Note that you must encase the entire CLI argument string in quotations.
The empty **configs** directory is included as the designated place to store custom/new scenario configurations.
This directory is mapped to the container's filesystem, so it will be able to find the scenario config files.
Here is an example command if the main config file was stored as **configs/test_01.json**:

```shell
RESONAATE_ARGS="configs/test_01.json -t 4" docker-compose -f docker-compose-external.yml up
```

Users can check the command line options with the following command:

```shell
RESONAATE_ARGS="--help" docker-compose -f docker-compose-external.yml up
```

### Volume Mapping

Common RESONAATE output folders are mapped to the container, so data from simulation runs can be analyzed.
It is a good idea to create the following folders wherever the workspace from which the RESONAATE container will be run from:

- **configs/**: Place to put custom scenario configuration files
- **debugging/**: Place where RESONAATE will store debug files, if configured to do so
- **logs/**: Place where RESONAATE will store log files, if configured to do so
- **output/**: Place where RESONAATE will store timestamped SQLite files

## Building

Users can re-build the Docker containers by running the following command:

```shell
docker-compose build
```

This must be executed in the same directory as the **docker-compose.yml** file, and next to the **resonaate** source code directory.

### Configuration

The container can be built with different RESONAATE configurations by altering options in **behavior.docker.config**.
This allows users to control the log levels & locations and various debugging options.
Also, one can change the **req.docker.txt** to alter the enforced Python dependencies when building the RESONAATE image.
However, one must make sure that they have access to the corresponding versions.
