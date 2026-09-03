# Implementation status

> Status: Active
>
> Owner: Project team
>
> Last verified: 2026-09-03
>
> Verified against: current Git tree, public CGV catalog and three-site live probes, 29 tests, the 2026-09-03 Docker build, and offline isolated-retry smoke output

## Status matrix

| Area | State | Evidence | Next step |
|---|---|---|---|
| Agent context system | Verified | root `AGENTS.md`, indexed context files, templates, and validator; validator passed on 2026-09-01 | Re-run after context-policy or document-structure changes |
| Python syntax | Verified | all nine image `v1/*.py` files passed AST parsing on 2026-09-03 | Re-run after Python changes |
| Docker toolchain | Verified | rebuilt image `sha256:45d244e...` passed syntax/secret-exclusion checks, tests, three-site live probes, and offline runtime smoke | Rebuild after source, dependency, or Dockerfile changes |
| CGV polling | Verified | public catalog confirms the three selected sites; final-image current-date requests succeeded for all three, including mixed-site filtering | Re-probe after endpoint, query, TLS-client, or schema changes |
| Change detection | Verified | fixtures and scheduler tests cover separate theater alerts, partial-date baselines, booking-control transition, recovery without duplicates, and horizon rollover | Expand fixtures if stable format codes replace keyword filters |
| Worker supervision | Verified | offline final-image smoke held main/status/worker processes, emitted one captured message per theater, and retried only the failed date between normal rounds | Retain limits and re-test after process-model or retry changes |
| Kakao self-message | Verified | owner-confirmed test delivery plus a 2026-09-03 container token refresh through the mounted `/data` path | Monitor refresh-token expiry and reauthorize when required |
| Discord delivery | Deprecated | Discord dependency, token lookup, channel routing, and sender were removed in favor of ADR-0001 | None unless multi-transport support is requested |
| Slack delivery | Planned | feasibility assessed; no Slack source or configuration is tracked | Define notifier boundary and select webhook or Web API contract |
| Status page | Partial | limited containers returned `/` 200, empty-log `/healthz` 503, and active-log `/healthz` 200 through `127.0.0.1`; log text is escaped | Add authentication before any non-local exposure |
| Automated tests | Verified | 29 focused tests plus a separate offline process smoke passed with the rebuilt image | Add coverage with each material behavior change |
| Production operation | Partial | each of the three targets passed a one-date live probe and isolated retry/delivery was validated offline; the full 14-day default horizon plus real Kakao delivery has not been run together | Run the first full deployment in the foreground with owner approval for its startup message |

`Implemented` means code or documentation exists but the required current behavior has not been proven.
Use `Verified` only when reproducible evidence has passed after the relevant change.

## Current tracked footprint

- Application versions: renewed CGV contract under historical directory name `v1`
- Python source files: 9
- Active movie-specific targets: 0
- Active screen targets: 3 (Yongsan, Wangsimni, Apgujeong IMAX)
- Unique CGV sites per default cycle: 3
- Default schedule horizon: 14 days with one-second sequential request spacing
- Notification transports: Kakao self-message only
- Durable state store: mounted Kakao OAuth token JSON only; CGV snapshots remain in memory
- Normal request budget: 42 per five-minute round; only failed site/date requests receive extra retries
- Automated tests: 29 focused unit tests in 4 files, one minimized JSON fixture, and one offline process smoke
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

## Kakao migration Docker validation record

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

## Current CGV contract validation record

On 2026-09-03:

- First-party page code maps the backend schedule operation to the same-origin
  `/api/v1/booking/searchMovScnInfo` BFF and supplies `coCd`, `siteNo`, `scnYmd`, and
  `rtctlScopCd=08`
- A normal PowerShell HTTP request returned 403; pinned `curl_cffi` with `impersonate="chrome"`
  returned HTTP 200 and `application/json`
- The public theater-list response verified site numbers for Yongsan, Yeouido, Centum City, Seomyeon,
  Yeongdeungpo Times Square, and Wangsimni
- A current Yongsan request returned 126 schedules; the target filter found six IMAX schedules
- A disabled Yongsan date returned `statusCode=0` with an empty `data` list
- Final image: `sha256:a7d6f98f3743945648f8482362a0e91682198b9831e399de0f7c4cd9dda3bf43`,
  67,210,080 bytes
- Final-image unit suite: 15 tests passed
- No-message runtime smoke: read-only root, 0.75 CPU, 256 MiB, PID limit 16, localhost status binding;
  three processes, zero restarts, `/` 200, and `/healthz` 200
- The final limited run completed four successful 15-second Yongsan IMAX polls with a stable count of
  six and no queued schedule change
- Temporary probe and smoke containers were removed; the rebuilt image remains locally available

## Three-IMAX isolated-retry validation record

On 2026-09-03, after the owner's target and retry changes:

- Public catalog: Yongsan `0013`, Wangsimni `0074`, Apgujeong `0040` verified with one bounded request.
- A draft strict site-ID check rejected legitimate co-located CINE de CHEF rows. A bounded shape
  probe confirmed Apgujeong's response contains `0040` and `P001`; the final watcher filters site/date
  rows without rejecting the valid response.
- Final image: `sha256:45d244e98d98d5086f8c8296b0ca422824585da32ea0404fca915e1856923250`,
  67,210,857 bytes; nine Python AST checks passed and image credentials were absent.
- Final-image current-date probe at 20:41 KST: three requests succeeded, with matching IMAX counts
  Yongsan 2, Wangsimni 2, and Apgujeong 1. No schedule messages were sent.
- 29 unit tests passed, including selective retries, independent backoff, no early normal-round
  retry, no duplicate retry at coincident deadlines, global spacing, mixed-site data, and date rollover.
- Eight-second offline runtime smoke: network disabled, read-only root, 0.75 CPU, 256 MiB, PID limit
  16, no published ports or token mount. Three Python processes stayed alive; local `/healthz` was 200.
- Captured alert order was Wangsimni, Apgujeong, then recovered Yongsan, once each. Request trace
  contained three normal rounds plus only one extra Yongsan retry (10 requests total), all mocked.
- Temporary containers exited and were removed. No real Kakao message or unattended deployment
  was started for this change.
