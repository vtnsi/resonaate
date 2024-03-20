(dev-style-top)=

# Style Guide

This page explains the RESONAATE style, linting, & formatting tools.

______________________________________________________________________

<!-- TOC formatted for sphinx -->

```{contents} Table of Contents
---
depth: 1
backlinks: top
local:
---
```

______________________________________________________________________

(dev-style-naming)=

## Naming Conventions

We use a specific set of naming conventions in the RESONAATE project, but they are very simple to remember:

- Class names are [upper camel case][camel-cased]: `TaskingEngine`
- Function & method names are [lower camel case][camel-cased]: `keplerSolve()`
- Constants, constant instance attributes, & class variables use [upper snake case][snake-cased]: `SPEED_OF_LIGHT`
- Variable, instance attribute, module, & package names use [lower snake case][snake-cased]: `eci_position`
- Variables, classes, functions, & methods with a leading underscore are designated as *protected*, and typically are not meant to be directly used outside the scope in which they are defined: `_privateFunction()`

Here is a *very* contrived example to demonstrate the naming conventions.
In a file called `my_module.py`:

```python
import other_module
from some_package import another_module

SOME_GLOBAL_VALUE = 3.14159

class FancyCircle:
    NAME = "circle"

    def __init__(self, radius: float):
        self._radius = radius

    def getArea(self) -> float:
        return SOME_GLOBAL_VALUE * self._radius ** 2

    def getRadius(self) -> float:
        return self._radius


def _isACircle(obj: Any) -> bool:
    if obj.NAME == FancyCircle.NAME:
        return True

    return False


def calculatePerimeter(obj: Any) -> float:
    if not _isACircle(obj):
        raise TypeError("This is not a Circle!")

    return 2.0 * obj.getRadius() * SOME_GLOBAL_VALUE


# Implementation code later....
my_circle = FancyCircle(10.5)
perimeter = calculatePerimeter(my_circle)
area = my_circle.getArea()
```

```{note}
These *mostly* agree with common Python conventions, but specifically function and method names do not.
The wider Python community uses `snake_case()` for those instead, but we appreciate the visual distinction from variables and attributes.
This is worth noting when interacting with other projects.
```

(dev-style-env)=

## Setting Up Your Environment

These are quick instructions for setting up your development environment to work on RESONAATE.

### Virtual Environment

We **highly** recommend setting up a dedicated Python virtual environment for developing RESONAATE.
There are many ways to go about this, so we refer to the user to choose any of the following options.

- [venv](https://docs.python.org/3/library/venv.html)
- [virtualenv](https://virtualenv.pypa.io/en/latest/)
- [conda](https://docs.conda.io/en/latest/)
- [pipenv](https://pipenv.pypa.io/en/latest/)
- [flit](https://flit.pypa.io/en/latest/)
- [hatch](https://hatch.pypa.io/latest/)
- [poetry](https://python-poetry.org/)

### Install Development Tools

If you plan on contributing to RESONAATE, we ask that you install the full suite of development tools.
These tools are further described below, so read on to learn what they are and why.

If you just want to get up and running, the tools are easily installed:

```bash
make install
```

This command will install all the dependencies to format/lint code, run tests, and build the documentation.
If you only want the format/lint dependencies:

```bash
pip install -e ".[dev]"
pre-commit install
```

Next time you `git commit`, you will see something similar happen:

```bash
check for added large files..............................................Passed
check json...............................................................Passed
check toml...............................................................Passed
check yaml...............................................................Passed
debug statements (python)................................................Passed
fix end of files.........................................................Passed
mixed line ending........................................................Passed
trim trailing whitespace.................................................Passed
black....................................................................Passed
isort....................................................................Passed
ruff.....................................................................Passed
mdformat.................................................................Failed
- hook id: mdformat
- files were modified by this hook
```

This commit was not executed, and rolled-back, because `pre-commit` hook failed the `mdformat` job.
You can run the checks yourself first with:

```bash
pre-commit run
```

See {ref}`dev-style-pre-commit` for more details on what `pre-commit` is and why we use it.

### Visual Studio Code

Most of the core developers use [VS Code][visual studio code] to work on RESONAATE, so if you chose to use it as well, we will be able to more directly aid with any issues.
Because of this, we include settings and configurations within the RESONAATE project, which are located under the `.vscode` directory.
These settings allow for formatting on editor saves, linting analyzing for style/naming issues, and debugging configurations.
We also have a list of recommended VS Code extensions in the [Contributing Guide](./contrib.md).

```{note}
We absolutely don't require you to use VS Code, but it is just highly recommended!
```

(dev-style-pre-commit)=

## pre-commit

We use [pre-commit] to ensure basic style and format guidelines are respected before committing code.
`pre-commit` works by installing a script to run in your **local** `.git/hooks` directory.
This hook script runs *before* any `git commit` is officially executed, so it will reject if the hook fails.
In order to get this working, you must run `pre-commit install` **after** installing the developer tools.
Note that you **must** perform this command any time you clone the project!
If properly installed, you will see the following response:

```bash
pre-commit installed at .git/hooks/pre-commit
```

Then you can manually run it to check your files:

```bash
pre-commit run
```

Or wait until your next `git commit`!

Initially, you may find this frustrating, but it prevents unformatted and unchecked code from being pushed to the repo.
This reduces the number of bugs that are introduced, ensures the style is consistent project wide, and makes code reviews easier.
You can temporarily disable `pre-commit` in [several ways][pre-commit-disable].

```{tip}
Only use this sparingly, you will certainly fail any pipelines if you cannot pass the `pre-commit` hook.
```

The configuration for the `pre-commit` tool lives in the [.pre-commit-config.yaml] file.
The hooks that run are:

- `check-added-large-files` prevents large files from being added by accident
- `check-json`, `check-yaml`, & `check-toml` ensure any files of those types have valid syntax
- `end-of-file-fixer`, `mixed-line-ending`, & `trailing-whitespace` sort out white space discrepancies
- `black`, `isort`, & `mdformat` run the respective formatters, see {ref}`dev-style-formatters` for more info
- `ruff` runs the linter tool with several plugins to analyze code, see {ref}`dev-style-linters` for more info

(dev-style-formatters)=

## Formatters

For all Python code, RESONAATE uses the formatters [isort] and [black] to apply consistent styling project-wide.
The reason for this is to reduce the cognitive load on developer; you no longer need to worry if a function is formatted correct, as `black` & `isort` will do it for you!
This also serves to remove almost all style/formatting discussions from code reviews, which improves the overall process.
Please refer to the project's [pyproject.toml] for details on the configuration.
These formatters run with `pre-commit`, but if you want to run them yourself, you can use:

```bash
make format
```

In addition to `isort` and `black`, we also use a formatter in `pre-commit` for Markdown file formats.
Markdown files are formatted using the [mdformat] tool along with extensions for [GitLab Flavored Markdown][glfm] and [MyST Markdown][myst], and this is auto-run with `pre-commit`.
`mdformat` does not have any significant configuration set.
To run the formatter manually:

```bash
mdformat .
```

JSON, YAML, and TOML file types use [Prettier][prettier docs] to format code.
Currently, this is only done when saving files in VS Code if the [extension][prettier ext] is installed.
The Prettier configuration lives at [.prettierrc.yaml].
There currently isn't a configured way to run Prettier via the command line (coming soon).

(dev-style-linters)=

## Linters

We use primarily `ruff` as our Python linter: [ruff].
The configuration for this tool lives in [ruff.toml].
`ruff` checks overall style, docstring format, and `pytest` style.

To run the linters, execute the following command:

```bash
make lint
```

(dev-style-other)=

## Other

Finally, there is a tool for properly checking that non-source code files are included in a built source distribution package.
This tool, [check-manifest] is run during CI pipelines to ensure package builds are valid.
The following command runs `check-manifest` to ensure proper source builds:

```bash
check-manifest -v
```

[.pre-commit-config.yaml]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/develop/.pre-commit-config.yaml
[.prettierrc.yaml]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/develop/.prettierrc.yaml
[black]: https://black.readthedocs.io/en/stable/
[camel-cased]: https://en.wikipedia.org/wiki/Camel_case
[check-manifest]: https://github.com/mgedmin/check-manifest
[glfm]: https://docs.gitlab.com/ee/user/markdown.html
[isort]: https://pycqa.github.io/isort/
[mdformat]: https://mdformat.readthedocs.io/en/stable/
[myst]: https://myst-parser.readthedocs.io/en/latest/
[pre-commit]: https://pre-commit.com/
[pre-commit-disable]: https://pre-commit.com/index.html#temporarily-disabling-hooks
[prettier docs]: https://prettier.io/
[prettier ext]: https://github.com/prettier/prettier-vscode
[pyproject.toml]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/develop/pyproject.toml
[ruff]: https://docs.astral.sh/ruff/
[ruff.toml]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/develop/ruff.toml
[snake-cased]: https://en.wikipedia.org/wiki/Snake_case
[visual studio code]: https://code.visualstudio.com/
