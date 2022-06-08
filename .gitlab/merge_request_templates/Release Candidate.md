# Release Candidate Merge Request

## Description

Please include relevant motivation and context. List any dependencies that are required for this change. This description will be included in the release notes above the included changelog.

# How Has This Been Tested?

Please describe the tests that you ran to verify your changes. Provide instructions so we can reproduce. Please also list any relevant details for your test configuration

  - [ ] Passes unit test suite
  - [ ] Passes linting checks
  - [ ] Passes integration test (run via CLI)
  - [ ] Passes MR pipeline

# Pre-Release Process

- [ ] Ensure this isn't a duplicate Merge Request
- [ ] Update the change log below, remove unnecessary sub-sections
- [ ] Add changelog subsections to repository **CHANGELOG.md** under __[Unreleased]__
- [ ] Increment all refs the version according to [SemVer](https://semver.org/spec/v2.0.0.html) using pre-release notation (e.g. `1.0.0rc`)
    - [ ] **setup.py**
    - [ ] **docs/source/conf.py**
    - Example version:  `1.3.2rc` is pre-release Major Version 1, Minor Version 3, Patch 2
- [ ] Complete the merge request (only on GitLab)
- [ ] Tag the commit on the `master` branch using
    ```shell
    $ git checkout master
    $ git tag -a v[Major].[Minor].[Patch]rc -m "Pre-Release v[Major].[Minor].[Patch]rc"
    ```
- [ ] Push the tag
    ```shell
    $ git push origin v[Major].[Minor].[Patch]rc
    ```
- [ ] Open a new MR for an Official Release

# Changelog:

Add a formatted changelog. These sub-sections need to be added to the the repository change log under __[Unreleased]__.

- Added

- Changed

- Deprecated

- Removed

- Fixed
