# ADR-0003: Isolate site/date retries and theater notifications

- Status: Accepted
- Date: 2026-09-03
- Owners/approvers: Project owner (requested target reduction and isolated retry behavior)
- Related tasks/context: [TASK-0003](../Work/Archive/TASK-0003-isolate-imax-polling.md), [Architecture](../Technical/ARCHITECTURE.md)
- Supersedes/superseded by: Supersedes the polling cadence, catalog, and snapshot granularity portions of [ADR-0002](ADR-0002-current-cgv-json-contract.md); its HTTP contract remains accepted.

## Context

The owner requested only Yongsan, Wangsimni, and Apgujeong IMAX, separate theater notifications,
and retries limited to failed requests. The previous whole-round snapshot could not publish any
theater's changes if one site/date request failed.

## Decision drivers

- Keep healthy requests and notifications progressing during partial CGV failures.
- Avoid replaying successful requests solely because another request failed.
- Preserve baselines through failures without duplicate or false opening notifications.
- Keep one sequential worker and a global request-spacing limit.

## Considered options

### Retry the whole round or sleep inside the failed request

- Benefits: less scheduler state.
- Costs and risks: repeats successful work or blocks healthy theaters during backoff.

### Add a worker per theater or request

- Benefits: parallel progress during slow network calls.
- Costs and risks: more processes and harder global request budgeting.

### Keep one worker with independent request deadlines

- Benefits: isolated recovery, shared response handling, and bounded sequential request traffic.
- Costs and risks: per-request baseline/deadline state; a single in-flight request can still take 20 seconds.

## Decision

- Default catalog: `YONGSAN-IMAX` (`0013`), `WANGSIMNI-IMAX` (`0074`), and
  `APGUJEONG-IMAX` (`0040`); all other default targets are removed.
- Normal rounds start at least 300 seconds apart and cover fourteen KST dates: 42 requests when
  all jobs are healthy. Keep a one-second global gap after request completion.
- Store last successful snapshots and retry deadlines by `(siteNo, scnYmd)`.
- On failure, retain that job's snapshot, continue the remaining jobs, and schedule only the failed
  job after 60, 120, 240, 480, then at most 900 seconds. Successful unrelated jobs do not reset it.
- A normal round skips failed jobs whose retry deadline is not due. A due retry and normal round
  share one attempt for the same key. Successful recovery returns the key to normal polling.
- Between normal rounds, wake for due retries; do not query healthy jobs during these retry passes.
  The global spacing rule applies across theaters and pass boundaries. Timers are lower bounds:
  a busy sequential worker can service a deadline late.
- After processing each theater's due dates, queue a separate message per target containing only
  additions on successfully refreshed dates. Never wait for another theater or a failed date's retry.
  A later recovered date can produce a separate message for the same theater.
- The first successful response for each site/date is a silent baseline, including first success
  after initial failure and dates newly entering the horizon. Drop expired snapshots and retries.
- CGV may return co-located CINE de CHEF schedules under another site code. Filter by the requested
  site/date before target matching rather than rejecting the whole response.

## Consequences

### Positive

- Healthy theaters notify even while another request is failing.
- Request volume drops from 84 to 42 per healthy normal round; failure retries add only failed keys.
- Recovery compares against the last success and does not mistake failed data for an empty schedule.

### Negative and risks

- Widespread CGV failure creates per-key retries; aggregate traffic is spaced but not subject to an
  additional daily quota or site-wide circuit breaker.
- A slow in-flight request still delays subsequent work until its timeout; no parallelism was added.
- Snapshots and notifications remain non-durable; a restart does not replay downtime.

## Validation and revisit conditions

Validated with 29 unit tests, public-site catalog verification, one current-date request per selected
site, and an offline resource-limited runtime smoke. The smoke held three Python processes, emitted
one captured message per theater, and retried only the failed Yongsan request between normal rounds.
Revisit if more targets, persistent snapshots, broader outage controls, or parallel polling are needed.
