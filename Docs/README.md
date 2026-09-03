# cgv-open-push project context index

> Status: Active
>
> Owner: Project owner
>
> Last verified: 2026-09-03
>
> Verified against: current Git tree, `README.md`, `v1/`, and 2026-09-03 CGV/Docker validation

This directory is the repository's durable, version-controlled project memory. It stores project
intent, architecture, implementation summaries, confirmed issues, decisions, and cross-session
handoff state. Source code and reproducible validation output remain the evidence for actual behavior.

## Minimum session context

Every new agent session starts with the root `AGENTS.md`, then reads:

1. [`Project/PROJECT_BRIEF.md`](Project/PROJECT_BRIEF.md)
2. [`Status/IMPLEMENTATION_STATUS.md`](Status/IMPLEMENTATION_STATUS.md)
3. [`Work/ACTIVE.md`](Work/ACTIVE.md)
4. Only the technical, issue, task, and ADR documents relevant to the request

Do not load every document by default. Inspect actual implementation and current validation evidence
before relying on mutable status claims.

## Context map

### Project intent

- [`Project/PROJECT_BRIEF.md`](Project/PROJECT_BRIEF.md): purpose, users, scope, constraints, and verified identity
- The root [`README.md`](../README.md): public service description and user-facing instructions

### Technical context

- [`Technical/ARCHITECTURE.md`](Technical/ARCHITECTURE.md): current components, processes, and data flow
- [`Technical/BUILD_TEST_RUN.md`](Technical/BUILD_TEST_RUN.md): safe build, test, probe, and run procedures

### Delivery state

- [`Status/IMPLEMENTATION_STATUS.md`](Status/IMPLEMENTATION_STATUS.md): capability-by-capability state matrix
- [`Status/KNOWN_ISSUES.md`](Status/KNOWN_ISSUES.md): confirmed defects, risks, and required corrective actions
- [`Work/ACTIVE.md`](Work/ACTIVE.md): short index of current cross-session tasks and ownership
- [`Work/Tasks/README.md`](Work/Tasks/README.md): task-file policy
- [`Work/Archive/README.md`](Work/Archive/README.md): useful completed-task history

### Decisions and templates

- [`Decisions/README.md`](Decisions/README.md): architecture decision record policy and index
- [`Templates/TASK_TEMPLATE.md`](Templates/TASK_TEMPLATE.md): cross-session task template
- [`Templates/ADR_TEMPLATE.md`](Templates/ADR_TEMPLATE.md): architecture decision template

## Authority and conflict handling

| Question | Primary source |
|---|---|
| What should the service provide? | Project brief and public README |
| What is actually tracked? | `v1/` source, dependency manifest, and Dockerfile |
| Why was a technical direction chosen? | Accepted ADR and technical documents |
| Has it been proven to work? | Reproducible static, build, bounded network, and container evidence |
| What is being worked on now? | `Work/ACTIVE.md` and linked task files |

If intent and implementation differ, retain both facts: preserve intended behavior and record the
implementation drift in status or known issues.

## Update policy

Update the relevant document in the same change when any of these changes:

- user-visible behavior or supported notification destination;
- CGV request/response contract or polling behavior;
- component, process, directory, or ownership boundaries;
- implemented or verified state;
- required setup, secret names, build, test, or run commands;
- a confirmed defect, expensive decision, or unfinished task's next step.

Do not add chat transcripts, session diaries, or hand-maintained inventories easily regenerated from
source. Validate the context set before completing a change:

```powershell
pwsh -File Scripts/Agent/ValidateProjectDocs.ps1
```
