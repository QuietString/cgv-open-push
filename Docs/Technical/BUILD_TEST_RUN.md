# Build, test, and run

> Status: Active
>
> Owner: Engineering
>
> Last verified: 2026-09-03
>
> Verified against: Docker engine 29.7.2, `v1/Dockerfile`, and the 2026-09-03 limited container tests

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

The 2026-09-01 suite contains nine CGV contract, Kakao token/delivery, and worker-retry tests.

## Build the legacy image

Use `v1/` as the build context:

```powershell
docker build --pull -t cgv-open-push:test .\v1
```

The 2026-09-03 Kakao image build succeeded on Docker engine 29.7.2. The resulting local image ID is
`sha256:9bc0586147c9801da1a948e49920110b65039d6cfc38ce73b5f028c80c0e10c6` and its size is
52,989,598 bytes. An in-image check compiled and imported all nine Python modules and confirmed that
`.env` and `data/kakao-token.json` were absent. `.dockerignore` excludes credentials, local token
data, tests, caches, and logs from the image context.

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

## Resource-limited failure smoke without messenger delivery

The recursive `os.execl` defect is resolved. On 2026-09-03, the following test held the full process
tree at 11 processes and zero container restarts across two failed requests from each of nine workers.
It substitutes `KakaoNotifier.send` in memory so no startup or alert message is sent, and it does not
modify the image:

```powershell
docker run -d --rm `
  --name cgv-open-push-failure-smoke `
  --pids-limit 32 `
  --cpus 1 `
  --memory 256m `
  --read-only `
  --tmpfs /tmp:rw,noexec,nosuid,size=32m `
  -w /tmp `
  -e PYTHONDONTWRITEBYTECODE=1 `
  -e PYTHONUNBUFFERED=1 `
  -e PYTHONPATH=/app `
  -e KAKAO_REST_API_KEY=00000000000000000000000000000000 `
  -e KAKAO_CLIENT_SECRET=11111111111111111111111111111111 `
  -e KAKAO_REDIRECT_URI=http://localhost:8765/oauth/kakao/callback `
  -e KAKAO_TOKEN_FILE=/tmp/not-used.json `
  -e KAKAO_MESSAGE_LINK_URL=https://github.com `
  --stop-timeout 10 `
  -p 127.0.0.1:5001:5000 `
  --entrypoint python `
  cgv-open-push:test `
  -c "import cgv_open_push_main as m; m.KakaoNotifier.send=lambda self,target_name,message:{'result_code':0}; m.main()"

Start-Sleep -Seconds 75
docker top cgv-open-push-failure-smoke -eo pid,ppid,comm
docker logs cgv-open-push-failure-smoke
docker stop --timeout 10 cgv-open-push-failure-smoke
```

Expected evidence after 75 seconds is 11 processes, no restart, and exactly 18 target error lines. The
configured legacy CGV URL currently redirects to `http://img.cgv.co.kr/System_Notice.html` and returns
404, so this test proves bounded failure behavior rather than functional polling.

## Full service

Starting the normal service sends a startup message to the authenticated Kakao chat. Obtain explicit
approval before the first normal run. Keep explicit resource limits and localhost-only status binding:

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

Run it in the foreground for the first normal test. In another terminal inspect `docker logs` and the
status page, then stop with `docker stop --timeout 10 cgv-open-push-test`. The configured CGV endpoint
still returns 404, so normal operation cannot yet detect schedule changes. Do not add a Docker restart
policy until graceful shutdown and the repaired CGV contract have been verified.

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
