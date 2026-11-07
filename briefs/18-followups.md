# 18-followups: approval time, file size, a small restore record, a quiet prompt hook

**Goal:** four follow-up changes to the control base on the same branch, decided by the lead after the package
review. Each comes with tests; everything that passes today keeps passing. Nothing else changes.

## Background (read first)

- `briefs/18-control-base.md` (the package brief; its scope, out-of-scope list and rules still hold) and
  `briefs/18-review-fixes.md` (the last round).
- `reviews/18-control-base/REPORT.md`, `REVIEW.md`, `REVIEW-2.md` and `control/README.md` (what was built and
  reviewed).
- The design: `git show origin/council/2026-11-07-control-layer:docs/design/CONTROL.md`, rules 4.1, 4.3, 4.4
  and 4.10.

## What to change

1. **Approval expiry: 15 minutes by default.** The owner approves on his phone through Remote Control, so the
   time from preparing a send until the send call arrives includes his answer; 120 seconds is too short. Make the
   default `approval_ttl` 900 seconds, still configurable (`control/settings/service.json` and the code default
   agree). Tests: a send arriving just before the limit goes through; one arriving just after is `failed`
   (nothing submitted) with the adapter's `drop` called. Use a controlled clock, not real waiting.
2. **File size: 25 MiB per file by default, sent in chunks.** Make the default per-file limit 25 MiB
   (26,214,400 bytes), a configurable value (`control/settings/proxy.json`, the service side, and the code
   defaults agree). Move file bytes over the socket in chunks, in both directions (the proxy's upload to the
   service and the download for saving), so no single message exceeds the wire limit. The service assembles an
   upload into its unchangeable blob, checks size and sha256 against what the proxy reported, and refuses anything
   incomplete, oversized, out of order or mismatched, keeping nothing half-written as a blob. Tests: a file just
   under the limit transfers and one just over is refused (both through the real proxy and service); the bytes
   the receiver gets are exactly the hashed bytes, also when the source file is replaced after reading; a chunk
   stream that is cut off, reordered or has a wrong hash leaves no blob.
3. **The separate record keeps only what restore protection needs.** Today `evidence_dir/operations.jsonl`
   holds every full event, including message text and app data. From now on, its entries hold only: the
   operation id, the generation, the input hash, the service's short description (what the owner needs to
   recognise the operation: action, account, recipients or targets, subject or title), and each state change
   with its time. No message bodies, attachment bytes, item contents or other app data: those stay only in the
   main log (SQLite) and the blob store. What must still hold, with the existing tests still passing:
   - An older main log is detected and refused until the owner's `restore_confirm`; then the generation moves on,
     earlier-generation ids are refused, and every operation the record knows but the log doesn't is listed
     `unknown` with its short description.
   - A crash (kill -9) at every point of a write never loses an operation from the record, never makes the
     record and the log disagree in a way that hides an operation, and never sends twice. If the write order or
     recovery changes, add kill points for the new boundaries.
   - The record entry for a send or delete is durable before any irreversible step, as today.
   - `aresos log` (`control_log`) keeps showing what was done today, now from the main log.
   Tests: a size test showing that a send's record entries don't grow with its body or attachments (the same
   send with a tiny body and with a body at the asking-input limit plus a 25 MiB attachment adds the same record
   size, give or take its subject and hashes), and a check that no body text or attachment bytes appear in the
   record. Note the record's growth per operation (bytes per state change, per typical send) in the report; no
   compaction is needed yet.
4. **The `UserPromptSubmit` hook never erases the owner's prompt.** On malformed or unreadable input, or any other
   failure, it exits 0 and adds nothing (it is not the safety net; design rule 4.10). It has to know which event
   it serves without parsing its input: give each hook its own launcher argument (for example
   `launch.py hook Stop` and `launch.py hook UserPromptSubmit`) in `control/settings/managed-hooks.json`, and treat
   input whose `hook_event_name` disagrees with that argument as malformed. Keep the `Stop` hook's behaviour as it
   is. Tests: malformed input to the prompt hook exits 0 with empty output; valid input with pending work still
   gives the reminder; the existing Stop tests still pass.

Update `control/README.md` where it describes these four things, regenerate the generated files if any
description changes (`python3 control/generate.py`), and add a short "Follow-ups" section to
`reviews/18-control-base/REPORT.md`: each change, its code and tests, the record's growth per operation, and the
workflow run IDs. Don't rewrite the rest of the report, and don't edit the `REVIEW*.md` files.

## Out of scope

Everything outside these four changes, including the other judgment calls in the report. Ideas or further findings
go in the report as **PLAN-GAP** or **JUDGMENT-CALL**, not into the code. Same out-of-scope list as
`briefs/18-control-base.md` (`os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`,
`docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`).

## Acceptance

- Each change has its tests; all existing tests still pass; none weakened, skipped or deleted. Where an existing
  assertion has to change because the behaviour changed on purpose (for example the old 1 MiB or 120-second
  values), say which and why in the report.
- The workflow passes twice on the final head (push and pull-request runs both count).
- No secrets, real addresses or account names.

## If unsure

Take the option that keeps a send from happening twice or without its approval, and keeps every outcome honest.
Say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/18-control-base`. Commit in small steps and push this branch; draft
  PR #6 already exists, so don't open another. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 10 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: careful changes to the operation record and file transfer, with tests.
