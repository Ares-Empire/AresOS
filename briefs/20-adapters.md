# 20, adapters: the six site adapters, checked against brief 20 and completed

A side build of stage "Now", running at the same time as the core build (`briefs/20-continue-3.md`, on
`pkg/20-chrome`) and the qualification build (`briefs/20-qualification.md`). The owner asked for parallel builds
(2026-11-09). `briefs/20-chrome.md`, `briefs/20-parallel-start.md`, `briefs/20-continue.md` and
`briefs/20-continue-2.md` stand for this area; where they differ, this brief wins.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## Where it starts

- Worktree `~/AresOS-20-adapters`, branch `pkg/20-chrome-adapters`, from the `pkg/20-chrome` head that carries this
  brief. Read the specification from `origin/main` with `git show` after `git fetch origin main`, as
  `briefs/20-continue.md` says under "Where to read".
- Start from `reviews/20-chrome/REPORT.md`: the six adapters exist and test group 10 passes on the fixtures (runs
  42664895844 and 42664908151). This build **checks them against every requirement** and completes what is
  missing; it doesn't rebuild what works.

## What to do

1. **A requirement map first,** committed as `reviews/20-chrome/ADAPTERS.md`: every adapter requirement of brief 20
   (item 6 and the adapter parts of items 5 and 6), section 6 ("Site adapters", "Confirmations", "Don't ask
   again", the actions table, test groups 4, 10 and 11) and the adapter rows of `docs/control/FEATURES.md` (Chrome
   part), each with the code that does it and the test that proves it on the fixtures, or **missing**. Per
   adapter: Gmail (account, To, Cc, Bcc, subject, text, attachments; Send and Ctrl+Enter; shortcuts that delete or
   send; exact-recipient "don't ask again"; two compose windows), WhatsApp Web (per message, chat and text as the
   page shows them; opening a chat and typing free; never "don't ask again"), GitHub (comments, reviews, merges,
   closing, deleting branches, tags and repositories, settings changes; its confirmations named in advance and
   matched exactly), his bank read-only (reading, scrolling and links only; host list empty in the shipped
   definition, owner-supplied), Gemini ("ask a question" named with its text, eligible for "don't ask again" per
   account; deleting or sharing a chat asks), Deezer (playback and library additions free; removing, deleting,
   posting, sharing or paying asks). An unrecognised page falls back to the generic rules; an adapter switched off
   by qualification falls back too; conservative mode turns adapters off.
2. **Complete every missing row** with its fixture and a strict test (the independent receiver's log as evidence,
   zero arrivals before approval, one after, none on a repeat), and every mismatch case of a named confirmation.
3. Keep the static test of the shipped host lists and the fixed list.

## Files

- **Yours:** `control/aresos_control/chrome/sites.py`; new fixture pages and adapter test files (put them in new
  files, for example `control/chrome/ci/sites/` and `control/chrome_tests/test_sites*.py`); `reviews/20-chrome/
  ADAPTERS.md` and `ADAPTERS-REPORT.md`.
- **Not yours (the core build changes them at the same time):** the extension (`control/chrome/extension/`), the
  service files other than `sites.py`, `definitions.py`, `unicode_words.json`, the generated artifacts
  (`control/generated/`, `docs/control/TOOLS.md`), `control/settings/`, the base under `control/aresos_control/`,
  and the core harness (`browser.mjs`, `fixture.mjs`, `matrices.mjs`, `prepare.mjs`, `run.sh`, `service.py`,
  `verdicts.mjs`). If your tests need a hook in a harness file, keep it to the smallest registration (a line that
  loads your new file) and name it in the report. If you need a change in a shared file (a new action kind, a word,
  a definition field), **don't make it**: list it exactly in the report; the package lead adds it when the builds
  are integrated.
- If the work turns out to need the core build's unfinished parts (the Claude-tabs-only injection, the reload
  rules, the owner-input rule), **stop and report** rather than building a stand-in.

## Report

`reviews/20-chrome/ADAPTERS-REPORT.md` (not `REPORT.md`, which the core build owns): the requirement map's final
state, what you added, the tests by name with run IDs and log lines, what you need in shared files, any harness
hook, **PLAN-GAP**s and **JUDGMENT-CALL**s. Mark claims **run**, **read** or **assumed**. Interim reviews you run
are named `BUILD-ADAPTERS-*.md`.

## Runs and PR

- About **25** runs of `control-chrome.yml` on this branch; push in batches and cancel superseded runs. Record the
  count in the report; if it would pass 25, say so and stop.
- Open a **draft PR into `pkg/20-chrome`** (`gh pr create --draft --base pkg/20-chrome`), never into `main`. The
  package lead merges it.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/20-chrome-adapters`. Don't merge other branches. Commit in small
  steps and push this branch. Never merge, never push to `main` or `pkg/20-chrome`, never force-push.
- Don't edit `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`, `README.md`, anything under `os/`
  or `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md` or `HANDOFF.md`.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No secrets, real addresses, account names, provider names or real sites; fixture hosts only (`.test`). Never load
  a real site or use a real account.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
