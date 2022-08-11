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
  - Open a merge request into `main` for the release candidate
  - This ensures `main` remains "production-ready" as much as possible

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
pytest -xm "not (event or scenario)"
```

This runs only the unit tests which are much faster to run.

To determine coverage statistics:

```shell
coverage run -m pytest -m "not (event or scenario)"
coverage combine
coverage report
coverage html
```

Also, refer to the example test module (`tests/example.py`) for how to write and format proper test cases.
To see how the tests behave, run the following:

```shell
pytest -vvs tests/example.py
```


[issue-list]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues
[napoleon]: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
[pytest-docs]: https://docs.pytest.org/en/latest/
[pytest-realpython]: https://realpython.com/pytest-python-testing/
[pytest-tutorial]: https://docs.pytest.org/en/latest/getting-started.html#getstarted
[sphinx-rest]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html
