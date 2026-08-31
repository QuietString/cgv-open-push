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
| ISSUE-002 | Critical | Open | A watcher exception executes the full entry script from the child process, recursively creating service trees and requests. | `os.execl(sys.executable, sys.executable, *sys.argv)` appears in both watchers; one smoke test reached 2,136 Python processes in about 12 seconds. | Replace it with bounded local retry/backoff or explicit parent supervision; failure-test process and request counts. |
| ISSUE-003 | High | Open | CGV requests have no timeout, HTTP status validation, or response content-type validation. | `requests.post` decodes and parses every response immediately. | Add explicit connect/read timeouts, `raise_for_status`, schema checks, and bounded backoff. |
| ISSUE-004 | High | Open | Notification delivery is not durable and can silently lose dequeued messages. | The consumer uses `Queue.empty()`, removes a message, and has no send-failure acknowledgement/requeue path. | Use blocking/timed consumption and explicit delivery retry/dead-letter semantics. |
| ISSUE-005 | High | Open | The status page can expose recent logs without authentication and inserts log text into HTML without escaping. | Flask `/` reads and renders the latest log lines directly. | Bind locally by default, escape output, minimize sensitive logs, and add access control before public exposure. |
| ISSUE-006 | Medium | Open | Public README status and tracked implementation can be mistaken for the same deployed version. | Git history labels `v1` as pre-renewal while no newer application source is tracked. | Clarify source availability/version support in user-facing documentation or add the maintained implementation. |
| ISSUE-007 | Medium | Open | CGV headers, cookies, encrypted target values, channel IDs, and transport configuration are hard-coded together. | `cgv_open_push_global_variable.py` contains all values. | Separate public target configuration, mutable request metadata, and runtime secrets with validation. |
| ISSUE-008 | Medium | Open | Discord reconnect can attempt to start the same background loop again. | `on_ready` always awaits `send_message.start()`. | Guard loop startup or use a dedicated sender task lifecycle. |
| ISSUE-009 | Low | Open | Screen addition logging records the deleted value instead of the added value. | `cgv_open_push_screen.py` logs `deleted_result` in the added-item branch. | Correct the variable and cover both branches with fixtures. |

Keep issue IDs stable. Mark an issue `Resolved` only after the corrective behavior and required
validation are recorded. Archive it only when the history no longer helps future maintenance.
