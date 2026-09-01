# TASK-0001: Replace Discord delivery with Kakao self-message

- Status: Active
- Owner: Codex
- Last updated: 2026-09-01 22:46 KST
- Scope: Kakao OAuth/token storage, notification delivery, worker safety, Docker setup, tests, and related documentation
- Related context: [`../../Project/PROJECT_BRIEF.md`](../../Project/PROJECT_BRIEF.md), [`../../Technical/ARCHITECTURE.md`](../../Technical/ARCHITECTURE.md), [`../../Status/KNOWN_ISSUES.md`](../../Status/KNOWN_ISSUES.md), [`../../Decisions/ADR-0001-kakao-self-message.md`](../../Decisions/ADR-0001-kakao-self-message.md)

## Goal

Replace the tracked Discord-only sender with Kakao's official "send to me" REST API, keep OAuth
tokens safely outside Git, and prove delivery with one explicit test message to the owner's own chat.

## Acceptance criteria

- [x] Kakao login and `talk_message` consent are configured for app `1564042`.
- [x] A one-time OAuth helper stores access/refresh tokens in an ignored, mounted data path.
- [x] Expiring access tokens refresh automatically and rotated refresh tokens are persisted.
- [x] The queue consumer sends target-labelled alerts through the Kakao self-message endpoint.
- [x] Worker failures remain bounded and cannot execute the full application recursively.
- [x] Unit tests cover token refresh/persistence and message payload/error handling.
- [x] One owner-approved test message reaches the owner's Kakao "나와의 채팅방".
- [x] Documentation and context validation are current.
- [ ] The changed Docker image builds and a resource-limited failure smoke test remains bounded.

## Current verified state

- App `1564042`, "CGV IMAX 예매 오픈 알리미", exists and the owner is signed in.
- Kakao Login is ON; `talk_message` is optional consent with the alert-delivery purpose recorded.
- Redirect URI `http://localhost:8765/oauth/kakao/callback` and product link domain
  `https://github.com` are registered.
- The tracked sender is Kakao-only; the Discord dependency and lifecycle were removed.
- Host unit suite: nine tests passed. Local status smoke: `/` returned 200 and `/healthz` correctly
  returned 503 with `{"status":"stale"}` when no runtime log existed.
- OAuth tokens are stored in ignored `v1/data/kakao-token.json`; Kakao's consent lookup reports
  `talk_message` with `using=true` and `agreed=true`.
- After one rejected attempt exposed missing consent, Kakao accepted the owner-approved test message,
  the isolated sender exited 0, and the owner confirmed the exact message arrived in `나와의 채팅방`.
- Live CGV polling remains blocked by HTTP 404 independently of notification delivery.
- The recursive watcher restart path was removed and failure injection proved 60/120/240-second
  same-worker retry delays.

## Decisions made

- Use the official Kakao REST API self-message endpoint; see ADR-0001.
- Keep initial OAuth separate from the long-running service.
- Persist rotated tokens in a Docker-mounted JSON file excluded from Git.

## Files changed

- `v1/cgv_open_push_kakao.py` — Kakao configuration, token store/refresh, and notifier
- `v1/cgv_open_push_kakao_auth.py` — one-time localhost OAuth helper
- `v1/cgv_open_push_kakao_send_test.py` — isolated owner-approved test sender
- `v1/cgv_open_push_main.py`, movie/screen workers, shared helpers, and status server — notifier swap,
  bounded queue/retry behavior, response validation, process safety, and health endpoint
- `v1/Dockerfile`, `.dockerignore`, `.env.example`, `.gitignore`, and requirements — safe packaging,
  secret exclusions, mounted state, and dependency update
- `v1/tests/` — nine focused CGV contract, Kakao, and worker-retry tests
- project brief, architecture, build/run, status, issues, README, ADR, and task indexes — durable context

## Validation evidence

- Command/tool: Kakao Developers console configuration and verification
- Result and timestamp: login ON, `talk_message` optional, redirect and product link saved, 2026-09-01 KST
- Command/tool: `..\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- Result and timestamp: nine tests passed, 2026-09-01 22:44 KST
- Command/tool: host Flask smoke on `127.0.0.1:5000`
- Result and timestamp: `/` 200; empty-log `/healthz` 503 stale, 2026-09-01 22:23 KST
- Command/tool: Kakao `/v2/user/scopes` and isolated `cgv_open_push_kakao_send_test.py`
- Result and timestamp: `talk_message` agreed; Kakao returned `result_code: 0`, 2026-09-01 22:43 KST
- Remaining uncertainty: Docker rebuild and container smoke testing are incomplete.

## Blockers and risks

- Docker Desktop 4.88.1 exits because it cannot remove the exact stale runtime socket
  `C:\Users\quietstring\AppData\Local\Docker\run\sailor-ingest.sock`; workspace policy prevented
  Codex from deleting that external file.
- CGV polling cannot be end-to-end tested until ISSUE-001 is resolved.

## Exact next steps

1. Remove the exact stale Docker runtime socket after Docker Desktop is fully stopped, restart Docker,
   build the image, and run the resource-limited tests.
2. Repair the current CGV request contract under ISSUE-001 before claiming end-to-end operation.
