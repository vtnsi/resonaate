# Contributing Guide

Thank you for considering contributing to RESONAATE!
Having contributors like you is what makes this project so awesome.
Here are few ways you can contribute to the project:

- Make new tutorials & examples
- Write technical explanations for the documentation
- Improve the source code docstrings
- Submit bug reports & feature requests
- Review merge requests
- Discuss the current status of the package
- Add unit tests for uncovered modules
- Contribute source code

All contributors are expected to be respectful of each other and welcoming to all newcomers.
Please see the Virginia Tech [Student Code of Conduct](https://codeofconduct.vt.edu) for more official guidelines.

Finally, this contributing guide is meant to serve as a brief overview of the most common topics.
There are more detailed guides in the official HTML documentation that are referenced here which provide much more context.
Please read over this page first, then follow the instructions under [Documentation](#documentation) to build and view the official HTML documentation.
You will find much more thorough explanation of all topics there.

______________________________________________________________________

<!-- START TOC -->

<!-- TOC Formatted for GitLab -->

**Table of Contents**

\[\[_TOC_\]\]

<!-- END TOC -->

______________________________________________________________________

## General Information

In general, we ask contributors to abide by software best practices as much as possible.
We try to reduce the cognitive overhead of this by automating as much as we can and laying out well-defined processes along with the requisite documentation.

We ask new developers to be curious about improving their software skills, and they will be rewarded with a great experience.
A few very important topics for new developers to learn are:

- software testing practices
- source control
- documentation
- style & formatting

Don't worry if you aren't familiar with any of these... they aren't prerequisites, but things to learn over time!

### Why?

If you're curious why a software tool for research *aims* to follow "professional" processes and management, please refer to the excellent paper by Software Carpentry on [Best Practices in Scientific Computing](https://arxiv.org/abs/1210.0530) and [The Good Research Code Handbook](https://goodresearch.dev/index.html).
The [Scikit HEP](https://scikit-hep.org/developer) is a great example of well-maintained, professional software used in cutting-edge research.

## Your First Contribution

If you are new to RESONAATE, checkout the [Issue Tracker][issue-list] for any ["Good First Issue"][newcomer issues] labels... these are specifically flagged as issues that are easier to start your RESONAATE development experience.
Please feel free to ask questions from any of the listed contributors; everyone was a beginner at some point!

The full documentation has a thorough explanation of the developer workflow, so make sure to [build the docs](#documentation) and read through them!
As a quick overview, the general process for working on an issue is:

1. Install the [Developer Tools](#developer-tools)
1. Create a new branch to track the issue (typically a **feat/** or **bug/**)
1. Code away, making sure to `git commit` *often*
1. Push the code back to GitLab
1. Open a [Merge Request][new merge request] following instructions in the [Template][merge request template]
1. Let others review your code

New contributors are also welcome to create issues for reporting bugs or requesting enhancements.
Please make sure to first search [All Open & Closed Issues][all issues] for similar or duplicate issues.
Then you can create an [Issue][new issue] following instructions in the provided [Template][issue template].

## Developer Tools

### Development Installation

First clone the repository (make sure you have [ssh keys][ssh-keys] set up):

```bash
git clone git@code.vt.edu:space-research/resonaate/resonaate.git
cd resonaate
```

Ensure the latest **develop** branch is checked out:

```bash
git checkout develop
```

Create a virtual environment and activate it:

```bash
python3 -m venv .venv --prompt res-dev
source .venv/bin/activate
```

It's highly recommended to install all development dependencies:

```bash
make install
```

If you want more explanation, please follow the instructions under [Documentation](#documentation) to build and serve the documentation.
The full documentation includes more specific details on development best practices.

Also, if you need help setting up the rest of your developer environment, checkout the [Developer Quickstart Guide][dev-quickstart].
This has a lot more detail on more general set up procedures, primarily focused at using WSL 2 on Windows with VS Code.

### Source Control

We use `git` extensively to properly manage many concurrent branches in activate development.
The developer documentation does include details on how to use `git` in common workflows, but does not go into great detail or provide an in-depth tutorial.
There are a myriad of resources on the internet for learning `git`, including a good [list maintained by `numpy`](https://numpy.org/devdocs/dev/gitwash/git_resources.html#git-resources) and a [tutorial by Software Carpentry](https://swcarpentry.github.io/git-novice/index.html).
We defer to those resources which do a much better job of properly introducing `git`.
Of course, all team members are happy to directly answer any questions you have!

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

## Documentation

- Follow [Developer Tools](#developer-tools) for how to install the required tools to build the documentation.

- Make the documentation

  ```bash
  make doc
  ```

- Open [http://localhost:8000/](http://localhost:8000/) in a browser

## Code Style

Please lint your features before merging into develop, so the codebase can remain clean, concise, and consistent.

To execute linting checks please run both of the following commands:

```bash
make lint
```

`ruff` is another linter that covers different checks:

```bash
ruff check --no-fix src tests
```

To run `pre-commit` against the entire repo:

```bash
pre-commit run --all-files
```

## Testing

Running unit tests is required before merging into protected branches.

The `pytest` package has _excellent_ [documentation][pytest-docs], so please refer to their [Getting Started][pytest-tutorial] page first.
There is also a helpful tutorial on `pytest` located [here][pytest-realpython].

Running the full test suite is easy:

```bash
make test_all
```

This does take a decent amount of time because it includes integration tests. To run a quicker, but still large percentage of tests run the following command:

```bash
make test
```

This runs only the unit tests which are much faster to run.

To include coverage information against the entire codebase, simply add `--cov`:

```bash
make coverage
```

Also, you can generate coverage statistics for a specific module (or package) by pointing at specific tests/files:

```bash
pytest --cov=src/resonaate/sensors tests/sensors
```

A lot of files may be created, you can quickly remove them with:

```bash
make clean
```

## Communications

The RESONAATE group uses a few different methods of communication: GitLab, Microsoft Teams, Google Group (email).
Please contact a core developer to be added to the proper communication channels.
Here is a brief description of each channel, and the most appropriate communication types:

- GitLab
  - Long-form topics, discussions, & issues related to project development
  - Project-specific context
  - Document bugs & request features
  - Ask for help debugging & request a code review
  - Collaborate on a paper
- Microsoft Teams
  - Shorter-form topics & discussions
  - Thread-specific context
  - Used for meetings, announcements, coding questions
  - Store documents that are commonly passed around
- Google Group (email)
  - Official or important emails
  - The most direct way to get everyone's attention

[all issues]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues?scope=all&state=all
[dev-quickstart]: https://code.vt.edu/space-research/developer-quickstart
[issue template]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/feature/auto-release/.gitlab/issue_templates/Default.md
[issue-list]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues
[merge request template]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/feature/auto-release/.gitlab/merge_request_templates/Default.md
[new issue]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues/new
[new merge request]: https://code.vt.edu/space-research/resonaate/resonaate/-/merge_requests/new
[newcomer issues]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues?scope=all&state=opened&label_name%5B%5D=Good%20First%20Issue
[pytest-docs]: https://docs.pytest.org/en/latest/
[pytest-realpython]: https://realpython.com/pytest-python-testing/
[pytest-tutorial]: https://docs.pytest.org/en/latest/getting-started.html#getstarted
[ssh-keys]: https://code.vt.edu/help/user/ssh
