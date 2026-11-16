# Package re-check 2: steps 3 and 4 (34c2e888 to 5bc7e4aa, Claude Opus, 2026-11-15)

**Verdict: FIX**

The fixes in the scope are correct: F2, NOTEs (a) to (c), H6, security NOTEs 1 to 4, the read-only `held-bundles` step and the indented candidate. Both runs are what PROGRESS.md says, and all 67 `mainfix-`/`gate60b-` probes fail when applied. One part of F1 needs to change before merge: a conflicting repeat fails a pull request even when the pull request did better than main.

### FIX

**F3. A failure main recorded blocks every later same-build pull request, the bot's own baseline-update PR included.**
- **Where:**
  - `control/chrome/qualify.py:355`: off main, the plan qualifies the head build again.
  - `qualify.py:223`: `prepare` then raises `Conflicting repeat` when the verdicts differ, so the publish job fails.
  - Pinned by `test_publisher.py:407` and probe `mainfix-f1-conflicting-repeat-relaxed`.
- **How main records a failure:** when a main shard fails (one `recheck2` popup failure in run 43660183139; another opener-row failure in run 43671248371), the `pair` step finds no completion marker. `valid` is then false and the published entry is all-false. That is by design: failed groups stay disabled, and the record never changes.
- **Scenario:**
  1. Main records (B, V, stable) all-false because of one failed shard.
  2. Every later pull request that leaves the build hash alone qualifies the pair again and passes. That includes test, CI and fixture fixes like H6, and the "Update shipped Chrome qualification record" PR that `notify` opens (`qualification.json` is not a build input).
  3. `prepare` raises, the publish job fails and the pull request is red. Re-running doesn't help. It stays red until Chrome stable moves on or a product file changes.
- **Fix:** make the check one-way off main.
  - **Fail** when the pull request is worse than the held record (a group true there, false here). A pull request can do this without the combine failing, because `merge-shards.mjs:17` lets adapter values be false while the shard stays green.
  - **Warn and keep the held entry** when the pull request is better (false there, true here).
  - Keep raising on main.
  - Adjust the test and the probe to cover both directions.

### NOTE
- **(d) Fork pull requests:** `delivery-attestation` and the publish job still fail on them because forks get no `id-token`. CI cost stays as it was after run 3.
- **Old signed link in history:** the expired SAS link is trimmed from the fixture, but commit `14e81352` on the branch still holds it. A squash merge drops it; it has expired either way.

### Checked
- **F1, the rest of it:**
  - `requalify_head` follows the same `on_main` as the publication guard; main's plan is unchanged.
  - The off-main candidate is written indented, so a pull request never attests the exact bytes main published. Main's bytes are unchanged.
  - The pull-request publish seeds `origin/chrome-qualification` by `git fetch`, holds no token, and verifies the held record from `--held-bundle` under main's policy. Without a bundle list it refuses, and origin publication refuses `--held-bundle`.
  - The step tests run the real `run:` bodies against local repositories, including the second-run path.
- **F2:** the recording is its own step, with `|| true`, six attempts, no sleep after the last one, then `::error::` and exit 1. `bundle_from_api` treats gh's `(HTTP 404)` like an empty list, and the other gh failures propagate. The real 404 shape is modelled in `attestation.py` and the tests.
- **NOTE (a):** the new matcher in `workflow_steps.py` catches both of my earlier evasions (a folded job-level `if: >-`, and `- if:` as a step's first key) plus three more forms. Each has a probe that fails when applied.
- **NOTE (b):** main keeps its exact publisher group; every other ref gets its own.
- **NOTE (c):** `bundle_url` is gone from the fixture, and a test pins it.
- **H6:** only `/popup-gate` is held now; no document is. The first document is on the opener's origin and calls `location.replace` only after the gate answers. `firstAnswer` still demands `document_start` and `stale_reference` for `typed-early`, and nothing changed in the extension or `aresos_control`.
- **Security NOTEs 1 to 4:**
  - Refusals count only as gh's own named failures (`CalledProcessError` with the expected reason).
  - The write-command scan covers every `run:` body in both workflows.
  - The pull-request publish step holds no token; the read-only step holds `GH_TOKEN` and runs only `held-bundles`.
- **Local results:** 104 Python tests and the popup/fixture Node tests pass, run in a copy of `5bc7e4aa` in my scratch directory; neither suite starts a browser. All 67 `mainfix-`/`gate60b-` probes fail when applied, including all 21 new step-4 probes and the H6 and security probes.
- **Runs** (checked with `gh`, at least 60 s apart):
  - Qualification 43678600028: pull_request on `7b015a7a`, 34/34 green.
    - The `recheck2` artifacts for repeats 1 and 2 both show `popup-typed-early … on the document_start path` and GROUP 8 PASS.
    - The attestation output shows "nothing listed 404 refused", "altered subject refused (verifying with issuer "sigstore.dev")" and "production main rejects … refs/pull/68/merge".
    - The publish log shows the first-record path and "reached only the local bare remote", and both main-only steps were skipped.
  - Control Chrome 43678600076: 28/28 green. `fixtures (policy, recheck2)` and `fixtures (external, recheck2)` both record `typed-early` on `document_start`, and both pass GROUP 8 and the opener-release row.
- **Scope:** nothing under `os/`, `mod/` or `docs/design`, and no STATE.md, HANDOFF.md, CONTROL.md, service unit, extension or `aresos_control` changes. No personal data or owner mail provider. The review worktree is still clean at `5bc7e4aa`.

Evidence is in the reviewer's scratch directory (not committed).