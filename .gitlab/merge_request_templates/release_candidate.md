# Release Candidate Merge Request

## Description

Please include relevant motivation and context. List any dependencies that are required for this change. This description will be included in the release notes above the included changelog.

# How Has This Been Tested?

Please describe the tests that you ran to verify your changes. Provide instructions so we can reproduce. Please also list any relevant details for your test configuration

- [ ] Unit tests updated or added to improve coverage
- [ ] Passes unit test suite
- [ ] Passes linting checks
- [ ] Passes integration test (run via CLI)
- [ ] Passes MR pipeline
- [ ] Documentation builds without errors/warnings & review any changes

# Release Process

- [ ] Ensure this isn't a duplicate Merge Request
- [ ] Update the change log below from __\[Unreleased\]__, remove unnecessary sub-sections
- [ ] Move changelog under __\[Unreleased\]__ of the repository **CHANGELOG.md** to a new section, titled for this release. Leave a blank __\[Unreleased\]__ section
- [ ] Increment all refs the version according to [SemVer](https://semver.org/spec/v2.0.0.html) using release notation (e.g. `1.0.0`)
  - [ ] **setup.py**
  - [ ] **docs/source/conf.py**
  - [ ] **src/resonaate/__init__.py**
  - Example version:  `1.3.2` is release Major Version 1, Minor Version 3, Patch 2
- [ ] Complete the merge request (only on GitLab)
- [ ] Tag the commit on the `main` branch using
  ```shell
  git checkout main
  git tag -a v[Major].[Minor].[Patch] -m "Release v[Major].[Minor].[Patch]"
  ```
- [ ] Push the tag
  ```shell
  git push origin v[Major].[Minor].[Patch]
  ```
- [ ] Edit the tag's release notes on GitLab to include the changelog below (and description section above) to officially release this version.

# Changelog:

Add a formatted changelog. This will be added to the release notes and the repository change log.

- Added

- Changed

- Deprecated

- Removed

- Fixed
