# Installation

These are instructions for installing RESONAATE and all dependencies on "bare metal".

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

## Pre-requisites

RESONAATE requires a few pre-requisites to be installed directly on a system.
The operating system must be Linux-based.
The minimum OS versions officially supported:

- CentOS 7+, or equivalent RHEL
- Debian 9+
- Fedora 25+
- Ubuntu 16.04+

RESONAATE The following items to be present on a system:

- Python >= 3.7.9
- A GCC Compiler
- `make`
- `libc`/`glibc`

## Redis

The exact release of Redis can be downloaded from https://download.redis.io/releases/.
Once downloaded (or provided already), it's simple to build Redis.

1. Extract Redis source, replacing `<version>` as necessary:
   ```shell
   tar xzf redis-<version>.tar.gz
   ```
1. Change directory into extracted Redis source directory:
   ```shell
   cd redis-<version>
   ```
1. Compile the Redis tool using `make`:
   ```shell
   make -j
   ```
1. Test Redis build:
   ```shell
   make test
   ```
1. (Optional) Install Redis binaries in path:
   ```shell
   sudo make install
   ```

If you installed Redis correctly, you should be able to run:

```shell
src/redis-server
```

You can interact with Redis using the built-in client:

```shell
src/redis-cli
redis> set foo bar
OK
redis> get foo
"bar"
```

## RESONAATE Dependencies

To install RESONAATE package, the following dependencies must be installed first:

```shell
async-timeout==4.0.2
concurrent-log-handler==0.9.20
cycler==0.11.0
Deprecated==1.2.13
fonttools==4.32.0
greenlet==1.1.2
importlib-metadata==4.11.3
kiwisolver==1.4.2
matplotlib==3.5.1
numpy==1.21.6
packaging==21.3
Pillow==9.1.0
portalocker==2.4.0
pyparsing==3.0.8
python-dateutil==2.8.2
redis==4.2.2
scipy==1.7.3
six==1.16.0
SQLAlchemy==1.4.35
typing_extensions==4.2.0
wrapt==1.14.0
zipp==3.8.0
```

### From PyPI

To install dependencies from PYPI, execute:

```shell
python3 -m pip install -r requirements.txt
```

### From Directory of Packages

If provided with an actual directory of the required packages (usually called **deps-vX.Y.Z**), users can install without accessing PyPI:

```shell
python3 -m pip install --no-index --find-links=rel/path/to/deps-vX.Y.Z/ -r requirements.txt
```

## RESONAATE Package

Once the dependencies are installed, navigate into the RESONAATE source code directory, and execute:

```shell
python3 -m pip install -e .
```
