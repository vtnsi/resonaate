(ci-top)=

# GitLab CI

This page describes the continuous integration/deployment (CI/CD) configuration for the `resonaate` project.
Although there are a lot of details, it is well-organized, and you can typically treat each pipeline stage's configuration separately.
Please try to completely read through this reference before altering the CI configuration.
There is a {ref}`ci-pre-reqs` section that defines common terms and mentions helpful tools for exploring the CI system.
Finally, the bottom of this page lists several {ref}`resources <ci-resources>` that should be useful in learning about GitLab CI.

```{note}
Note that this CI is set up to run on a custom shared runner, managed directly by the VT `resonaate` team.
Contact the {ref}`Core Developers <main-index-auth>` if you have questions or there are issues with the CI system.
```

______________________________________________________________________

<!-- TOC formatted for sphinx -->

```{contents} Table of Contents
---
depth: 1
backlinks: entry
local:
---
```

______________________________________________________________________

(ci-pre-reqs)=

## Pre-Requisites

This section describes some basic details that will be necessary before diving further into this document.
Currently, there is a section for common definitions and a section for helpful tools, but more information may come later.

### Definitions

```{rubric} Pipeline
```

A *pipeline* the main component of the CI system; this is what GitLab CI executes.
Pipelines are defined primarily by two subcomponents: *jobs* and *stages*.
Pipelines can be very simple and linear, or they can be extremely complex using directed acyclic graphs and even kicking off other pipelines in different projects!
Basically, a pipeline defines the entire set of operations to be executed and the rules which they must follow.

```{rubric} Job
```

A *job* defines **what** is run during a pipeline.
Jobs typically define `shell` commands for a *runner* to execute.
These jobs also typically use Docker containers for repeatable environments and security reasons.
Examples of jobs include linting, testing, & compiling source code or pushing Docker images to an external registry.

```{rubric} Stage
```

A *stage* defines **when** a pipeline is run.
This means that jobs are grouped into stages which defines their overall order, but not necessarily the order within the stage itself.
You can customize how this works, but usually all jobs of one stage must successfully complete before jobs in the next stage are started.
If the runner is configured to handle it, jobs in the same stage are typically run in parallel.

```{rubric} Runner
```

A *runner* is the computer/server that executes jobs defined by a pipeline.
The runner is connected to the GitLab API over the internet, sending & receiving jobs & data.
Often, runners are provided by GitLab themselves, but the self-hosted VT GitLab instance (<https://code.vt.edu>) doesn't have instance-wide runners to use.
Therefore, we have procured our own server to be a runner, and this is the computer which executes all pipelines for the `resonaate` project.

### Tools

```{rubric} GitLab Workflow
```

I highly recommend the [GitLab Workflow] VS Code extension.
It provides extra details on CI YAML keywords, and will highlight errors.
It is also supposed to lint your CI config, but it isn't currently working for ours.
Finally, it can show you the CI job results and directly links to them.

```{rubric} GitLab CI Editor
```

Another good resource for understanding the CI configuration is the [GitLab CI Editor] which allows you to lint the CI config of different branches, visualize the entire job graph, and directly edit the CI configuration.

(ci-main-cfg)=

## Main CI Config File

The main configuration for GitLab CI in this project lives at `/.gitlab/.gitlab-ci.yml`.
This defines the pipelines that are generated and run when certain events occur; all CI behavior starts with this file.
The main configuration file defines a few keywords that are extremely important to understand and are explained in subsections below:

- {ref}`ci-main-include`
- {ref}`ci-main-default`
- {ref}`ci-main-workflow`
- {ref}`ci-main-stages`

Please refer to the official [reference page][`.gitlab-ci.yml` reference] for details on all the possible keywords in a GitLab CI configuration.

(ci-main-include)=

### Include

The main configuration file is relatively short because it includes other CI configurations under the `.gitlab/ci` directory.
The CI configs are split across multiple files to make it easier to understand the different stages as well as reduce code duplication.

The `include:` keyword controls this behavior, by telling the GitLab CI system to include other files into this file directly.
We currently use only the `local` option which simply points to other config files in the same project, but there are options to include external files as well.
This can be useful for templates and configurations that are already well-defined, such as the [GitLab CI Templates].

<details><summary>Main CI Includes (Click to expand)</summary>

```{literalinclude} ../../../.gitlab/.gitlab-ci.yml
---
name: ci-include
caption: CI Includes
language: yaml
linenos: true
start-at: 'include:'
end-before: =====
---
```

</details>

(ci-main-default)=

### Default

The main pipeline CI configuration file is allowed to define keywords that are used by default for all jobs.
This limited subset of options is defined under the `default:` keyword.

Currently, we only use this to define the job `tags` keyword used by all jobs.
This controls which runner is allowed to execute the job, and is a requirement for all jobs to define.
We only have a single, Linux-based, runner so there isn't a need to distinguish them via job tags (besides the GitLab requirement!).
However, this could be useful if you had runners dedicated to natively testing/building for a specific operating system or if runners had various levels of resources.

<details><summary>CI Default Settings (Click to expand)</summary>

```{literalinclude} ../../../.gitlab/.gitlab-ci.yml
---
name: ci-default
caption: CI Default Properties
language: yaml
linenos: true
start-at: 'default:'
end-before: =====
---
```

</details>

(ci-main-workflow)=

### Workflow

The workflow defines when a pipeline is generated based on specific events.
The events are checked with logic typically using the predefined [GitLab CI Variables].

The `resonaate` pipeline is run for all updates to Merge Requests, direct pushes to the **default** branch, & pushed tags (for releases).

<details><summary>CI Workflow (Click to expand)</summary>

```{literalinclude} ../../../.gitlab/.gitlab-ci.yml
---
name: ci-workflow
caption: CI Workflow
language: yaml
linenos: true
start-at: 'workflow:'
end-before: =====
---
```

</details>

(ci-main-stages)=

### Stages

To better organize the large number of jobs, we sort jobs into several stages.
The stages are defined (in order) as **Check**, **Test**, **Build**, **Release**, **Publish**.
Please look at the `resonaate` [pipelines] page to see examples of these stages.
If one defines a job as part of a stage, it will wait until the previous stage completes to begin by default.
The nominal stage order is shown below in code and in {numref}`fig-mermaid-pipeline`

<details><summary>CI Stages (Click to expand)</summary>

```{literalinclude} ../../../.gitlab/.gitlab-ci.yml
---
name: ci-stages
caption: CI Stages
language: yaml
linenos: true
start-at: 'stages:'
end-before: =====
---
```

</details>

(fig-mermaid-pipeline)=

```{mermaid}
---
caption: CI pipeline stages
---
flowchart LR
  Check --> Test --> Build --> Release --> Publish
```

This behavior can be changed by explicitly setting the [`needs` keyword] which will make the job run asynchronously, only requiring the explicitly stated jobs to finish first.

Here is a quick definition of the pipeline stages:

```{rubric} Check
```

The **check** stage is for linting & static analysis jobs to flag if the pushed code breaks any common conventions.
These jobs are usually run by [`pre-commit`] as well as all pipelines.
They should also be commands that run relatively fast, to quickly inform developers of improper code.

```{rubric} Test
```

The **test** stage is for jobs related to testing the source code.
The entire test suite is checked for all pipelines as well as jobs to track the code coverage.
These jobs typically run immediately, without dependencies, so they quickly inform the developers if something broke.

```{rubric} Build
```

The **build** stage is for building the package into `sdist` and `wheel` forms as well as building the HTML documentation pages.
These jobs are also run for all pipelines, and are typically the last jobs run on Merge Request triggered pipelines.

```{rubric} Release
```

The **release** stage is for jobs related to official releases of the code.
These jobs only run when tags are pushed to GitLab, so we can automate creating [releases].

```{rubric} Publish
```

The **publish** stage pushes the built packages to the GitLab registry.
This is also where Docker or GitLab Pages publishing would go.
These jobs typically run on pushed tags and/or pushes to develop.

(ci-common)=

## Common CI Files

Because many jobs are similar in their basic construction, there are a set of common CI files that most jobs use.
This makes it easier to control overall pipeline behavior and reduce code duplication.
The subsections below describe each of the common CI files.

(ci-common-rules)=

### Rules

Jobs use a common set of rules to define *when* they run.
Every job inherits from one of these so-called "hidden" jobs to ensure they are run at the proper times.
These rules are defined in `/.gitlab/ci/rules.gitlab-ci.yml`:

- `.rules:default`: runs for all pushes to Merge Requests, the default branch, or pushed tags
- `.rules:mr`: runs **only** for pushes to Merge Requests
- `.rules:branch`: runs **only** for pushes to the default branch
- `.rules:tag`: runs **only** for pushed tags
- `.rules:schedule`: runs **only** for **scheduled** pipelines, also it has an optional manual trigger for pushes to Merge Requests

<details><summary>CI Rules Config (Click to expand)</summary>

```{literalinclude} ../../../.gitlab/ci/rules.gitlab-ci.yml
---
name: ci-rule-jobs
caption: Common Rules
language: yaml
linenos:
start-at: .rules:default
---
```

</details>

These hidden jobs are built with simple logic statements using [GitLab CI Variables].

<details><summary>CI Rule Conditions (Click to expand)</summary>

```{literalinclude} ../../../.gitlab/ci/rules.gitlab-ci.yml
---
name: ci-rule-conditions
caption: Rule Definitions
language: yaml
linenos: true
start-at: '.mr:'
end-before: =====
---
```

</details>

(ci-common-jobs)=

### Jobs

Besides the rules, there are many jobs which share other properties because they all use `python`-based Docker images as the job base.
To ensure commonality, reduce duplication, and improve reproducibility a set of common "base" `python` jobs are defined in `/.gitlab/ci/base.gitlab-ci.yml`.
Each of the common job bases extends the `.python-base` job which defines properties to control the `pip` cache directory & when it's invalidated.

<details><summary>Common CI Job Config (Click to expand)</summary>

```{literalinclude} ../../../.gitlab/ci/base.gitlab-ci.yml
---
name: ci-common-job
caption: Base Python Job
language: yaml
linenos: true
start-at: '.python-base:'
end-before: Docker
---
```

</details>

All other jobs can extend one of these jobs if they intend to execute `python` or `pip` commands:

- `.python-latest`: points at the latest officially supported image
- `.python-oldest`: points at the oldest officially supported image
- `.python311`: uses the latest `python3.11-bullseye` image from Docker Hub
- `.python310`: uses the latest `python3.10-bullseye` image from Docker Hub
- `.python39`: uses the latest `python3.9-bullseye` image from Docker Hub

<details><summary>Common Python CI Jobs (Click to expand)</summary>

```{literalinclude} ../../../.gitlab/ci/base.gitlab-ci.yml
---
name: ci-python-jobs
caption: Extendible Python Jobs
language: yaml
linenos: true
start-after: Docker
---
```

</details>

```{note} We only include/support the officially supported versions of Python.
```

(ci-common-scripts)=

### Support Scripts

Different jobs often require similar shell commands to be run, such as installing `apt` & `pip` packages.
The `/.gitlab/ci/scripts.gitlab-ci.yml` file is used to store the shell commands that can be reused across multiple jobs.
The scripts are organized by type: `common`, `pip`, & `apt`.
Any scripts that are specific to a job should remain define directly in the job's keywords.
However, users can reference the these scripts using the `!reference [job, keyword]` syntax.

(ci-jobs)=

## Job Definitions

Now that we have covered the basics of the configuration setup and described the common/reusable pieces, we can dive into the actual jobs.
The jobs below are organized by their **stage**, but this doesn't necessarily restrict them to this exact order.

````{note}
CI configuration file should include the common configuration files, so they can appropriately extend base jobs & reuse commands:

```yaml
include:
  - local: .gitlab/ci/base.gitlab-ci.yml
  - local: .gitlab/ci/rules.gitlab-ci.yml
  - local: .gitlab/ci/scripts.gitlab-ci.yml
```
````

(ci-jobs-check)=

### Check Stage

Jobs in the check stage define **pre**-test checks to enforce code styling, encourage type compliance, and ensure prerequisites for other jobs are appropriately met.
These jobs are quick, run for every pipeline, and only expose the job log as an artifact if they fail.
Also, these jobs have zero dependencies, so they are always immediately started by each pipeline.

- **ruff** runs a full `ruff` linter check

  <details><summary>Config (Click to expand)</summary>

  ```{literalinclude} ../../../.gitlab/ci/check.gitlab-ci.yml
  ---
  name: ci-ruff-job
  caption: ruff
  language: yaml
  linenos: true
  start-at: 'ruff:'
  end-before: ====
  ---
  ```

  </details>

- **manifest** verifies that the `Manifest.in` file properly includes tracked files, so that source distributions work properly

  <details><summary>Config (Click to expand)</summary>

  ```{literalinclude} ../../../.gitlab/ci/check.gitlab-ci.yml
  ---
  name: ci-manifest-job
  caption: check-manifest
  language: yaml
  linenos: true
  start-at: 'manifest:'
  ---
  ```

  </details>

(ci-jobs-test)=

### Test Stage

Jobs in the test stage run test cases against the source code as well as calculate coverage statistics.
All jobs in this stage run for every pipeline, and the `pytest` jobs are run immediately.
However, the coverage jobs must wait for the tests to finish before downloading the artifacts and compiling coverage reports.

- **pytest** jobs run various portions of the test suite via `pytest`. These are split into separate chunks and run in parallel for faster pipelines. Once complete, the jobs upload coverage data & unit test reports as job artifacts.

  <details><summary>Config (Click to expand)</summary>

  ```{literalinclude} ../../../.gitlab/ci/test.gitlab-ci.yml
  ---
  name: ci-unit-test-job
  caption: Unit Test
  language: yaml
  linenos: true
  start-at: 'pytest-unit:'
  end-before: ====
  ---
  ```

  </details>

- **coverage** collects data from the `pytest` jobs and calculates the coverage statistics, uploading the combined coverage data as a job artifact. This job also reports the `coverage` keyword which is automatically parsed by GitLab.

  <details><summary>Config (Click to expand)</summary>

  ```{literalinclude} ../../../.gitlab/ci/test.gitlab-ci.yml
  ---
  name: ci-coverage-job
  caption: Test Coverage
  language: yaml
  linenos: true
  start-at: 'coverage:'
  ---
  ```

  </details>

(ci-jobs-build)=

### Build Stage

The build stage defines tasks that build the source code package and documentation.
All jobs for this stage run in every pipeline, but they may have dependencies on jobs in earlier stages.

- **build-pkg** creates source (`sdist`) and binary (`whl`) distributions of the package and then uploads them as job artifacts using the `build` tool. This job relies on **manifest** finishing successfully.

  <details><summary>Config (Click to expand)</summary>

  ```{literalinclude} ../../../.gitlab/ci/build.gitlab-ci.yml
  ---
  name: ci-build-pkg-job
  caption: Build Package
  language: yaml
  linenos: true
  start-at: 'build-pkg:'
  end-before: =====
  ---
  ```

  </details>

- **build-docs** builds the full HTML documentation and uploads it as a job artifact. This uses the `sphinx` documentation system (and a bunch of plugins) to generate API documentation from docstrings in the source code. This is merged with narrative documentation written in the `/docs/source` directory.

  <details><summary>Config (Click to expand)</summary>

  ```{literalinclude} ../../../.gitlab/ci/build.gitlab-ci.yml
  ---
  name: ci-build-docs-job
  caption: Build Documentation
  language: yaml
  linenos: true
  start-at: 'build-docs:'
  ---
  ```

  </details>

(ci-jobs-release)=

### Release Stage

The release stage performs the actions required for properly releasing a new version of the source code.
Jobs in this stage only run on pushed tag pipelines (releases, after merging into the **main** branch).
By default, these jobs rely on all previous stages to finish before being started.
This is to prevent a premature release in case an earlier stage fails.

- **release-notes** compiles the `git` history since the previous tag and saves it to a temporary file with nice formatting. This file serves as the release notes, and includes regular commits, merge commits, & commit authors. The release notes are uploaded as an artifact.

  <details><summary>Config (Click to expand)</summary>

  ```{literalinclude} ../../../.gitlab/ci/release.gitlab-ci.yml
  ---
  name: ci-release-notes-job
  caption: Generate Release Notes
  language: yaml
  linenos: true
  start-at: 'release-notes:'
  end-before: ====
  ---
  ```

  </details>

- **release** performs an official release procedure using the GitLab [`release` keyword]. This ingests the release notes artifact directly.

  <details><summary>Config (Click to expand)</summary>

  ```{literalinclude} ../../../.gitlab/ci/release.gitlab-ci.yml
  ---
  name: ci-release-job
  caption: Generate Release
  language: yaml
  linenos: true
  start-at: 'release:'
  ---
  ```

  </details>

(ci-jobs-publish)=

### Publish Stage

The publish stage uploads package distributions & containers to the GitLab package & container registries as well as handling any deployments to specific environments.
Jobs in this stage typically only run on pushed tag pipelines (releases, after merging into the **main** branch).
These jobs typically have earlier dependencies that must finish successfully before being able to start.

- **publish-pkg** uploads the package distributions to the GitLab registry. It is only run on pushed tag pipelines (after merges into **main**), and it relies on the **build-pkg** job succeeding.

  <details><summary>Config (Click to expand)</summary>

  ```{literalinclude} ../../../.gitlab/ci/publish.gitlab-ci.yml
  ---
  name: ci-pkg-upload-job
  caption: Publish Package
  language: yaml
  linenos: true
  start-at: 'publish-pkg:'
  end-before: ====
  ---
  ```

  </details>

(ci-jobs-other)=

### Other

These are the other CI jobs/pipelines included under `/.gitlab/ci/` which configure external tools or use external templates.

- `dependabot.gitlab-ci.yml` for running scheduled jobs to perform automated dependency updating. On the GitLab repo, go to <kbd>CI/CD</kbd> → <kbd>Schedules</kbd> → <kbd>RESONAATE - Weekly</kbd> for details on how/when it's run. This is only run against the default branch
- `security.gitlab-ci.yml` includes GitLab SAST & Secret Detection templates for automated security scanning of the repository. This is run during the test stage, only on pushes to the default branch.

(ci-resources)=

## Extra Resources

Here is a compiled list of external resources for those wishing to learn more about CI/CD and the GitLab-specific system in general.

- [GitLab CI/CD Reference] for overall GitLab CI/CD concepts & design
- [`.gitlab-ci.yml` reference] for defining all GitLab CI recognized keywords
- [Resonaate pipelines][pipelines] for exploring recent pipelines and how they execute
- [GitLab Quality CI] for inspiration on a general "rules" file and overall organization\`
- [GitLab containers with `buildah`] for the self-explanatory
- [GitLab CI Templates] for grabbing SAST & Secret Detection tools. There are also a bunch of other good resources
- [Contributing Guide](./contrib.md) for overall description of developer tools used in these jobs
- [GitLab Workflow]: is a VS Code extension that uses the GitLab API to allow for interaction with GitLab directly through VS Code
- [GitLab CI Editor]: is a tool that lets you alter the CI rules and lint the config file
- [GitLab CI Variables]: lists all the predefined GitLab CI variables that are accessible during jobs

[gitlab ci editor]: https://code.vt.edu/space-research/resonaate/resonaate/-/ci/editor
[gitlab ci templates]: https://gitlab.com/gitlab-org/gitlab/-/tree/master/lib/gitlab/ci/templates
[gitlab ci variables]: https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
[gitlab ci/cd reference]: https://docs.gitlab.com/ee/ci/yaml/gitlab_ci_yaml.html
[gitlab containers with `buildah`]: https://major.io/2019/05/24/build-containers-in-gitlab-ci-with-buildah/
[gitlab quality ci]: https://gitlab.com/gitlab-org/quality/pipeline-common/-/tree/master/ci
[gitlab workflow]: https://marketplace.visualstudio.com/items?itemName=GitLab.gitlab-workflow
[pipelines]: https://code.vt.edu/space-research/resonaate/resonaate/-/pipelines
[releases]: https://code.vt.edu/space-research/resonaate/resonaate/-/releases
[`.gitlab-ci.yml` reference]: https://docs.gitlab.com/ee/ci/yaml/
[`needs` keyword]: https://docs.gitlab.com/ee/ci/yaml/#needs
[`pre-commit`]: https://pre-commit.com/index.html
[`release` keyword]: https://docs.gitlab.com/ee/ci/yaml/#release
