# Known issues and risks

> Status: Active
>
> Owner: Project team
>
> Last verified: 2026-09-03
>
> Verified against: `v1/` source, first-party CGV page assets, focused tests, bounded live probes, and 2026-09-03 resource-limited Docker evidence

| ID | Severity | State | Issue | Evidence | Required action |
|---|---|---|---|---|---|
| ISSUE-001 | Critical | Resolved | The retired ticket endpoint returned 404 instead of the pre-renewal JSON-wrapped XML. | ADR-0002 replaces it with the current same-origin JSON BFF; final-image probes returned 200 JSON, the current/empty response shapes parsed, and fixture tests passed. | Re-open if the endpoint, TLS acceptance, query, or response schema changes. |
| ISSUE-002 | Critical | Resolved | Watcher failures previously executed the full entry script recursively, creating service trees and request storms. | On 2026-09-03 a limited container stayed at 11 processes and zero restarts across two attempts per each of nine failing workers, producing exactly 18 errors; no application re-exec path remains. | Re-run the bounded failure smoke after process-model or retry changes. |
| ISSUE-003 | High | Resolved | CGV requests previously had no timeout, HTTP status, content-type, or response-schema validation. | Current GET requests use a 20-second timeout, `raise_for_status()`, JSON content checks, API status checks, list validation, and required schedule-identity checks. | Re-run the contract tests and bounded probe after request changes. |
| ISSUE-004 | High | Partial | Queue consumption and transient delivery retry were improved, but alerts are still not durable across process or host failure. | The consumer uses `Queue.get(timeout=1)` and three delivery attempts, with no persisted outbox. | Add an outbox or explicitly accept at-most-once loss during host failure. |
| ISSUE-005 | High | Partial | The status page can expose recent logs without authentication, although output escaping and localhost-only Docker binding are now verified. | Flask `/` renders escaped recent log lines; 2026-09-03 smoke commands bound port 5000 to `127.0.0.1`. | Add access control before any public exposure and keep production port binding local by default. |
| ISSUE-006 | Medium | Resolved | Public README status and tracked implementation could be mistaken for the same deployed version. | README and status docs now state that `v1` is a historical directory name, describe its renewed contract, and limit operational claims to recorded validation. | Keep deployment claims tied to current evidence. |
| ISSUE-007 | Medium | Resolved | CGV headers, cookies, encrypted target values, channel IDs, and transport configuration were hard-coded together. | Stale cookies and encrypted values were removed; the target catalog contains public site/filter data, polling values and target selection accept environment overrides, and Kakao secrets remain separate. | Move the public catalog to an external config file if operators need arbitrary targets. |
| ISSUE-008 | Medium | Resolved | The Discord reconnect loop could start the same background loop again. | Discord delivery and its asyncio lifecycle were removed under ADR-0001. | None. |
| ISSUE-009 | Low | Resolved | Screen addition logging recorded the deleted value instead of the added value. | The rewritten added-item branch logs `added`; source compiled and focused tests passed. | Add broader change-detection fixtures under the general test backlog. |
| ISSUE-010 | High | Resolved | One failed site/date used to abort the entire scan and defer every theater's notifications. | ADR-0003 adds per-key snapshots and retry deadlines; unit tests and an offline three-process smoke prove healthy-theater notifications continue and only the failed request retries. | Retain partial-baseline, recovery, date-rollover, and global-spacing coverage. |

Keep issue IDs stable. Mark an issue `Resolved` only after the corrective behavior and required
validation are recorded. Archive it only when the history no longer helps future maintenance.
