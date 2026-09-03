# TASK-0003: Isolate IMAX polling and request retries

- Status: Done
- Owner: Codex
- Last updated: 2026-09-03 KST
- Scope: target catalog, schedule watcher, tests, polling documentation
- Related context: [Architecture](../../Technical/ARCHITECTURE.md), [ADR-0003](../../Decisions/ADR-0003-isolated-site-date-retries.md)

## Goal

Monitor only Yongsan, Wangsimni, and Apgujeong IMAX, publish each theater's alerts independently,
and retry failed site/date requests without restarting successful work.

## Acceptance criteria

- [x] Verify Apgujeong's public site number and limit the catalog to the three requested IMAX targets.
- [x] Queue separate theater notifications before querying the next theater.
- [x] Preserve successful site/date baselines, retry only failed requests with bounded backoff,
  and continue healthy requests while failures wait.
- [x] Cover initial/partial baselines, retries, recovery, independent alerts, and date rollover in tests.
- [x] Rebuild and validate a resource-limited container without real Kakao delivery; update documents.

## Current verified state

- Working tree started clean at `aa3ba88`.
- Replaced the whole-round failure behavior with `SchedulePoller` per-site/date state and deadlines.
- No `CGV_TARGET_NAMES` override exists in the ignored local environment file.
- Final Docker image `cgv-open-push:test` is
  `sha256:45d244e98d98d5086f8c8296b0ca422824585da32ea0404fca915e1856923250`.

## Decisions made

- Keep one sequential worker and the global request-spacing limit.
- Retain five-minute normal rounds and fourteen KST calendar dates.
- Separate failure state and last successful snapshots by site/date; do not treat errors as empty data.
- Accept mixed-site CGV responses and filter requested site/date rows; Apgujeong's public response
  also contains CINE de CHEF `P001`. Do not reject these valid responses wholesale.
- [ADR-0003](../../Decisions/ADR-0003-isolated-site-date-retries.md) records the accepted tradeoffs.

## Files changed

- `v1/cgv_open_push_global_variable.py`, `v1/.env.example`: three IMAX targets and retry settings.
- `v1/cgv_open_push_screen.py`: per-key state, normal/retry scheduling, theater-local notification flush.
- `v1/tests/test_screen_schedule.py`, `v1/tests/test_worker_retry.py`: catalog and scheduler regressions.
- `v1/tests/smoke_isolated_polling.py`: bounded offline real-process/queue validation.
- `README.md`, project/architecture/runbook/status/decision/work documents: current scope and evidence.

## Validation evidence

- `docker build -t cgv-open-push:test ./v1`: passed; final image size 67,210,857 bytes.
- Final image with `/tests` read-only mount, `--network none`, and
  `-m unittest discover -s /tests -v`: 29 tests passed at 2026-09-03 20:45 KST.
- In-image AST check: all nine top-level Python files parsed; `.env` and token data absent.
- Bounded public catalog GET verified `0013`, `0074`, and `0040`.
- Final-image `SchedulePoller.poll_once()` with all three targets, one date and one-second spacing:
  three requests succeeded at 20:41 KST; IMAX counts were Yongsan 2, Wangsimni 2, and Apgujeong 1.
- Offline eight-second process smoke, using the exact command in the runbook: exit 0,
  `ISOLATED_SMOKE_OK`, three Python processes, health HTTP 200, and one captured message per theater.
  Its ten fake requests comprised three normal rounds plus one failed-key retry, with no duplicates.
- All probe/smoke containers were removed automatically; no real Kakao message was sent.
- `pwsh -File Scripts/Agent/ValidateProjectDocs.ps1`: passed (20 Markdown files);
  `git diff --check`: passed. No commit or push was performed.
- Remaining uncertainty: full 14-day live polling plus real Kakao sending remains unverified together.

## Blockers and risks

- CGV's public endpoint and accepted client behavior remain mutable.
- No blocker remains for this scoped change. Full unattended deployment and its startup message
  still require owner approval; in-memory snapshots do not replay downtime.

## Exact next steps

1. On owner request, commit the changes or run the first bounded foreground deployment using the
   updated runbook. Do not send an unsolicited startup/test Kakao message.
