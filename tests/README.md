# Testing

This folder contains all configuration, data, and source code for running the RESONAATE test suite.
There is a fully detailed guide on testing best practices included in the [documentation](../docs/README.md), so please build the docs and read the guide there if you have any questions.

______________________________________________________________________

<!-- START TOC -->

<!-- TOC Formatted for GitLab -->

**Table of Contents**

\[\[_TOC_\]\]

<!-- END TOC -->

______________________________________________________________________

## Overview

Running unit tests is required before merging into protected branches.

The `pytest` package has _excellent_ \[documentation\]\[pytest-docs\], so please refer to their \[Getting Started\]\[pytest-tutorial\] page first.
There is also a helpful tutorial on `pytest` located \[here\]\[pytest-realpython\].

Running the full test suite is easy:

```bash
pytest
```

This does take a decent amount of time because it includes integration tests. To run a quicker, but still large percentage of tests run the following command:

```bash
pytest -m "not (event or scenario)"
```

This runs only the unit tests which are much faster to run.

To determine coverage statistics:

```bash
coverage run -m pytest -m "not (event or scenario)"
coverage combine
coverage report
coverage html
```

Also, refer to the example test module (`tests/example.py`) for how to write and format proper test cases.
To see how the tests behave, run the following:

```bash
pytest -vvs tests/example.py
```

## Layout

The `tests/` directory is laid out to keep a *relatively flat* structure to help make it easier to find test modules.
Test modules are stored in the subdirectory with a name that mirrors its `resonaate` sub-package.
Typically, we only have further subdirectories holding test modules if there are many test modules.
Each test subdirectory requires an `__init__.py` file to properly be discovered by `pytest`.
Each test module typically tests a single class or single module.
Users may configure `pytest` per-directory using a `conftest.py` file or add common fixtures used throughout several testing modules.
