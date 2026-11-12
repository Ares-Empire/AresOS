# 19-review-fixes-16: installed settings must equal the generated ones; bounded MIME; bounded storage

**Goal:** close security review 8 (`reviews/19-mail/SECURITY-REVIEW-8.md`, head `9e4b1375`; read it first). All
review-7 findings are closed. One blocking finding and three should-fixes remain; fix all of them in this round.
Approved by the lead on 2026-11-08. Briefs 19 and `19-review-fixes` to `-15b` still apply where this brief doesn't
change them; where in doubt, their "If unsure" rule decides.

## What to build

1. **The installed settings must equal the generated ones** (blocking). `control/aresos_control/boundary.py` checks a
   list of known values, so it accepts `sandbox.excludedCommands: ["aresos *"]` with `permissions.allow:
   ["Bash(aresos *)"]` (excluded commands run outside the sandbox and the Bash grant skips the prompt, so `aresos mail
   send --input <approval>` sent with no prompt), and `sandbox.filesystem.disabled: true`.
   - Replace the value list with exact equality: the installed managed settings must equal the generated
     `control/settings/managed-settings.draft.json`, compared as canonical JSON. Any added, removed or changed key
     refuses with `boundary_not_installed`, naming the differing key paths. Do the same for `managed-mcp.json`, and for
     managed hooks if they are installed as their own file. One source of truth: nothing can be left off a list.
   - **Settings Claude Code still merges from other scopes.** Check the official Claude Code settings reference
     (code.claude.com, settings and sandbox sections) for which settings are still merged from user, project and local
     scopes when managed settings exist. For each one that could loosen confinement (`sandbox.excludedCommands`,
     sandbox filesystem and network paths, permission allow rules, MCP servers, hooks), pin it with a managed-only
     setting where one exists, in the generated managed settings. Where none exists, prove that no write path reaches
     the files those scopes come from: Bash is sandboxed and Edit is denied by the managed settings, so what remains is
     the control layer's own file-writing tools (`mail_attachment_save`, `testapp`'s `file_save`, and any other action
     that writes a file for the caller). Add tests that each of them refuses `~/.claude/**`, `~/.claude.json`,
     `**/.claude/**`, `**/.mcp.json` and the shell start-up files (`~/.bashrc`, `~/.bash_profile`, `~/.profile`,
     `~/.zshrc`, `~/.zprofile`, `~/.zshenv`). Write the result in `REPORT.md`: which settings merge, which are pinned
     and how, which rely on the write-path proof, with the documentation read and its date (claims marked **read**).
   - Regressions: the review's exact settings, `sandbox.filesystem.disabled: true`, one extra allow rule, one extra
     excluded command and one extra MCP server each refuse, naming the difference. The generated file and brief 18b's
     boundary package output pass.

2. **The whole path to the settings is protected** (should-fix, do it now). Every ancestor directory of the managed
   files must be owned by root, not writable by group or others, and not a symlink, checked component by component.
   The production paths are fixed constants in the code. Test fixture paths must not be reachable through the service
   configuration in production: remove that configuration option and let tests patch the constant.

3. **Deep MIME can't crash the service** (should-fix, do it now). `control/aresos_control/mail/codec.py` (around line
   20) parses incoming mail with Python's recursive parser and no bound: a 38.5 KB mail with 1,200 nested
   `message/rfc822` parts makes `mail_read` raise `RecursionError`, which the daemon's handler doesn't catch.
   - Every parse of mail bytes from a server goes through a bounded parser: an explicit nesting-depth limit and part
     count, enforced before or while parsing, with a controlled refusal that names the message. Reading other mail
     keeps working.
   - The daemon turns any unexpected exception from one request (including `RecursionError` and `MemoryError`) into
     an error for that request and keeps serving; it never writes past a failed journal transaction (round 15's
     fail-closed rule stays).
   - Regressions: the review's 1,200-level mail through `mail_read`, `mail_search`, `mail_thread` and an attach or
     forward path, refused with the message named; the service still answers the next request; an injected unexpected
     exception in one request is answered as an error and the next request works.

4. **Storage can't be filled at will** (should-fix, do it now). Free `mail_compose` calls with 200,000-character
   bodies each persist a composition even when the answer is `result_too_large`, with no total limit; filling
   storage forces `journal_incomplete` and an owner restore.
   - Reject an oversized composition before anything is persisted.
   - Admission limits: a cap on stored compositions (count and total bytes), with old unused ones expiring (never one
     an open operation still uses). A refusal at the cap names the limit and how to free space.
   - Check the other free actions that persist data on Claude's request (caller file imports, export blobs, drafts
     kept locally, filing intents, notices) and give each a bound of the same kind where it can grow without limit;
     list in `REPORT.md` what each one stores and its limit.
   - Keep the fail-closed behaviour. Regression: filling to each cap refuses cleanly, the journal stays valid, a restart
     reports no corruption, and freeing space (expiry) lets work continue.

5. **Report.** Add `reviews/19-mail/SECURITY-REVIEW-8.md` (already committed) to the review links in `REPORT.md`. Add a
   "Review fixes, round 16" section: each finding, what changed, the files changed and why, the tests by name, and the
   settings-scope result from point 1. If the composition or file caps are something the owner would notice in
   normal use, add one owner-section line saying they follow the safety rule and are not a new choice (as the lead did
   for the installed-boundary bullet). Run IDs as before: in `REPORT.md`, the runs of the last commit that changes code
   or tests (both workflows, both passes) and the statement that any later commit changes only files under
   `reviews/`; in the PR body, the runs on the final head.

## Out of scope

Everything else, including a fresh hunt for other issues. Don't edit `reviews/19-mail/REVIEW*.md` or
`reviews/19-mail/SECURITY-REVIEW*.md`. The same paths as brief 19 stay untouched: `os/`, `mod/`, `docs/INSTALL*`,
`docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`,
and the workflow files under `.github/`. Change brief 18b's `control/boundary/` only as far as point 1 needs, and name
each change. Brief 18's tests under `control/tests/` change only by additions or where the new rules force it; name
each change and keep its assertions.

## Acceptance

- Each point has regression tests that would fail on `9e4b1375` and pass now; the report names them. No earlier test
  is weakened, skipped or deleted.
- The Mail workflow and the base workflow both pass twice on the final head; the boundary workflow still passes.
- Generated artifacts in sync; no secrets, real addresses, account names or provider names.

## If unsure

Refuse. Installed settings that differ from the generated ones in any way refuse asking tools; a mail that can't be
parsed within the bounds is refused; a write past a cap is refused, never squeezed in.

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
  test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_ingress_bounds
  test_journal_closed`, plus your new plain-Python tests. Aim for one push with the code and tests and one with the
  report. For the second pass on the final head, rerun the same run with `gh run rerun <id>`; never push again just to
  get another run. Keep it to about 8 workflow runs.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: boundary equality, parser bounds and storage admission across the base and Mail.
