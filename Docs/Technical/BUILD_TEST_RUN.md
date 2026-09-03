# Build, test, and run

> Status: Active
>
> Owner: Engineering
>
> Last verified: 2026-09-03
>
> Verified against: Docker engine 29.7.2, current CGV JSON responses, `v1/Dockerfile`, and limited container tests

## Prerequisites

- Windows with WSL 2 and Docker Desktop using Linux containers, or an equivalent Linux Docker host
- PowerShell 7 for the repository context validator
- Network access for the base image, Python packages, bounded CGV polling, and Kakao delivery
- Kakao credentials supplied through ignored `v1/.env` and token data under ignored `v1/data/`

Never add a real token, webhook URL, cookie, `.env`, or token file to source, documentation, the image,
or Git.

## Validate source and tests

From the repository root:

```powershell
$PythonFiles = Get-ChildItem .\v1 -Filter '*.py'
python -c "import ast,pathlib,sys; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in sys.argv[1:]]; print(f'AST parse OK: {len(sys.argv)-1} files')" $PythonFiles.FullName
```

Build the image first, then run tests from the host source as a read-only mount so the image's pinned
dependencies execute the suite:

```powershell
docker build --pull -t cgv-open-push:test .\v1

$SourcePath = (Resolve-Path .\v1).Path
docker run --rm `
  --name cgv-unit-tests `
  --pids-limit 32 `
  --cpus 1 `
  --memory 256m `
  --read-only `
  --tmpfs /tmp:rw,noexec,nosuid,size=32m `
  -e PYTHONDONTWRITEBYTECODE=1 `
  -v "${SourcePath}:/workspace:ro" `
  -w /workspace `
  cgv-open-push:test `
  -m unittest discover -s tests -v
```

The 2026-09-03 suite contains 15 CGV contract, schedule fixture/change, Kakao, and worker-retry tests.
The final image was `sha256:a7d6f98f3743945648f8482362a0e91682198b9831e399de0f7c4cd9dda3bf43`
and 67,210,080 bytes.

## Configure CGV polling

The default catalog contains these target names:

- `YONGSAN-IMAX`, `YONGSAN-4DX`, `YONGSAN-SCREENX`
- `YEOUIDO-4DX`
- `CENTUM-IMAX`, `SEOMYEON-IMAX`
- `YEONGDEUNGPO-IMAX`, `YEONGDEUNGPO-SCREENX`
- `WANGSIMNI-IMAX`

With an empty `CGV_TARGET_NAMES`, all nine are enabled. Use a comma-separated subset in `v1/.env`
when appropriate, for example:

```dotenv
CGV_TARGET_NAMES=YONGSAN-IMAX
CGV_LOOKAHEAD_DAYS=14
CGV_POLL_INTERVAL_SECONDS=300
CGV_REQUEST_INTERVAL_SECONDS=1
```

The defaults scan 14 dates across six unique sites: at most 84 sequential requests per cycle, with a
one-second interval and no cycle starting sooner than every five minutes. Prefer a smaller target set
or horizon when broader coverage is unnecessary. Unknown target names fail at startup.

## Configure Kakao credentials

Copy `v1/.env.example` to `v1/.env`, then fill in only the REST API key and Client Secret shown in the
owner's Kakao Developers console. The tracked defaults match app `1564042`:

```powershell
Copy-Item .\v1\.env.example .\v1\.env
```

`v1/.env` and `v1/data/` are ignored by Git. Never print their contents or include them in a patch,
commit, image, issue, or chat message.

## Complete one-time Kakao OAuth

Create the ignored token directory and run the callback helper with localhost-only port binding:

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
the helper to save `/data/kakao-token.json`. It verifies OAuth `state` and accepts one callback on the
configured localhost URI.

## Send an isolated Kakao test message

This starts no CGV watcher. Obtain the owner's explicit approval for the exact message immediately
before running it:

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

Success requires exit code 0 and owner confirmation that the message arrived in KakaoTalk
`나와의 채팅방`.

## Bounded current CGV contract probe

The current contract is a same-origin BFF used by the public cinema page. Its bot filtering rejects a
normal `requests` client, so the application uses pinned `curl_cffi` with its current Chrome target.
Run one site/date request only; this starts no watcher and sends no message:

```powershell
docker run --rm `
  --name cgv-live-contract-smoke `
  --pids-limit 16 `
  --cpus 0.5 `
  --memory 192m `
  --read-only `
  --tmpfs /tmp:rw,noexec,nosuid,size=16m `
  -e PYTHONDONTWRITEBYTECODE=1 `
  --entrypoint python `
  cgv-open-push:test `
  -c "from datetime import datetime; from cgv_open_push_function import get_request_to_cgv_api; from cgv_open_push_global_variable import CGV_API_URL,CGV_HEADERS,CGV_COMPANY_CODE; from cgv_open_push_screen import KST; day=datetime.now(KST).strftime('%Y%m%d'); params={'coCd':CGV_COMPANY_CODE,'siteNo':'0013','scnYmd':day,'scnsNo':'','scnSseq':'','rtctlScopCd':'08','custNo':''}; schedules=get_request_to_cgv_api(CGV_API_URL,CGV_HEADERS,params,'0013:'+day); print('LIVE_CONTRACT_OK date='+day+' total='+str(len(schedules)))"
```

On 2026-09-03 the final-image probe returned 126 schedules for Yongsan; the IMAX filter found six.
A separate known-empty date returned `statusCode=0` with `data=[]`.

## Resource-limited runtime smoke without messenger delivery

This command selects one site/target/date and substitutes `KakaoNotifier.send` in memory. It sends no
startup or schedule message and does not modify the image:

```powershell
docker run -d --rm `
  --name cgv-open-push-contract-smoke `
  --pids-limit 16 `
  --cpus 0.75 `
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
  -e CGV_TARGET_NAMES=YONGSAN-IMAX `
  -e CGV_LOOKAHEAD_DAYS=1 `
  -e CGV_POLL_INTERVAL_SECONDS=15 `
  -e CGV_REQUEST_INTERVAL_SECONDS=0 `
  -p 127.0.0.1:5002:5000 `
  --entrypoint python `
  cgv-open-push:test `
  -c "import cgv_open_push_main as m; m.KakaoNotifier.send=lambda self,target_name,message:{'result_code':0}; m.main()"

Start-Sleep -Seconds 38
docker top cgv-open-push-contract-smoke -eo pid,ppid,comm
docker inspect --format "status={{.State.Status}} restart={{.RestartCount}}" cgv-open-push-contract-smoke
Invoke-WebRequest http://127.0.0.1:5002/healthz
docker logs cgv-open-push-contract-smoke
docker stop --timeout 10 cgv-open-push-contract-smoke
```

Expected evidence is three processes, no restart, HTTP 200 health, repeated stable schedule counts,
and no added-schedule message after the initial baseline. The final 2026-09-03 smoke completed four
successful 15-second polls.

## Full service

Starting the normal service sends a startup message to the authenticated Kakao chat. Obtain explicit
approval before the first normal run. Keep resource limits and localhost-only status binding:

```powershell
$KakaoDataPath = (Resolve-Path .\v1\data).Path
docker run --rm `
  --name cgv-open-push `
  --pids-limit 32 `
  --cpus 1 `
  --memory 512m `
  --env-file .\v1\.env `
  -p 127.0.0.1:5000:5000 `
  -v "${KakaoDataPath}:/data" `
  cgv-open-push:test
```

Run it in the foreground first, inspect its logs and status page, then stop it with
`docker stop --timeout 10 cgv-open-push`. Add a restart policy only after graceful shutdown and the
chosen full target configuration have been observed successfully.

## Minimum verification by change type

| Change | Minimum safe evidence |
|---|---|
| Documentation/context rules | `Scripts/Agent/ValidateProjectDocs.ps1` passes |
| Pure Python helper | Syntax check plus focused unit test |
| CGV request/parser | Fixture tests plus one bounded live probe with timeout |
| Change detection | Before/after fixture proves exactly the intended queued result |
| Process supervision | Failure or live limited smoke proves process count remains bounded |
| Messenger integration | Mocked delivery test plus one owner-approved test message |
| Docker/runtime change | Image build and resource-limited smoke test |

## Validate repository context

```powershell
pwsh -File Scripts/Agent/ValidateProjectDocs.ps1
git status --short
```

If required validation cannot run, record the reason, affected confidence, and exact follow-up command
in the active task or final handoff.
