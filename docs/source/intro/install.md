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

## Prerequisites

RESONAATE requires a few prerequisites to be installed directly on a system.
The operating system must be Linux-based.
The minimum OS versions officially supported:

- CentOS 7+, or equivalent RHEL
- Debian 9+
- Fedora 25+
- Ubuntu 20.04+

RESONAATE requires the following items to be present on a system:

- Python >= 3.7
- Redis >= 5.0.10

(install-redis)=

### Installing Redis

#### Install Redis with a Package Manager

Unless there is good reason, please install Redis according to the instructions for your operating system described in the [Redis Install][redis install main] page.
This page has easy to follow instructions for the most common operating systems, and it will also install in such a way that you can easily upgrade the Redis version via your package manager.

#### Install Redis from Source

If you have a specific need, or can't use a package manager, you can also install Redis from [source][redis source install].
The following tools are required in order to install Redis:

- A GCC Compiler
- `make`
- `libc`/`glibc`

If using an Ubuntu distribution of Linux, you can ensure these requirements are installed with:

```bash
sudo apt install build-essential
```

```{note}
This installs **much more** than the minimum requirements, but will guarantee those are met.
```

The exact release of Redis can be downloaded from <https://download.redis.io/releases/>.
Once downloaded (or provided already), it's simple to build Redis.

1. Extract Redis source, replacing `<version>` as necessary:
   ```bash
   tar xzf redis-<version>.tar.gz
   ```
1. Change directory into extracted Redis source directory:
   ```bash
   cd redis-<version>
   ```
1. Compile the Redis tool using `make` (`-j` allows for a parallel build):
   ```bash
   make -j
   ```
1. Test Redis build:
   ```bash
   make test
   ```
1. (Optional) Install Redis binaries in your path:
   ```bash
   sudo make install
   ```

If you installed Redis correctly, you should be able to run:

```bash
src/redis-server
```

You can interact with Redis using the built-in client:

```bash
src/redis-cli
redis> set foo bar
OK
redis> get foo
"bar"
```

### RESONAATE Dependencies

To install RESONAATE package, the following dependencies must be installed first:

```bash
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

If provided with an actual directory of the required packages (usually called **deps-vX.Y.Z**), users can install without accessing PyPI:

```bash
python3 -m pip install --no-index --find-links=rel/path/to/deps-vX.Y.Z/ -r requirements.txt
```

## RESONAATE Package

Once the dependencies are installed, navigate into the RESONAATE source code directory, and execute:

```bash
python3 -m pip install -e .
```

[redis install main]: https://redis.io/docs/getting-started/installation/
[redis source install]: https://redis.io/docs/getting-started/installation/install-redis-from-source/
