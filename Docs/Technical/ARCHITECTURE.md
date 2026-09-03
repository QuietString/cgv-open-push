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
polling implementation now follows the renewed CGV JSON booking contract described by ADR-0002.

## Runtime components

| Component | Source | Current responsibility |
|---|---|---|
| Coordinator and Kakao sender | `v1/cgv_open_push_main.py` | Configure logging, start the status and schedule processes, consume alerts, and deliver them through Kakao |
| Kakao notifier and token store | `v1/cgv_open_push_kakao.py` | Validate Kakao configuration, refresh and persist OAuth tokens, and call the self-message API |
| Kakao OAuth helper | `v1/cgv_open_push_kakao_auth.py` | Complete the one-time local authorization-code flow and save the initial token set |
| CGV/target configuration | `v1/cgv_open_push_global_variable.py` | Hold the public BFF URL, polling limits, public site catalog, and selectable target names |
| CGV contract helper | `v1/cgv_open_push_function.py` | Send Chrome-compatible bounded GET requests and validate the JSON envelope and schedule identities |
| Schedule watcher | `v1/cgv_open_push_screen.py` | Scan site/date pairs, filter premium screens, compare in-memory identity snapshots, and enqueue openings |
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
  → exclude cntlYn=Y and filter IMAX / 4DX / SCREENX text fields
  → compare (siteNo, scnYmd, scnsNo, scnSseq, prodNo) sets
  → multiprocessing.Queue([target_name, summarized opening message])
  → Kakao "나에게 보내기" REST endpoint
```

The default target catalog contains nine filters across six unique sites. The worker scans today plus
13 days, sleeps one second between requests, shares one site/date response among targets for that site,
and starts the next cycle no sooner than 300 seconds after the previous cycle began. Operators can
select a comma-separated subset with `CGV_TARGET_NAMES`.

The initial snapshot does not notify. A new identity, or an identity previously excluded by
`cntlYn=Y` that becomes bookable, produces one aggregated notification per target per cycle. Up to
three schedule descriptions are included before a remaining-count suffix; the Kakao formatter still
enforces its 200-character limit. Existing schedules on the first scan of a date newly entering the
moving horizon are treated as that date's baseline, preventing a horizon-boundary false alert.

## State and delivery semantics

- Previous CGV responses exist only in watcher memory; there is no durable snapshot database.
- A process restart establishes the current response as a new baseline and does not replay downtime.
- Query or contract failures remain in the same worker and retry after 60 seconds, doubling to a
  900-second maximum.
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
