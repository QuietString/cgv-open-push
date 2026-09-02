# Technical architecture

> Status: Active
>
> Owner: Engineering
>
> Last verified: 2026-09-03
>
> Verified against: `v1/*.py`, `v1/requirements.txt`, and `v1/Dockerfile`

## Repository boundary

The repository currently contains documentation assets at the root and one application version under
`v1/`. Git history identifies `v1` as the pre-CGV-renewal implementation. No post-renewal application
source is tracked at this baseline.

## Runtime components

| Component | Source | Current responsibility |
|---|---|---|
| Coordinator and Kakao sender | `v1/cgv_open_push_main.py` | Configure logging, create the shared queue, start child processes, and deliver queued messages through the notifier |
| Kakao notifier and token store | `v1/cgv_open_push_kakao.py` | Validate Kakao configuration, refresh and persist OAuth tokens, and call the self-message API |
| Kakao OAuth helper | `v1/cgv_open_push_kakao_auth.py` | Complete the one-time local authorization-code flow and save the initial token set |
| Target configuration | `v1/cgv_open_push_global_variable.py` | Hold CGV request metadata and target lists |
| Shared CGV/XML helpers | `v1/cgv_open_push_function.py` | Send CGV requests, decode JSON-wrapped XML, extract fields, remove volatile tags, and launch the status process |
| Movie watcher | `v1/cgv_open_push_movie.py` | Compare the `PlayDays` fragment for one configured movie target |
| Screen watcher | `v1/cgv_open_push_screen.py` | Compare sanitized schedule XML for one theater/screen target |
| Status page | `v1/cgv_open_push_status.py` | Serve recent file-log content and a basic freshness indicator on port 5000 |

## Current process and data flow

```text
main Python process
  ├─ one Flask status-server process
  ├─ one process per configured movie target
  ├─ one process per configured screen target
  └─ blocking queue consumer and Kakao notifier

watcher process
  → HTTP POST to configured CGV endpoint
  → JSON decode
  → extract embedded XML
  → compare previous in-memory snapshot with new snapshot
  → multiprocessing.Queue([target_name, message])
  → target-labelled Kakao text template
  → Kakao "나에게 보내기" REST endpoint
```

At the current baseline, all movie targets are commented out and nine screen targets are configured.
Each watcher establishes an initial in-memory baseline and then polls every 300 seconds. Request or
parse failures retry in the same worker after 60 seconds, doubling up to a 900-second ceiling. Target
process starts are staggered by one second.

## State and delivery semantics

- Previous CGV responses exist only in watcher memory; there is no durable snapshot database.
- A process restart establishes the current response as a new baseline and does not replay downtime.
- Watchers enqueue two positional values: target name and plain alert text.
- The coordinator uses a timed blocking queue read and retries delivery three times with increasing
  delay. Messages are not persisted across process or host failure.
- The access and refresh tokens live in a JSON file outside the image. A refresh persists a rotated
  refresh token when Kakao returns one.
- Kakao REST key, Client Secret, redirect URI, token path, and product link come from environment
  variables. CGV request metadata remains tracked in the target module.

## Packaging and external boundaries

- `v1/Dockerfile` expects `v1/` itself to be the Docker build context and copies that context into
  `/app`; `.dockerignore` excludes credentials, local token data, tests, caches, and logs.
- The image uses `python:3.10-slim` and installs three pinned top-level packages.
- A named or bind-mounted `/data` volume preserves `kakao-token.json` across container replacement.
- Ports 5000 and 8765 are exposed for the status page and one-time OAuth callback respectively. Run
  commands bind both to localhost.
- CGV and Kakao are external systems; their current contracts must be verified independently.

## Intended refactoring boundaries

These are safe design directions, not claims about current implementation:

1. Separate polling/change detection from notification delivery behind a small notifier interface.
2. Represent an alert with named fields such as target, event type, text, and observed time.
3. Put retry/backoff and delivery acknowledgement at the notification-consumer boundary.
4. Supervise bounded watcher retries without executing the entire application from a child process.
5. Load endpoints, targets, channel destinations, intervals, and secrets from validated configuration.
6. Add fixture-driven tests for response parsing and change detection before live polling tests.

A refactor that establishes a new process model, persistence layer, or multi-messenger delivery contract
should be captured in an ADR.
