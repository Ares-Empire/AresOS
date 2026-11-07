# 19-review-fixes-12: every approval starts with one plain question written by the service

**Goal:** an owner decision (2026-11-07). Phone tests showed that the owner's phone shows Claude Code's approval
prompt as fields and values. He decided to use it as it is: approvals stay Claude Code's own prompt, and every asking
input starts with one plain sentence written by the service, so the prompt reads well on the phone. The full content
fields stay below that sentence, unchanged. Approved by the lead on 2026-11-07. Briefs 19 and `19-review-fixes` to
`-11` still apply where this brief doesn't change them; where in doubt, their "If unsure" rule decides.

## What to build

1. **A `question` field in the shared approval format (base).** `approval_input()` in
   `control/aresos_control/common.py` and the `APPROVAL` schema in `control/aresos_control/definitions.py` are brief
   18's shared format, which the Chrome adapter (brief 20) will also use. Add a required `question` string there, as
   the **first** field of every asking input (`{question, operation_id, description}`, in that order in the returned
   approval and in the schema's properties). The adapter builds it at prepare time, from the same facts as the
   description; the engine stores it as part of the approval and checks it like the rest: the input must equal the
   whole stored approval, so an altered `question` refuses with `stale_approval` and nothing is submitted. It counts
   toward the 16 KiB asking limit and goes through the same escaping (`visible`) as the description. Every action
   that reserves an operation provides one, including `testapp` (a plain fixture sentence), repairs and the owner-only
   onboarding probes. Brief 18's tests under `control/tests/` change only where the new field forces it; keep their
   assertions and name each change in the report.

2. **Mail's questions**, in plain English, one sentence, bounded in length:
   - `mail_send`: "Send this mail to Anna Example and Ben Example, Cc Carla Example, hidden copy (Bcc) to
     x@example.com? Subject: Angebot für die Wohnung. 6 lines, 2 attachments: offer.pdf, floorplan.png." Recipients
     by display name, falling back to the address when there is none; after a few recipients per group, "and N more"
     (the full lists stay in the fields below). The subject as written. The line count of the text Claude wrote; say
     when a quoted or forwarded part is included ("quotes the earlier mail", "forwards 1 mail"). Attachment names after
     a few become "and N more".
   - `mail_delete`: "Delete 3 messages for good? From Anna Example, 'Angebot' (5 Nov); from …" or "Move 3 messages to
     Trash? …", with sender, subject and date per message for the first few, then "and N more".
   - `mail_folder_delete`: "Delete the empty folder 'Projects/Old'?"
   - `mail_unsubscribe`: "Unsubscribe from <list or sender> by sending a mail to <address>?" or "… by a one-click web
     request to <host>?"
   - Any other Mail action that reserves an operation gets a matching one sentence.
   - Everything from a mail (names, subjects, folder names) is escaped exactly as in the description: control and
     bidi characters shown escaped, nothing cut in the middle of an escape sequence.
   - Update the tool descriptions (Claude passes the approval unchanged, `question` included) and regenerate the
     artifacts.

3. **Tests:**
   - `mail_send` questions for many recipients in To, Cc and Bcc ("and N more", full lists still in the fields),
     non-ASCII display names, a recipient without a display name, display names and a subject with control and bidi
     characters (escaped as elsewhere), many attachments, a reply that quotes and a forward.
   - `mail_delete` for both modes and many messages, `mail_folder_delete`, `mail_unsubscribe` (mailto and one-click).
   - An altered `question` (and a removed one) refuses with `stale_approval` and nothing is sent or deleted, for Mail
     and for `testapp`.
   - The question stays within the 16 KiB asking limit together with the rest, or the whole approval is refused as
     too large, never cut.
   - `question` is the first field of every returned approval.

4. **Report.** Add a short "Owner decision: plain question first (round 12)" section to `reviews/19-mail/REPORT.md`:
   what changed, that the `question` field lives in the base's shared approval format so Chrome (brief 20) uses the
   same thing, the base files and base tests changed and why, and the tests by name. Update "For the owner: decisions
   before merge" and the PR body: the approval prompt now starts with one plain sentence; the details follow below
   it. Run IDs as before: in `REPORT.md`, the runs of the last commit that changes code or tests (both workflows, both
   passes) and the statement that any later commit changes only files under `reviews/`; in the PR body, the runs on
   the final head.

## Out of scope

Everything else, including a fresh hunt for other issues and brief 18b's boundary workflow. Don't edit
`reviews/19-mail/REVIEW*.md` or `reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched:
`os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`,
`docs/control/PLAN.md`, `docs/control/FEATURES.md`, and the workflow files under `.github/`.

## Acceptance

- Each point has tests that would fail before this round and pass now; the report names them. No earlier test is
  weakened, skipped or deleted; expectations that change only because approvals gained `question` are named.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names (examples use
  example.com/.invalid addresses and invented names).

## If unsure

The question never says less than or something different from the fields below it; when in doubt, say less in the
sentence ("and N more") and leave the detail in the fields. Never cut the approval.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/19-mail`, on top of its current head. Never rebase, never merge
  another branch in. Draft PR #9 already exists, so don't open another. Never merge, never push to `main`, never
  force-push.
- **Push as little as possible; the owner gets a mail for every failed run.** Every push to the PR starts the Mail,
  base and boundary workflows. Before each push, run locally everything that doesn't need containers (Docker isn't
  available on this Mac): `python3 control/generate.py --check`, a syntax check of every `control/**/*.py`, and the
  plain-Python test classes (`unittest.TestCase` subclasses that need no mail server, including your new ones where
  they can run that way, and brief 18's tests under `control/tests/` that run without containers). Batch your commits
  into as few pushes as you can, ideally one for the code and tests and one for the report. For the second pass on
  the final head, rerun the same run with `gh run rerun <id>`; never push again just to get another run. Keep it to
  about 6 workflow runs in all.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a base format change with careful bounded text and approval-equality tests.
