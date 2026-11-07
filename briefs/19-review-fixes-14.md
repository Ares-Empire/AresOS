# 19-review-fixes-14: refuse duplicate JSON keys at every entrance; name the message that blocks a delete

**Goal:** close security re-review 6 (`reviews/19-mail/SECURITY-REVIEW-6.md`, head `3058c256`; read it first).
Addresses and ordinary reordering are closed. One blocking finding (duplicate JSON keys bypass the question-first
check) and one should-fix remain. Approved by the lead on 2026-11-07. **Keep this round tight:** the Codex allowance is
nearly used up for the week. Briefs 19 and `19-review-fixes` to `-13` still apply where this brief doesn't change
them; where in doubt, their "If unsure" rule decides.

## What to build

1. **Duplicate keys are refused before any dict exists** (blocking). Python's `json.loads` keeps the first key's
   position and the last value, so `{"question": "Do nothing?", "operation_id": …, "description": …, "question":
   "<the genuine question>"}` passes `require_question()`.
   - Add one shared strict decoder in `control/aresos_control/common.py` (`json.loads` with an `object_pairs_hook`
     that refuses any repeated key at any nesting level, and refuses `NaN`/`Infinity`). Use it everywhere outside JSON
     enters: the socket (`protocol.py` `receive`), the CLI's `--input` (both places in `cli.py`), the hook's stdin
     (`hooks.py`), the daemon's configuration file (`daemon.py`), and the MCP proxy's ingress. Internal reads of the
     service's own storage (`storage.py`, `blobs.py`, `testapp.py`) may stay as they are; say so in the report.
   - **The MCP proxy:** the MCP SDK's `stdio_server` decodes JSON-RPC itself before `call_tool` sees the arguments, so
     a duplicate is gone by then. Check each raw incoming line with the strict decoder before the SDK parses it (for
     example by giving `stdio_server` a wrapped stdin stream), and answer a refused line with a JSON-RPC error for its
     request id so the client never hangs. Prove it with the real proxy process.
   - Refuse the whole request before validation, hashing, reservation, submission, staging, evidence checks or any
     adapter call. Use `stale_approval` when the request is an asking input (a send, delete or other approval tool);
     otherwise the existing `invalid_input` code. Don't change any other behavior.
   - **Tests, on raw JSON text (not dict permutations):** a duplicate `question` (plain, and spelled with a
     `q` escape), a duplicate `operation_id`, a duplicate `description`, a duplicate key inside `description`,
     and a duplicate key in the request envelope. Each through the socket, the CLI and the real MCP proxy, for
     `testapp` send and delete and for Mail send, delete and folder delete: refused, nothing ran (operation still
     `reserved`, no stages, no arrival or deletion on the fixtures, no adapter execution). The correct raw JSON still
     runs exactly once. Plus a plain-Python unit test of the strict decoder.

2. **Name the message that blocks a delete** (should-fix). In `control/aresos_control/mail/adapter.py` (around line
   529), one message whose From display name holds a control character makes the whole batch's Trash or permanent
   delete preparation refuse. Keep the address check exactly as strict. The refusal names the offending message
   reference(s) (escaped) and says in plain words: leave these out of the selection and delete them in your mail
   program. Test: a batch of healthy messages plus one bad one; the refusal names exactly the bad one, and preparing
   the batch without it works.

3. **Report.** Link `reviews/19-mail/SECURITY-REVIEW-6.md` from `REPORT.md` next to the other review files. Add a short
   "Review fixes, round 14" section: each finding, what changed, the files changed and why (base files included), the
   tests by name. In "For the owner: decisions before merge", add one clause to the approval-prompt bullet: an asking
   input with a repeated field is refused. Run IDs as before: in `REPORT.md`, the runs of the last commit that changes
   code or tests (both workflows, both passes) and the statement that any later commit changes only files under
   `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues and brief 18b's boundary workflow. Don't edit
`reviews/19-mail/REVIEW*.md` or `reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched:
`os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`,
`docs/control/PLAN.md`, `docs/control/FEATURES.md`, and the workflow files under `.github/`. Brief 18's tests under
`control/tests/` change only by additions or where the strict decoder forces it; name each change.

## Acceptance

- Each point has regression tests that would fail on `3058c256` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Refuse the whole request. Never repair, merge or reorder what the caller sent.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Every push to the PR starts the Mail,
  base and boundary workflows. Before each push, run locally everything that doesn't need containers (Docker isn't
  available on this Mac): `python3 control/generate.py --check`, the syntax and plain-Python test helper
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`,
  and `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest
  test_operations test_record test_crashes test_approval_questions`, plus your new plain-Python tests. Aim for one
  push with the code and tests and one with the report. For the second pass on the final head, rerun the same run
  with `gh run rerun <id>`; never push again just to get another run. Keep it to about 4 workflow runs in all.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a small, exact boundary fix (the lead's pick for this round).
