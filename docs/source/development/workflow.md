(dev-workflow-top)=

# Workflow

This page describes common processes used during RESONAATE development as well as information specific to the project's GitLab page.
The core developers greatly appreciate anyone who attempts to properly follow the guidelines described below and include good details in their communications.
These guidelines help to respect everyone's time by reducing noise on both sides, and encouraging detailed/direct discussions.

______________________________________________________________________

<!-- TOC formatted for sphinx -->

```{contents} Table of Contents
---
depth: 2
backlinks: top
local:
---
```

______________________________________________________________________

(dev-workflow-issues)=

## Issues

All contributors are encouraged to [submit issues][new issue] by following the provided templates on GitLab.
The instructions should be self-explanatory, and core developers may ask for more details if not enough are provided.

RESONAATE defines two issue categories: **Bug Report** and **Feature Request**.

```{rubric} Bug Report
```

A Bug Report is for describing unexpected behavior of the `resonaate` tool.
To facilitate fixing the bug, it is important to include as much detail as is relevant.
Other contributors should be able to easily reproduce the same exact bug without much effort, and it's typically expected that logs and/or code snippets are included in the Bug Report.
Finally, it is important to be specific in the difference between the *expected versus actual* behavior, so it is clear **why** this is a bug.

```{rubric} Feature Request
```

A Feature Request is any issue that is specifically **not describing a bug**.
This can range between many things, including large architectural changes and minor feature additions.
Specific details on *what* needs to be changed and *why* this feature is wanted is encouraged.
However, these issues can be more open-ended involving discussions over time that clarify the scope or implementation details.
If this is the case, it is helpful to update the issue description when more details are agreed upon.

(dev-workflow-workflow)=

## Typical Workflow

To get started, you will need to have `git` installed locally. There are also a number of other dependencies required detailed in "Developer Tools" section of the [Contributing Getting Started](./contrib).

Let's assume that you decide to work on Issue 45, a **Feature Request** issue titled "Add node dynamics".
The very first step is to always ensure that the issue is small enough in scope, AKA one unit of work.
This prevents issues from touching too many things at once, which prevents complex `git` issues and bugs.
The next step is to make sure you are marked as the assignee on GitLab, to avoid developers working on the same issues.
If someone else is already assigned, please contact them directly to determine if they have already started making progress.
Now we're ready to begin work!

You should have [SSH Keys][ssh keys tutorial] configured first, before continuing.
Once you have `git` and are sure you have all the necessary dependencies, it's time to start!

### Step 1: Clone

Clone the project [on GitLab][repo root] locally to your machine.

```bash
git clone git@code.vt.edu:space-research/resonaate/resonaate.git
cd resonaate
```

Configure `git` so that it knows who you are:

```bash
git config user.name "Bobby Boucher"
git config user.email "captain.insano@example.com"
```

If you already have the RESONAATE project cloned, you can instead check out the default branch and pull the latest changes:

```bash
git checkout develop
git pull origin develop
```

### Step 2: Branch

As a best practice to keep your development environment as organized as possible, create local branches to work within.
These should also be created directly off of the default branch (**develop** in this project).
Generally branches should be named according to their issue type, issue number, & issue title.

- **Feature Requests** should use the prefix **feat/**
- **Bug Fixes** should use the prefix **bug/**
- Include the number of the issue it addresses before a descriptive name

The general command for this is:

```bash
git checkout -b my-branch -t default-branch
```

Following the example from above, the branch name should be something similar to **feat/45-add-node-dynamics**.
The properly filled out command will be:

```bash
git checkout -b feat/45-add-node-dynamics -t develop
```

### Step 3: Code

The vast majority of issues in the RESONAATE repository includes changes to one or more of the following:

- source code contained within `src`
- documentation within `docs`
- tests within `tests`

If you are modifying code, please be sure to properly lint the code to ensure changes abide by the RESONAATE [code style guide](./style.md).
Also, please make sure to add tests covering any added or changed code.
See [Test Tutorial](./test.md) for more information.
Any documentation you write (including code comments and API documentation) should follow the [documentation style guide](./docs.md).

### Step 4: Commit

It is a best practice to keep your changes as logically grouped as possible within individual commits.
There is no limit to the number of commits any single merge request may have, and many contributors find it easier to review changes that are split across multiple commits.
However, please keep in mind that issues and changes should be as small in scope as possible, so it is easier to review and understand the changes

```bash
git add my/changed/files
git commit
```

#### Commit message guidelines

A good commit message should describe what changed and why.

1. The first line should:

   - contain a short description of the change (preferably 50 characters or
     fewer, and no more than 72 characters)
   - be entirely in lowercase except for proper nouns, acronyms, and
     the words that refer to code, like function/variable names
   - be prefixed with the type of changes and start with an imperative verb, see [type labels](./labels.md#type-labels) for prefix types.

   Examples:

   - `ENH: add keplerSolve() to orbits sub-pkg`
   - `DOC: fix typos in README.md`

1. Keep the second line blank.

1. Wrap all other lines at 72 columns (except for long URLs).

1. If your patch fixes an open issue, you can add a reference to it at the end
   of the log. Use the `Fixes:` prefix and the issue number. For other
   references use `Refs:`.

   Examples:

   - `Fixes: #45`
   - `Refs: #2`

Sample complete commit message:

```text
TYPE: explain the commit in one line

The body of the commit message should be one or more paragraphs, explaining
things in more detail. Please word-wrap to keep columns to 72 characters or
less.

Fixes: #45
Refs: #2
```

If you are new to contributing to RESONAATE, please try to do your best at conforming to these guidelines, but do not worry if you get something wrong.
One of the existing contributors will help get things situated.

### Step 5: Rebase

As a best practice, once you have committed your changes, it is a good idea
to use `git rebase` (not `git merge`) to synchronize your work with the **develop** branch.

```bash
git checkout develop
git pull origin develop
git checkout my-branch
git rebase develop
```

This ensures that your working branch has the latest changes from RESONAATE.
If you have an issue doing this, please ask for help from another contributor.

### Step 6: Test

Bug fixes and features should always come with tests. A [guide for writing tests](./test.md) has been provided to make the process easier.
Looking at other tests to see how they should be structured can also help.

Before submitting your changes in a merge request, always run the full test suite.
To run the tests:

```bash
pytest
```

For some configurations, running all tests might take a long time (a few minutes).
To run a subset of the test suite, see the "Testing" section of [Contributing Guide](./contrib).

### Step 7: Push

Once you are sure your commits are ready to go, with passing tests and linting, begin the process of opening a merge request by pushing your working branch to [GitLab][repo root].

```bash
git push origin my-branch
```

Or, following the example

```bash
git push origin feat/45-add-node-dynamics
```

### Step 8: Opening the Merge Request

From within GitLab, opening a new [merge request][new merge request] will present you with [merge request directions][default mr].
It will point you to the templates which are pre-formatted with sections to fill in.
Please try to do your best at filling out the details, but feel free to skip parts if you're not sure what to put.

All merge requests are initially set to "Draft Mode" with an "In Progress" label when first opened.
Initially, no reviewer should be assigned until work is complete.
When you think you are close to done, you can remove the "Draft Mode" by clicking `Mark as ready` on the GitLab Merge Request.
Make sure the latest pipeline has completed without any job failures.
After this, assign a reviewer (usually one of the core developers).

Once the reviewer is done, you should implement all requested fixes.
Fixes prefixed with "NIT" are optional.
Comment on the MR when the fixes are complete, tagging the reviewer, so they can review the latest changes.

This cycle may occur a few times before the branch is officially merged into **develop**, don't be discouraged!
Please don't take a large set of fixes personally.
Also, if you do not understand a required fix, please ask the reviewer or another contributor for help.

If a git conflict arises, it is necessary to synchronize your branch with other changes in **develop** by using `git rebase`:

```bash
git checkout develop
git pull origin develop
git checkout my-branch
git rebase develop
git push --force-with-lease origin my-branch
```

```{warning}
The `git push --force-with-lease` command is one of the few ways to delete history in `git`.
It also complicates the review process, as it won't allow reviewers to get a quick glance on what changed.
Before you use it, make sure you understand the risks.
If in doubt, you can always ask for guidance in the MR.
```

## Reviewing Merge Requests

If you have been assigned an issue, please try to review within a few days.
Also, you may reassign the review to another contributor if that is appropriate.
Once starting the review, change the MR status label to "In Review".

Reviewers should check out the branch locally on their own machine and run any tests or examples.
Once they have reviewed locally, the reviewer can choose to perform a review directly in GitLab, or submit a comment outlining all review points.
Please be polite, respectful, and encouraging when reviewing a MR.
Pointing out good solutions is always welcome.
Use "NIT" as a prefix for small details that are optional (anything that isn't incorrect, incomplete, confusing, or needs refactoring).

Once you submit the review, the MR author will implement any fixes and ping you when it's ready for another review.
Please be cognizant of people's time and don't hold up a MR for very small subjective reasons.
Once it is ready for merge, comment "LGTM" (Looks Good To Me), wait for the pipeline to succeed, and hit `Merge...`.

[default mr]: https://code.vt.edu/space-research/resonaate/resonaate/-/blob/feature/auto-release/.gitlab/merge_request_templates/Default.md
[new issue]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues/new
[new merge request]: https://code.vt.edu/space-research/resonaate/resonaate/-/merge_requests/new
[repo root]: https://code.vt.edu/space-research/resonaate/resonaate
[ssh keys tutorial]: https://code.vt.edu/help/ssh/index.md
