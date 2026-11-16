# 20, main fix: the first runs on main after PR #27

PR #27 (Chrome) merged on 2026-11-14 as `09cedc84`. On that commit, `Control boundary` passed on main, but two
workflows failed:

- `Control Chrome` run 43647781438: only `latency (audit)` failed, step "Require lead ceilings and reject paired
  latency regressions". In `history-4000`, every call's p95 was over its ceiling, while the medians were fine. For
  example, `approval_to_done` was 665 / 1,172 ms against 700 / 850, and `navigate` 66 / 332 against 100 / 150.
  `latency (plain)` passed in the same run. Both pull-request runs of the final head `d25ccbd3` passed every latency
  gate.
- `Control Chrome qualification` run 43647781498: four jobs that run only on main had never run before.
  - `qualification-pairs` failed in "Full Python file partition": `test_state_crashes` child processes fail with
    `ModuleNotFoundError: No module named 'test_engine'` in the runtime layout.
  - `delivery-attestation` failed because `qualification.verify`'s anonymous GitHub API fetch got
    `HTTP 403: rate limit exceeded` on the shared runner.
  - `qualification-combine` and `qualification-publish` failed after those, in "Require complete browser Python and
    native evidence" and "Verify the held attestation and shipped baseline before appending".

The product still fails closed: without a published qualification record Chrome stays in conservative mode, and
none of this code is on the owner's laptop yet. Main is red, though, and the paths that only run on main were never
exercised before the merge. This brief makes main green and makes sure that can't happen again.

**Rules.** `briefs/20-final-fixes.md` still applies: its rules, the files it says not to touch, no persistent
extension storage, never naming the owner's mail provider, repo-relative paths, no force-push, no `--no-verify`.
Agents never push to main. Work on `pkg/20-main-fix` and open a draft PR. **Never start, read or touch Chrome,
Chromium or any browser profile on this Mac.** Browser tests run only on GitHub's Linux runners. Locally, run only
plain-Python and Node tests that start no browser. The ceilings, the sample counts (60 now, 20 for the old runtime)
and the "median or p95" rule stay as they are. A fix that removes a feature, or changes the trust model of the
qualification records, stops and goes to the lead first.

## H1. The qualification layout imports its test modules

Find why `test_state_crashes`'s child processes can't import `test_engine` in `qualification-pairs`' runtime
layout, while the same tests pass in `control-chrome.yml`'s Python shards. Fix the layout or the child's import
path. Don't skip or move tests out of the partition: "Full Python file partition" must still cover every file.

## H2. The attestation check doesn't depend on GitHub's anonymous quota

The product's anonymous fetch stays. It exists so that public delivery works without the owner's GitHub login, and
the API response is never trusted evidence: `gh attestation verify` checks the signature and the identity.

1. **CI.** Fetch the real bundle with the job's token (for example `gh api` with `GITHUB_TOKEN`), then run the full
   verify, and the altered-copy tests, through `verify(..., bundle=...)`. Test the anonymous fetch path itself
   without the network: a local stub server or a recorded response that feeds the same code. A token must never
   reach the product's code path. Without the real network, a 403 can't fail the job by chance.
2. **Product on the laptop.** Check what a 403 or 429 rate limit, a timeout or a 5xx does in the service's daily
   fetch: the held record must stay, the service must keep running, and the next attempt must come later, never in
   a tight loop. Add tests for each.

## H3. Publish and combine on the first run

Once H1 and H2 pass, check whether `qualification-combine` and `qualification-publish` pass on their own merits.
Pay special attention to "Verify the held attestation and shipped baseline before appending" on the first run on
main, when no record has been published yet. If the first publish can't start by design, give it an explicit,
reviewed first-record path. It must never invent a qualification and must never trust an unattested record.

## H4. Main-only paths run before the merge

The root cause of this failure class is that four jobs had never run before they ran on main. Give every main-only
job a pull-request mode that runs all of its steps except the write that must happen only on main (publishing or
appending the record). That includes the real verification of a real bundle from the PR run itself, if GitHub
allows attesting there; otherwise, the nearest real check. Publishing stays main-only. Add a check that fails when a
job is main-only without a PR mode.

## H5. The `latency (audit)` tail on main

Diagnose run 43647781438's `history-4000` tail from its artifacts:

- the per-sample timings and whether the slow samples are periodic;
- what the service and Chrome were doing in those samples;
- whether anything runs differently on main, for example the qualification record refresh or a network fetch
  triggered by `GITHUB_REF_NAME == main`;
- whether the old runtime's samples on the same runner show the same stalls.

If something specific to main causes it, fix that. If it's the runner, show the evidence and record it in the
report. Don't widen the ceilings or change the sample counts.

## Runs and order

- **Order:** diagnosis first, for H1, H2, H3 and H5, committed to `reviews/20-main-fix/PROGRESS.md`. Then fix in
  that order. Each fix gets a test that fails without it and a removal probe in the mutation audit, as in brief 20.
- **Run limits:** `control-chrome.yml` has about 9 runs left in the budget (271 of about 280); this brief may use at
  most 2 of them. `control-chrome-qualification.yml` runs on the branch, dispatched or on the PR, at most 4. Stop
  and report before you go over either limit.
- **Before "ready":**
  - the full local preflight;
  - the qualification workflow green on the PR, in its new PR mode for the main-only jobs;
  - `Control Chrome` green on the PR;
  - a fresh package review and a fresh security review. The security review is for H2 and H3, the trust path.

The lead merges.
