# Release Candidate

**NOTICE:**

Follow the instructions below first. Then fill out the remaining sections. Finally, delete this notice and the instructions.
Review the [GitLab Quick Actions][quick actions] page if you need help.
Review the [Contributing Guidelines][contributing] for details on common developer tasks, the MR process, & the release procedure.

1. Assign this merge request to the primary author using their GitLab username (e.g. `/assign @bobby`).
1. Fill out the description, **thoroughly**.
1. Complete the steps laid out in [Release Procedure](#release-procedure)

<!-- Quick Actions -->

/assign

/draft
/target_branch main
/label ~"Assigned: In Progress"
/label ~"Type: REL"
/label ~"Triage: Label"

## Description

Include relevant motivation and context.
List any dependencies that are required for this change.
This description will be included in the release notes above the included changelog.

## Actionable Tasks

List the action items that **still need to be completed** before the MR is *ready for review*.

**Example:**

- [ ] A checklist
- [ ] outlining the tasks
- [ ] Still needed to be complete
- [ ] and their current
- [x] status

## Minimum Requirements

Please ensure these steps are completed before being approved:

- [ ] Unit tests updated or added to improve coverage
- [ ] Passes unit test suite
- [ ] Passes linting checks
- [ ] Passes integration and regression tests
- [ ] Passes CI/CD pipeline
- [ ] Update docstrings of changed classes, methods, functions
- [ ] Configuration changes are updated in `docs/source/reference/config_format.md`
- [ ] Documentation builds without errors/warnings

## Release Procedure

The HTML documentation for more details on this procedure, see [Contributing](https://code.vt.edu/space-research/resonaate/resonaate/-/blob/develop/CONTRIBUTING.md) for details.

- [ ] Ensure this isn't a duplicate MR
- [ ] Update the changelog below with entries from the __\[Unreleased\]__ section of `CHANGELOG.md`
  - Remove unnecessary subsections
  - Organize and combine items
  - Add links to relevant issues and MRs (see bottom of the of `CHANGELOG.md`)
  - Refer to [Keep A Changelog] for guidelines
- [ ] Move changelog entries from the __\[Unreleased\]__ section of `CHANGELOG.md` to a new section, titled for this release.
  - Leave a blank __\[Unreleased\]__ section at the top.
  - Update the links at the bottom of `CHANGELOG.md`:
    - The latest release should be compared to the previous release
    - Adjust the __\[Unreleased\]__ link to this release to `HEAD`
    - See the bottom of `CHANGELOG.md` for examples
  - The new section should be titled as follows:
    - `#\[M.m.p\]\[vM.m.p\] - YYYY-MM-DD`
    - `M.m.p` is the major/minor/patch release version
    - `YYYY-MM-DD` is the zero-padded release date
- [ ] Increment the version number in the following files:
  - **setup.py**
  - **docs/source/conf.py**
  - **src/resonaate/__init__.py**
  - Example version: `1.3.2` is release Major Version 1, Minor Version 3, Patch 2
- [ ] Request a review from a [Core Developer][core devs]
- [ ] Complete the MR (only on GitLab)
- [ ] Tag the commit on the **main** branch, and push the tag:
  ```bash
  git checkout main
  git pull origin main
  git tag -a vM.m.p -m "Release vM.m.p"
  git push origin vM.m.p
  ```
- [ ] Ensure that the [tag pipeline][pipeline] succeeds
  - Pipeline is created when the tag is pushed to GitLab
- [ ] Change the MR label to: ~"Assigned: Complete"

## Changelog:

Add a formatted changelog. This will be added to the release notes and the repository changelog.

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

[contributing]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/develop/CONTRIBUTING.md
[core devs]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/develop/README.md#authors
[keep a changelog]: https://keepachangelog.com/en/1.0.0/
[pipeline]: https://code.vt.edu/space-research/resonaate/resonaate/-/pipelines?ref=main
[quick actions]: https://docs.gitlab.com/ee/user/project/quick_actions.html
