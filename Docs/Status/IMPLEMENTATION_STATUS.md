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
| Python syntax | Verified | all nine `v1/*.py` files compiled successfully on 2026-09-01 | Re-run after Python changes |
| Docker toolchain | Blocked | Docker Desktop 4.88.1 currently exits on a stale `sailor-ingest.sock`; the new image has not been rebuilt | Remove the stale Docker runtime socket, start the engine, and rebuild |
| CGV polling | Blocked | configured endpoint returned HTTP 404 HTML instead of JSON on a bounded 2026-08-31 probe | Discover and document the current supported request contract |
| Change detection | Implemented | movie and screen XML diff paths exist in source | Add fixture tests and verify semantics against current responses |
| Worker supervision | Implemented | recursive `os.execl` paths were removed; focused failure injection verified 60/120/240-second same-worker backoff | Rebuild and run a resource-limited container failure smoke test |
| Kakao self-message | Verified | owner OAuth completed with `talk_message` agreed; Kakao returned `result_code: 0` and the owner confirmed arrival in `나와의 채팅방` on 2026-09-01 | Verify automatic refresh after the first access-token expiry |
| Discord delivery | Deprecated | Discord dependency, token lookup, channel routing, and sender were removed in favor of ADR-0001 | None unless multi-transport support is requested |
| Slack delivery | Planned | feasibility assessed; no Slack source or configuration is tracked | Define notifier boundary and select webhook or Web API contract |
| Status page | Partial | host smoke returned `/` 200 and an expected empty-log `/healthz` 503; log text is escaped | Add authentication before any non-local exposure and verify healthy-log semantics |
| Automated tests | Partial | nine focused CGV contract, Kakao, and worker-retry tests passed on 2026-09-01 | Add fixture tests for change detection |
| Production operation | Blocked | CGV polling is blocked and the current Docker rebuild/smoke test is incomplete | Satisfy project brief recovery criteria |

`Implemented` means code or documentation exists but the required current behavior has not been proven.
Use `Verified` only when reproducible evidence has passed after the relevant change.

## Current tracked footprint

- Application versions: legacy `v1` only
- Python source files: 9
- Active movie-specific targets: 0
- Active screen targets: 9
- Notification transports: Kakao self-message only
- Durable state store: mounted Kakao OAuth token JSON only; CGV snapshots remain in memory
- Automated tests: 9 focused unit tests in 3 files
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

## Current change validation record

On 2026-09-01:

- Kakao app `1564042`: Kakao Login ON, `talk_message` optional consent, localhost redirect URI, and
  `https://github.com` product link verified in the owner console
- Host unit tests: 9 passed
- Python compile check: passed for all current modules
- Docker rebuild: blocked before build because Docker Desktop could not remove its stale
  `C:\Users\quietstring\AppData\Local\Docker\run\sailor-ingest.sock`
- Kakao OAuth: `talk_message` was initially not agreed, then additional consent returned `agreed=true`
- Live Kakao delivery: isolated sender exited 0 after Kakao returned `result_code: 0`; the owner then
  confirmed the exact test message was visible in `나와의 채팅방`
