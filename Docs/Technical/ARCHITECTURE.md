# Technical architecture

> Status: Active
>
> Owner: Engineering
>
> Last verified: 2026-09-03
>
> Verified against: `v1/*.py`, `v1/requirements.txt`, current CGV page assets, live probes, and limited Docker output

## Repository boundary

The tracked application lives under `v1/`. The directory name is historical; its active screen
polling implementation follows ADR-0002's renewed CGV JSON booking contract and ADR-0003's isolated
site/date retry scheduler.

## Runtime components

| Component | Source | Current responsibility |
|---|---|---|
| Coordinator and Kakao sender | `v1/cgv_open_push_main.py` | Configure logging, start the status and schedule processes, consume alerts, and deliver them through Kakao |
| Kakao notifier and token store | `v1/cgv_open_push_kakao.py` | Validate Kakao configuration, refresh and persist OAuth tokens, and call the self-message API |
| Kakao OAuth helper | `v1/cgv_open_push_kakao_auth.py` | Complete the one-time local authorization-code flow and save the initial token set |
| CGV/target configuration | `v1/cgv_open_push_global_variable.py` | Hold the public BFF URL, polling limits, public site catalog, and selectable target names |
| CGV contract helper | `v1/cgv_open_push_function.py` | Send Chrome-compatible bounded GET requests and validate the JSON envelope and schedule identities |
| Schedule watcher | `v1/cgv_open_push_screen.py` | Schedule normal rounds and per-site/date retries, preserve successful snapshots, and enqueue each theater's openings independently |
| Movie compatibility wrapper | `v1/cgv_open_push_movie.py` | Reuse the schedule watcher for a future movie-name target; no movie target is currently configured |
| Status page | `v1/cgv_open_push_status.py` | Serve recent file-log content and a basic freshness indicator on port 5000 |

## Current process and data flow

```text
main Python process
  ├─ Flask status-server process
  ├─ one CGV schedule-worker process
  └─ blocking queue consumer and Kakao notifier

schedule worker
  → sequential GET per unique site and date
  → same-origin /api/v1/booking/searchMovScnInfo BFF
  → validate statusCode=0 and data[] schedule identities
  → retain only requested site/date, exclude cntlYn=Y, and filter IMAX text fields
  → compare (siteNo, scnYmd, scnsNo, scnSseq, prodNo) sets
  → multiprocessing.Queue([target_name, summarized opening message])
  → Kakao "나에게 보내기" REST endpoint
```

The default targets are Yongsan (`0013`), Wangsimni (`0074`), and Apgujeong (`0040`) IMAX, in that
order. The worker scans today plus 13 days, shares each site/date response between that site's
filters, and starts normal rounds at least 300 seconds apart. A healthy round makes 42 requests.
Operators can select a comma-separated subset with `CGV_TARGET_NAMES`.

`SchedulePoller` keeps snapshots and retry deadlines per site/date. It retains failed dates' last
successful data and continues the other dates and theaters. Only failed keys are retried between
normal rounds, with independent 60/120/240/480/900-second backoff. A normal round does not bypass a
pending retry deadline or make a duplicate attempt when the two timers coincide. All attempts,
including failures and retries, share a one-second gap after the previous request completed.
One in-flight request can still delay later work until its 20-second timeout; retry deadlines are
lower bounds, not a promise of immediate execution while the worker is busy.

After each theater's due dates have been attempted, its successfully refreshed dates are compared
and its messages are queued before the next theater is queried. A new identity, or an identity
previously excluded by `cntlYn=Y` that becomes bookable, produces one aggregated message per target
in that pass. A recovered date may send a later separate message for the same theater. Up to three
schedule descriptions are included before a remaining-count suffix; the Kakao formatter retains
its 200-character limit.

The first successful response of every site/date is a silent baseline, even after initial failure.
New dates entering the horizon are likewise baselined; expired dates' snapshots and retries are
removed. The scheduler revisits the horizon at least every 60 seconds while idle, without issuing
extra healthy requests. CGV responses can include a co-located CINE de CHEF site; rows for a different
site/date are filtered out rather than treated as a failed request.

## State and delivery semantics

- Previous CGV responses exist only in watcher memory; there is no durable snapshot database.
- A process restart establishes the current response as a new baseline and does not replay downtime.
- Query or contract failures remain in the same worker, with a separate retry state for each
  site/date; successful responses for other jobs do not reset that backoff.
- The coordinator uses a timed blocking queue read and retries Kakao delivery three times. Messages
  are not persisted across process or host failure.
- Kakao access and refresh tokens live in a JSON file outside the image. A refresh persists a rotated
  refresh token when Kakao returns one.

## Packaging and external boundaries

- `v1/Dockerfile` uses `v1/` as its build context and copies it into `/app`; `.dockerignore` excludes
  credentials, token data, tests, caches, and logs.
- The image uses Python 3.10, ordinary `requests` for Kakao, and pinned `curl_cffi` with the moving
  `chrome` impersonation target for CGV.
- A named or bind-mounted `/data` volume preserves `kakao-token.json` across container replacement.
- Ports 5000 and 8765 are exposed for the status page and one-time OAuth callback. Run commands bind
  both to localhost.
- CGV and Kakao are external systems; their current contracts must be reverified after relevant
  dependency, endpoint, or response changes.

## Intended refactoring boundaries

These are safe design directions, not claims about current implementation:

1. Put the CGV endpoint, target catalog, and scan horizon in a validated external configuration file.
2. Represent an alert with named fields such as target, event type, text, and observed time.
3. Add a durable outbox and delivery acknowledgement at the notification-consumer boundary.
4. Persist schedule snapshots if openings during host downtime must be replayed.
5. Replace text keyword filters with verified stable format codes when CGV documents them.

A refactor that changes the process model, persistence layer, request budget, or notification contract
should update or supersede the relevant ADR.
