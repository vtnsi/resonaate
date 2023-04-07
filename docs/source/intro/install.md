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
RESONAATE requires the following items to be present on a system:

- Python >= 3.9

### RESONAATE Dependencies

To install RESONAATE package, the following dependencies must be installed first:

```bash
contourpy==1.0.7
cycler==0.11.0
fonttools==4.39.0
greenlet==2.0.2
importlib-resources==5.12.0
kiwisolver==1.4.4
matplotlib==3.7.1
mjolnir==1.3.0
numpy==1.24.2
packaging==23.0
Pillow==9.4.0
pyparsing==3.0.9
python-dateutil==2.8.2
pyzmq==25.0.0
scipy==1.10.1
six==1.16.0
SQLAlchemy==2.0.5.post1
typing_extensions==4.5.0
zipp==3.15.0
```

`mjolnir` is a special case amongst these packages, as it is not available on PyPI.
To install `mjolnir`, you'll need to clone the repository (available [here](https://code.vt.edu/space-research/resonaate/mjolnir)) and install in development mode *or*
install `mjolnir` from its package registry (instructions available [here](https://code.vt.edu/space-research/resonaate/mjolnir/-/packages/827)).

## RESONAATE Package

Once the dependencies are installed, navigate into the RESONAATE source code directory, and execute:

```bash
python3 -m pip install -e .
```
