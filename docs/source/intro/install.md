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

### RESONAATE Dependencies

To install RESONAATE package, the following dependencies must be installed first:

```bash
async-timeout==4.0.2
cycler==0.11.0
Deprecated==1.2.13
fonttools==4.32.0
greenlet==1.1.2
importlib-metadata==4.11.3
kiwisolver==1.4.2
matplotlib==3.5.1
mjolnir==1.1.3
numpy==1.21.6
packaging==21.3
Pillow==9.1.0
portalocker==2.4.0
pyparsing==3.0.8
python-dateutil==2.8.2
scipy==1.7.3
six==1.16.0
SQLAlchemy==1.4.35
typing_extensions==4.2.0
wrapt==1.14.0
zipp==3.8.0
```

`mjolnir` is a special case amongst these packages, as it is not available on PyPI.
To install `mjolnir`, you'll need to clone the repository (available [here](https://code.vt.edu/space-research/resonaate/mjolnir)) and install in development mode *or*
install `mjolnir` from its package registry (instructions available [here](https://code.vt.edu/space-research/resonaate/mjolnir/-/packages/827)).

## RESONAATE Package

Once the dependencies are installed, navigate into the RESONAATE source code directory, and execute:

```bash
python3 -m pip install -e .
```
