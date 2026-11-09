# 20, continue: finish stage "Now" (lead decisions, 2026-11-09)

The first run stopped at the owner-input failure (`reviews/20-chrome/REPORT.md`, run 42596054202). The lead
decided it is **not a stop**: it fails toward asking more, never toward sending unasked. This brief resumes the
build. `briefs/20-chrome.md` and `briefs/20-parallel-start.md` still stand; where they differ from this brief, this
brief wins. The goal is unchanged: the note's whole **Now** part, built, with section 6's test groups 1 to 11 and 13
passing by name, twice on the final head.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## Where to read

As before: read these from `origin/main` with `git show origin/main:<path>` and treat them as the specification:
`AGENTS.md`, `briefs/20-chrome.md`, `briefs/19b-owner-state.md`, `docs/design/CONTROL.md` (section 6; sections 3,
4 and 7), `docs/control/FEATURES.md` (Chrome part), `docs/control/PLAN.md` and
`reviews/control-design/2026-11-08-RECHECK-29.md` to `-34.md`. Don't copy, add or change them on this branch. Read
code, the shared base and the reports on this branch. Start from your own `reviews/20-chrome/REPORT.md`.

## 1. The owner's own input (lead's decision, with its conditions)

- A submission is the owner's, and isn't held, **only** when it happens in the same browser task as a trusted input
  event that arrived while the extension had no dispatch of its own in flight. Everything else inside the short
  limit after Claude's input is held, as now. When it's unclear whose input it was, hold.
- **"In flight" must over-cover.** The extension marks its dispatch before sending it, and clears the mark only
  after the page has finished handling that input. Any trusted input in between counts as Claude's. A mark cleared
  too early would let Claude's own click pass as the owner's and its submission go unasked: that is the failure
  that matters.
- **The page can't read or forge the mark or the verdict.** They travel only through the extension's isolated world
  and messaging, never through a DOM event, attribute or global the page can see or write. If a check can't be
  made that way, hold.
- **Tests, all strict, each with the independent receiver's log as evidence** (keep run 42596054202's regression):
  - the owner presses Enter 130 ms after Claude's click: not held, one arrival;
  - Claude's click starts a delayed submit at 300 ms: held, zero arrivals before approval;
  - owner input during Claude's in-flight dispatch: held;
  - a page that forges any message or attribute it can reach: still held;
  - the owner's input starts a delayed page step inside the limit in a Claude tab: held, as the recorded expected
    case.
- In the report: a **JUDGMENT-CALL** for that last case, with a proposed qualification of section 6's line "Nothing
  he does in his tabs is held or checked". The lead takes it to the owner; don't edit design files.

## 2. Aresus is never a hard-coded address

- Remove `aresus.app` everywhere (`manifest.json`, `policy.js`, `policy.py` and any other place). It was a guess,
  and his real address is personal infrastructure that stays out of this public repo.
- The shipped fixed list holds only the vendor entries: `claude.ai`, `console.anthropic.com`, `platform.claude.com`,
  plus anything else section 6 names (Chrome's own settings, password and extension pages, and so on).
- His own entries (Aresus) are read from a **root-owned, owner-only image setting**, in the same style as the other
  owner-only lists. The extension's rules for them are built at run time (session `declarativeNetRequest` rules and
  dynamic content-script registration), not from the manifest.
- **Fail closed:** if the setting is missing, unreadable or unsafely owned, Chrome refuses reads and actions with a
  plain message. An existing empty list is allowed.
- Tests use a `.test` host for the Aresus-like entry, including a page on that host reached through each route of
  test group 6.
- In the report: the setting's path and format for the image brief (18c and `laptop-aresos`), for example under
  `/etc/aresos/control/`.

## 3. Every finding of your own two reviews

Fix all of them, with tests: `reviews/20-chrome/BUILD-REVIEW-1.md` findings 1 to 3 and
`reviews/20-chrome/BUILD-SECURITY-REVIEW-1.md` findings 1 to 6 (the owner-input ones are settled by part 1). In
particular, the three blocking ones:
- the page script's asking names must match the reader's (`aria-labelledby`, associated `<label>`), in both
  wrappers and the fallback;
- a read-only restriction added after preparation refuses the prepared operation before dispatch (sends, uploads,
  dialogs, trusted and resumed submissions);
- a password-exclusion failure recorded after preparation refuses before the extension rereads for binding.

**The base suite broke.** Control base run 42597065762 (head `6db0d953`) fails
`test_all_socket_peer_credentials_even_permissive_modes` for the `chrome`, `act` and `admin` sockets (one
`JSONDecodeError` on `chrome`, the rest `FAIL`); the same suite passes on the other packages' branches, so this
package's daemon change caused it. Fix the cause, never the assertion. The base, Mail and boundary workflows must
pass on the final head.

Name your own interim reviews `BUILD-*.md` from now on: `REVIEW.md` and `SECURITY-REVIEW.md` are reserved for the
package reviews that follow this run.

## 4. The rest of "Now"

Everything your report lists as unfinished Now work, among them: the full matrices of test groups 1 to 11 and 13 in
the container; all six adapters with their fixture sites; exact covered confirmations; the qualification workflow
and record as `briefs/20-chrome.md` describes them (stable and beta lookup, the build hash, the record, the
publisher with its own verification, attestation, delivery with its runtime callers, gating and conservative mode,
and all their tests); R1 to R3, round 27's rule and the warning lifecycle for Chrome's owner-visible state (pending
derived from committed context plus the live session); the storage fault sweep over all of Chrome's durable writes;
complete bounded paging; bounded upload retention; the measured view sizes on representative long pages; and tool
descriptions that promise only what is built.

**Publisher tests stay off the real data branch.** Runs from this branch never write to the real
`chrome-qualification` branch, never to `main`, never open real issues or pull requests. Test the publisher against a
repository inside the runner (or stubs for issues and pull requests). A test entry signed from this branch on the
real data branch would make every later `main` run refuse to publish.

## For 18d, later (don't build it now)

- Keep every Chrome asking action declared in the definitions, so its ask rule is generated, never hand-written.
- Keep each description's shared block (`SHARED`) liftable unchanged into the MCP `instructions`.
- Keep the owner-entry check for `chrome_submit_trusted` in one adapter method that 18d's `require_trusted_send(verb,
  op)` (returns `True` only for a matching owner entry) can call directly.

## Runs

About **50 runs of `control-chrome.yml`** for this stage in all; 9 are used. The base, Mail and boundary workflows
the pull request triggers alongside don't count, but push in batches. Record the count in the report; if it would
pass 50, say so in the report and stop.

## Stop rules

As `briefs/20-chrome.md`, for a guarantee of section 6 that fails toward sending unasked, twice, or differently from
the approval, or toward returning a password value. The owner-input case is decided above and is not a stop.

## Report

Rewrite `reviews/20-chrome/REPORT.md` for the finished stage, in the brief's format: the 13 groups by name with
test names, run IDs and log lines; the feature → tool → test mapping; the measured view sizes; the descriptions as
Claude reads them; the residuals; **PLAN-GAP**s and **JUDGMENT-CALL**s; what moving onto 18d and 19b will take; the
run count. Mark claims **run**, **read** or **assumed**.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/20-chrome`. Don't merge other branches. Commit in small steps and push
  this branch; the draft PR #27 exists. Never merge, never push to `main`, never force-push.
- Don't edit `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`, `README.md`, anything under `os/`
  or `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md` or `HANDOFF.md`.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No secrets, real addresses, account names, provider names or real sites; fixture hosts only (`.test`).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
