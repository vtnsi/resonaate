# Contributing Guide

When contributing to this repository, please first discuss the change you wish to make via issue,
email, or any other method with the owners of this repository before making a change.

______________________________________________________________________

<!-- Start TOC -->

**Table of Contents**

- [Contributing Guide](#contributing-guide)
  - [General Information](#general-information)
    - [New Developers](#new-developers)
    - [Merge Request Process](#merge-request-process)
    - [Git Workflow](#git-workflow)
  - [Developer Tools](#developer-tools)
    - [VS Code Extensions](#vs-code-extensions)
    - [Code Styling](#code-styling)
    - [Testing](#testing)
    - [Docker Images](#docker-images)
  - [GitLab CI/CD](#gitlab-cicd)
    - [Check Stage](#check-stage)
    - [Test Stage](#test-stage)
    - [Build Stage](#build-stage)
    - [Deploy Stage](#deploy-stage)
    - [Release Stage](#release-stage)
    - [Other](#other)

______________________________________________________________________

<!-- END TOC -->

## General Information

In general, developers should attempt to create unit tests for all new code added to ensure proper coverage.
Also, users should review their use of `print()` and `log.debug()` statements when merging completed code into main branches.

Please review the Sphinx-flavored [reST][sphinx-rest] and [napoleon] documentation before contributing code.
Properly documenting your functions and classes is critical to allowing other users to understand how to use them, and adhering to the established style/rules of the RESONAATE documentation is necessary to provide a consistent documentation reading experience.
Also, documenting your own code will force you to review it before passing it on to others to review.

### New Developers

Any new developers should first familiarize themselves with using RESONAATE.
To do this, follow the README instructions to install the tool, and run some short simulations making changes to configuration files to see how behavior is changed.
Once semi-familiar with using the tool, creating the `sphinx` documentation will be helpful for understanding how to use the different parts of the API.

Finally, scan the [issue list][issue-list] and see if there are any interesting bugs or features.
If an issue peaks your interest, read it over and ask a maintainer about tackling the issue.
They should be able to provide more information on if it's a good "first issue" and how to get started.
Open a new branch based on the latest **develop** commit, and start working!

### Merge Request Process

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

### Git Workflow

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

## Developer Tools

To install all development dependencies:

```shell
pip install -e .[dev,test,doc]
pre-commit install
```

### VS Code Extensions

The following VS Code extensions are highly recommended; they can be easily installed by searching them from within the VS Code extension page. Also, make sure to install into WSL as well!

1. [ms-vscode-remote.vscode-remote-extensionpack](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack)
1. [ms-python.python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
1. [esbenp.prettier-vscode](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode)
1. [yzhang.markdown-all-in-one](https://marketplace.visualstudio.com/items?itemName=yzhang.markdown-all-in-one)
1. [eamodio.gitlens](https://marketplace.visualstudio.com/items?itemName=eamodio.gitlens)
1. [streetsidesoftware.code-spell-checker](https://marketplace.visualstudio.com/items?itemName=streetsidesoftware.code-spell-checker)
1. [njpwerner.autodocstring](https://marketplace.visualstudio.com/items?itemName=njpwerner.autodocstring)
1. [bungcip.better-toml](https://marketplace.visualstudio.com/items?itemName=bungcip.better-toml)

### Code Styling

Please lint your features before merging into develop, so the codebase can remain clean, concise, and consistent.

Run the following command to install the proper tools for linting:

```shell
pip install -e .[dev]
pre-commit install
```

To execute linting checks please run both of the following commands:

```shell
pylint *.py tests src/resonaate docs
```

`pylint` is pretty slow for checking every file, so this only checks dirty **.py** files:

```shell
pylint `git diff --name-only --diff-filter=d | grep -E '\.py$' | tr '\n' ' '`
```

`flake8` is another linter that covers different checks:

```shell
flake8 .
```

### Testing

Running unit tests is required before merging into protected branches.

Install `pytest` and our required plugins by executing

```shell
pip install -e .[test]
```

The `pytest` package has _excellent_ [documentation][pytest-docs], so please refer to their [Getting Started][pytest-tutorial] page first.
There is also a helpful tutorial on `pytest` located [here][pytest-realpython].

Running the full test suite is easy:

```shell
redis-server &
pytest
```

This does take a decent amount of time because it includes integration tests. To run a quicker, but still large percentage of tests run the following command:

```shell
pytest -xm "not (service or event or scenario)"
```

This runs only the unit tests which are much faster to run.

To determine coverage statistics:

```shell
coverage run -m pytest -m "not (service or event or scenario)"
coverage combine
coverage report
coverage html
```

Also, refer to the example test module (`tests/example.py`) for how to write and format proper test cases.
To see how the tests behave, run the following:

```shell
pytest -vvs tests/example.py
```

**NOTE** Using `ResonaateDatabase::getSharedInterface()` or `ImporterDatabase::getSharedInterface()` is _usually_ a bad idea when writing a unit test unless the test **requires** it be called first.
If this is the case, please call `ResonaateDatabase::resetData()` or `ImporterDatabase::resetData()` with the appropriate tables to drop.

### Docker Images

Once the **resonaate** submodule is updated & tested, and once the repository is updated to accommodate any changes to **resonaate**, developers should rebuild, tag, save, and upload the new image to the GitLab registry.

1. Rebuild the Docker images:
   ```shell
   docker-compose -f docker-compose.yml build
   ```
1. Generate a personal access token with `write_package_registry` permissions from [GitLab](https://code.vt.edu/-/profile/personal_access_tokens)
1. Login into the container registry:
   ```shell
    docker login code.vt.edu:5005
   ```
   - Use your GitLab username, and the personal access token as your password
1. Next, tag the image(s) using the proper registry hostname & port (from above):
   ```shell
   docker tag <image_id> code.vt.edu:5005/space-research/resonaate/resonaate/<image_name>:<tag>
   ```
   - Be sure to replace `<image_id>`, `<image_name>`, and `<image_tag>` accordingly
1. Now that the image is properly tagged, you can simply push it to the registry:
   ```shell
   docker push code.vt.edu:5005/space-research/resonaate/resonaate/<image_name>:<tag>
   ```
1. Finally, logout of the registry:
   ```shell
   docker logout code.vt.edu:5005
   ```

## GitLab CI/CD

The continuous integration/deployment configuration is located in **.gitlab/.gitlab-ci.yml**.
This is the main CI config file, and it includes other CI config files from **.gitlab/ci/**.
The CI configs are split across multiple files to make it easier to understand the different stages.
The pipeline is run for all updates to Merge Requests or direct pushes to the **develop** & **master** branches.

The **.gitlab/ci/common.gitlab-ci.yml** file defines the workflow, default configs, environment variables, stages, & aliases used by many job definitions.
All jobs will inherit these attributes unless explicitly refusing it or overwriting the configuration values.

### Check Stage

Jobs in the check stage define pre-test checks to enforce code styling and ensure that the documentation builds.

- **flake8** runs a full `flake8` linter check and outputs results to a job artifact
- **pylint** runs a full `pylint` linter check and outputs results to a job artifact
- **sphinx** builds the full documentation and uploads it to a job artifact
- **manifest** verifies that the **Manifest.in** file properly includes tracked files, so that source distributions work properly

The check stage jobs are always run during a pipeline.

### Test Stage

Jobs in the test stage define run test suites against the source code.

- **pytest:\*** jobs run various portions of the test suite. These are split into separate chunks and run in parallel for faster pipelines. The jobs upload coverage data & unit test reports as job artifacts
- **coverage-report** collects data from the test suite jobs and calculates the coverage statistics, uploading the combined coverage data as a job artifact

The test stage jobs are always run during a pipeline.

### Build Stage

The build stage defines tasks that build the source code package distributions.

- **build** creates source (`sdist`) and binary (`whl`) distribution packages and uploads them as job artifacts. This job relies on **manifest** successfully succeeding.

### Deploy Stage

The deploy stage uploads package distributions & containers to the GitLab package & container registries as well as any deployments to specific environments.

- **pages** deploys built documentation to the correct path for GitLab Pages SSG. This doesn't work and needs a new option. This job relies on **sphinx** succeeding.
- **publish** uploads package distributions to the GitLab registry. It is only run when releases are merged into the **master** branch, and it relies on the **build** job succeeding.

### Release Stage

The release stage performs required actions for properly releasing a new version of the source code.
Currently, there are no jobs, but this will change soon.
Jobs to perform are bumping version numbers automatically, creating release notes, tagging the release.
These may need to come before or after **deploy** stage jobs.

### Other

These are the other CI jobs/pipelines included under **.gitlab/ci/** which configure external tools or use external templates.

- **dependabot.gitlab-ci.yml** for running scheduled jobs to perform automated dependency updating. See "CI/CD" -> "Schedules" -> "RESONAATE - Nightly" for details on when it's run
- **security.gitlab-ci.yml** includes GitLab SAST & Secret Detection templates for automated security scanning of the repository.

[issue-list]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues
[napoleon]: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
[pytest-docs]: https://docs.pytest.org/en/latest/
[pytest-realpython]: https://realpython.com/pytest-python-testing/
[pytest-tutorial]: https://docs.pytest.org/en/latest/getting-started.html#getstarted
[sphinx-rest]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html
