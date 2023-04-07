# Feature Implementation

**NOTICE:**

Follow the instructions below first. Then fill out the remaining sections. Finally, delete this notice and the instructions.
Review the [GitLab Quick Actions][quick actions] page if you need help.
Review the [Contributing Guidelines][contributing] for details on common developer tasks & the MR process.

1. Link issue(s) closed by this MR (e.g. `Closes #2, #30`).
1. Link issue(s) that are related, but not closed by this MR (e.g. `Related to #4, #15`).
1. Assign this issue to the primary author using their GitLab username (e.g. `/assign @bobby`).
1. Copy the labels & milestones from the most relevant issue (e.g. `/copy_metadata #2`).

<!-- Closing/Related Issues -->

Closes #(issue), #(issue), ...

Related to #(issue), #(issue), ...

<!-- Quick Actions -->

/assign
/copy_metadata

/draft
/target_branch develop
/label ~"Assigned: In Progress"

## Description

Include relevant motivation and context.
List any dependencies that are required for this change.
Include important discussion threads from the relevant issues.

## Proposed Changes

Describe, in list format, the proposed changes to the project.

**Example:**

- Typo in `module.py`
- Math error in `Class.methodB()`
- Added test case `ApplicationTest.testBehavior()` to ensure new bugs aren't missed

## Actionable Tasks

List the action items that **still need to be completed** before the MR is *ready for review*.

**Example:**

- [ ] A checklist
- [ ] outlining the tasks
- [ ] Still needed to be complete
- [ ] and their current
- [x] status

## Test Plan

Describe the tests that you ran to verify your changes.
Provide instructions so we can reproduce.
Please also list any relevant details for your test configuration.

## Minimum Requirements

Please ensure these steps are completed before being approved:

- [ ] Unit tests added to cover the enhancement
- [ ] Passes unit test suite
- [ ] Passes linting checks
- [ ] Passes integration and regression tests
- [ ] Passes CI/CD pipeline
- [ ] Update docstrings of changed classes, methods, functions
- [ ] Configuration changes are updated in `docs/source/reference/config_format.md`
- [ ] Documentation builds without errors/warnings
- [ ] Add updates to `CHANGELOG.md` under **Unreleased**
  - **NOTE**: This should be an organized version of items under [Proposed Changes](#proposed-changes)

## Concerns

List any concerns or issues you may have regarding this MR.

> Optional

## Roadblocks

List any obstacles to completing this MR.
The items should include links/@tags to appropriate Issues/POCs.

> Optional

<!-- Links -->

[contributing]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/develop/CONTRIBUTING.md
[quick actions]: https://docs.gitlab.com/ee/user/project/quick_actions.html
