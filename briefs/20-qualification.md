# 20, qualification: the record, the workflow and delivery, checked against brief 20 and completed

A side build of stage "Now", running at the same time as the core build (`briefs/20-continue-3.md`, on
`pkg/20-chrome`) and the adapters build (`briefs/20-adapters.md`). The owner asked for parallel builds
(2026-11-09). `briefs/20-chrome.md`, `briefs/20-parallel-start.md`, `briefs/20-continue.md` and
`briefs/20-continue-2.md` stand for this area; where they differ, this brief wins.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## Where it starts

- Worktree `~/AresOS-20-qual`, branch `pkg/20-chrome-qual`, from the `pkg/20-chrome` head that carries this brief.
  Read the specification from `origin/main` with `git show` after `git fetch origin main`, as
  `briefs/20-continue.md` says under "Where to read".
- Start from `reviews/20-chrome/REPORT.md`: stable and beta lookup, the build plan, published-history and baseline
  verification, attestation and main-only publication, and runtime refresh exist. This build **checks them against
  every requirement** and completes what is missing; it doesn't rebuild what works.

## What to do

1. **A requirement map first,** committed as `reviews/20-chrome/QUALIFICATION.md`: every requirement of brief 20's
   "Qualifying each new Chrome stable" (tool build, trigger, result, publishing, delivery to the laptop, gating by
   major version, disabling, conservative mode) and **every test it lists** (failed adapter, failed core group, a
   failure on one patch with a later unrecorded patch, a later patch of a qualified major; each conservative-mode
   case; each delivery case; the build-hash cases; the beta/stable sequence; the publisher's refusal cases), each
   with the code that does it and the test that proves it, or **missing**.
2. **Complete every missing row**, with strict tests.
3. Keep the rails: runs from any branch other than `main` never write to the real `chrome-qualification` branch,
   never open real issues or pull requests (test the publisher against a repository inside the runner, or stubs).
   The attestation is verified with a well-tried verifier (Sigstore's library or `gh attestation verify`), never
   hand-written crypto. Use an attestation from one of this package's own workflow runs and altered copies of it as
   fixtures.
4. Conservative-mode browser cases need the browser harness: if they turn out to need the core build's unfinished
   parts (the Claude-tabs-only injection, the reload rules), test them at the service level here, list the browser
   cases in the report, and **don't build a stand-in** for the core's parts.

## Files

- **Yours:** `control/chrome/qualify.py`, `control/chrome/qualification.json`, `control/chrome/builds.json`,
  `control/chrome/build.py`, `control/aresos_control/chrome/qualification.py`, `control/chrome/ci/attestation.py`,
  their tests (`test_publisher.py`, `test_build.py`, new files), the qualification and publishing jobs of the
  workflow (you may move them into their own workflow file, `.github/workflows/control-chrome-qualification.yml`;
  in `control-chrome.yml` change only those jobs), `reviews/20-chrome/QUALIFICATION.md` and
  `QUALIFICATION-REPORT.md`.
- **Not yours (the core build changes them at the same time):** the extension, the service files other than
  `qualification.py`, `definitions.py`, `unicode_words.json`, the generated artifacts (`control/generated/`,
  `docs/control/TOOLS.md`), `control/settings/`, the base under `control/aresos_control/`, the core harness
  (`browser.mjs`, `fixture.mjs`, `matrices.mjs`, `prepare.mjs`, `run.sh`, `service.py`, `verdicts.mjs`) and the
  `fixtures` job of `control-chrome.yml`. If you need a change there, **don't make it**: list it exactly in the
  report; the package lead adds it when the builds are integrated.

## Report

`reviews/20-chrome/QUALIFICATION-REPORT.md` (not `REPORT.md`, which the core build owns): the requirement map's
final state, what you added, the tests by name with run IDs and log lines, what you need in shared files, the
browser cases left for the integrated head, **PLAN-GAP**s and **JUDGMENT-CALL**s. Mark claims **run**, **read** or
**assumed**. Interim reviews you run are named `BUILD-QUAL-*.md`.

## Runs and PR

- About **25** workflow runs on this branch; push in batches and cancel superseded runs. Record the count in the
  report; if it would pass 25, say so and stop.
- Open a **draft PR into `pkg/20-chrome`** (`gh pr create --draft --base pkg/20-chrome`), never into `main`. The
  package lead merges it.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/20-chrome-qual`. Don't merge other branches. Commit in small steps and
  push this branch. Never merge, never push to `main`, `pkg/20-chrome` or `chrome-qualification`, never
  force-push.
- Don't edit `docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`, `README.md`, anything under `os/`
  or `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md` or `HANDOFF.md`.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No secrets, real addresses, account names, provider names or real sites; fixture hosts only (`.test`).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
