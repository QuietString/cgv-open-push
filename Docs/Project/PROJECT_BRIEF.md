# cgv-open-push project brief

> Status: Active
>
> Owner: Project owner
>
> Last verified: 2026-09-03
>
> Verified against: `README.md`, `v1/`, current CGV page assets, bounded live probes, and Git history

## One-sentence purpose

Periodically inspect selected CGV movie or premium-screen schedules and notify users when newly
bookable schedule data appears.

## Current verified identity

- Project name: `cgv-open-push`
- Runtime: Python 3.10 in the provided Dockerfile
- Tracked application source: current CGV JSON schedule implementation under `v1/`
- Data acquisition: bounded GET requests to CGV's same-origin booking BFF with a browser-compatible
  TLS client
- Change detection: in-memory comparison of stable schedule identity tuples
- Tracked notification implementation: KakaoTalk self-message with OAuth token refresh
- Observability: rotating log file and a Flask status page on port 5000
- License: AGPL-3.0
- Remote: `https://github.com/QuietString/cgv-open-push.git`

## Intended users and outcomes

- Users subscribe to alerts for selected theaters, movies, or premium screens.
- A detected addition should produce one understandable notification at the configured destination.
- Operators should be able to deploy the service continuously, diagnose failures, and restart it
  without duplicate workers or notification loss.

## Current scope

- CGV schedule polling and opening-change detection
- Theater/screen and optional movie-specific targets
- Personal KakaoTalk "나와의 채팅방" notification delivery
- Docker packaging and a lightweight status page
- Future messenger integrations such as Slack are permitted when their configuration and delivery
  semantics are documented and verified.

## Constraints and non-goals

- CGV is an external system with no tracked integration contract; endpoints and payloads may change.
- This project is not affiliated with CGV and must avoid abusive request volume.
- Secrets must be injected at runtime and never stored in Git.
- A successful container start or HTTP 200 from the status page does not prove polling or notification
  delivery works.
- Automatic ticket purchasing, seat selection, or reservation is outside the verified project scope.
- Do not assume the public service described in `README.md` is powered by the tracked `v1` source.

## Near-term recovery criteria

The tracked service can be called operational only after all of the following are verified:

1. a bounded request to the current CGV source returns the expected structured schedule data;
2. worker failures retry without launching duplicate service trees or causing a request storm;
3. an added schedule fixture triggers exactly one queued notification;
4. the selected messenger accepts a test message with secrets supplied outside Git;
5. a resource-limited container remains healthy through at least two polling intervals.
