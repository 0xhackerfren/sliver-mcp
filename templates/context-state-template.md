# Context State: [Project Name]

Last updated: [YYYY-MM-DD HH:MM]
Updated by: [human / agent-task-id]

## Active Phase

[Current phase in the pipeline: Phase 0-7 / 6b. Include what station work is currently at.]

## Project Summary

[2-3 sentences describing the project, its purpose, and current scope. Enough for a new agent session to orient without reading every document.]

## Architecture Decisions

[Key architectural decisions made during Phase 1 that constrain all subsequent work. List only decisions, not rationale (link to architecture docs for rationale).]

- [ ] _[Decision 1]_
- [ ] _[Decision 2]_

## Active Bounded Contexts

[List the bounded contexts currently defined, with their status.]

| Context | Status | Spec | SDK | Tests | Casting |
|---------|--------|------|-----|-------|---------|
| _[name]_ | _[active/complete/blocked]_ | _[done/in-progress/pending]_ | _[done/in-progress/pending]_ | _[done/in-progress/pending]_ | _[done/in-progress/pending]_ |

## Current Work

[What is actively being worked on right now. Include agent task IDs if applicable.]

### In Progress

- _[Task description, linked to spec section]_

### Blocked

- _[Blocker description and what is needed to unblock]_

### Recently Completed

- _[Completed item with date]_

## Open Decisions

[Decisions that need human input before work can proceed.]

1. _[Decision needed, context, options considered]_

## Known Gaps

[Gaps discovered but not yet recovered. Link to gap assessment if filed.]

- _[Gap description, severity, link]_

## SDK Surface Summary

[Current state of the SDK constraint surface. What building blocks exist, what is planned.]

- **Available blocks:** _[list or link to block registry]_
- **Planned extensions:** _[list]_
- **Design tokens:** _[present / not yet created / link to design identity]_

## Key File Locations

[Quick reference for an agent starting a new session.]

- Specification: _[path]_
- SDK: _[path]_
- Test plan: _[path]_
- Architecture: _[path]_
- Design identity: _[path or N/A]_
- Block registry: _[path or N/A]_

## Session History

[Brief log of recent sessions for continuity.]

| Date | Agent/Human | Summary |
|------|-------------|---------|
| _[date]_ | _[who]_ | _[what happened]_ |

## Checkpoint

[Structured snapshot for the next session to pick up from.]

**Resume from:** _[Exact point where work should continue]_
**Prerequisites met:** _[What is already done that the next session can assume]_
**Next action:** _[The very first thing the next session should do]_
