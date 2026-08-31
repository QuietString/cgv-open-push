# Technical architecture

> Status: Active
>
> Owner: Engineering
>
> Last verified: 2026-09-01
>
> Verified against: `v1/*.py`, `v1/requirements.txt`, and `v1/Dockerfile`

## Repository boundary

The repository currently contains documentation assets at the root and one application version under
`v1/`. Git history identifies `v1` as the pre-CGV-renewal implementation. No post-renewal application
source is tracked at this baseline.

## Runtime components

| Component | Source | Current responsibility |
|---|---|---|
| Coordinator and Discord sender | `v1/cgv_open_push_main.py` | Configure logging, create the shared queue, start child processes, and deliver queued messages to Discord |
| Target configuration | `v1/cgv_open_push_global_variable.py` | Hold runtime token lookup, Discord channel mapping, CGV request metadata, and target lists |
| Shared CGV/XML helpers | `v1/cgv_open_push_function.py` | Send CGV requests, decode JSON-wrapped XML, extract fields, remove volatile tags, and launch the status process |
| Movie watcher | `v1/cgv_open_push_movie.py` | Compare the `PlayDays` fragment for one configured movie target |
| Screen watcher | `v1/cgv_open_push_screen.py` | Compare sanitized schedule XML for one theater/screen target |
| Status page | `v1/cgv_open_push_status.py` | Serve recent file-log content and a basic freshness indicator on port 5000 |

## Current process and data flow

```text
main Python process
  ├─ status supervisor process
  │    └─ Flask status subprocess (replaced hourly)
  ├─ one process per configured movie target
  ├─ one process per configured screen target
  └─ Discord asyncio client and queue consumer

watcher process
  → HTTP POST to configured CGV endpoint
  → JSON decode
  → extract embedded XML
  → compare previous in-memory snapshot with new snapshot
  → multiprocessing.Queue([target_name, message])
  → Discord target-to-channel lookup
  → channel.send(message)
```

At the current baseline, all movie targets are commented out and nine screen targets are configured.
Each watcher performs an initial request, waits approximately five seconds, requests again, and then
waits another 295 seconds per loop. Target process starts are staggered by one second.

## State and delivery semantics

- Previous CGV responses exist only in watcher memory; there is no durable snapshot database.
- A process restart establishes the current response as a new baseline and does not replay downtime.
- Watchers enqueue two positional values: target name and Discord-formatted text.
- The queue is process-safe, but the sender checks `Queue.empty()` before a non-blocking read; that
  observation is not a reliable synchronization contract across processes.
- A message is removed before Discord delivery and is not durably retried after a send failure.
- Target configuration, transport configuration, HTTP metadata, and secrets are coupled in one module.

## Packaging and external boundaries

- `v1/Dockerfile` expects `v1/` itself to be the Docker build context because it uses `COPY * .`.
- The image currently uses the mutable `python:3.10` tag and installs four pinned top-level packages.
- `DISCORD_BOT_TOKEN` is read during module import and must exist in the environment.
- Port 5000 is exposed by the image. The Flask development server is the tracked status server.
- CGV and Discord are external systems; their current contracts must be verified independently.

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
