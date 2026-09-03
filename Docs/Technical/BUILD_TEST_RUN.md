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

The current suite contains 29 CGV contract, target/filter, Kakao, and isolated-retry tests. The
2026-09-03 final image is `sha256:45d244e98d98d5086f8c8296b0ca422824585da32ea0404fca915e1856923250`
and 67,210,857 bytes. `tests/smoke_isolated_polling.py` is a separate bounded process smoke, not a
unit test; it is excluded from the image and mounted only for validation.

## Configure CGV polling

The default catalog contains these target names:

- `YONGSAN-IMAX`: 용산아이파크몰, site `0013`
- `WANGSIMNI-IMAX`: 왕십리, site `0074`
- `APGUJEONG-IMAX`: 압구정, site `0040`

With an empty `CGV_TARGET_NAMES`, all three are enabled. Use a comma-separated subset in `v1/.env`
when appropriate, for example:

```dotenv
CGV_TARGET_NAMES=YONGSAN-IMAX
CGV_LOOKAHEAD_DAYS=14
CGV_POLL_INTERVAL_SECONDS=300
CGV_REQUEST_INTERVAL_SECONDS=1
CGV_RETRY_INITIAL_SECONDS=60
CGV_RETRY_MAX_SECONDS=900
```

The defaults scan 14 dates across three unique sites: 42 sequential requests per healthy normal
round, with one second after request completion and at least five minutes between round starts.
That is nominally 504 requests/hour or 12,096/day when healthy rounds complete within five minutes.
Retries add requests for failed keys only; these counts are not a hard aggregate quota.

A failed site/date retains its last successful baseline and retries after 60, 120, 240, 480, then
900 seconds, without sleeping the other jobs through that backoff. Normal rounds skip failed keys
whose deadline is not due; successful recovery returns them to normal polling. The one-second
spacing limit covers every request, including retries. A single in-flight timeout can still delay
later work for up to the configured 20 seconds.

Messages are queued after each theater's due dates are attempted, before the next theater. A failed
date does not suppress successful-date notifications, and later recovery may produce another message
for that same theater. First successful responses per site/date establish silent baselines. Snapshots
remain in memory only. Unknown or removed target names fail at startup; replace old target overrides
when deploying. Environment changes require recreating the container with the updated `--env-file`.

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

During the earlier ADR-0002 validation on 2026-09-03, the then-current image returned 126 schedules
for Yongsan; the IMAX filter found six. A separate known-empty date returned `statusCode=0` with `data=[]`.

The later three-IMAX validation used one current-date request per selected site and found Yongsan 2,
Wangsimni 2, and Apgujeong 1 matching schedule at 20:41 KST. These counts vary throughout the day.
The public catalog verified Apgujeong as `0040`; its schedule response also contained CINE de CHEF
site `P001`, which the watcher correctly ignores when building the requested site/date snapshot.

## Offline isolated-retry runtime smoke

This eight-second smoke starts the real main/status/worker process tree, replaces CGV and Kakao
calls with in-memory fakes, and runs with networking disabled. It mounts only tests, not credentials.
It verifies three independent messages, one isolated retry, continued healthy-theater progress,
no duplicate messages on the next round, three Python processes, and container-local health HTTP 200.
The short test intervals (3-second normal rounds and 1-second initial retry) never reach CGV.

```powershell
$TestPath = (Resolve-Path .\v1\tests).Path
docker run --rm `
  --name cgv-isolated-runtime-smoke `
  --network none `
  --pids-limit 16 `
  --cpus 0.75 `
  --memory 256m `
  --read-only `
  --tmpfs /tmp:rw,noexec,nosuid,size=32m `
  -e PYTHONDONTWRITEBYTECODE=1 `
  -e PYTHONPATH=/app `
  -e KAKAO_REST_API_KEY=smoke-only `
  -e KAKAO_CLIENT_SECRET=smoke-only `
  -e KAKAO_REDIRECT_URI=http://localhost:8765/oauth/kakao/callback `
  -e KAKAO_TOKEN_FILE=/tmp/unused-token.json `
  -v "${TestPath}:/tests:ro" `
  -w /tmp `
  cgv-open-push:test /tests/smoke_isolated_polling.py
```

Success requires exit code 0 and `ISOLATED_SMOKE_OK`. Any "Kakao message sent" log in this smoke
refers to the fake sender; no real message is sent. The temporary container is automatically removed.

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
