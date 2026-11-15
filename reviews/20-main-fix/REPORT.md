# Brief 20 main fix: report

Brief `briefs/20-main-fix.md`, branch `pkg/20-main-fix`, PR #68. Builders: steps 1 and 2 Claude Fable 5.2, steps 3 to 5
Claude Opus 5.5 (2026-11-15). Lead: `mac-aresos-control`. Claude builders can't write `REPORT.md`, so the lead made this
report from their `PROGRESS.md`. This first part is the summary. The builders' step-by-step record follows it unchanged,
newest step first.

## Outcome

Main went red after PR #27 because four jobs that only ran on main had never run before, plus one latency tail. All of
it is fixed or explained, and every job now runs on pull requests too.

- **H1, the qualification layout imports its test modules.** `test_state_crashes`' child process now uses absolute
  paths built from `__file__`, runs with the temporary root as its working directory and a clean `PYTHONPATH`. "Full
  Python file partition" still covers every file.
- **H2, no dependence on GitHub's anonymous quota in CI.** CI fetches the real bundle with the job's token and runs
  the product's unchanged anonymous `verify()` through a recorded-response opener. That opener answers only the
  product's own URL and refuses any request that carries a token. The product's fetch is unchanged: the anonymous API
  answer is never evidence, and `gh attestation verify` checks signature and identity under main's policy. New
  product tests cover 403, 429, 5xx and timeouts: the held record stays, the service keeps running, and the next try
  comes a day later.
- **H3, the first publish.** With no data branch on origin, `prepare` takes the first-record path: the shipped
  baseline plus this run's entries, still append-only. `publish` verifies the candidate against the bundle the attest
  step just made. There is no unattested path.
- **H4, no main-only jobs.**
  - Every job runs on pull requests and branch dispatches. Only the two steps that write to GitHub are main-only, and a
    test allows exactly those (`control/chrome_tests/workflow_steps.py` parses every YAML form of `if:` and `run:`).
  - In pull-request mode, publish goes to a local bare remote.
  - PR bundles attest on `refs/pull/N/merge`, and a CI case proves main's policy refuses them.
  - `qualify.py` refuses to publish to origin or notify off main, and refuses `--remote`, `--ref` and `--held-bundle`
    for origin.
- **H5, the `latency (audit)` tail on main.** The cause is the runner's disk: synchronous store writes (journal fsync
  and SQLite commits) stall on it. Nothing in the code differs on main. Changes:
  - CI-only stages `store_write` and `journal_fsync` now show where a tail sits;
  - the audit profile's two harness log streams moved to a tmpfs.

  The ceilings, the sample counts and the median-or-p95 rule are unchanged.
- **H6, the `typed-early` popup row is deterministic.** It opens a same-origin `/popup-gate` first document and holds
  no document, which avoids the `Page.enable` deadlock.
- **Review fixes:**
  - **F1:** off main, the head build is qualified again.
  - **F2:** `gh api`'s 404 is tolerated, with retries.
  - **F3:** off main, the repeat check is one-way. A pull request that does worse than the held record fails. One
    that does better warns and keeps the held entry. On main, any conflicting repeat still fails.
  - **Security NOTEs 1 to 4:** the refusal cases count only their own named refusal, and any other exception fails the
    job.

## Final runs (head `bf0bf6e4`, code `496018a5`)

- **Local preflight on `496018a5`:** 335 Python and 428 Node tests, and 523 removal mutations rejected with every
  baseline passing (`records/final-local-496018a5.json`). No browser was started on the Mac.
- **`Control Chrome qualification` 43687610978** (pull request, run 5 of 6): 34 of 34 jobs green. The PR-mode publish
  reached only the local bare remote, and main's policy refused the bundle attested on `refs/pull/68/merge`.
- **`Control Chrome` 43687610984** (pull request, the brief's run 3 of 3): 27 of 28 jobs green on the first attempt.
  Only `latency (plain)` failed, on lead-ceiling misses with no regression against the reference. The lead re-ran that
  one job (attempt 2, job 132750730195): green, with `navigate` p95 51 / 54 / 69 ms and `free_click` 582 / 586 / 596 ms
  (fresh / history-1000 / history-4000) on a runner whose slowdown factor was 1.24 to 1.27. `latency (audit)` passed
  in both attempts.

### The `latency (plain)` tail on attempt 1 (the lead's attribution)

The runtime is identical to step 4's green run 43678600076: none of step 5's files is a runtime build input. The
medians stayed within about 5 ms of step 4. Only the tail rose: p95 for `navigate` was 212 ms fresh and 226 ms at
history-4000, against 150; `free_click` at history-4000 was 785 ms against 750. Step 4's p95s were 38, 53 and 584.

H5's stages (`latency-service.jsonl` in artifact `chrome-latency-43687610984-1-current-plain`) put every slow sample's
extra time inside the service's store write. The bridge and the extension were normal:

| Sample | Service total | Store write | Journal fsync | Bridge round trip |
|---|---|---|---|---|
| navigate, fresh 15 | 372 | 341 | 1 | 28 |
| navigate, fresh 14 | 255 | 222 | 1 | 30 |
| navigate, history-4000 52 | 293 | 252 | 245 | 25 |
| navigate, history-4000 17 | 242 | 198 | 1 | 28 |
| free_click, fresh 16 | 1,013 | 452 | 442 | 558 |
| free_click, history-4000 17 | 849 | 281 | 33 | 552 |

All values are in ms. The medians of the service time outside the bridge were 11 to 30 ms. Where `journal_fsync` is
small, the stall is in SQLite's own commit sync on the same disk.

So H5's finding holds, now measured directly: the gate's p95 is exposed to the shared runner's disk sync latency, on
the plain profile too. The product makes 2 to 10 fsyncs per writing call (H5's count), and on a local SSD each returns in about
0.03 ms (H5's measurement on the Mac). Changing that exposure (for example a store on tmpfs plus a separate fsync budget, or measuring the
sync stages apart from the ceilings) changes what the gate measures. It is left to the tools lead, `linux-tools`
(`docs/control/TOOLS-HANDOFF.md`).

## Reviews

Every review was by a fresh agent that didn't build the code.

| File | Reviewer | Range | Verdict |
|---|---|---|---|
| `REVIEW-1.md` | package, Claude Opus | to `34c2e888` | FIX: F1, F2 (fixed in step 4) |
| `SECURITY-1.md` | security, Claude Fable | to `34c2e888` | SAFE, NOTEs 1 to 4 (folded in, steps 3 and 4) |
| `REVIEW-RECHECK-2.md` | package | `34c2e888` to `5bc7e4aa` | FIX: F3 (fixed in step 5) |
| `SECURITY-RECHECK-2.md` | security | `34c2e888` to `5bc7e4aa` | SAFE, NOTE on any-exception refusals (fixed in step 5) |
| `REVIEW-RECHECK-3.md` | package | `5bc7e4aa` to `bf0bf6e4` | SAFE |
| `SECURITY-RECHECK-3.md` | security | `5bc7e4aa` to `bf0bf6e4` | SAFE, one optional NOTE |

## Left open, none blocking

- **Fork pull requests** (package review, (d)): forks get no `id-token`, so `delivery-attestation` and the publish job
  fail on them. They fail closed, and nothing is published from a fork.
- **First-record path without the repeat check** (both re-checks agree it's safe): with no data branch on origin, a
  duplicate pair fails closed with "Repeated qualification key". It is reachable only after someone deletes the data
  branch. If that error ever appears, that is the cause.
- **`::warning::` on stdout** (security re-check 3, optional): `qualify.py` about :248. It is harmless because
  `prepare`'s output is the candidate file, but stderr would be safer if `prepare` is ever piped.
- **Latency gate and the runner's disk:** see above. It belongs to `linux-tools`.

**Runs used:** `Control Chrome` 3 runs plus one re-run of a single job (43663583962, 43678600076, 43687610984);
qualification 5 of 6 (two branch dispatches, three pull-request runs).

---

# The builders' record

Builder step 1 (Claude Fable 5.2, 2026-11-15): diagnoses and the H1 fix. Builder step 2 (Claude Fable 5.2, 2026-11-15):
H2, H3, H4, H5 built on the lead's decisions. Builder step 3 (Claude Opus 5.5, 2026-11-15): H6 and security NOTEs 1–3.
Builder step 4 (Claude Opus 5.5, 2026-11-15): the package review's F1 and F2, security NOTE 4, review NOTEs (a) to (c),
the altered-subject refusal, the final preflight and the final runs. Builder step 5 (Claude Opus 5.5, 2026-11-15): the
package re-check's F3 and the security re-check's first NOTE, the preflight and the last pull-request runs. Brief:
`briefs/20-main-fix.md`. Branch `pkg/20-main-fix`.

## Handover (step 5)

Builder step 5 (Claude Opus 5.5, 2026-11-15): the two items the lead scoped from the re-checks, then the one final
commit that starts the pull-request runs.
- **Done:** F3 (off main the repeat check is one-way: a worse repeat fails the PR, a better one keeps the held entry,
  warns and goes on; main unchanged) and the security re-check's first NOTE (the rollback and publisher cases of
  `attestation.py` count only their own named refusal). Code `496018a5`; details under "Step 5: what was built".
- **Local:** full preflight on `496018a5` green (**335 Python, 428 Node, 523 removal mutations rejected**, 11 new
  and 1 re-pointed); record `reviews/20-main-fix/records/final-local-496018a5.json`.
- **Runs:** the commit that adds this section has no `[skip ci]`. It starts qualification run 5 of 6 and `Control
  Chrome` run 3 (one more than the brief's two, allowed by the lead). Their IDs and results are in the step-5 report to
  the lead. Nothing is committed after them, so the PR head stays the commit they checked.
- **Left:** **ready for the lead's re-check.**
- **Note (not blocking, unchanged):** `prepare`'s first-record path (no data branch on origin) appends this run's
  entries to main's shipped record without the repeat check, so a duplicate pair refuses (`Repeated qualification
  key`, fail-closed). It is reachable only when main's shipped record holds the head build's pair while origin has
  no data branch, that is after someone deletes the data branch. F3's scope didn't cover it.

## Step 5: what was built (`496018a5`)

**F3. One-way repeat check off main** (`qualify.py`, `test_publisher.py`).
- `compared(held, repeat)` names each group `core.<name>` or `adapters.<name>` and returns the worse ones (true held,
  false here) and the better ones (false held, true here).
- `prepare(..., on_main=True)`: strict by default; the CLI passes its `on_main` (`GITHUB_REF == refs/heads/main`, the
  same value the publication guard and `requalify_head` use).
  - **On main:** any repeat with another verdict raises exactly as before, with the same message.
  - **Off main, worse** (at least one group true held and false here, mixed included): raises `Conflicting repeat for
    an immutable qualification pair: this run fails <groups>, which the held record passes; publish nothing`. No
    candidate is written.
  - **Off main, better** (nothing true→false): prints one `::warning::` line with the improved groups, the build (12
    characters), channel and version, and says the held entry stays and those groups stay disabled. The candidate
    keeps the held entry unchanged; the PR's differing entry is dropped. New pairs are appended as usual, and an
    identical repeat is skipped without a warning, as before.
  - Only the CLI's data-branch path passes `on_main`. The direct calls in `attestation.py` and the older unit tests
    keep the strict default.
- Tests replace `test_off_main_an_identical_repeat_is_skipped_and_a_conflicting_one_fails_the_pull_request`. Each one
  runs the real `prepare` CLI against a local origin whose data branch holds the pair, with a new beta pair in the
  same run (helper `Publisher.repeat`; the held record is verified from its bundle list first):
  - `..._an_identical_repeat_is_skipped_and_never_carries_main_s_bytes`: PR indented, main compact, no warning.
  - `..._a_worse_repeat_fails_the_pull_request_and_writes_no_candidate`: a core group and an adapter group alone;
    the error names the group; no candidate.
  - `..._a_better_repeat_warns_keeps_the_held_entry_and_the_rest_proceeds`: held all-false (main's failed shard)
    and held with two groups failed; exactly one warning naming exactly the improved groups; the candidate is the
    held entry unchanged plus the new pair, indented.
  - `..._a_mixed_repeat_fails_the_pull_request`: two core groups better, one adapter worse; the error names only
    the worse group.
  - `test_on_main_any_conflicting_repeat_raises`: better and worse both raise the unchanged message; no candidate.
- Probes (all rejected, each for its stated reason; `.work/20-main-fix/step5-mutations.json`):
  - `mainfix-f1-conflicting-repeat-relaxed`, re-pointed: a worse repeat on a PR is allowed.
  - `mainfix-f3-adapter-regression-ignored`: only core groups are compared.
  - `mainfix-f3-mixed-repeat-passes`: worse counts only when nothing is better.
  - `mainfix-f3-better-repeat-overwrites-held`: a better repeat replaces the held entry.
  - `mainfix-f3-better-repeat-fails-off-main`: F3 itself, the two-way check off main.
  - `mainfix-f3-better-repeat-silent`: no `::warning::`.
  - `mainfix-f3-better-repeat-kept-on-main`: main becomes one-way too.
  - `mainfix-f3-prepare-strict-everywhere`: the CLI doesn't pass `on_main`.

**Security re-check NOTE: named refusals for the rollback and publisher cases** (`attestation.py`,
`test_qualification.py`).
- `expected_refusal(action, reason)` generalises step 3's rule:
  - gh's `CalledProcessError` counts only when its stderr names `reason`;
  - `Refused` counts only when its code is `reason` (`ROLLBACK = 'qualification_rollback'`), and any other code is
    raised again;
  - any other exception propagates, and an accepted record fails the case.
  - `refused()` now calls it, so the verifier cases behave as before.
- `rollback_cases(...)`: the two held-history cases ("dropped held entry", "changed held entry") call `refused(...,
  ROLLBACK, held)`, so the held record must also be unchanged.
- `publisher_cases(...)` first verifies the genuine held record, then:
  - "unsigned inserted entry" expects gh's named policy failure. Its bytes are no longer the signed ones, the same
    path as the altered subject, which run 43678600028 logged as `verifying with issuer "sigstore.dev"`.
  - "non-append-only shipped baseline" expects `ROLLBACK`. It now writes the genuine signed bytes, so verification
    passes and only the baseline check can refuse it. Before, it wrote `json.dumps(candidate)`, which equals the
    signed bytes only because both CI records happen to serialize that way (checked: the synthetic record and the
    retained fixture both do). The case no longer depends on that.
- Log lines name the reason, e.g. `QUALIFICATION DELIVERY dropped held entry refused (qualification_rollback) after
  real verification PASS` and `QUALIFICATION PUBLISHER unsigned inserted entry refused (verifying with issuer
  "sigstore.dev"); no write, issue stubbed PASS`.
- Tests:
  - `RecordingOpener.test_a_rollback_case_counts_only_as_the_append_only_refusal` (real `Qualification` and `Store`,
    stand-in verifier): with a passing verifier both cases pass. A timeout, gh missing and
    `Refused('qualification_invalid')` propagate. A gh refusal fails, naming the case.
  - `RecordingOpener.test_the_publisher_cases_count_each_refusal_only_by_its_own_reason`: a stand-in that verifies
    only the signed bytes passes both cases with their reasons. Each of these fails the job or propagates: an
    inserted entry that is accepted, refused by a timeout or by another gh failure; a baseline case refused by
    verification, by a timeout or by "gh too old".
- Probes (all rejected): `mainfix-sec-rollback-any-exception` (the old catch-all), `mainfix-sec-refusal-code-unchecked`
  (any `Refused` code counts), `mainfix-sec-publisher-any-exception` (the old catch-all),
  `mainfix-sec-publisher-baseline-case-unsigned-bytes` (the baseline case writes re-serialized bytes again).
- **Not provable on this Mac:** gh here is 2.94 and `verify()` requires 2.102, so the real cases run only in
  `delivery-attestation`. Expected there: the log lines above for the run's own record and for the retained fixture.

**Local verification (step 5).** Full preflight on `496018a5` (`reviews/20-main-fix/records/final-local-496018a5.json`,
step 4's driver unchanged): **335 Python** (shards 68/57/49/161; the Linux-only socket case skipped on the Mac), **428
Node**, **523 removal mutations rejected** with every baseline passing (512 + 11 new; the re-pointed probe replaces
its old self), generator check, `git diff --check`, and the service unit byte-identical to `8b7e799c`. The
touched suites (`test_build`, `test_publisher`, `test_qualification`, `test_qualification_service`: 75 tests) also pass
from a foreign working directory with no `PYTHONPATH`. The 26 `mainfix-f1-`/`-f3-`/`-sec-` probes were also run on their
own (26 of 26). No browser was started.

## Handover (step 4)

Builder step 4 (Claude Opus 5.5, 2026-11-15): everything the lead scoped for step 4, then the one final set of runs.
- **Done:** F1 (off main the plan qualifies the head build again; identical repeat skipped, conflicting repeat fails
  the PR; off-main candidates never carry main's bytes), security NOTE 4 (read-only token step fetches the held
  record's bundle list; the token-free PR publish seeds origin's data branch by `git fetch` and verifies the held
  record from that file under main's policy), F2 (the recording survives the 404, bounded backoff, clear failure;
  404 modelled in `bundle_from_api`, `attestation.py` and tests), NOTEs (a) to (c), the altered-subject refusal.
  Code `5de22178`; details under "Step 4: what was built".
- **Local:** full preflight on `5de22178` green (**329 Python, 428 Node, 512 removal mutations rejected**, 21 new);
  record `reviews/20-main-fix/records/final-local-5de22178.json`.
- **Runs (final push `7b015a7a`, both green):** qualification **43678600028** (run 4 of 6), 34 of 34 jobs; `Control
  Chrome` **43678600076** (run 2 of 2), 28 of 28 jobs. `recheck2` passed in both installs and both repeats, and
  `typed-early` recorded `document_start` (answering `stale_reference`) in all four: H6's first browser proof. Details
  under "Step 4: runs". The lead's hold on this push reached me after it had gone out; the lead then said to let both
  runs finish. No further run started.
- **Decision for the lead (not blocking, reversible):** off main, `prepare` writes the candidate indented instead of
  compact, so a pull request never attests the exact bytes main published (with F1 an identical repeat would
  otherwise add one attestation per PR run to the real record's listing, which the laptop and main read one page of
  100 and at most 4 MiB of). Main's bytes are unchanged. The alternative is to skip attest and publish off main when
  nothing is new, which would also skip the second-run path NOTE 4 asks for.
- **Left:** **ready for the lead's re-check.** The opener-row flake on another PR (run 43671248371) is being diagnosed
  separately, so this step didn't touch it. That row passed in all four `recheck2` shards here.

## Step 4: what was built (`5de22178`)

**F1. Off main the plan qualifies the head build again** (`qualify.py`, workflow, `test_publisher.py`).
- `plan(..., requalify_head=False)`: a pair the held record covers is skipped as before, except the head build's
  pairs when `requalify_head` is set. The CLI sets it from the run's ref (`GITHUB_REF != refs/heads/main`, the same
  `on_main` the publication guard uses), so pull requests and branch runs qualify the head build on stable even after
  main has published it; main's plan is unchanged (shipped builds stay skipped everywhere).
- `prepare` is unchanged: an identical repeat adds nothing, a conflicting repeat (same build, version and channel,
  another verdict) raises `Conflicting repeat for an immutable qualification pair; publish nothing`, so the PR's
  publish job fails and writes no candidate. Never relaxed, never overwritten. (Step 5's F3 makes the check one-way
  off main: only a worse repeat fails; see "Step 5: what was built".)
- **Added (my call, see "Decision for the lead"):** off main the candidate is written indented
  (`serialized(record, on_main)`); main writes the compact bytes as before. Without it an identical repeat would make
  the PR attest exactly the bytes main published, and every such PR run would add one more attestation to the listing
  the laptop and main read for the real record (one page of 100, at most `DELIVERY_LIMIT` bytes). Content and every
  check are unchanged; the PR-mode check compares JSON, not bytes.
- Tests: `Publisher.test_off_main_the_plan_qualifies_the_head_build_again_while_main_skips_what_is_held` (unit, and the
  real `plan` CLI against a local origin whose data branch holds the head build: main → no rows, `refs/pull/9/merge`
  and a branch ref → the head build's stable pair twice); `Publisher.test_off_main_an_identical_repeat_is_skipped_and_a_conflicting_one_fails_the_pull_request`
  (the real `prepare` CLI against a local origin with a data branch: identical repeat on a PR → candidate equals the
  held record, indented; on main → the compact bytes; conflicting repeat on a PR → `ValueError`, no candidate).

**Security NOTE 4. The PR-mode publish runs the second-run path** (workflow, `qualify.py`, `test_publisher.py`).
- New read-only step "Fetch the held record's attestations for the pull-request publish (read only)" (PR-mode
  condition, `GH_TOKEN`, runs only `qualify.py held-bundles --output .work/held-bundles.jsonl`): when
  `refs/remotes/origin/chrome-qualification` exists it takes that record's exact bytes (the data branch `prepare` just
  fetched and extended) and writes its bundle list through `bundle_from_api` (same serialization and bound as the
  product); without a data branch it writes nothing and says so.
- The PR-mode publish step stays token-free. It seeds `.work/publish-remote.git` with `origin/main` and, when it
  exists, `origin/chrome-qualification`, both by `git fetch "$PWD"` (no `git push` in any `run:`), and runs
  `publish ... --held-bundle .work/held-bundles.jsonl`. `--held-bundle` makes the held verifier `held_from_file`:
  `verify(path, bundle=<file>)` with the unchanged main policy; with a data branch and no file it refuses. The CLI
  refuses `--held-bundle` for a publication to origin (main keeps `verify_held` through `gh api`).
- Tests run **both steps as written** (`workflow_steps.StepRunner`: the step's `run:` body under `bash -e`, its own
  `env:` applied, stand-in `gh` and `sleep` on `PATH`, no network) against local repositories shaped like the publish
  job's checkout: `PullRequestPublish.test_without_a_data_branch_...` (read step writes nothing; publish verifies only
  the fresh bundle on the PR ref and cuts the data branch from main), `..._with_a_data_branch_the_held_record_is_verified_from_the_read_steps_list_under_main_policy_then_appended`
  (read step: one `gh api` call for the held record's digest, with the token; publish: the candidate on the PR ref and
  the held record's exact bytes under `refs/heads/main` from `.work/held-bundles.jsonl`, no `gh api`, no token, the
  local data branch appended to the seeded commit, `main` unmoved; a new pair and an identical repeat),
  `..._a_held_record_without_a_listing_or_a_bundle_list_refuses_and_nothing_moves` (API 404 → the read step fails;
  publish without the file fails, data branch unmoved). The step-3 "no `GH_TOKEN`" check now reads the parsed step:
  no token key or `github.token`/`secrets.` value in the publish step, and the read step is exactly its condition,
  `env.GH_TOKEN` and its one command.

**F2. The `gh api` recording survives the 404** (workflow, `attestation.py`, `qualify.py`, tests).
- The recording is its own step "Record this run's attestation API response with the job's token" (`GH_TOKEN` only
  there): six attempts, `gh api ... > .work/attestation/api-response.json || true`, the response decides (a non-empty
  `attestations` list), 10 s between attempts (none after the last), then
  `::error::The attestation API listed no attestation for this run's record after 6 attempts over 50 s ...` and exit 1.
  "Retain this workflow's real Sigstore bundle and test altered copies" no longer holds a token (it verifies only from
  bundles; the minimal-environment case already ran token-free in run 3).
- `bundle_from_api` refuses gh's `(HTTP 404)` like an empty list (`NOT_LISTED`); any other gh failure propagates.
  `attestation.py`: `listed()` reads a recording (404 body, empty list, empty file, other shapes → nothing), and the
  anonymous path's negative cases add "nothing listed 404" beside the empty list.
- Tests: `Workflow.test_the_api_recording_survives_the_404_of_a_not_yet_listed_attestation` runs the step as written:
  404, 404, listed → passes after 3 calls and 2 sleeps; empty list then listed; no answer then listed; six 404s →
  exit 1 with the message, 6 calls, 5 sleeps. `RecordingOpener.test_a_recorded_404_an_empty_list_or_no_json_lists_nothing`;
  the product's `verify()` through the recording refuses 403, **404**, 429, 500 and the empty list; the
  `bundle_from_api` cases in `test_held_record_bundle_comes_from_gh_api_with_the_job_login`.

**NOTE (a). Conditions and run bodies however written** (`control/chrome_tests/workflow_steps.py`, new helper, no test
file added). PyYAML is not in the test environment (not importable here), so a careful matcher follows the block
structure by indentation (a `- ` item opens a mapping) and joins each value's continuation: `- if:` as a step's
first key, `if: >-`/`|` with the condition below, `if:` with the value on the next line, a plain scalar continued on
deeper lines; the same for `run:`. `workflow_conditions` and `workflow_runs` now come from it; on both real workflows
they find exactly what the old matchers found (17/17 and 11/11 conditions, 17/17 and 9/9 run bodies). Conditions
that start with a YAML alias or anchor fail the test. Test `Workflow.test_conditions_and_run_bodies_are_found_however_written`.

**NOTE (b).** The publisher's group is `${{ github.ref == 'refs/heads/main' && 'chrome-qualification-publisher' ||
format('chrome-qualification-publisher-{0}', github.ref) }}`: main's group is exactly the old one, every other ref has
its own. Test `Workflow.test_the_publisher_keeps_main_s_group_and_gives_every_other_ref_its_own`.

**NOTE (c).** `bundle_url` (the expired signed link) is trimmed from `42687597384/api-response.json` (12,025 bytes;
`bundle`, `initiator`, `repository_id` kept; README says so). The replay tests pass, and the trimmed list still
verifies with the real `gh attestation verify` on this Mac (branch policy exit 0; main policy exit 1, `expected
SourceRepositoryRef to be refs/heads/main`). Test `RecordingOpener.test_the_retained_fixture_holds_no_signed_link`.

**Altered subject** (`attestation.py`): `altered_subject()` counts the case refused only through `refused(...,
POLICY, ...)` (a `CalledProcessError` naming `verifying with issuer "sigstore.dev"`), restoring the subject's bytes
either way. gh's wording reproduced on this Mac with gh 2.94 against the retained fixture plus one byte (`Error:
verifying with issuer "sigstore.dev"`, exit 1; sigstore-go checks the subject digest inside the policy verify). Test
`RecordingOpener.test_an_altered_subject_counts_only_as_ghs_named_policy_refusal`. The two held-history rollback cases
and the publisher refusals below it still catch any exception (outside this step's scope; a follow-up could expect
`Refused('qualification_rollback')` there the same way).

**Probes (21 new, all rejected, each for its stated reason;** `.work/20-main-fix/step4-mutations.json`, 26 of 26 with
the step-3 `mainfix-sec-*`): `mainfix-f1-plan-skips-the-held-head-off-main`, `-plan-requalifies-on-main`,
`-conflicting-repeat-relaxed`, `-pull-request-attests-main-bytes`, `-pull-request-seeds-main-only`,
`-held-record-through-gh-api`, `-held-record-under-the-pull-request-ref`, `-held-record-unchecked-without-a-list`,
`-origin-publish-accepts-a-held-bundle`; `mainfix-f2-recording-ends-on-the-first-404`,
`-recording-passes-after-the-last-attempt`, `-gh-404-not-a-refusal`, `-listing-trusts-any-shape`;
`mainfix-note-a-step-if-as-first-key`, `-job-if-block-scalar`, `-job-if-plain-continuation`, `-step-if-on-the-next-line`,
`-run-plain-continuation` (the old matchers pass all five of these mutations; checked); `mainfix-note-b-shared-publisher-group`;
`mainfix-note-c-fixture-signed-link`; `mainfix-sec-altered-subject-any-exception`. Step 3's
`mainfix-sec-pull-request-publish-token` still applies unchanged (a token in the publish step's `env:`).

**Local verification (step 4).** Full preflight on `5de22178`
(`reviews/20-main-fix/records/final-local-5de22178.json`, the step-3 driver with its Node count pattern fixed to read
Node's `ℹ tests N` line): **329 Python** (shards 66/57/49/157; the Linux-only socket case skipped on the Mac), **428
Node**, **512 removal mutations rejected** with every baseline passing (491 + 21), generator check, `git diff --check`,
the service unit byte-identical to `8b7e799c`. The touched suites also pass from a foreign working directory with no
`PYTHONPATH` (the qualification layout's shape). No browser was started.

**What the code doesn't show.**
- `prepare`'s `git fetch origin chrome-qualification` also updates `refs/remotes/origin/chrome-qualification` (git
  updates the remote-tracking ref of a configured refspec, which actions/checkout sets), so the read step and the
  seeding use exactly the record `prepare` extended. Were it stale, a main publication between checkout and `prepare`
  would make the PR's `append_only(held, candidate)` refuse: fail closed, never a wrong pass.
- `origin/chrome-qualification` still does not exist, so this PR's runs take the first-record path; the second-run
  path is proven by the local step tests and runs in CI from the first PR after main's first publication.
- Once main has published, every PR touching `control/**` keeps running the head build's stable matrix (28 pair jobs
  plus combines), as this PR's runs already do: no new cost against run 3.

## Step 4: runs

The final push `7b015a7a` (no `[skip ci]`) started all five Control workflows on the PR. All five passed: Control
boundary, base and Mail (outside this brief's budgets) and the two below. Budgets are now used up: qualification 4 of 6,
`Control Chrome` 2 of 2.

1. **Qualification 43678600028** (pull-request event, run 4 of 6): **34 of 34 jobs green.**
   - `qualification-tests` ran the new step tests on the hosted runner (bash, git, stand-in `gh`).
   - `delivery-attestation`: the new recording step found this run's attestation on the first attempt (no retry
     line). The token-free "Retain ..." step passed every case. That includes the new "anonymous lookup nothing
     listed 404 refused", "altered subject refused (verifying with issuer "sigstore.dev")", and "production main
     rejects a bundle attested on refs/pull/68/merge". The trimmed retained fixture passed the same cases.
   - Pairs: 28 jobs for the head build on stable, 2 repeats.
   - `recheck2`, repeat 1 and repeat 2: every GROUP 8 row PASS. Each recorded the extension's install path as
     `typed-early` → `document_start`, `typed-late` → `late`, `typed-clean` → `late` (`POPUP RECEIVER ... on the
     document_start path`). `control-status.json` holds `document_start`/`ready` for both.
   - Both combines passed.
   - `qualification-publish`: prepare took the first-record path and wrote the indented candidate. The read-only step
     said "No data branch on origin: the pull-request publish takes the first-record path". The token-free publish
     step then printed "Pull-request mode: the verified candidate reached only the local bare remote".
   - The two main-only steps were skipped.
2. **`Control Chrome` 43678600076** (pull-request event, run 2 of 2): **28 of 28 jobs green.** That covers every
   fixture shard in both installs, the four Python shards, native precedence, both aggregates, and `latency (plain)`
   and `latency (audit)`.
   - `fixtures (policy, recheck2)` and `fixtures (external, recheck2)`: the same three `POPUP RECEIVER` paths,
     `typed-early` → `document_start`.
   - GROUP 8 "popups preserve opener flow and guard first input without moving windows" PASS in both installs. So did
     "closing or releasing an opener ends popup control and clears badges", the row that flaked on another PR.

Evidence in `.work/20-main-fix/` (not committed): `final-attestation.log`, `final-chrome-recheck2-132704158641.log`,
`final-chrome-recheck2-132704158647.log`, `final-qual-recheck2/rep{1,2}/`, `final-publish.log`, and the watch outputs.

## Handover (step 3)

Builder step 3 (Claude Opus 5.5, 2026-11-15): H6 (the lead's addition) and security NOTEs 1–3. Stopped at a clean
`[skip ci]` commit on the lead's budget rule; **no CI run in this step**.
- **Done:** H6 (`ddac1f34`), security NOTEs 1–3 (`c4ffa69c`), this file and the preflight record. Local: popup and
  fixture Node suites green, the touched Python tests green, 8 new removal probes rejected (27 `mainfix-` probes now),
  full local preflight under "Step 3: local verification".
- **Left for step 4 (all done in step 4, above), in order:** the package review's F1 (plan re-qualifies the head build on stable off main; a
  conflicting repeat on a PR fails; seed the PR-mode bare remote with `origin/chrome-qualification` when it exists,
  which is security NOTE 4, now required), F2 (the `gh api` retry loop survives the 404 for a digest with no
  attestations; model the real 404 in `attestation.py`, `test_publisher.py` and `bundle_from_api`, keep the empty-list
  cases), NOTEs (a) to (d) of the review; then the full preflight and the **one final push**, which starts qualification
  run 4 of 6 on the PR and the last `Control Chrome` run. Both must be fully green, `recheck2` in both installs.
- **Note for F1's seeding:** `origin/chrome-qualification` does not exist yet (`git ls-remote` empty on 2026-11-15), so
  the seeding is a no-op on this PR's runs. Once it exists, `publish()` calls `verify_held` → `gh api`, which needs a
  token: the seeding step must then set `GH_TOKEN` again, which NOTE 3 removed from the pull-request publish step for
  now (it calls no `gh` today). The write-command scan itself ignores tokens, but the same test's "no `GH_TOKEN` in the
  pull-request step" assertion (`test_write_commands_appear_only_in_the_guarded_publication_steps`) must then be changed
  with F1, deliberately, together with probe `mainfix-sec-pull-request-publish-token`.

## H6. The `typed-early` popup row is deterministic (step 3)

**Cause (from run 43660183139's recheck2 repeat-2 artifact and Chromium's source).** The row failed because the
extension's very first command on the popup, `Page.enable` (id 350, `browser-boundary.jsonl` line 16460), never got an
answer: it "failed" about 5 s later (session rules at …259,099 ms for the click, …264,129 ms after the failure). That is
`initializeTab`'s owner-dialog fallback (`background.js`: if `Page.enable` has not completed in 5 s it treats the tab as
blocked, sets `modalHandoff` and `popupNeedsReload`, and **detaches the debugger**). `admitTab` then logged
`popup_admitted` anyway, the harness took that as "breakpoint set" and released the held document, which loaded with no
debugger attached; the next `read` re-attached (`recoverOwnerDialog`) and the late reader installed late. The two late
records are **not two documents of a renderer swap** (step 2's reading was wrong): `bb36d1eb…` is the popup's main
document and `f43b1dba…` its hidden `sink` iframe (`about:blank`), both of the final document.

Why `Page.enable` hung: in Chromium (`content/browser/devtools/render_frame_devtools_agent_host.cc`,
`devtools_session.cc`, current source), `DidStartNavigation` of a frame suspends every attached session
(`SuspendSendingMessagesToAgent(kAll)`), and `FallThrough` queues each renderer command (`Page.enable`,
`Debugger.enable`, …) until `DidFinishNavigation` resumes them; an agent host created after the navigation started has
no pending request and is not suspended. So the outcome depends on one order:
- the extension attaches **after** the popup's navigation to its document started → no suspension → commands reach
  the initial empty document's renderer at once, the breakpoint is set, `popup_admitted`, release, the document pauses
  at `context.js` → `document_start` (repeat 1 of the same run, lines 16460–16485: `Page.enable` completes at once);
- the extension attaches **before** it started → the session is suspended until the navigation ends, but the fixture
  holds that navigation's response until `popup_admitted` → deadlock until the 5 s fallback → `late` (repeat 2).

In both logs `Page.frameStartedNavigating` follows `Page.enable` directly: `PageHandler::Enable` emits it itself when a
navigation is already pending, so both orders look alike in the log. **Site isolation plays no part:** the suspension is
for any cross-document navigation, same-site or not, so a same-site popup document under the hold would deadlock the
same way. Passing runs compared: 43656398035 (run 1) and 43663583972 (run 3) passed the row; repeat 1 of 43660183139
shows the passing order directly; brief 20's 43626497829 also passed (not downloaded: same harness and the same order
as repeat 1 is the only passing shape the code allows).

**Fix (harness only, `ddac1f34`; no extension change).** The hold moves off the popup's navigation:
- `popups.mjs`: `popupOpenURL(id, mode)` is what Claude's click opens. For `typed-early` it is a first document on the
  **opener's own origin** (`/?case=popup-start`), which fetches `/popup-gate?id=…` and only when that answers does
  `location.replace` to the row's usual document (`popupChild`, unchanged, cross-site as before). The row holds the gate
  (same `fixture.hold`, same `popup_admitted` wait, code lines unchanged). So no navigation is pending while the
  extension admits the popup (whatever the attach order, the first document's own navigation is never held), and the
  row's document starts navigating only after the breakpoint is set: the path every navigation of a controlled tab uses.
  Same origin for the first document also means the admission sees no renderer change (no POST-style dead context).
- `fixture.mjs`: `/popup-gate` is the only held request; no document is ever held (the `popup-child` hold is gone).
- `clean`, `dirty`, `typed-clean` and `typed-late` open exactly what they opened before (pinned by the test below).
  The assertion is unchanged: the path comes from the extension's record, `typed-early` must record `document_start`
  and answer `stale_reference`; no retry, no branch on outcome.

**Tests** (local, no browser): `popups.test.mjs` — the stand-in browser now opens what the real opener page opens
(`popupOpenURL`), holds only the gate as `fixture.mjs` does, and models DevTools' attach order (`attach:
'after-navigation' | 'before-navigation'`); "each install path …" runs both orders × both races and requires
`typed-early` → `document_start`/`stale_reference` in all four (`typed-clean` takes the natural path: the race after,
late before). New "typed-early opens a first document on its opener origin, which navigates only once the gate
answers" runs the real opener and first-document scripts in `node:vm` on stand-in globals: the window name and target
of every row (only `typed-early` changed), one gate fetch, no navigation before it answers, then exactly one
`location.replace` to the row document. `fixture.test.mjs` "gate60b a held popup gate …" (renamed): the gate waits for
its release, the first and the row documents answer at once while it is held, closing releases a hold.

**Probes** (rejected): `mainfix-h6-early-opens-row-document` (typed-early opens the row document directly again: fails
under `before-navigation`), `mainfix-h6-start-navigates-before-gate`, `mainfix-h6-fixture-holds-the-document`; the
existing `gate60b-popup-*` (7) and `gate60b-fixture-hold-ignored` (its test filter renamed) still rejected
(`.work/20-main-fix/h6-mutations.json`, 11 of 11).

**Risk the CI must confirm:** the browser rows themselves run only on the final push's runs (recheck2 in both installs
of `Control Chrome`, and two repeats of the qualification's recheck2).

## Step 3: local verification

Full local preflight on `c4ffa69c` (`reviews/20-main-fix/records/final-local-c4ffa69c.json`, the step-2 driver):
**318 Python** (shards 60/57/49/152; the Linux-only socket case skipped on the Mac), **428 Node**, **491 removal mutations
rejected** with every baseline passing (483 + the 8 new), generator check, `git diff --check`, the service unit
byte-identical to `8b7e799c`. No browser was started. Subsets: H6 and the `gate60b-popup-*`/`-fixture-*` probes 11 of 11
(`.work/20-main-fix/h6-mutations.json`); the `mainfix-sec-*`, `-h2-*`, `-h4-*` probes 18 of 18
(`.work/20-main-fix/sec-mutations.json`). Runs: none in this step; budgets unchanged (qualification 3 of 6 used,
`Control Chrome` 1 of 2).

## Security NOTEs folded in (step 3, `c4ffa69c`)

1. **Named refusals** (`attestation.py`): `refused()` accepts only `subprocess.CalledProcessError` whose stderr holds
   the case's own reason, in gh's wording (read from `cli/cli` trunk, `pkg/cmd/attestation`, and reproduced with gh
   2.94 on this Mac against the retained fixture): wrong branch and production main → `expected SourceRepositoryRef to
   be <the expected ref>`; wrong workflow and altered signature → `verifying with issuer "sigstore.dev"` (gh reports a
   certificate-identity or signature policy failure only so; the genuine bundle passes with the right workflow just
   before, so the wrong-workflow case fails on identity alone); missing bundle → `could not load content from file
   path`. Anything else (timeout, gh missing or too old, another gh error) propagates and fails the job, and the held
   record must be unchanged. The "altered subject" case below it still catches any exception (outside the NOTE).
   Test `RecordingOpener.test_a_refusal_counts_only_as_ghs_failed_verification_naming_its_reason`; probes
   `mainfix-sec-refusal-any-exception`, `mainfix-sec-refusal-reason-unchecked`.
2. **Write-command scan** (`test_qualification.py`, `workflow_runs()` and
   `Workflow.test_write_commands_appear_only_in_the_guarded_publication_steps`): every `run:` body of both workflows
   (single-line and block scalars, `- run:` as a step's first key too) is scanned for `git … push`, `gh issue|pr|release`
   and their `subprocess` list forms; none may appear. `qualify.py publish` to origin and `notify` only in the
   allow-listed main-only steps, `publish --remote .work/publish-remote.git` only in the pull-request step. To make
   the rule absolute, the pull-request step now seeds its bare remote with `git -C .work/publish-remote.git fetch
   "$PWD" refs/remotes/origin/main:refs/heads/main` instead of `git push` (checked locally on a scratch repository).
   Probe `mainfix-sec-unconditional-write-step` (a step that pushes), `mainfix-sec-pull-request-publish-to-origin`.
3. **No token in the pull-request publish step** (workflow): `GH_TOKEN` dropped; it calls no `gh` (the fresh bundle is
   verified offline by `gh attestation verify --bundle`, which skips gh's auth check when `--bundle` is given). Pinned by
   the same test; probe `mainfix-sec-pull-request-publish-token`.
4. **Not done here:** moved to step 4 as part of F1 (see the handover; it needs the token back once the data branch
   exists).

## Handover (step 2)

- **Done:** H1 (step 1), H2, H3, H4, H5 as decided by the lead (below, "Step 2: what was built"). Local: the touched
  Python suites green, 19 main-fix removal probes rejected (`.work/20-main-fix/mainfix-mutations.json`, 18 new plus
  H1's), generator and whitespace checks green, and the recorded API bundle of the retained fixture verifies with the
  real `gh attestation verify` on this Mac (branch policy passes, main policy refuses it).
- **Runs:** qualification green on the PR in PR mode (run 3 of 4), `Control Chrome` green on the PR (run 1 of 2);
  details under "Runs". Full local preflight on the final head under "Final local preflight".
- **Left:** a fresh package review and a fresh security review (H2 and H3, the trust path). The lead merges.

### Step 2: what was built

**H2. Attestation checks without GitHub's anonymous quota** (`control/chrome/ci/attestation.py`,
`control/chrome/qualify.py`, `.github/workflows/control-chrome-qualification.yml`, tests).
- CI records the real attestation API response for the record it just attested with `gh api` and the job's token
  (retrying up to a minute until the fresh attestation is listed). `attestation.py` installs a `urllib` opener
  (`RecordedAttestationAPI`) that answers exactly the product's own URL for that digest with the recorded bytes and
  refuses every other URL, plain HTTP, and any request carrying `Authorization`. The product's anonymous
  `verify()` runs unchanged in the minimal environment through it, then the real `gh attestation verify --bundle`.
  Negative cases through the same opener: empty list, 403, 429 with `Retry-After`, 500 (each refused), and an
  unrecorded URL. The retained fixture (`control/chrome_tests/fixtures/qualification/42687597384/`) got its own
  recorded response (`api-response.json`, the fixture's entry of the API response, 12 KB) so that case needs no
  network at all; the API lists 64 attestations for those bytes because every earlier run attested the same
  synthetic record, which is why the synthetic record now carries the run id (`entry(run=...)`) and is unique per run.
- The synthetic record's digest therefore differs per run, and the anonymous path on the PR verifies this run's own
  attestation on the run's full ref (`--ref "$GITHUB_REF"`, `refs/pull/N/merge` on pull requests).
- **Product change, small and trust-neutral:** `verify()` takes `ref=None` (the full source ref) beside `branch`; the
  default stays `refs/heads/main`, and the installed service never passes it. It exists so CI can check the bundle it
  attested on a pull-request ref through the product's own code path. No token reaches `qualification.py`; the
  "never ships" test asserts no installed file contains `install_opener`, `RecordedAttestationAPI`, `OpenerDirector`
  or `api-response.json`, and that the product module names no `Authorization`, `GH_TOKEN` or `GITHUB_TOKEN`.
- **H2.3 (part of "as proposed"):** `qualify.py` verifies a *held* data-branch record from a token-fetched bundle list
  (`bundle_from_api` → `gh api`, serialized exactly as the product does, bounded by `DELIVERY_LIMIT`; `verify_held`
  passes it as `--bundle`). `plan`, `prepare` and `publish` use it for the held record; the anonymous API is no longer
  called anywhere in CI. Same policy (`gh attestation verify`, main, this workflow, hosted runners); the response is
  transport, not evidence.
- **Product tests (no product gap found):** `test_rate_limits_timeouts_and_server_errors_keep_held_and_wait_a_day`
  (verifier HTTPError 403, 429 with `Retry-After`, 500; download `URLError(TimeoutError)`, `TimeoutError`, HTTPError
  503): held record unchanged, result names only the exception class and "held record retained" (no URL, body, header
  or reason), no request at +1 s or +86,399 s, one at +86,400 s, no temporary left, and a later good fetch is accepted.
  `test_failed_forced_refresh_for_an_uncovered_version_is_attempted_once_per_connection` (through the real adapter
  and `refresh`, with `urlopen` raising 403): one fetch per `(session, version)` across repeated `maintenance()`
  calls, a new connection or version gets exactly one more, record unchanged, nothing private logged.

**H3. First publish and the attestation just made** (`qualify.py`, workflow, `test_publisher.py`).
- `qualify.py publish --bundle "$BUNDLE"` takes the attest step's bundle (`id: attest` on the publisher's attest step)
  and `publish()` verifies the candidate with `verify(candidate, bundle=...)`; `--bundle` is required. The first-record
  path is unchanged in shape and now pinned: `test_first_publication_cuts_the_data_branch_from_main_and_extends_only_the_shipped_baseline`
  runs the real `prepare` CLI against a seeded local repository with `origin/main` and no data branch (candidate =
  shipped baseline + this run's aggregated entries, held verifier never called), then `publish()` to a local bare
  remote (verifier called once with the bundle, `main` untouched, the data branch cut from `main` with the candidate),
  and two refusals with nothing pushed: a candidate whose prefix is not the trusted baseline, and a `main` whose
  shipped record is not the trusted baseline. No unattested path exists.

**H4. Main-only paths run before the merge** (both workflows, `qualify.py`, `test_qualification.py`).
- No job of either workflow is main-only any more. `qualification-plan`, `-pairs`, `-combine`, `-publish` and
  `delivery-attestation` run on pull requests and branch dispatches. The writes that reach GitHub are the only
  main-only steps: "Verify the new attestation then push only the data branch" and "Publish failure details and
  propose shipped-copy update" (`if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'`, the
  second with `always() &&`). Their pull-request counterpart "Verify the new attestation then publish to a local
  bare remote (pull-request mode)" seeds a bare repository from `origin/main`, runs
  `publish --bundle "$BUNDLE" --remote .work/publish-remote.git`, and checks the local data branch holds the candidate
  and `main` did not move.
- **In code:** `qualify.py`'s guard requires this repository for everything; `notify` and `publish` without
  `--remote` require `refs/heads/main`; `prepare` and `publish --remote <dir>` run anywhere; `--remote` must be an
  existing local directory (a URL, `file://`, `git@…` or a missing directory is refused before any git call).
- **PR cost:** the plan takes `--channels stable` off main (`QUALIFICATION_CHANNELS` is `stable,beta` on main), so a
  pull request runs one channel × 2 repeats × 14 shards (9 browser, 4 Python, precedence) = 28 pair jobs plus two
  combines, half of main's matrix. Every step of every job runs except the two main-only writes.
- **Negative test in CI:** `attestation.py` on a non-main ref adds the case "production main rejects a bundle
  attested on <ref>": `verify(subject, bundle=<PR bundle>)` with the default main policy must raise, and the held
  record must stay. It runs in the PR job on the PR-made bundle (and on dispatches on the branch ref).
- **Workflow test:** `test_no_job_is_main_only_and_only_allow_listed_write_steps_are` parses both workflows'
  `if:` lines by indentation: no job-level condition may mention `refs/heads/main`, `pull_request`, `github.ref`,
  `event_name`, `base_ref` or `head_ref`; a step-level main-only condition must be exactly the form above and on an
  allow-listed write step; each allow-listed write step must carry it; the PR-mode counterpart must carry the exact
  complement; `qualify.py` must hold both guard lines. `test_path_triggers_cover_every_input_of_the_jobs`: both
  workflows' `push` and `pull_request` paths now include everything the jobs copy or archive
  (`docs/control/TOOLS.md`, `reviews/20-chrome/audit-review-evidence.mjs`, and each other's workflow file).

**H5. The `latency (audit)` tail: a runner storage stall** (`latency-profile.py`, `service.py`, `run.sh`,
`latency-pair.sh`, `test_latency.py`). No ceiling, sample-count or rule change.
- CI-only stages `store_write` (sum per marked sample) and `journal_fsync` (sum and `count`) in
  `latency-profile.py`: `store.write` is wrapped on the daemon's store, and the storage module's `os` is replaced by
  a proxy whose `fsync` is timed (everything else delegates to `os`). Both stages are emitted for every marked sample
  (0 when nothing was written), so the summary's per-call sample counts stay complete for `latency-check.py`'s strict
  validation, and nothing outside a marked sample is counted. The gate reads its listed stages only; unchanged.
- The two harness streams of the instrumented profile are harness-only: `service.txt` is the CI service's stdout
  (`CHROME_EVENT` lines, `FIXTURE_BACKGROUND_ERROR`), `browser-boundary.jsonl` the CI audit sink
  (`bridge.audit_sink`, set only in `ci/service.py`). In the container their only readers are fixture matrices
  (`matrices.mjs`, `popups.mjs`, `review-matrices.mjs`, `admin.py start_service`) which the latency probe never
  reaches (`run.sh` exits after `browser.mjs` when `LATENCY_PROBE=true`; `latency-probe.mjs` reads no `/out` file).
  `latency-pair.sh` now mounts `--tmpfs /scratch` (256 MB, mode 1777); `run.sh` writes both streams there when
  `LATENCY_PROBE=true`, and after the probe stops the service and copies them to `/out`, so the artifacts still
  carry them. The store stays in `/var/lib/aresos-tools` on the container's disk; its fsyncs keep being measured.
  Fixture shards are unchanged (`FIXTURE_LOG_DIR` stays `/out`).

**Probes** (`reviews/20-chrome/mutation-audit.py`, prefix `mainfix-`, all rejected, baselines passing): h2 recording
answers any URL / accepts credentials / refresh retries before a day after failure / logs transport detail / forced
refresh every call / held record verified anonymously; h3 publish skips fresh verification / ignores the trusted
baseline (both append-only checks); h4 publish to origin off main / notify off main / `--remote` accepts a URL / plan
job main-only again / publish step unconditional / attestation job skips pull requests; h5 storage stages count
outside samples / journal fsync untimed / harness streams on the store disk.

**What the code doesn't show.**
- The API's representation of a bundle differs from the attest step's `bundle.json` (same signature and payload,
  different field layout); the recorded representation verifies with gh 2.x on this Mac (exit 0 with the branch
  policy, 1 with main's), which is what the product path has always serialized.
- `prepare` on a pull request reaches `origin` read-only (`ls-remote`, public); with a data branch present it
  verifies the held record through `gh api` with the job's `GH_TOKEN` (already set on that step).
- Whether GitHub grants `id-token: write` and `attestations: write` to same-repository pull-request runs is decided by
  the first PR run; the fallback is the retained-fixture verification only (lead's H4 decision).

### Runs

Qualification workflow budget 4, `Control Chrome` 2 (both used only for the final PR check).

1. **43656398035** (dispatch on the branch, head `14e81352`): `qualification-tests`, `-plan` (28 pair jobs: stable ×
   2 repeats × 14 shards) and `delivery-attestation` passed. The attestation job's recorded response listed exactly
   this run's attestation on the first `gh api` attempt; the product's anonymous path ran offline through it; the
   negative cases refused; "production main rejects a bundle attested on refs/heads/pkg/20-main-fix" PASS (the
   retained fixture's offline case too). Two `python-3` pair shards failed in my new plan test, which ran
   `qualify.py plan` with `--root .` (the qualification layout's cwd has no `control/`); both combines failed on that.
   `qualification-publish` ran every step in PR mode and failed in the PR-mode publish step **as it must**: the
   candidate was attested on the branch ref and `publish --bundle` verified it under main's policy. Fix `af0e620e`:
   the PR-mode step passes `--ref "$GITHUB_REF"` for the fresh candidate only; `qualify.py` refuses `--ref` for a
   publication to origin (test and probe `mainfix-h4-origin-publish-accepts-a-foreign-ref`); the plan test names the
   repo root.
2. **43660183139** (dispatch on the branch, head `af0e620e`): tests, plan, attestation, 27 of 28 pair jobs, one
   combine and **`qualification-publish` passed in PR mode** (attested on `refs/heads/pkg/20-main-fix`, verified on
   that ref, published to `.work/publish-remote.git`, the local data branch holds the candidate, `main` unmoved).
   One browser shard failed: `recheck2`, repeat 2, "GROUP 8 popups preserve opener flow and guard first input
   without moving windows": the `typed-early` row recorded the `late` install path instead of the forced
   `document_start`; its combine then failed ("every browser shard is required"). Repeat 1 of the same shard and
   both recheck2 shards of run 1 passed. **Diagnosis from the artifact** (`control-status.json`,
   `browser-boundary.jsonl`): the popup tab `1364224890` holds two install records, both `late`, for two documents
   (`f43b1dba…`, never ready, and the final `bb36d1eb…`); `popup_admitted` for that tab was logged after the
   popup's `Page.frameStartedNavigating`, so the fixture's hold released the document as designed, but the popup's
   first document was replaced during admission and the extension attached to the second one late. That is the
   renderer-swap-during-admission shape the lead's post-popup fixes handle for the admission itself (mutation probes
   `post-popup-*`), now showing in the install-path record. Nothing on this branch touches the extension, the popup
   admission or the fixture shards (`FIXTURE_LOG_DIR` stays `/out` there); the next run re-exercises recheck2 twice.
   **For the lead:** a browser-timing flake in brief 20's popup fixture, outside this brief; no change made here.
3. **43663583972** (pull-request event, head `8579c5c9`, qualification run 3 of 4): **green, all 34 jobs** in PR mode.
   GitHub granted `id-token` and `attestations: write` to the same-repository pull request: `delivery-attestation`
   created a real attestation on `refs/pull/68/merge`; the recorded response listed exactly that attestation on the
   first `gh api` attempt; the product's anonymous path verified it on the PR ref offline; **"production main rejects a
   bundle attested on refs/pull/68/merge" PASS** (the required negative test, on the PR-made bundle, in the PR job).
   `qualification-publish`: prepare (first-record path, no data branch on origin), attest on `refs/pull/68/merge`,
   publish to the local bare remote with `--ref`, "Pull-request mode: the verified candidate reached only the local
   bare remote". No fallback was needed. The same push ran `Control base`, `Control Mail` and `Control boundary` on the
   PR (all green; outside this brief's budgets).
4. **`Control Chrome` 43663583962** (pull-request event, run 1 of 2): green, every fixture shard in both installs,
   Python shards, native precedence, both aggregates, **`latency (plain)` and `latency (audit)`**. The audit artifact
   carries the new stages with 60 samples per call (history-4000 `approval_to_done`: `store_write` 17.8 / 62.2 ms,
   `journal_fsync` 3.1 / 10.9 ms, `service_without_bridge` 34.6 / 79.7 ms, `client_total` 590 / 628 ms against 700 /
   850; `read` 0 / 0 for both storage stages) and the two harness streams copied from the tmpfs (`service.txt`
   12.6 MB, `browser-boundary.jsonl` 11.6 MB).

Budget used: qualification 3 of 4 (two dispatches, one PR event), `Control Chrome` 1 of 2.

### Final local preflight

On the final head `8579c5c9` (`reviews/20-main-fix/records/final-local-8579c5c9.json`, driver equivalent to
`.work/post18d/final-local.py`): **316 Python** (shards 58/57/49/152; the Linux-only socket case skipped on the Mac),
**427 Node**, **483 removal mutations rejected** with every baseline passing, generator check, `git diff --check` and
the service unit byte-identical to `8b7e799c`. The same preflight on `14e81352` is in `final-local-14e81352.json`.

### Report (step 2, final)

- **Commits:** `14e81352` (H2–H5), `af0e620e` (PR-mode publish `--ref`, plan test root), `8579c5c9` (runs recorded;
  the pull-request event), plus this one. Draft PR #68.
- **Tests and probes:** new or changed tests in `test_qualification.py` (verifier `ref`, recording opener, never
  ships, rate limits and timeouts, workflow allow-list, path triggers), `test_publisher.py` (guard, token-fetched
  held bundle, channels, first publication), `test_qualification_service.py` (forced refresh once),
  `test_latency.py` (storage stages, harness streams). 19 `mainfix-` probes rejected (18 new, H1's one).
- **Decisions for the lead:** none blocking. (a) The `recheck2` typed-early popup flake in run 2 is a brief-20
  fixture/extension timing race (diagnosis above); it passed in runs 1 and 3. (b) `verify()`'s `ref=` keyword and
  `qualify.py`'s `--ref` (refused for publication to origin) are the two trust-adjacent additions for the security
  review, with H2's token-fetched held bundle and H3's `--bundle`.
- **Left:** a fresh package review and a fresh security review (H2 and H3, the trust path); `Control Chrome` run 2 is
  unused reserve. The lead merges. This file stays until the lead's REPORT is written.

## Diagnoses

### H1. `test_state_crashes` child cannot import `test_engine` in the qualification layout

**Cause.** The crash-cut child (`control/chrome_tests/test_state_crashes.py`, `CHILD`) put
`sys.path[:0]=['control','control/chrome_tests']` on its path: two paths relative to the **parent's working
directory**. They hold in `control-chrome.yml` (`python-shards` runs `python3 control/chrome/ci/python-shard.py` from
the checkout root) but not in `control-chrome-qualification.yml` `qualification-pairs`, whose "Full Python file
partition" step runs `python3 runtime/control/chrome/ci/python-shard.py` from the job workspace, where the tree lives
under `runtime/` and `driver/` (workflow lines 104–113). The parent itself imports fine because `python-shard.py`
resolves its root from `__file__` and puts it on `sys.path` in-process (`control/chrome/ci/python-shard.py:14`); it
sets no `PYTHONPATH`, so the child inherits nothing.

**Evidence.** Run 43647781498, all four `qualification-pairs` Python shards that hold `test_state_crashes`: each of
the 9 cuts fails with `AssertionError: 1 != 73 : Traceback ... File "<string>", line 6 ... ModuleNotFoundError: No
module named 'test_engine'` (log lines 445–552, 985–1080, 1509–1604, 2136). Local reproduction: from
`.work/20-main-fix` with `PYTHONPATH` unset and the two absolute paths on `sys.path` in-process (as the shard does),
`unittest.main(module='test_state_crashes')` fails all 9 cuts with the same error; from the repo root the same command
passes. The earlier local run that passed from the foreign directory had inherited my shell's `PYTHONPATH`, which is
why the bug never showed locally.

**Fix (committed).** `test_state_crashes.py` derives `CONTROL` and `TESTS` from its own `__file__`, starts the child
with `cwd=self.root` (the test's temporary directory) and an environment whose `PYTHONPATH` is exactly those two
absolute paths (any inherited one removed), and the relative `sys.path` line is gone from `CHILD`. The test is its own
failing test: with the paths relative again it fails from anywhere, because the child's working directory is now
never the checkout. Verified: passes from `.work/20-main-fix` without `PYTHONPATH` (`Ran 1 test ... OK`, 9 cuts) and
from the repo root. **Probe** `mainfix-h1-child-relative-import-path` in `reviews/20-chrome/mutation-audit.py` puts the
relative paths back: run alone through a one-case driver it reports `MUTATION REJECTED` with
`ModuleNotFoundError: No module named 'test_engine'` (`.work/20-main-fix/h1-mutation.json`). The partition is
unchanged: no file skipped or moved. The same shape already existed in `test_state_mutations.py:80`, which passes an
absolute `PYTHONPATH` to its child and so never failed.

### H2. `delivery-attestation` fails on GitHub's anonymous API quota

**Cause.** `control/chrome/ci/attestation.py:36` deliberately runs the product's default path
`verify(path, branch=branch)` in a minimal environment (lines 29–38: "public HTTPS lookup, no personal
authentication"). That path (`control/aresos_control/chrome/qualification.py:103–120`) fetches
`https://api.github.com/repos/Ares-Empire/AresOS/attestations/sha256:<digest>` with no token. Unauthenticated GitHub
API requests are limited to 60 per hour **per source IP**, and GitHub-hosted runners share egress addresses, so the
quota is routinely exhausted by other tenants. The job makes this anonymous request twice (the synthetic record and
the retained fixture, workflow lines 258–259).

**Evidence.** Run 43647781498, `delivery-attestation`, step "Retain this workflow's real Sigstore bundle and test
altered copies": `QUALIFICATION DELIVERY newer valid attested record used PASS` (the bundle path works), then
`File ".../attestation.py", line 36, in exercise: verify(path, branch=branch)` →
`qualification.py", line 106, in verify: with urllib.request.urlopen(request, timeout=10)` →
`urllib.error.HTTPError: HTTP Error 403: rate limit exceeded` (log lines 11–38). The job had never run before the merge:
its `if` excludes pull requests (workflow line 228), and the branch pushes that trigger the workflow are
`pkg/20-chrome-qual` and `main` only (line 4). The same anonymous call also sits on main's `qualification-plan`
(`control/chrome/qualify.py`, `plan` command: `verify(temporary.name)` once the data branch exists) and in
`qualification-publish` (`publish()`: `verifier(candidate)` for the attestation it just made and
`verifier(repository/RECORD)` for the held one). On the first run the plan path was skipped (no data branch yet).

**Product on the laptop today** (`qualification.py` `refresh`, lines 141–168, called from
`Qualification.maintenance()` in `control/aresos_control/chrome/adapter.py:219–230`, which the daemon runs every 60 s
and once on each Chrome connection, `control/aresos_control/daemon.py:61–66, 184`):
- Every failure inside the `try` is caught by `except Exception` and turned into
  `Qualification refresh refused (<ExceptionType>); held record retained.`: a 403, 429 or 5xx from the API is a
  `urllib.error.HTTPError` raised inside `verify()` → `accept()`; a connect timeout is `URLError`, a read timeout
  `TimeoutError`; a 5xx or timeout on the raw.githubusercontent.com download is the same. The reason string holds
  only the exception class, never the body or URL.
- The held record stays: `accept()` raises before `store.write`, and the temporary file is unlinked in `finally`.
- The service keeps running: `maintenance()` is itself wrapped by the daemon in `try/except` →
  `background_error`.
- The next attempt is not soon: the `finally`-like write of `chrome:qualification_fetch` with `time: now` happens for
  failures too (line 168), so the daily gate (`now - previous['time'] < 86400`, line 144) holds the next fetch for
  24 h. The forced refresh for an uncovered build/version is attempted once per `(session, version)`
  (`_refresh_attempted`, adapter lines 227–229), so a failing forced fetch does not loop either. A `Retry-After`
  header on a 429 is ignored; the 24 h gate is longer than any GitHub asks for.
- **Tests that exist:** `test_offline_keeps_held_logs_reason_and_obeys_retry_interval` (OSError on the download),
  `test_bad_signature_rollback_malformed_and_oversized_downloads_keep_held` (verifier `Refused`, rollback, bad JSON,
  oversize). **Missing:** HTTPError 403/429/500 raised by the verifier's API fetch, read and connect timeouts, and
  5xx on the download, each asserting held record kept, result names only the class, next `refresh` within 24 h makes
  no request, and `_refresh_attempted` stops a second forced attempt.

### H3. Can the first publish on main pass "Verify the held attestation and shipped baseline before appending"?

**Yes, by design.** `control/chrome/qualify.py` `prepare` command: `exists = git ls-remote --heads origin
refs/heads/chrome-qualification`; when the data branch does not exist it writes the candidate as
`append_only(baseline, {'format':1, 'entries': baseline['entries'] + entries})` and returns **without** calling the
verifier. There is nothing to verify yet: the shipped baseline is `control/chrome/qualification.json` on `origin/main`,
trusted because it is in the reviewed tree, and the new entries come from this run's artifacts. The record is then
attested (`attest-build-provenance`, workflow line 213) and `publish()` verifies that fresh attestation, fetches
`main`, creates the data branch from it, checks `append_only(baseline, held)` and `append_only(held, candidate)`, and
pushes. No invented qualification and no unattested record is trusted on this path.

**Why it failed in run 43647781498.** The step starts with `test "$TEST_OUTCOME" = success` and
`test "$VERIFIER_OUTCOME" = success`; the log shows `TEST_OUTCOME: success`, `VERIFIER_OUTCOME: failure`, and
`##[error]Process completed with exit code 1` before `qualify.py prepare` ran (log lines 4068–4078). That is H2's
consequence, not a first-run gap. `qualification-combine` failed earlier for H1's reason: `merge-python.py:13`
`assert proof['index']==index and proof['count']==4 and proof['successful'] is True` on the shard that held
`test_state_crashes` (log lines 2566–2568; the browser shards and group 12 had passed: `Every browser shard and all 999
word cases PASS; native group 12 PASS`).

**Two first-run weaknesses that do remain** (fixes proposed below): `publish()` verifies the attestation it just made
through the anonymous API (`verifier(candidate)`), so a 403 or the attestation store's propagation delay can fail the
publish after a green run; and the second and later runs verify the held data-branch record anonymously in both `plan`
and `publish`.

### H5. The `latency (audit)` history-4000 tail in run 43647781438

**Per-sample timings** (artifact `chrome-latency-43647781438-1-current-audit`, `latency-client.json`, phase
history-4000, 60 samples per call; ms):
- `approval_to_done` median 666, p95 1,172, max 1,570; slow samples 18 (1,172), 20 (1,243), 27 (1,120), 31 (1,570),
  32 (1,157), 38 (1,024), 39 (1,544), 41 (1,123).
- `navigate` median 66, p95 332, max 448; over 2× the median at samples 15, 16, 19, 23, 26, 30, 32, 34, 37, 47.
- `asking_click` median 34, p95 230, max 291; over 2× at 11, 15, 18, 31, 32, 33, 42, 51, 53, 55, 59.
- `fill` median 603, p95 923; `free_click` median 630, p95 961 (spikes at 12, 20–23, 26–28, 30, 33, 36, 53).
- `read` median 23, p95 29, max 31: **no spike at all**.

**Periodicity: none.** The slow samples come in bursts (11–13, 15–16, 19–23, 26–34, 37–42, 51–55) and the calls'
spike indices overlap only loosely. The wall clock from the audit log's `session_network_rules.time` fields puts the
whole phase at 140 s; samples 19–33 took 2.5–3.4 s each against 2.0 s for samples 0–10 and 44–59, a slow stretch of
about 50 s in the middle of the phase, not a fixed interval.

**What the service and Chrome were doing.** In every slow sample the time is inside the Python service with the
bridge idle: for `approval_to_done` sample 31, `service_total` 1,569 ms, `bridge_round_trip` 548 ms (normal; the
525 ms hold is inside it), `service_without_bridge` 1,020 ms against about 50 ms in a normal sample,
`client_outside_service` 1 ms, `daemon_expiry_inside_sample` 0.2 ms; `extension_total` 544 ms (normal). `navigate`
sample 26: `service_total` 447, bridge 27, `service_without_bridge` 420. So Chrome and the extension were not slow,
the daemon's expiry sweep was not running, and the client's IPC was not waiting: the service stalled in its own
request path between bridge calls. The only call that never stalled, `read`, is also the only call that writes
nothing to the store. A plain-Python measurement on this Mac with the test fixture's fake bridge and the same 4,000-row
synthetic history (`control/chrome_tests/test_engine.py` fixture, 60 samples per call) shows what that path does:
`approval_to_done` makes 10 `os.fsync` calls per call (two journal appends with fsync per store write,
`control/aresos_control/storage.py:553–573`, plus two SQLite transactions per write with their own syncs),
`free_click` 4, `asking_click` 2, `read` 0; the interpreter's GC is not it (0 generation-2 collections in any phase,
41,542 tracked objects at 4,000 rows because the history lives in SQLite, generation-0 pauses 0.3 ms); medians grow
with history (read 0.9 → 9.5 ms, approval 13.7 → 23.8 ms) with no spikes on a local SSD where fsync returns in
0.03 ms. The stalls therefore sit in synchronous storage writes (fsync and SQLite commits) whose duration depends on
the runner's disk, and the audit profile is the exposed one because it alone adds two more append streams on the
same disk during the measurement: `/out/browser-boundary.jsonl` (11.6 MB, line-buffered) and `/out/service.txt`
(12.7 MB, one `print(..., flush=True)` per audit event, `control/chrome/ci/service.py:88–89, 98`); the plain profile's
`service.txt` has 0 lines. ext4 in its default `data=ordered` mode makes an fsync wait for the running journal
transaction, which carries other files' dirty data, so each store fsync can wait on those streams. The journal itself
is 30 MB at 4,000 rows (`history_fixture` rows in `latency-service.jsonl`), 8.3 MB at 1,000.

**Nothing runs differently on main.** `latency-pair.sh` and `control-chrome.yml`'s latency job read no ref: the only
main-conditioned code in `control/chrome/ci` is `attestation.py` (the qualification workflow). The CI service sets
`refresh_qualification=False` (`service.py:78`) and the container runs with `--network none`, so no qualification
refresh or network fetch can occur; the audit `service.txt` contains no line besides `CHROME_EVENT` and no mention of
qualification. The merge commit `09cedc84` differs from the PR head `d25ccbd3` under `control/` only in
`control/aresos_control/hooks.py` (the Claude Code hook's input schema, not in any Chrome request path),
`control/README.md` and two Mail tests; that `hooks.py` change landed on main at 08:00 on 2026-11-14, so the two
pull-request runs of `d25ccbd3` (22:15) already measured the merged tree and passed both profiles. The same code
passed the audit profile in run 43626497829 too (4,000: approval 594.6 / 597.0, navigate 51.1 / 54.3).

**The old runtime on the same runner** (`chrome-latency-43647781438-1-ab7aba92-audit`, 20 samples, measured after the
current runtime in the same job): history-4000 approval 1,408 / 1,506, navigate 838 / 905, asking 836 / 891, read
591 / 633, every p95 within 10 % of its median and no sample over 2× the median. Its runner factor was 0.99–1.31. The
runner was quiet again by then; the same job's earlier phases already showed the pattern in a milder form (fresh
`navigate` 9 samples over 2× median, p95 136 against the 150 ceiling; 1,000 `asking_click` p95 103 against 100 would
have failed on its own too had the 4,000 phase been clean). The earlier audit-only failure the report records (run
43603381599, `reviews/20-chrome/REPORT.md` "Failed, no code cause found") had the same shape: isolated samples, medians
equal to the plain profile's, the old runtime noisy in the same job.

**Verdict:** a runner-side storage stall during the audit profile's history-4000 phase, not a code change and not
anything main-specific. Evidence of the stall's location (store writes) is indirect: the artifacts time the bridge,
the expiry sweep and the whole request, but not the store. The proposal below adds that timing so the next tail, if
any, is attributed from the artifact itself.

## Step 1 proposals (built in step 2 as decided by the lead; kept as the record)

### H2. Attestation checks without GitHub's anonymous quota

1. **CI fetches the real bundle with the job's token and verifies through `verify(..., bundle=...)`.** In
   `delivery-attestation` the attest step already outputs `bundle-path`; `attestation.py` already uses it for the
   first PASS and the altered-copy cases. For the anonymous **path** itself, `attestation.py` installs a
   `urllib.request` opener (`install_opener`) whose handler answers exactly
   `https://api.github.com/repos/Ares-Empire/AresOS/attestations/sha256:<digest>` with a **recorded response** and
   refuses any other URL. The recording is made in the same step by `gh api` with `GITHUB_TOKEN` and written to
   `.work/attestation/api-response.json`; the product's `verify(path, branch=branch)` then runs unchanged in the
   minimal environment (its `urlopen` goes through the installed opener), serializes the bundles and calls the real
   `gh attestation verify --bundle`. The token stays in the workflow step and `gh api`; the product code path sees a
   file-backed response and no token or header. A second recorded case uses the retained fixture
   (`control/chrome_tests/fixtures/qualification/42687597384/`), checked in as a recorded API response so that case
   needs no network at all. Negative cases through the same opener: `{"attestations":[]}`, a 403 body and a 429 body
   (both raise `HTTPError` out of `verify`), and the propagation case (the record attested in this run not yet listed:
   same as empty). Files: `control/chrome/ci/attestation.py`, `.github/workflows/control-chrome-qualification.yml`
   (lines 251–259), new fixture `control/chrome_tests/fixtures/qualification/42687597384/api-response.json`. Unit
   test: `test_qualification.py` gets a test that the opener helper refuses foreign URLs and that `verify` with the
   recorded response produces the same `.jsonl` bundle bytes as before (existing
   `test_runtime_verifier_uses_bounded_anonymous_bundle_lookup` stays). Probes: remove the host check in the handler;
   make the handler answer the real network on a miss.
2. **Product tests** in `control/chrome_tests/test_qualification.py` (`Refresh` class): verifier raising
   `urllib.error.HTTPError` 403, 429 (with `Retry-After`) and 500; download raising `URLError(TimeoutError)`,
   `TimeoutError` and `HTTPError` 503; each asserts `record()` unchanged, the result string contains the class name
   and "held record retained" and no URL, body or header; a `refresh(now=now+86399)` makes no request and
   `now+86400` does; and through the adapter, `maintenance()` with an uncovered version forces exactly one fetch per
   `(session, version)` across repeated calls even when it fails (`test_qualification_service.py`, next to
   `test_runtime_connection_refresh_for_uncovered_version_once_and_daily_caller`). No product change is expected;
   if the HTTPError path turns out to leak anything, the fix is in the `except` branch. Probes: one that makes
   `refresh` write `time: now` only on success (would create the tight loop); one that drops `_refresh_attempted`.
3. **The other anonymous calls on main** (`plan` and `publish`'s `verifier(repository/RECORD)`): give `qualify.py` a
   `--bundle-from-api` helper that runs `gh api` for the held record's digest, writes the `.jsonl` and passes it to
   `verify(..., bundle=...)`. `gh` is authenticated there by `GH_TOKEN` already (workflow lines 48, 205, 219). Same
   trust: `gh attestation verify` checks signature, workflow identity, `refs/heads/main` and hosted runners either way;
   the API response is transport, not evidence. Unit test with a recording `subprocess.run`.

**Verification within the run limits:** everything above is plain Python locally; one qualification dispatch on the
branch (run 1 of 4) exercises `delivery-attestation` in PR mode (H4) with the real bundle and the recorded response.

### H3. First publish and the attestation just made

- `qualification-publish` passes the attest step's `bundle-path` to `qualify.py publish --bundle "$BUNDLE"`;
  `publish()` verifies `candidate` with `verify(candidate, bundle=...)` instead of the anonymous API (removes the 403
  and propagation-delay failure modes after a green run). The held data-branch record uses H2.3. The first-record path
  (no data branch) stays as it is: it already has an explicit, reviewable branch in `prepare` and `publish`
  (`exists` false → candidate from the shipped baseline; the data branch is cut from `main`). I propose to add a
  **test that pins it**: `test_publisher.py` gets a first-publication case against a local bare remote without a
  data branch, asserting the candidate equals baseline + this run's entries, the verifier was called on the
  candidate exactly once with the given bundle and never anonymously, and the branch is created from `main`; and a
  negative case where the baseline on `origin/main` is not a prefix of the candidate (refused, nothing pushed).
  Probes: skip the `verifier(candidate)` call; make the no-data-branch path accept a candidate whose prefix is not the
  baseline.
- **Not proposed:** any path that publishes without an attestation, or that trusts a data-branch record whose
  attestation cannot be fetched.

### H4. Main-only jobs get a pull-request mode

- **`delivery-attestation`:** drop `github.event_name != 'pull_request'` from its `if` (keep the repository check).
  Same-repository pull requests can hold `id-token: write` and `attestations: write`, so the real
  `attest-build-provenance` runs on the PR; `attestation.py` verifies the PR-made bundle with `--source-ref` set to the
  run's own ref: `GITHUB_REF` is `refs/pull/N/merge` on pull-request events, which is what the provenance records (today
  it builds `refs/heads/<GITHUB_HEAD_REF>`, which would not match; the retained-fixture case keeps its branch ref).
  The workflow's `pull_request.branches` already lists `main` as base. If GitHub refuses the attestation on a PR
  event, the fallback is the retained-fixture verification only, reported as such.
- **`qualification-plan`, `-pairs`, `-combine`:** drop the main-only `if`s; the plan on a PR is the same command (it
  reads only public data and `origin`), the pairs and combine jobs run the full matrix (today: the head build × stable
  and beta × 2 repeats, since `control/chrome/builds.json` has no shipped builds) and produce `pair.json`s and the
  combined artifact. That is the one job class that *could* have found H1 before the merge.
- **`qualification-publish`:** run on the PR too, with every step except the write. `prepare` and `attest` as on main;
  `publish` in PR mode pushes to a **local bare clone** of `origin` (`publish(root, candidate, baseline,
  remote=<path>)`, the parameter the tests already use) and `notify` does not run. `qualify.py`'s guard "publication is
  restricted to this repository on main" (`main()`, before `prepare`/`publish`/`notify`) becomes: `notify` and a push
  to the real remote are main-only; `prepare` and `publish --remote <local path>` are allowed anywhere, and `--remote`
  accepts only an existing local directory, never a URL. **Lead decision** (trust-adjacent): see below. The alternative
  I reject is faking `GITHUB_REF=refs/heads/main` in a PR step to pass the existing guard.
- **The check that fails when a job is main-only without a PR mode:** a unit test in `test_qualification.py` (next to
  `test_main_only_mutations_serialized_publication_and_daily_stable_beta_pairs`) parses both workflows and asserts that
  no job-level `if` mentions `refs/heads/main` or `pull_request`; the only main-only conditions allowed are on **steps**
  and only on steps in an allowlist of writes (`publish` push, `notify`), each with `if: github.ref == 'refs/heads/main'
  && github.event_name != 'pull_request'`. Probe: put a main-only `if` back on `qualification-plan`.
- **Triggers:** add `pkg/20-main-fix` to neither workflow's `push.branches` (the PR event covers it, and the
  qualification workflow's `pull_request.branches` already includes `main`); H4's PR mode is exercised by the PR runs
  the brief budgets.

**Verification within the run limits:** qualification runs 1–2 on the PR (PR mode of all five jobs, with the fix
rounds); runs 3–4 are reserve. `Control Chrome` runs: none for H4.

### H5. Make the next tail attributable; no code fix

- No code cause and nothing main-specific was found, so no product change and no change to ceilings, sample counts
  or the median-or-p95 rule. Proposed, CI-only, in `control/chrome/ci/latency-profile.py`: wrap `store.write` and
  `os.fsync` for the duration of a marked sample and emit stages `store_write` (sum per sample) and `journal_fsync`
  (sum and count), so the next summary shows where a stall sits. `latency-summary.py` already carries any stage
  present in `latency-service.jsonl`; `latency-check.py` validates only its listed stages, so the gate is unchanged
  (the reference's `summary_program_sha256` is pinned nowhere). Test: a unit test on the profile's wrapper with a fake
  store, asserting the emitted rows and that nothing is emitted outside a marked sample. Probe: emit `store_write`
  outside a sample (the summary's identity assertion must reject it).
- Optional, **not recommended now**: buffer the audit profile's two `/out` streams instead of flushing per event. It
  would reduce the exposure but also change what the audit profile measures; it needs the lead's view and its own
  paired run.
- A re-run of `Control Chrome` on main is the lead's call and outside this brief's two-run budget for the PR.

## Decisions for the lead (answered 2026-11-15: 1 approved; 2 confirmed; 3 accepted, stages added, harness streams moved; 4 fallback as stated)

1. **H4 guard change in `qualify.py`** (trust-adjacent): allow `prepare` and `publish --remote <local directory>` off
   main, keep push-to-origin and `notify` main-only. Recommended; the alternative (faking `GITHUB_REF`) is worse for the
   security review. Needs the security review's eye.
2. **H2.3 / H3: CI verifies held and fresh attestations from token-fetched or attest-step bundles instead of the
   anonymous API.** Trust-neutral in my reading (same `gh attestation verify` policy), but it means the product's
   anonymous path is exercised in CI only through the recorded response (H2.1). Confirm.
3. **H5 verdict:** accept "runner-side storage stall, not code" with the evidence above, and whether to add the
   CI-only store/fsync stages (recommended) and whether to re-run `Control Chrome` on main now or after this PR merges.
4. **H4 PR-mode attestation** relies on GitHub granting `id-token`/`attestations: write` to same-repository pull
   requests; if the first PR run shows it is refused, the PR mode keeps the retained-fixture verification only.

## Local test counts (step 1)

- `test_state_crashes` (9 cuts): OK from the repo root and from `.work/20-main-fix` with no `PYTHONPATH`; fails 9/9
  with the relative paths restored from the foreign directory.
- Mutation audit, one case: `mainfix-h1-child-relative-import-path` MUTATION REJECTED (baseline passed).
- GC/fsync measurement (diagnostic only, not a test): 60 samples × 4 calls × 3 phases through the fixture's fake
  bridge; no browser started.
