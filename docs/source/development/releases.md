(dev-releases-top)=

# Releases

Releases provide a way to chronologically break up major development pushes.
The current release "philosophy" is that every few major feature/enhancement merge requests should trigger a new release.
Also, important smaller updates (e.g. bug fixes) should trigger releases.
See our [Changelog](../meta/changelog.md) for details on the versioning scheme.

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

## Prerequisites

You must be a maintainer of the RESONAATE project in order to officially accept the Merge Request on GitLab.
Please read through this entire page to understand the complete process.

Start by reviewing the commits and `git diff` since the latest tag and deciding if the changes are worth creating a new release.
After that, review the `[Unreleased]` section of the [Changelog](../meta/changelog.md) and note if items should be reworded, combined, or removed.
Next, decide whether the release will be a major, minor, or patch version update.
Using this, determine the new release version if the form `vM.m.p`.

## Procedure

If a new release is needed, open a [merge request][new mr] from the **develop** branch into the **main** branch.
Please select the "Release" merge request template, and read through the instructions.
Typically, if you open a release merge request, you should be the assignee, and you should plan on completing the release within a few days.
The merge request name should be something along the lines of "Release vM.m.p" where `vM.m.p` is the associated release version from [Prerequisites](#prerequisites).

### Step 1: Prepare the Changelog

Take the items in the `[Unreleased]` section of the [Changelog](../meta/changelog.md), and place them into the "Release" merge request description under the "Changelog" section.
Use this as a way to properly revise the Changelog items.
Make sure the entries are concise and clear and are organized properly into the sub-categories.
Also, try to add links to relevant merge requests or issues.
Ideally, commits are prefixed with [types](./labels.md#type-labels), which should help organize the changes.

Once the Changelog entries have been organized and revised, create a new section in the repo [Changelog](../meta/changelog.md) file for the new version.
The section should be titled `[M.m.p][vM.m.p] - YYYY-MM-DD]` where `M.m.p` is the release version numbers and `YYYY-MM-DD` is the date of the release (updated later if needed).
Add a link at the bottom of `CHANGELOG.md` for the new release, it should compare the previous release to the new one.
Change the `[unreleased]` link to compare the new release to HEAD.
Create a new blank `[Unreleased]` section in `CHANGELOG.md` with empty sub-categories, see [below](#template-changelog).

```{note}
The links won't actually work until the new release version tag is pushed, but it should be easy to do correctly without verifying it.
See the current links for examples of how to do this.
```

### Step 2: Update the Version

Change the version number to the determined new version `M.m.p` in the following files:

- **setup.py**
- **docs/source/conf.py**
- **src/resonaate/__init__.py**

```{note}
This will change shortly to a more automated process!
```

### Step 3: Commit and Push

Commit the changes to the `CHANGELOG.md` and files with version numbers.
The commit should be titled:

```text
REL: Prep for release vM.m.p
```

Once committed, push it to GitLab, and wait for the pipeline succeed.

### Step 4: Complete the Merge Request

After a successful pipeline, assign a [Core Developer][core devs] to review the release merge request.
The reviewer should review it shortly, and once they have approved you may complete the Merge Request on GitLab.

Once complete, checkout the **main** branch on your local machine and pull the latest updates:

```bash
git checkout main
git pull origin main
```

Then tag the **main** branch using the release version `vM.m.p`:

```bash
git tag -a vM.m.p -m "Release vM.m.p"
```

```{note}
Please make sure to change the version properly!
```

Push the tag to GitLab:

```bash
git push origin vM.m.p
```

This will kick off a pipeline to automatically generate a new [GitLab release][release].
Make sure that this pipeline succeeds and a properly formatted release is generated.
Finally, change the merge request label to "Assigned: Complete".

## Template Changelog

Here is a blank Changelog section with all sub-categories:

### Added

*for new features*

### Changed

*for changes in existing functionality*

### Deprecated

*for soon-to-be removed features*

### Removed

*for now removed features*

### Fixed

*for any bug fixes*

### Security

*in case of vulnerabilities*

### Test

*for test suite specific improvements*

### Development

*for improving developer tools & environment*

### CI

*related to the continuous integration system*

[core devs]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/feature/auto-release/README.md#authors
[new mr]: https://code.vt.edu/space-research/resonaate/resonaate/-/merge_requests/new
[release]: https://code.vt.edu/space-research/resonaate/resonaate/-/releases
