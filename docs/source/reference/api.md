# API Documentation

The RESONAATE (Responsive Space Observation Analysis & Autonomous Tasking Engine) library is a set
of Python packages that contain algorithms for performing space domain awareness (SDA) research.
The main command line/executable {command}`resonaate` tool is meant to provide a simple interface for starting complex
SDA software simulations via JSON configuration files. Please see the {ref}`Module Documentation <api-main>` below
for details on how the executable {command}`resonaate` works. For details on the library API, see the
documentation of the {ref}`api-subpackages` listed below.

```{eval-rst}

______________________________________________________________________

.. _api-main:

.. automodule:: resonaate.__init__
    :members:

.. automodule:: resonaate.__main__
    :members:

______________________________________________________________________

```

```{eval-rst}

.. _api-subpackages:

.. rubric::  Subpackages

.. currentmodule:: resonaate

.. autosummary::
    :toctree: ../gen/autosummary
    :template: custom-module.rst
    :recursive:

    agents
    common
    data
    dynamics
    estimation
    parallel
    physics
    scenario
    sensors
    tasking

```
