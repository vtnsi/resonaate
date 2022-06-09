# Contributing

When contributing to this repository, please first discuss the change you wish to make via issue,
email, or any other method with the owners of this repository before making a change.

## Table of Contents

- [Contributing](#contributing)
   - [Table of Contents](#table-of-contents)
- [General Information](#general-information)
   - [New Developers](#new-developers)
   - [Merge Request Process](#merge-request-process)
   - [Git Workflow](#git-workflow)
- [Developer Tools](#developer-tools)
   - [Code Styling](#code-styling)
   - [Testing](#testing)
   - [Generating Documentation](#generating-documentation)
- [GitLab CI/CD](#gitlab-cicd)
   - [Check Stage](#check-stage)
   - [Test Stage](#test-stage)
   - [Build Stage](#build-stage)
   - [Upload Stage](#upload-stage)

# General Information

In general, developers should attempt to create unit tests for all new code added to ensure proper coverage.
Also, users should review their use of `print()` and `log.debug()` statements when merging completed code into main branches.

## New Developers

Any new developers should first familiarize themselves with using RESONAATE.
To do this, follow the README instructions to install the tool, and run some short simulations making changes to configuration files to see how behavior is changed.
Once semi-familiar with using the tool, creating the `sphinx` documentation will be helpful for understanding how to use the different parts of the API.

Finally, scan the [issue list](https://code.vt.edu/space_at_vt/sda/resonaate/-/issues) and see if there are any interesting bugs or features.
If an issue peaks your interest, read it over and ask a maintainer about tackling the issue.
They should be able to provide more information on if it's a good "first issue" and how to get started.
Open a new branch based on the latest **develop** commit, and start working!

## Merge Request Process

- Use the provided merge request templates
- Properly format the code using the established linting procedures
- Ensure any install or build dependencies are removed before the end of the layer when doing a 
   build.
- Update the README.md with details of changes to the interface, this includes new environment 
   variables, exposed ports, useful file locations and container parameters.
- Update CHANGELOG.md with in-depth developer log notes
- Increase the version numbers in any examples files and the README.md to the new version that this
   Merge Request would represent. The versioning scheme we use is [SemVer](http://semver.org/).
- You may merge the Merge Request in once you have the sign-off of a maintainer or owner, or if you 
   do not have permission to do that, you may request the reviewer to merge it for you.

## Git Workflow

- New features and bug-fixes are completed in a separate branch, based off the `develop` branch
  - Make sure to do the following before creating the new branch: `git pull origin develop`
  - Use a descriptive name starting with either the `feature/` or `bugfix/` prefix.
   - Include the number of the issue it addresses before a descriptive name
   - `bugfix/10-hanging-process` or `feature/54-add-node-dynamics` are good examples (address issues 10 & 54, resp.)
   - Ensures easy tracking of issues and new features
- Once the feature is initially finished, it can be reviewed
  - Open a merge request into `develop` for the branch
  - Assign a reviewer to check your work, a code review may be requested
  - This ensures `develop` is stable enough for "continuous development"
- Once `develop` is deemed stable enough, it can become a release candidate
  - Open a merge request into `master` for the release candidate
  - This ensures `master` remains "production-ready" as much as possible

# Developer Tools

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

**NOTE** Using `ResonaateDatabase::getSharedInterface()` or `ImporterDatabase::getSharedInterface()` is *usually* a bad idea when writing a unit test unless the test **requires** it be called first.
If this is the case, please call `ResonaateDatabase::resetData()` or `ImporterDatabase::resetData()` with the appropriate tables to drop.

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

# GitLab CI/CD

The continuous integration/deployment configuration is located in **.gitlab/.gitlab-ci.yml** which defines several pipeline stages: `check`, `test`, `build`, and `upload`.
The pipeline is run for all updates to Merge Requests or direct pushes to the **develop** branch.
Each job in a stage installs Redis, all dependencies, and RESONAATE before running, and then runs the particular jobs.

## Check Stage

The check stage defines pre-test checks to enforce code styling and ensure that the documentation builds.
- **flake8** runs a full `flake8` linter check and outputs results to a job artifact
- **pylint** runs a full `pylint` linter check and outputs results to a job artifact
- **pages** generates and builds the `sphinx` documentation and uploads the produced html

The check stage jobs are always run during a pipeline.

## Test Stage

The test stage defines active test suites run against the RESONAATE source code.
- **pytest** runs the *entire* unit test suite and calculates the coverage statistics
- **sast** runs static security analysis tools

The test stage jobs are always run during a pipeline.

## Build Stage

The build stage creates source and binary distribution packages of RESONAATE to be distributed on GitLab.
This job is run for every pipeline in which the test stage succeeds.

## Upload Stage

The upload stage pushes the source and binary packages of RESONAATE from the build stage to the GitLab package registry in the RESONAATE repository.
This job is only run on Merge Requests on the **develop** branch for release candidates if the build stage succeeds.
