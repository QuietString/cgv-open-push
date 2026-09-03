# TASK-0002: Repair the current CGV schedule contract

- Status: Done
- Owner: Codex
- Last updated: 2026-09-03 01:27 KST
- Scope: `v1` CGV request/configuration, schedule parsing and change detection tests, runtime documentation
- Related context: [`../../Project/PROJECT_BRIEF.md`](../../Project/PROJECT_BRIEF.md), [`../../Technical/ARCHITECTURE.md`](../../Technical/ARCHITECTURE.md), [`../../Technical/BUILD_TEST_RUN.md`](../../Technical/BUILD_TEST_RUN.md), [`../../Status/KNOWN_ISSUES.md`](../../Status/KNOWN_ISSUES.md)

## Goal

Replace the retired pre-renewal CGV request contract with the current public schedule source so the
configured premium-screen watchers can establish a real baseline and detect newly opened schedules.

## Acceptance criteria

- [x] A bounded live request returns structured schedule data for a configured theater and date.
- [x] The implementation rejects malformed or unexpected responses with actionable errors.
- [x] Current-response fixtures prove parsing and exactly-one added-schedule notification behavior.
- [x] The Docker image builds and a resource-limited no-message smoke remains bounded through two polls.
- [x] Architecture, runbook, status, and known-issue records match the verified implementation.

## Current verified state

- The renewed implementation uses the public page's same-origin
  `/api/v1/booking/searchMovScnInfo` JSON BFF and validates each schedule identity.
- A browser-compatible TLS client is required: normal HTTP returned 403 while final-image
  `curl_cffi` returned 200 JSON.
- The nine filters share requests across six sites and scan a 14-day horizon sequentially with a
  one-second gap by default.
- Initial and newly entering date horizons establish baselines; later new or newly bookable schedules
  enqueue one aggregated message per target.

## Decisions made

- Keep live diagnostics bounded to one request at a time with explicit timeouts.
- Do not run normal Kakao delivery while discovering or testing the CGV contract.
- Adopt ADR-0002 for the JSON BFF, pinned `curl_cffi`, identity snapshot, and request-budget model.

## Files changed

- `v1/cgv_open_push_global_variable.py` — current endpoint, public site catalog, target filters, and runtime polling overrides
- `v1/cgv_open_push_function.py` — browser-compatible request and current JSON contract validation
- `v1/cgv_open_push_screen.py` — shared site/date scanner and identity-based opening detection
- `v1/cgv_open_push_main.py`, `v1/cgv_open_push_movie.py` — single schedule-worker process model and future movie compatibility
- `v1/requirements.txt`, `v1/.env.example` — pinned client and documented polling controls
- `v1/tests/` — current-response fixture and 15 contract, change, Kakao, and retry tests
- `AGENTS.md`, `README.md`, `Docs/` — architecture, decision, status, runbook, and task records

## Validation evidence

- Command/tool: first-party page inspection and bounded normal/TLS-compatible HTTP probes
- Result and timestamp: current URL/query mapping confirmed; normal HTTP 403, compatible client 200 JSON at 2026-09-03
- Command/tool: final image unit suite and live contract probe
- Result and timestamp: 15 tests passed; 126 Yongsan schedules and six IMAX schedules parsed at 2026-09-03
- Command/tool: final resource-limited no-message smoke
- Result and timestamp: three processes, zero restarts, `/` and `/healthz` 200, four stable 15-second polls
- Remaining uncertainty: the full nine-target default and live Kakao sender have not been exercised together

## Blockers and risks

The external endpoint and accepted TLS fingerprints remain mutable. Re-run the bounded probe and
upgrade or revisit ADR-0002 if CGV changes either behavior.

## Exact next steps

1. With owner approval for the startup message, run the chosen production target set in the foreground.
