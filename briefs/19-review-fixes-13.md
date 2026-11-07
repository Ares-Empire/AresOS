# 19-review-fixes-13: never cut an address; question-first order enforced at the boundary

**Goal:** close security re-review 5 (`reviews/19-mail/SECURITY-REVIEW-5.md`, head `9061d892`; read it first). The
notice blocker and the notice escaping are closed. Two blocking points remain: a question can still hide a real
address, and a reordered approval is accepted. Approved by the lead on 2026-11-07. Briefs 19 and `19-review-fixes`
to `-12` still apply where this brief doesn't change them; where in doubt, their "If unsure" rule decides.

## What to build

1. **Never cut an address, anywhere** (re-review finding 1). In `control/aresos_control/mail/questions.py`, every
   place a person or address appears in a question goes through one helper: send recipients (To, Cc, Bcc), the
   senders in the delete sentence, the unsubscribe recipients (today `few(details['to'])` cuts them at 80 characters)
   and the unsubscribe sender.
   - The helper parses each header into its mailboxes and handles each one separately: the display name may be
     shortened (80 visible characters, "…", never mid-escape), the complete address never is, at any length. A
     header with several mailboxes (a From with two people) shows each one as name plus complete address, the first
     few then "and N more" with an exact count, like recipient lists.
   - If a header can't be parsed into mailboxes (no address, a parse defect, an empty address), refuse the approval
     with a clear reason instead of showing the raw header shortened. If the complete addresses don't fit the 4,096
     question cap, refuse the approval as too large; never shorten an address to make it fit.
   - Folder names in questions are shown whole as well (they name what is deleted); too long for the cap refuses.
   - Tests: the re-review's long-name unsubscribe case through the real preparation path (the complete
     `stranger@example.org` appears); a valid 117-character bare address shown whole; a delete of a message whose
     From holds two long-named mailboxes (both complete addresses appear); an unparsable header refused with the
     reason; addresses that can't fit the cap refused, not cut. Update the round-12 lookalike test only where its
     unparsable-header expectation changes, and name the change.

2. **Question-first order enforced at the service boundary** (re-review finding 2). Today `require_question()` only
   checks presence, submission compares order-insensitive hashes and dicts, and `protocol.send()` serializes every
   message with `display_json()`, which puts `question` first and so hides a caller's reordering before the service
   sees it.
   - Check the order of an asking input where it arrives, before anything reorders it: in the MCP proxy on the tool
     call's arguments as received, and in the service on the socket payload as parsed (Python's `json.loads` keeps
     the received key order; check it right after parsing, before any canonical or display serialization). The
     terminal command (`aresos … send --input …`) is checked the same way at the service. Anything other than exactly
     `question`, then `operation_id`, then `description` (and no other keys) refuses with `stale_approval`, and nothing
     runs: no submission, no stage, no evidence check, no adapter call.
   - Requests from the proxy or CLI to the service are serialized in the caller's order; the question-first
     presentation order (`approval_order`/`display_json`) applies to results only, so outgoing serialization can't
     hide a reordering. Keep result presentation question-first as round 12 made it.
   - This is brief 18's base (`common.py`, `protocol.py`, `proxy.py`, `engine.py`, `cli.py` as needed); keep the
     change minimal, keep the base suite green, and say which files changed and why. Brief 18's tests under
     `control/tests/` change only where this forces it; keep their assertions and name each change.
   - Tests: the re-review's `{description, operation_id, question}`, and every other non-matching order, refused with
     `stale_approval` and no execution for `testapp` send and delete (through the real MCP proxy and through the
     socket), and for Mail send, delete and folder delete (no SMTP arrival, no deletion, no adapter execution, checked
     on the fixtures). The correct order still runs once.

3. **Report.** Link `reviews/19-mail/SECURITY-REVIEW-5.md` from `REPORT.md` next to the other review files. Add a short
   "Review fixes, round 13" section: each finding, what changed, the base files changed and why, the tests by name.
   Update the owner section and PR body only if what the owner sees changes. Run IDs as before: in `REPORT.md`, the
   runs of the last commit that changes code or tests (both workflows, both passes) and the statement that any later
   commit changes only files under `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues and brief 18b's boundary workflow. Don't edit
`reviews/19-mail/REVIEW*.md` or `reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched:
`os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`,
`docs/control/PLAN.md`, `docs/control/FEATURES.md`, and the workflow files under `.github/`.

## Acceptance

- Each point has regression tests that would fail on `9061d892` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Refuse. A question that can't show every address it names in full is refused, never shortened; an asking input in
any other order is refused, never reordered.

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
  test_operations test_record test_crashes test_approval_questions`, plus your new plain-Python tests. Batch your
  commits into as few pushes as you can, ideally one for the code and tests and one for the report. For the second
  pass on the final head, rerun the same run with `gh run rerun <id>`; never push again just to get another run. Keep
  it to about 6 workflow runs in all.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a base boundary change and exact address handling, on code it wrote.
