# Contributing

When contributing to this repository, please first discuss the change you wish to make via issue,
email, or any other method with the owners of this repository before making a change.

## Table of Contents

- [Contributing](#contributing)
   - [Table of Contents](#table-of-contents)
   - [Merge Request Process](#merge-request-process)
   - [Git Workflow](#git-workflow)
   - [Code Styling](#code-styling)
   - [Testing](#testing)
   - [Generating Documentation](#generating-documentation)

## Merge Request Process

- Use the provided merge request templates
- Properly format the code using the established linting procedures
- Ensure any install or build dependencies are removed before the end of the layer when doing a 
   build.
- Update the README.md with details of changes to the interface, this includes new environment 
   variables, exposed ports, useful file locations and container parameters.
- Increase the version numbers in any examples files and the README.md to the new version that this
   Merge Request would represent. The versioning scheme we use is [SemVer](http://semver.org/).
- You may merge the Merge Request in once you have the sign-off of a maintainer or owner, or if you 
   do not have permission to do that, you may request the reviewer to merge it for you.

## Git Workflow

- New features and bug-fixes are completed in a separate branch, based off the `develop` branch
  - Make sure to do the following before creating the new branch: `git pull origin develop`
  - Use a descriptive name starting with either the `feature/` or `bugfix/` prefix.
  - `bugfix/hanging-process` or `feature/add-node-dynamics` are good examples
  - Ensures easy tracking of issues and new features
- Once the feature is initially finished, it can be reviewed
  - Open a merge request into `develop` for the branch
  - This ensures `develop` is stable enough for "continuous development"
- Once `develop` is deemed stable enough, it can become a release candidate
  - Open a merge request into `master` for the release candidate
  - This ensures `master` remains "production-ready" as much as possible

## Code Styling

Please lint your features before merging into develop, so the codebase can remain clean, concise, and consistent.

Run the following command to install the proper tools for linting:

```shell
(resonaate) $ pip install -r requirements/development.txt
```

To execute linting checks please run both of the following commands:

```shell
(resonaate) $ pylint --rcfile=.pylintrc *.py tests src/resonaate
```

```shell
(resonaate) $ flake8 --config=.flake8 *.py tests src/resonaate
```

## Testing

Running unit tests is required before merging into protected branches.

Install `pytest` by executing 

```shell
(resonaate) $ pip install -r requirements/development.txt
```

The `pytest` package has *excellent* [documentation](https://docs.pytest.org/en/latest/), so please refer to their [Getting Started](https://docs.pytest.org/en/latest/getting-started.html#getstarted) page first. There is also a helpful tutorial on `pytest` located [here](https://realpython.com/pytest-python-testing/).

Running the full unit test suite is easy:

```shell
(resonaate) $ redis-server &
(resonaate) $ pytest -vv
```

This does take a decent amount of time because it includes integration tests. To run a quicker, but still large percentage of unit test run the following command:

```shell
(resonaate) $ pytest -x -m "not integration" -k "not service"
```

Also, refer to the example test module (`tests/example.py`) for how to write and format proper test cases.
To see how the tests behave, run the following:

```shell
(resonaate) $ pytest -vvs tests/example.py
```

## Generating Documentation

1. Install required packages:
   ```shell
   (resonaate) $ pip install -r requirements/development.txt
   ```
1. Navigate into the **docs** directory:
   ```shell
   (resonaate) $ cd docs
   ```
1. Create Sphinx source files for entire package
   ```shell
   (resonaate) $ sphinx-apidoc -MPTefo source/modules ../src/resonaate
   ```
   - `-M`: module documentation written above sub-module documentation
   - `-P`: include "private" members in documentation
   - `-T`: don't create a table of contents file using `sphinx-apidoc`
   - `-e`: separate each module's documentation onto it's own page
   - `-f`: force overwriting of Sphinx source files
   - `-o`: where to output the Sphinx source files, created if it doesn't exist
1. Build the documentation
   ```shell
   (resonaate) $ make clean; make html
   ```
1. Open **docs/build/html/index.html** in a browser to view the documentation
