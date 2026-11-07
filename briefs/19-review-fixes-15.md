# 19-review-fixes-15: the installed boundary is a precondition; renames stay put; the journal fails closed

**Goal:** close security review 7 (`reviews/19-mail/SECURITY-REVIEW-7.md`; read it first). Unlike the earlier
reviews, it covers the whole approval and ingress path at `6a2e0e36`, not one round's diff. It found three blocking
issues and two should-fixes; fix all of them in this round. The attachment-route finding stays under the owner's
decision (no change). Approved by the lead on 2026-11-08. Briefs 19 and `19-review-fixes` to `-14` still apply where
this brief doesn't change them; where in doubt, their "If unsure" rule decides.

## What to build

1. **The installed boundary is a hard precondition, checked by the service** (blocking, review finding 1). The design
   already relies on the deployment for the approval gate: managed Claude Code ask rules make the owner approve, and
   Claude's Bash runs in a sandbox that can't reach the service's sockets (`README`, `docs/control/PLAN.md` "No way
   around the tools", brief 18b). The service never checks that this gate is installed. Make it check:
   - On start, and before every asking preparation and submission (you may cache by file identity and mtime), read
     the installed system-wide Claude Code files the boundary package installs: the managed settings and the managed
     MCP file (`/etc/claude-code/managed-settings.json`, `/etc/claude-code/managed-mcp.json`). Require each to be a
     regular file owned by root and not writable by group or others (no symlinks), with:
     - `sandbox.enabled` true and `sandbox.failIfUnavailable` true; `sandbox.allowUnsandboxedCommands` false;
       `sandbox.network.allowAllUnixSockets` false; the service's socket directory (`/run/aresos-tools`) in
       `sandbox.filesystem.denyRead`;
     - `permissions.disableBypassPermissionsMode` `"disable"`; `allowManagedPermissionRulesOnly` and
       `allowManagedHooksOnly` true;
     - an ask rule in `permissions.ask` for every asking tool of every app, derived from the generated definitions
       (never a hard-coded list), and none of them in `permissions.allow`;
     - managed MCP servers exactly the expected ones (today `control` and `mail`), with the expected commands.
   - If anything is missing or different, refuse every asking operation (preparation and submission) with
     `boundary_not_installed` and a reason naming exactly what is missing or wrong, and make Mail onboarding refuse to
     finish. Free actions (reads and changes) keep working.
   - **One source of truth:** today the MCP ask rules live in the generated `control/settings/ask-rules.json` while
     `control/settings/managed-settings.draft.json` (what brief 18b's boundary image installs) asks only for
     `WebFetch` and `WebSearch`. Make `control/generate.py` also write the asking tools' rules into the managed-settings
     draft (keeping its other content), so the generated draft is exactly what the check accepts and `--check` catches
     drift. A test proves that the boundary package's installed settings and MCP file, as brief 18b's image builds
     them (`control/boundary/`), pass this check.
   - The installed paths are configurable for tests (for example through `service.json`), but a missing setting
     means the default `/etc/claude-code` paths, never "no check". Test environments install valid root-owned copies
     of the generated files; adjust the test fixtures accordingly, never by skipping the check.
   - Tests: each required value missing or wrong (one at a time), wrong owner, group- or world-writable, symlink,
     unexpected or missing MCP server, a missing ask rule, an asking tool in `allow`: each refuses preparation and
     submission with `boundary_not_installed` naming it, and free actions still work; the correct files pass; Mail
     onboarding refuses to finish without them.
   - Say in `REPORT.md` that this is a precondition check: whether Claude Code honours the file is proven by brief
     18b's hostile tests and brief 18c, not by this check. `os/` installs the files later; another session owns that.
     Don't touch `os/`.

2. **A folder rename stays within its parent** (blocking, review finding 2). `mail_folder_rename` (around
   `adapter.py` line 1042) can rename a populated folder under a parent that becomes Trash between the role check and
   `RENAME`. Remove the race instead of reporting it:
   - `mail_folder_rename` only changes the last name part, within the same parent. A new name that contains the
     folder's hierarchy separator, or names a different parent, is refused with "move folders between parents in your
     mail program".
   - After `RENAME`, `LIST` the new name. If it now carries any special-use role (some servers assign roles by name),
     record it and warn through the existing bounded filing-notice path (round 11), never `done` silently.
   - Add one owner-section bullet as a JUDGMENT-CALL in plain words, with the alternative (cross-parent renames with a
     post-check and warning, as filing does).
   - Tests: the review's reproduction (`Source` to `Parent/Subfolder`) is refused before anything changes; a rename
     within the same parent works; a new name containing the separator is refused; a server that assigns a role by
     name after the rename produces the warning.

3. **The journal can't be corrupted by input, and fails closed** (blocking, review finding 3). `1e400` decodes to
   infinity; the socket's `saved` method accepts an unvalidated outcome; `storage.py` (around line 170) appends the
   independent record before serializing the event; and the service keeps writing past an incomplete transaction, so a
   restart reports `evidence_corrupt`.
   - `strict_json_loads` refuses non-finite numbers (`parse_float`, `parse_constant`) and integers beyond an explicit
     bound (for example 2^63 in absolute value or a fixed digit count).
   - Every transport envelope and every method's payload is validated against an explicit schema before dispatch,
     `saved` included.
   - The complete event is serialized (and validated as serializable) before any durable change: nothing goes to the
     independent record, SQLite or blobs until it is.
   - After an incomplete journal transaction, the service fails closed: it stops all writes and refuses every request
     that would write until restart recovery has run, instead of writing past it.
   - Regressions for each, including the review's exact `{"v":1,"method":"saved","app":"mail","outcome":1e400}`
     followed by a composition: refused, the journal stays valid, and a restart does not report `evidence_corrupt`.

4. **Decoder bounds** (should-fix, do it now). In the shared strict decoder and the error-classification parser
   (the one `JSONInputError` and the proxy's error answer use):
   - an explicit nesting-depth limit, checked without recursion overflow (1,200 nested arrays today raises
     `RecursionError`);
   - explicit byte limits for MCP lines and hook input (the socket already has one);
   - strict UTF-8 with Unicode scalar values only: refuse lone surrogates, including escaped `\ud800`, surrogateescape
     bytes and a byte-order mark.
   - A raw-input regression for each on every ingress (socket, CLI, MCP proxy, hook), with nothing run.

5. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-7.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 15" section: each finding, what changed, the files changed and why (base, settings and
   boundary files included), the tests by name. Update "For the owner: decisions before merge": the rename judgment
   call, and one clause that asking tools refuse until the managed Claude Code settings are installed. Run IDs as
   before: in `REPORT.md`, the runs of the last commit that changes code or tests (both workflows, both passes) and
   the statement that any later commit changes only files under `reviews/`; in the PR body, the runs on the final
   head.

## Out of scope

Everything else, including a fresh hunt for other issues and the attachment-route finding. Don't edit
`reviews/19-mail/REVIEW*.md` or `reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched:
`os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`,
`docs/control/PLAN.md`, `docs/control/FEATURES.md`, and the workflow files under `.github/`. Change brief 18b's
`control/boundary/` only as far as point 1's single source of truth needs, and name each change. Brief 18's tests
under `control/tests/` change only by additions or where the new precondition or schemas force it (installing the
valid managed files in a fixture); name each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `6a2e0e36` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; brief 18's whole suite still passes; the
  boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Refuse. An asking operation without a verified boundary is refused, never allowed with a warning; a rename that could
leave its parent is refused; a write after an incomplete journal transaction is refused.

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
  test_operations test_record test_crashes test_approval_questions test_strict_json`, plus your new plain-Python tests.
  Aim for one push with the code and tests and one with the report. For the second pass on the final head, rerun the
  same run with `gh run rerun <id>`; never push again just to get another run. Keep it to about 8 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a bigger round across the base boundary, storage and Mail, on code it wrote.
