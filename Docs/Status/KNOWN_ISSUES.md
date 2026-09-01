# Known issues and risks

> Status: Active
>
> Owner: Project team
>
> Last verified: 2026-09-01
>
> Verified against: `v1/` source and 2026-08-31 Docker/probe evidence

| ID | Severity | State | Issue | Evidence | Required action |
|---|---|---|---|---|---|
| ISSUE-001 | Critical | Open | The configured CGV ticket endpoint no longer returns the expected JSON-wrapped XML. | A single bounded request returned HTTP 404 and `text/html` on 2026-08-31. | Identify the current legitimate public request contract, update parsing/configuration, and add fixtures. |
| ISSUE-002 | Critical | In validation | The recursive child restart path was replaced with bounded same-worker retry, but container-level process-count proof is pending. | Focused failure injection produced 60/120/240-second delays and no application re-exec path remains; Docker is currently unavailable for the required resource-limited smoke test. | Rebuild and failure-test process and request counts in a resource-limited container, then resolve. |
| ISSUE-003 | High | Resolved | CGV requests previously had no timeout, HTTP status, content-type, or response-schema validation. | Connect/read timeouts, `raise_for_status()`, JSON content checking, `d.DATA` schema checking, and three focused tests passed on 2026-09-01. | Revisit the schema when ISSUE-001 identifies the current CGV contract. |
| ISSUE-004 | High | Partial | Queue consumption and transient delivery retry were improved, but alerts are still not durable across process or host failure. | The consumer uses `Queue.get(timeout=1)` and three delivery attempts, with no persisted outbox. | Add an outbox or explicitly accept at-most-once loss during host failure. |
| ISSUE-005 | High | Open | The status page can expose recent logs without authentication and inserts log text into HTML without escaping. | Flask `/` reads and renders the latest log lines directly. | Bind locally by default, escape output, minimize sensitive logs, and add access control before public exposure. |
| ISSUE-006 | Medium | Open | Public README status and tracked implementation can be mistaken for the same deployed version. | Git history labels `v1` as pre-renewal while no newer application source is tracked. | Clarify source availability/version support in user-facing documentation or add the maintained implementation. |
| ISSUE-007 | Medium | Open | CGV headers, cookies, encrypted target values, channel IDs, and transport configuration are hard-coded together. | `cgv_open_push_global_variable.py` contains all values. | Separate public target configuration, mutable request metadata, and runtime secrets with validation. |
| ISSUE-008 | Medium | Resolved | The Discord reconnect loop could start the same background loop again. | Discord delivery and its asyncio lifecycle were removed under ADR-0001. | None. |
| ISSUE-009 | Low | Resolved | Screen addition logging recorded the deleted value instead of the added value. | The rewritten added-item branch logs `added`; source compiled and focused tests passed. | Add broader change-detection fixtures under the general test backlog. |

Keep issue IDs stable. Mark an issue `Resolved` only after the corrective behavior and required
validation are recorded. Archive it only when the history no longer helps future maintenance.
