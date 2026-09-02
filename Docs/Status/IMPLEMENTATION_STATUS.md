# Implementation status

> Status: Active
>
> Owner: Project team
>
> Last verified: 2026-09-03
>
> Verified against: current Git tree, source inspection, tests, 2026-09-03 Docker build, and resource-limited smoke output

## Status matrix

| Area | State | Evidence | Next step |
|---|---|---|---|
| Agent context system | Verified | root `AGENTS.md`, indexed context files, templates, and validator; validator passed on 2026-09-01 | Re-run after context-policy or document-structure changes |
| Python syntax | Verified | all nine `v1/*.py` files compiled successfully on 2026-09-01 | Re-run after Python changes |
| Docker toolchain | Verified | Docker engine 29.7.2 built `cgv-open-push:test` from commit `2e7f9da`; image validation found nine importable Python modules and no `.env` or token file | Rebuild after dependency or Dockerfile changes |
| CGV polling | Blocked | configured endpoint returned HTTP 404 HTML instead of JSON on a bounded 2026-08-31 probe | Discover and document the current supported request contract |
| Change detection | Implemented | movie and screen XML diff paths exist in source | Add fixture tests and verify semantics against current responses |
| Worker supervision | Verified | resource-limited container held 11 processes and zero restarts across two failure attempts per each of nine workers; exactly 18 errors were observed | Retain limits in deployment and re-test after process-model changes |
| Kakao self-message | Verified | owner-confirmed test delivery plus a 2026-09-03 container token refresh through the mounted `/data` path | Monitor refresh-token expiry and reauthorize when required |
| Discord delivery | Deprecated | Discord dependency, token lookup, channel routing, and sender were removed in favor of ADR-0001 | None unless multi-transport support is requested |
| Slack delivery | Planned | feasibility assessed; no Slack source or configuration is tracked | Define notifier boundary and select webhook or Web API contract |
| Status page | Partial | limited containers returned `/` 200, empty-log `/healthz` 503, and active-log `/healthz` 200 through `127.0.0.1`; log text is escaped | Add authentication before any non-local exposure |
| Automated tests | Partial | nine focused CGV contract, Kakao, and worker-retry tests passed on 2026-09-01 | Add fixture tests for change detection |
| Production operation | Blocked | the configured CGV endpoint still returns HTTP 404 and change detection lacks current-contract fixtures | Satisfy the remaining project brief recovery criteria |

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

## Docker validation record

On 2026-09-03:

- Docker engine: 29.7.2; the earlier stale runtime-socket condition was no longer present
- Image: `cgv-open-push:test`, ID `sha256:9bc0586147c9801da1a948e49920110b65039d6cfc38ce73b5f028c80c0e10c6`,
  size 52,989,598 bytes
- Image validation: nine Python files compiled in memory and imported; `/app/.env` and
  `/app/data/kakao-token.json` were absent
- Status smoke: read-only root, 0.5 CPU, 128 MiB, PID limit 16, localhost binding; `/` returned 200
  and empty-log `/healthz` returned the expected 503
- Failure smoke: read-only root, 1 CPU, 256 MiB, PID limit 32, localhost binding; 11 processes and
  zero container restarts remained stable while nine workers made exactly two failed attempts each
- Full-smoke status: `/` and `/healthz` returned 200; memory was about 97.45 MiB and CPU about 0.02%
- Token smoke: ignored host token data mounted at `/data`; expired access token refreshed and persisted
  successfully without sending a Kakao message
- All temporary test containers were stopped and removed; the rebuilt image remains locally available
