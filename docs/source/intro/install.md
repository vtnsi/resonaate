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

## RESONAATE Package

RESONAATE requires at least Python 3.9 to be installed directly on a system.
Please ensure a supported Python version is installed and on your path.

It is recommended to use a virtual environment, so first create one:

```bash
python3 -m venv .venv --prompt resonaate
```

Next, activate the new virtual environment.
The command on Linux/Mac is:

```bash
source .venv/bin/activate
```

If you're using Windows, use:

```bat
.venv\Scripts\activate.bat
```

Your prompt should now have a prefix that looks similar to:

```bash
(resonaate) >
```

You can now install the latest RESONAATE version directly into your virtual environment:

```bash
python3 -m pip install "resonaate@git+ssh://git@code.vt.edu/space-research/resonaate/resonaate.git"
```

If you wish to contribute or edit source code, please follow the instructions for a [development install][dev-install].

[dev-install]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/develop/CONTRIBUTING.md?ref_type=heads#development-installation
