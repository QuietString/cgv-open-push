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

Run the focused unit suite in an environment with `v1/requirements.txt` installed:

```powershell
Push-Location .\v1
python -m unittest discover -s tests -v
Pop-Location
```

The 2026-09-01 suite contains eight CGV contract, Kakao token/delivery, and worker-retry tests.

## Build the legacy image

Use `v1/` as the build context:

```powershell
docker build -t cgv-open-push:test .\v1
```

The 2026-08-31 baseline image built successfully. The Kakao change has not yet been rebuilt because the
local Docker Desktop backend is blocked by an inaccessible stale runtime socket. `.dockerignore`
excludes `.env`, local token data, tests, caches, and logs from the image context.

## Configure Kakao credentials

Copy `v1/.env.example` to `v1/.env`, then fill in only the REST API key and Client Secret shown in the
owner's Kakao Developers console. The tracked defaults already match app `1564042`:

```powershell
Copy-Item .\v1\.env.example .\v1\.env
```

`v1/.env` and `v1/data/` are ignored by Git. Never print their contents or include them in a patch,
commit, image, issue, or chat message.

## Complete one-time Kakao OAuth

Create the ignored local token directory and run the callback helper with localhost-only port binding.
The bind mount lets the same token file be used by host diagnostics and the eventual service container:

```powershell
$KakaoDataPath = (New-Item -ItemType Directory -Force .\v1\data).FullName
docker run --rm `
  --name cgv-open-push-kakao-auth `
  --pids-limit 32 `
  --cpus 0.5 `
  --memory 256m `
  --env-file .\v1\.env `
  -p 127.0.0.1:8765:8765 `
  -v "${KakaoDataPath}:/data" `
  cgv-open-push:test `
  cgv_open_push_kakao_auth.py
```

Open the printed authorization URL, approve the optional KakaoTalk message permission, and wait for
the helper to report that `/data/kakao-token.json` was saved. The helper verifies OAuth `state` and
accepts one callback on `http://localhost:8765/oauth/kakao/callback`.

## Send an isolated Kakao test message

This starts no CGV watchers and is safe while `ISSUE-001` remains open. Obtain the owner's explicit
approval for the exact message immediately before running it:

```powershell
$KakaoDataPath = (Resolve-Path .\v1\data).Path
docker run --rm `
  --name cgv-open-push-kakao-test `
  --pids-limit 16 `
  --cpus 0.5 `
  --memory 128m `
  --env-file .\v1\.env `
  -v "${KakaoDataPath}:/data" `
  cgv-open-push:test `
  cgv_open_push_kakao_send_test.py
```

Success requires both process exit code 0 and confirmation that the message arrived in the owner's
KakaoTalk `나와의 채팅방`.

## Bounded CGV endpoint probe

Run at most a single request while diagnosing the current contract. This probe starts no watchers:

```powershell
docker run --rm --entrypoint python cgv-open-push:test -c "import requests; import cgv_open_push_global_variable as g; r=requests.post(g.screen_url,cookies=g.screen_cookies,headers=g.screen_headers,json=g.screen_json_data[0],timeout=15); print('STATUS=',r.status_code); print('CONTENT_TYPE=',r.headers.get('content-type')); print('BODY=',repr(r.text[:500]))"
```

Baseline result on 2026-08-31: HTTP 404, `text/html`, and an HTML error document. Update the endpoint,
request contract, and this evidence together when the result changes.

## Full-service safety gate

The recursive `os.execl` defect has been removed and focused failure injection passed, but full
container proof is still pending. The 2026-08-31 baseline reached 2,136 Python processes in about 12
seconds; keep strict resource limits until a new smoke test proves bounded process and request counts.

After the restart defect is fixed and tested, use explicit resource limits for the first smoke test:

```powershell
$KakaoDataPath = (Resolve-Path .\v1\data).Path
docker run --rm `
  --name cgv-open-push-test `
  --pids-limit 64 `
  --cpus 1 `
  --memory 512m `
  --env-file .\v1\.env `
  -p 127.0.0.1:5000:5000 `
  -v "${KakaoDataPath}:/data" `
  cgv-open-push:test
```

Run it in the foreground for the first test. In another terminal inspect `docker logs` and the status
page, then stop with `docker stop cgv-open-push-test`. The configured CGV endpoint still returns 404,
so this test can prove bounded failure behavior but not functional schedule polling. Do not add a
Docker restart policy until failure behavior and graceful shutdown have been verified.

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
