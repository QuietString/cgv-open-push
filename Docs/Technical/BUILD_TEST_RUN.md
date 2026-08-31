# Build, test, and run

> Status: Active
>
> Owner: Engineering
>
> Last verified: 2026-09-01
>
> Verified against: Docker Desktop with WSL 2, `v1/Dockerfile`, and the 2026-08-31 smoke test

## Prerequisites

- Windows with WSL 2 and Docker Desktop using Linux containers, or an equivalent Linux Docker host
- PowerShell 7 for the repository context validator
- Network access for the base image, Python packages, CGV diagnostics, and messenger delivery
- A messenger credential supplied through an ignored `.env` file or another secret store

Never add a real token or webhook URL to the Dockerfile, source, documentation, command history, or Git.

## Validate Python syntax without importing runtime configuration

From the repository root:

```powershell
$PythonFiles = Get-ChildItem .\v1 -Filter '*.py'
python -c "import ast,pathlib,sys; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in sys.argv[1:]]; print(f'AST parse OK: {len(sys.argv)-1} files')" $PythonFiles.FullName
```

This catches syntax errors but does not prove imports, external APIs, polling, or notification delivery.

## Build the legacy image

Use `v1/` as the build context:

```powershell
docker build -t cgv-open-push:test .\v1
```

The 2026-08-31 baseline build succeeded. Docker reported a `SecretsUsedInArgOrEnv` warning because the
Dockerfile declares the token variable with an empty `ENV` instruction; no real token was embedded.

## Bounded CGV endpoint probe

Run at most a single request while diagnosing the current contract. This probe starts no watchers:

```powershell
docker run --rm --entrypoint python cgv-open-push:test -c "import requests; import cgv_open_push_global_variable as g; r=requests.post(g.screen_url,cookies=g.screen_cookies,headers=g.screen_headers,json=g.screen_json_data[0],timeout=15); print('STATUS=',r.status_code); print('CONTENT_TYPE=',r.headers.get('content-type')); print('BODY=',repr(r.text[:500]))"
```

Baseline result on 2026-08-31: HTTP 404, `text/html`, and an HTML error document. Update the endpoint,
request contract, and this evidence together when the result changes.

## Full-service safety gate

Do **not** start the unmodified full service while `ISSUE-002` in
[`../Status/KNOWN_ISSUES.md`](../Status/KNOWN_ISSUES.md) is open. The 2026-08-31 test created 2,136
Python processes within about 12 seconds after CGV parsing failures triggered `os.execl` recursively.

After the restart defect is fixed and tested, use explicit resource limits for the first smoke test:

```powershell
docker run --rm `
  --name cgv-open-push-test `
  --pids-limit 64 `
  --cpus 1 `
  --memory 512m `
  --env-file .env `
  -p 127.0.0.1:5000:5000 `
  cgv-open-push:test
```

Run it in the foreground for the first test. In another terminal inspect `docker logs` and the status
page, then stop with `docker stop cgv-open-push-test`. Do not add a Docker restart policy until failure
behavior and graceful shutdown have been verified.

## Minimum verification by change type

| Change | Minimum safe evidence |
|---|---|
| Documentation/context rules | `Scripts/Agent/ValidateProjectDocs.ps1` passes |
| Pure Python helper | Syntax check plus focused unit test or fixture invocation |
| CGV request/parser | Fixture tests plus one bounded live probe with timeout |
| Change detection | Before/after XML fixtures prove exactly the intended added/deleted result |
| Process supervision | Failure-injection test proves process count remains bounded |
| Messenger integration | Mocked delivery test plus one explicit test message to a test destination |
| Docker/runtime change | Image build and resource-limited foreground smoke test |

## Validate repository context

```powershell
pwsh -File Scripts/Agent/ValidateProjectDocs.ps1
git status --short
```

If a required validation cannot run, record the exact reason, affected confidence, and next command in
the active task or final handoff.
