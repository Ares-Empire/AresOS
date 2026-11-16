# Package review 1: steps 1 and 2 (to 34c2e888, Claude Opus, 2026-11-15)

**Verdict: FIX**

The H1, H2, H3 and H5 fixes are correct. The claimed runs are what PROGRESS.md says, and all 19 `mainfix-` probes fail when applied. Two things in H4 and H2's CI step need to change before merge.

### FIX

**F1. Once a record exists, pull requests that change only tests or CI skip the qualification layout again (the H4 gap).**
- **Where:** `control/chrome/qualify.py:70` drops every (build, version, channel) the held record already covers. The `plan` command (`:276-282`) counts the data-branch record as held. When the plan is empty, `control-chrome-qualification.yml:64` and `:134` skip pairs and combine, and `:183` skips publish.
- **Why it matters:** `build.py` hashes only the installed runtime, so a pull request that changes only `chrome_tests/`, `ci/`, `qualify.py` or the workflows keeps the build hash of main.
- **Scenario:**
  1. This PR merges and main publishes the first record (build B on stable V and beta W).
  2. A later pull request changes only test driver code, for example `test_state_crashes` (H1's shape) or H6's fixture fix. Its plan, stable only, is empty, so it runs no pairs, no combine and no publish, and goes green.
  3. On main, the next beta release qualifies (B, beta W′) with the new driver. That is the first time the change runs in the runtime/driver layout, so main goes red.
- **Fix:** off main, `plan` re-qualifies the head build on stable even when the held record covers it. `prepare` already skips an identical repeat; decide whether a conflicting repeat on a pull request should fail it or be relaxed. Add a test and a probe.
- **Related gap:** the pull-request publish seeds the local bare remote from `origin/main` only (`:236`), so the second-run path in `publish()` never runs on a pull request (`exists` → `held_verifier` → append to the data branch). When `origin/chrome-qualification` exists, also push it into the local remote.

**F2. The `gh api` retry loop exits on its first attempt in exactly the case it was written for.**
- **Where:** `.github/workflows/control-chrome-qualification.yml:279` and `:285-289`.
- **Evidence:** I checked the API. For a digest with no attestations listed it returns **404** (`gh: Not Found (HTTP 404)`, exit 1), not `{"attestations":[]}`. The step runs under `set -euo pipefail`, so a 404 from attempt 1 ends the step.
- **Scenario:** the listing lags the attest step → `delivery-attestation` fails → the publish step's `test "$VERIFIER_OUTCOME" = success` refuses → main is red. That is the propagation delay the builder's own H3 diagnosis named.
- **Fix:** `gh api … > file || true` inside the loop, and fail with a clear message after the last attempt.
- **Related:** the CI empty-list cases test a response the API doesn't give: `attestation.py:115`, `test_publisher.py:227`, and `bundle_from_api` (`qualify.py:109-120`). A real 404 surfaces as `HTTPError` or `CalledProcessError`. Both still fail closed, so that part is a NOTE.

### NOTE

- **The workflow test misses two common YAML forms.** `test_qualification.py:357` only matches an `if:` line that starts with spaces. In the scratch copy both of these regressions passed the test:
  - a job given back `if: >-` with the main-only condition on the next line;
  - a step written as `- if: … github.ref == 'refs/heads/main'` (with `if:` as its first key).

  Match `(?:- )?if:` and join block-scalar continuation lines, or parse the YAML.
- **Shared publisher concurrency group.** `concurrency: chrome-qualification-publisher` (`:185-187`) is shared by every ref, and pull-request runs now enter it. GitHub keeps one pending job per group, so a pull request's publish job can cancel main's pending publish. This needs three publish jobs within about 2 minutes, so it is unlikely; a group per ref off main would remove it.
- **Pull-request cost.** Every pull request touching `control/**`, including Mail and base packages, now runs 34 jobs: about 242 job-minutes and 55 minutes wall time (run 3). That is about the same as `Control Chrome`, and runner minutes are free for a public repo.
  - Each push also writes two public attestations.
  - On fork pull requests, `delivery-attestation` now runs and will fail because forks get no `id-token`.
- **Expired signed link in a fixture.** `fixtures/qualification/42687597384/api-response.json` keeps `bundle_url`, which carries an expired Azure SAS token. The product never reads it; trim it so secret scanners don't flag it.
- **Stale probe count.** The PROGRESS.md handover (`:9`) says 18 probes; the code and the report say 19.
- **Reconnects (behaviour from before this PR).** A forced refresh happens once per (connection, version) and ignores the daily gate. A storm of Chrome reconnections would mean one fetch per reconnection. It is bounded by how often Chrome reconnects; it is not a tight loop.

### Checked
- **H1:** the child gets absolute `CONTROL`/`TESTS` paths, an inherited `PYTHONPATH` is removed, and `cwd` is the test's temp directory. `python-shard.py` is unchanged, so the partition is unchanged. The test passes from a foreign working directory with no `PYTHONPATH`. With the probe applied, the child fails with `ModuleNotFoundError: test_engine`, even from the repo root.
- **H2:**
  - No anonymous API call is left in CI: plan, prepare and both publish modes get their bundles through `gh api` with the token or from the attest step.
  - The product's anonymous `verify()` runs offline in a minimal environment through the recorded opener. The opener refuses other URLs, plain HTTP and `Authorization` headers.
  - The product tests cover 403, 429 (`Retry-After`), 500, connect and read timeouts, a 503 on the download, and the once-only forced refresh. They assert the held record stays, the result names only the exception class, there is no request at +86,399 s and one at +86,400 s, and a later good fetch is accepted.
  - The new `ref=` defaults to main, and the installed service never passes it.
- **H3:** the first-publication test runs the real `prepare` against a local repository plus `publish` to a local bare remote, with two refusals. `--bundle` is checked both ways: present (passed through) and missing (`ValueError`). `--ref` is refused for publication to origin.
- **H4:**
  - No job-level ref condition remains in either workflow.
  - The only main-only steps are the push to the data branch and `notify`, and the pull-request counterpart has the exact complement.
  - The guard in `qualify.py` enforces the same thing, and `--remote` accepts only an existing local directory.
  - The path triggers cover every input the jobs read outside `control/`.
  - Stable versus beta changes only the package, so the stable-only plan skips no step kind.
- **H5:** I re-derived the diagnosis from run 43647781438's artifacts.
  - The numbers match PROGRESS.md: approval 664.8/1,172 ms, max 1,570; read has no spike.
  - In sample 31, `service_without_bridge` is 1,020 ms while the bridge is at its normal ~548 ms.
  - The old runtime is steady: approval 1,407/1,506 ms, read 591/633 ms.
  - `service.txt` has no qualification lines.
  - The storage stages live only in `ci/`, and `audit_sink` is set only in CI. The store stays at `/var/lib/aresos-tools` on disk. The old runtime gets the same current `ci/` overlay, so both runtimes are measured with the same harness.
  - The gate files are unchanged; the artifact's own record shows 60 and 20 samples and the "median or p95" policy text.
- **Tests and probes:** 91 tests across the six touched suites pass in a scratch copy, and all 19 `mainfix-` probes fail when applied, each for the stated reason (spot-checked four). Nothing in the review worktree was modified.
- **Runs** (checked with `gh run view`):
  - 43656398035: dispatch on `14e81352`, 5 jobs failed exactly as PROGRESS.md describes.
  - 43660183139: one browser shard and its combine failed (the popup flake); publish passed in pull-request mode.
  - 43663583972: pull request on `8579c5c9`, 34/34 green. Its attestation was made on `refs/pull/68/merge`, and the log shows "production main rejects a bundle attested on refs/pull/68/merge … PASS" and "Pull-request mode: the verified candidate reached only the local bare remote".
  - 43663583962: 28/28 green, including `latency (audit)`.
  - The head commit `34c2e888` changes only PROGRESS.md and the preflight record.
- **Scope:** nothing under `os/`, `mod/` or `docs/design`, and no STATE.md, HANDOFF.md, CONTROL.md, service unit or extension changes. No personal data, owner mail provider or absolute paths.

Scratch evidence is in the reviewer's scratch directory (not committed); the 404 response is in `att-empty.json` there.