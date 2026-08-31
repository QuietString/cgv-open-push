# Implementation status

> Status: Active
>
> Owner: Project team
>
> Last verified: 2026-09-01
>
> Verified against: current Git tree, source inspection, AST parse, Docker build, bounded CGV probe, and smoke-test output

## Status matrix

| Area | State | Evidence | Next step |
|---|---|---|---|
| Agent context system | Verified | root `AGENTS.md`, indexed context files, templates, and validator; validator passed on 2026-09-01 | Re-run after context-policy or document-structure changes |
| Python syntax | Verified | all six `v1/*.py` files parsed successfully on 2026-08-31 | Re-run after Python changes |
| Docker toolchain | Verified | Docker Desktop Linux engine and WSL 2 responded; `cgv-open-push:test` built on 2026-08-31 | Rebuild after dependency or Dockerfile changes |
| CGV polling | Blocked | configured endpoint returned HTTP 404 HTML instead of JSON on a bounded 2026-08-31 probe | Discover and document the current supported request contract |
| Change detection | Implemented | movie and screen XML diff paths exist in source | Add fixture tests and verify semantics against current responses |
| Worker supervision | Blocked | parse failure caused recursive application execution and 2,136 processes in about 12 seconds | Replace `os.execl` restart behavior and failure-test it |
| Discord delivery | Partial | client and channel routing exist; empty token produced expected 401 during smoke test | Test with operator-provided test credential after worker safety fix |
| Slack delivery | Planned | feasibility assessed; no Slack source or configuration is tracked | Define notifier boundary and select webhook or Web API contract |
| Status page | Partial | Flask endpoint returned HTTP 200 on port 5000 during smoke test | Correct health semantics and address log exposure |
| Automated tests | Planned | no unit, integration, or process-safety tests are tracked | Add fixture tests before restoring live operation |
| Production operation | Blocked | CGV polling and worker supervision are blocked | Satisfy project brief recovery criteria |

`Implemented` means code or documentation exists but the required current behavior has not been proven.
Use `Verified` only when reproducible evidence has passed after the relevant change.

## Current tracked footprint

- Application versions: legacy `v1` only
- Python source files: 6
- Active movie-specific targets: 0
- Active screen targets: 9
- Notification transports: Discord only
- Durable state store: none
- Automated tests: none
- Container orchestration file: none

## Baseline validation record

On the 2026-08-31 Windows/Docker Desktop workstation:

- Docker Desktop and WSL 2: available
- Docker image `cgv-open-push:test`: built successfully
- Status page during smoke test: HTTP 200
- Discord login without a configured token: HTTP 401 / `LoginFailure`
- One bounded CGV request: HTTP 404 with HTML response
- Full-service failure behavior: 2,136 Python processes after about 12 seconds; container stopped
- Test container: removed after capture; built image retained locally

This record documents the baseline failure mode; it does not certify the service as operational.
