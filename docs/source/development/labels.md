(dev-labels-top)=

# Labels

Because this is a large, complex project it helps to organize the issue list with [labels][resonaate labels].
These labels are organized into a few main categories:

- [Priority][priority issue board]
- [Type][type issue board]
- [Status][status issue board]
- [Triage][triage issue board]
- Miscellaneous

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

## Priority Labels

Priority labels (such as ["1: High"][high priority]) describe the overall priority of the issue related to both immediate and long term goals of the project.
The purpose of a priority label is to signal to contributors where they should focus their effort.
Typically, high/critical priority is for immediate research goals or project-critical work.
Low priority is for "nice-to-haves" that are more "wants" than "needs" at the moment.
Everything else falls into medium priority.
Although not frequent, priority labels can change depending on project goals and timelines.

## Type Labels

Type labels (such as ["Type: ENH"][type enh]) provide further context to what topic(s) the issue covers or what types of changes will be needed.
`"ENH"` indicates that this issue is requesting an enhancement (addition) to the project feature set.
`"REF"` is for an issue that primarily requires a refactor of the source code.
`"DEV"` describes changes to non-source code developer tools.
`"DOC"` is for fixes, updates, or additions **solely** to documentation or docstrings.
`"TEST"` is for fixes, updates, or additions **solely** to the test suite.
`"DEP"` is for updating dependency versions.
`"INT"` is for integrating `resonaate` with a specific system or project.
`"REL"` is for creating a new official release.
`"BUG"` is specific to Bug Report issues and is not typically used with other type labels.
Other type labels can be combined if the Feature Request may span multiple topics.
However, three or more type labels can often indicate that a Feature Request is too large in scope, and it should be split into several issues.

## Status Labels

Status labels (such as ["Assigned: In Progress"][assigned in progress]) are for indicating the status of an issue with respect to the implementation.
The typical flow of an issue status is:

```{mermaid}
---
caption: Issue Statuses
---
flowchart LR
  id1[Unassigned] --> id2[On Deck];
  id1[Unassigned] --> id3[In Progress];
  id2[On Deck] --> id3[In Progress];
  id3[In Progress] --> id6[Stalled];
  id6[Stalled] --> id3[In Progress];
  id3[In Progress] --> id4[In Review];
  id4[In Review] --> id5[Complete];
```

These status labels make it easy for other developers to understand the progress of issues and merge requests.
All issues start without a status, and they are considered unassigned.
`"On Deck"` is for issues that contributors expect to start working on soon.
If an issue is currently being worked on it should be in the `"In Progress"`, so other contributors know progress is being made.
However, if an issue becomes stale for a long time it will be labeled with `"Stalled"`.
The `"In Review"` is for issues/merge requests that are in the review process and are close to being complete.
Finally, `"Complete"` is to indicate closed issues that were closed due to completion.
This also specifies issues *not* closed because they were completed/implemented, which can be useful for exploring past issues.

## Triage Labels

Triage labels indicate issues that require attention by core developers.
The most common, `"Label"` indicates that the issue needs labels for proper organization.
The `"Guidance"` is for assignees of issues to indicate that they need help on the issue.
Finally, `"Support"` is for issues asking for help understanding the tool.
All of these issues are great ways for contributors to help out!

## Miscellaneous

The remaining labels don't fit nicely into the previously discussed categories.
`"Discussion"` signals that the issue welcomes open discussion and opinions, this is great for designing new features or deciding between several options.
`"Good First Issue"` are issues that likely require only a few changes.
Issues flagged with this label are a great place for newcomers to start contributing to the project!

[assigned in progress]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues?scope=all&state=opened&label_name%5B%5D=Assigned%3A%20In%20Progress
[high priority]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues?scope=all&state=opened&label_name%5B%5D=1%3A%20High
[priority issue board]: https://code.vt.edu/space-research/resonaate/resonaate/-/boards/1052
[resonaate labels]: https://code.vt.edu/space-research/resonaate/resonaate/-/labels
[status issue board]: https://code.vt.edu/space-research/resonaate/resonaate/-/boards/1053
[triage issue board]: https://code.vt.edu/space-research/resonaate/resonaate/-/boards/1054
[type enh]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues?scope=all&state=opened&label_name%5B%5D=Type%3A%20ENH
[type issue board]: https://code.vt.edu/space-research/resonaate/resonaate/-/boards/1051
