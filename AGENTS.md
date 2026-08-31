# cgv-open-push agent instructions

## Project

- `cgv-open-push` is a Python service that polls CGV reservation data and publishes opening alerts.
- Repository files are the durable cross-session memory. Chat history is not a source of truth.
- Start at `Docs/README.md` and load only the documents relevant to the current task.
- The tracked implementation is the legacy pre-renewal version under `v1/`. Do not describe it as
  operational without current verification.

## Session startup

Before changing files:

1. Read `Docs/README.md`, `Docs/Project/PROJECT_BRIEF.md`,
   `Docs/Status/IMPLEMENTATION_STATUS.md`, and `Docs/Work/ACTIVE.md`.
2. Inspect `git status`, relevant diffs, and the implementation files involved.
3. Read linked architecture, runbook, issue, task, and ADR documents relevant to the request.
4. Verify mutable claims against source, configuration, bounded network probes, and build/test output.
   If status documentation is stale, update it in the same change.

## Sources of truth

- Project purpose and scope: `Docs/Project/PROJECT_BRIEF.md` and the public `README.md`.
- Actual tracked implementation: `v1/*.py`, `v1/requirements.txt`, and `v1/Dockerfile`.
- Architecture and operating procedure: `Docs/Technical/`.
- Current summary and confirmed defects: `Docs/Status/`.
- In-progress handoff state: `Docs/Work/ACTIVE.md` and linked task files.
- Technical decisions: accepted ADRs under `Docs/Decisions/`.
- Runtime claims: reproducible build, test, bounded HTTP probe, and container output.

When documentation and implementation disagree, preserve stated intent, record the drift, and
correct mutable status claims. Do not silently redefine intent to match legacy code.

## Safety and working rules

- Keep changes scoped to the requested task and preserve unrelated user changes.
- Never commit bot tokens, webhook URLs, session credentials, `.env` contents, or other secrets.
- Treat CGV endpoints, cookies, request payloads, and response schemas as mutable external behavior.
- Use bounded requests with explicit timeouts for diagnostics. Avoid high-frequency or parallel probes.
- Do not run the unmodified full `v1` service while `ISSUE-002` in
  `Docs/Status/KNOWN_ISSUES.md` is open. Its worker restart path can create an exponential process and
  request storm. Use a single-request probe, or first repair the restart behavior.
- When full container testing becomes safe, apply CPU, memory, PID, and restart limits appropriate to
  the test and bind the status port to localhost unless public exposure is explicitly required.
- Do not commit, push, rewrite history, or modify remote state unless the user requests it.

## Work and decision records

- Use a task file based on `Docs/Templates/TASK_TEMPLATE.md` when work may span sessions, crosses
  components, has unresolved decisions, or is delegated.
- Add active cross-session tasks to `Docs/Work/ACTIVE.md` with owner and file scope.
- Use an ADR based on `Docs/Templates/ADR_TEMPLATE.md` for expensive-to-reverse decisions, changes
  affecting multiple components, or project-wide conventions.
- Keep current summaries concise. Do not store full chat transcripts or narrative session diaries.

## Documentation updates

Update documentation in the same change when external behavior, architecture, directory ownership,
runtime status, required setup, validation commands, known issues, decisions, or handoff state changes.

Use these implementation states consistently:

- `Planned`: intent exists, no implementation.
- `Active`: currently being implemented.
- `Partial`: implementation exists but acceptance criteria are unmet.
- `Implemented`: implementation exists but required current verification is incomplete.
- `Verified`: required verification passed.
- `Blocked`: a stated condition prevents progress.
- `Deprecated`: no longer supported and awaiting or completing removal.

## Definition of done

Before reporting completion:

1. Run the smallest relevant safe build, test, static check, or bounded runtime probe.
2. Update affected architecture, status, issue, task, and ADR documents.
3. Record exact validation evidence and remaining uncertainty.
4. Remove completed work from `Docs/Work/ACTIVE.md` and archive only useful task records.
5. Run `pwsh -File Scripts/Agent/ValidateProjectDocs.ps1`.

If validation cannot run, state the reason and leave an exact follow-up command.
