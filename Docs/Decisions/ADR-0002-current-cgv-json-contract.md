# ADR-0002: Use the renewed CGV JSON booking contract

- Status: Accepted
- Date: 2026-09-03
- Owners/approvers: Project owner
- Related tasks/context: [`../Work/Archive/TASK-0002-repair-cgv-contract.md`](../Work/Archive/TASK-0002-repair-cgv-contract.md), [`../Technical/ARCHITECTURE.md`](../Technical/ARCHITECTURE.md)
- Supersedes/superseded by: Polling cadence, catalog, and snapshot granularity updated by [ADR-0003](ADR-0003-isolated-site-date-retries.md); the HTTP contract remains accepted.

## Context

The tracked watcher used the retired HTTP ASP.NET ticket endpoint, session cookies, encrypted request
values, and XML embedded in JSON. That endpoint now redirects to a static notice and returns 404. The
renewed public cinema page obtains schedules through a same-origin JSON booking BFF. A normal
`requests` client receives 403 from that BFF, while a current browser-compatible TLS client receives
the same structured data used by the public page.

## Decision drivers

- Restore schedule polling without credentials or private CGV interfaces.
- Keep request volume low and avoid duplicate calls for targets at the same theater.
- Detect a transition from booking-controlled to bookable as an opening.
- Reject contract drift explicitly instead of comparing malformed data.

## Considered options

### Continue the pre-renewal ASP.NET contract

- Benefits: minimal source changes.
- Costs and risks: the endpoint is retired, its encrypted parameters and cookies are stale, and live
  requests return 404 HTML.

### Run a persistent headless browser

- Benefits: executes the public site exactly as a user browser does.
- Costs and risks: materially larger image, more memory and process complexity, and harder recovery
  when page layout changes.

### Use the same-origin JSON BFF with `curl_cffi`

- Benefits: small request surface, structured JSON, explicit timeouts, and browser-compatible TLS
  behavior without a persistent browser process.
- Costs and risks: the external endpoint, query schema, and accepted TLS fingerprints can change;
  the pinned client must be kept current and verified with bounded probes.

## Decision

Use `GET https://cgv.co.kr/api/v1/booking/searchMovScnInfo` with the public company, site, date, and
booking-scope query parameters. Use `curl_cffi` with its current Chrome impersonation target and a
20-second timeout. Scan the configured six unique sites sequentially, share each site/date result
across its target filters, wait one second between requests, and repeat the cycle no more often than
every five minutes by default.

Represent a bookable schedule by the tuple `(siteNo, scnYmd, scnsNo, scnSseq, prodNo)`. Exclude
records whose `cntlYn` is `Y`; if that flag later changes to a bookable value, the schedule enters the
snapshot and produces one target-level notification. Initial snapshots never notify.
When a new date first enters the moving 14-day horizon, its existing schedules establish a date
baseline rather than appearing as false openings; later additions on that date do notify.

## Consequences

### Positive

- The service consumes the current JSON response and no longer stores stale CGV cookies or encrypted
  request values.
- One bounded worker replaces one process per target and prevents same-theater duplicate requests.
- Fixture tests can express response validation, filters, and change detection directly.

### Negative and risks

- A default 14-day scan makes up to 84 sequential requests across six sites per cycle.
- State remains in memory, so a restart establishes a fresh baseline and cannot replay openings that
  occurred during downtime.
- Future CGV security or contract changes may require a new client version or integration approach.

## Validation and revisit conditions

Accepted after the current page code and site list were inspected, normal HTTP returned 403,
`curl_cffi` returned HTTP 200 JSON, a final-image live probe parsed 126 schedules and six IMAX
schedules for Yongsan, an empty date returned an empty list, 15 focused tests passed, and a
resource-limited no-message container remained at three processes with healthy status output.

Revisit if CGV stops accepting the pinned client, the request budget needs to be reduced, a persistent
browser becomes necessary, or monitoring expands beyond the current 14-day target model.
