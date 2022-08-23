# GitLab CI System

This directory contains all the configuration for the GitLab continuous integration system used by RESONAATE.
We have several pipeline configurations with multiple stages and jobs per stage.
There is a detailed guide on how the CI system works included in the [documentation](../docs/README.md), so please build the docs and read the guide there if you have any questions.

______________________________________________________________________

<!-- START TOC -->

<!-- TOC Formatted for GitLab -->

**Table of Contents**

\[\[_TOC_\]\]

<!-- END TOC -->

______________________________________________________________________

## Layout

The "entry" point file for GitLab CI pipelines is the `.gitlab-ci.yml` file which contains global pipeline settings.
The `ci` directory contains further configurations split into separate files by stage.
The `templates` directories contain GitLab issue and merge request templates files for the project.
The `dependabot.yml` file is for configuring the Dependabot dependency checker job.
