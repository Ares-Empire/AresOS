# 19-review-fixes-26: close three classes completely, each at one central point, with an inventory

**Goal:** close security review 18 (`reviews/19-mail/SECURITY-REVIEW-18.md`, head `d8a7f21b`; read it first), judged
against the lead's refined disk bar (round 25, in `REPORT.md`). Again there is no approval, replay, credential or
free-action bypass, and observation paging held (7 MB across 1,176 bounded pages, foreign cursors rejected). Three
blocking points remain, and all three are **new instances of classes already fixed once**. So this round works
differently:

**For each of the three classes below, find every instance yourself, close the class at one central point, and list
the instances in `REPORT.md` in a table per class (place, how it is closed, test).** The review's examples are tests,
not the scope. Review 19 checks completeness against those tables.

Approved by the lead on 2026-11-08. Briefs 19 and `19-review-fixes` to `-25` still apply where this brief doesn't
change them; where in doubt, their "If unsure" rule decides.

## What to build

1. **Class A: every response is bounded, errors included** (review finding 1: `mail/adapter.py` around line 566 embeds
   every rejected reference in an error; `results.py` around line 79 only bounds responses with observations; a 2 MB
   schema-valid request produced a 9 MB refusal that the transport rejected, dropping the owner warning).
   - **Central point:** one bounding step at the final serialization, covering every result, success or error, on
     every way out (socket, MCP, CLI). It always keeps the error code, the plain message and every owner warning, and
     pages or shortens the rest (details, rejected references, observations), with counts saying what was cut.
   - Error details built from request or mail data are also bounded where they are built.
   - Bound references and other untrusted string fields in the input schemas to sane lengths where the protocol allows
     it (a Message-ID line can't legally exceed 998 characters; use protocol limits, documented in the report).
   - **Inventory (table A):** every place a result or error embeds request- or mail-derived data.
   - Tests: the review's case (ten messages with malformed From headers and Message-IDs ending in 100,000 tabs, plus a
     pending filing warning) returns the refusal and the warning under the transport limit; and a generic test that,
     for every action in the definitions, sends a maximal schema-valid request plus mail fixtures with oversized
     headers and checks that every response passes the real transport limit with its warnings intact.

2. **Class B: no refusal outlives its cause, except a real transaction latch** (review finding 2: `storage.py` around
   line 208 keeps an index-admission refusal, and `require_index()` keeps refusing after space returns).
   - **Central point:** stored refusal state is re-checked on the next call, through one mechanism, so a recovered
     disk works without a restart. The only exception is round 25's transaction latch for a write that may have
     started.
   - **Inventory (table B):** every stored failure or refusal state (index admission, ledger, blobs, startup checks,
     boundary results, anything cached) and how each now re-checks.
   - Tests: the review's case (start with too little index space, restore space, the next write works); and a sweep
     mode: after each admission or limit refusal, restore space, and the same flow's next call succeeds without a
     restart.

3. **Class C: an unfinished durable intent always yields an owner warning after restart** (review finding 3:
   `mail/filing.py` around line 273 keeps a failed warning write only in memory; after a crash and a healthy restart
   the intent stays `started` but `control_pending` and `mail_filing_notices` are empty).
   - **Central point:** startup recovery turns every intent left `started` into an owner-visible notice in
     `control_pending` and the app's notices: filing, send, delete, unsubscribe, APPEND, repair, and every other intent
     type the inventory finds. The notice stays until it is resolved, and is written durably as soon as a write
     succeeds.
   - **Inventory (table C):** every durable intent type and its recovery notice.
   - Tests: the review's case (MOVE, the destination's role turns to Trash, post-MOVE writes refused, crash, healthy
     restart: the warning is shown); and, in the sweep's crash/restart mode, assert that every owner warning present or
     implied before the crash is visible afterwards.

4. **Should-fix, in scope.**
   - `blobs.py` (around line 80): the stream's implicit close must not replace the primary error. Close explicitly
     through round 25's cleanup helper.
   - Sweep: send completion requires matching evidence, meaning the receiver's DATA for that message and a Sent copy
     with its Message-ID, never an unrelated old Sent message. Add the review's probe (one DATA attempt and only an
     unrelated old message in Sent) as a test of the assertion function, which must reject it.
   - Sweep: run cleanup pairs at the syscall level (`ENOSPC` on the primary write, `EIO` on every later close, unlink,
     rename or truncate in the same flow), not only on helper-tagged operations.

5. **CI time.** Keep each Mail job under about 30 minutes on a normal runner. Split the sweep further if needed;
   `.github/workflows/control-mail.yml` may change for that only (keep `timeout-minutes: 45` on every job). Report the
   measured durations.

6. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-18.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 26" section with: the three inventory tables (place, how it is closed, test), each central
   point in plain words, the should-fixes, the files changed and why, the sweep's new modes and counts, the CI layout
   and durations, the tests by name. Run IDs as before: in `REPORT.md`, the runs of the last commit that changes code
   or tests (all workflows, both passes) and the statement that any later commit changes only files under `reviews/`;
   in the PR body, the runs on the final head.

## Out of scope

Everything else beyond these three classes and the should-fixes. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/` other than `control-mail.yml` as point 5 allows. Brief 18's tests under
`control/tests/` change only by additions or where the new rules force it; name each change and keep its assertions.

## Acceptance

- Each class has its table, a central point, and tests that would fail on `d8a7f21b` and pass now; the report names
  them. No earlier test is weakened, skipped or deleted.
- The Mail workflow (all its jobs) and the base workflow both pass twice on the final head; the boundary workflow still
  passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Bound at the last step and keep the error and warnings; re-check every stored refusal; turn every unfinished intent
into an owner warning. When unsure whether something is an instance of a class, treat it as one and list it.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Before each push, run locally:
  `python3 control/generate.py --check`,
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`,
  and `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest
  test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_boundary_exact
  test_ingress_bounds test_journal_closed test_policy_sources test_archive test_journal_capacity test_journal_streaming
  test_restore_batches test_review21_pending test_review21_storage test_review22_protocol test_review22_storage
  test_review23_results test_review24_exports`, plus your new plain-Python tests (including as much of the sweep as
  runs without containers). If you change the workflow, check its YAML locally before pushing. Aim for one push with
  the code and tests and one with the report. Don't start extra manual workflow runs. For the second pass on the final
  head, rerun the same pull-request run with `gh run rerun <id>`; never push again just to get another run. Keep it to
  about 6 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Commit in small, complete steps (one per class, then the should-fixes).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: three cross-cutting classes closed centrally with inventories, on code it wrote.
