# 22c, stage 1b: three additions (integrator, 2026-11-14)

Stage 1b is section C (guides), D (bundle and bindings), B12 (route and binding tests) and F (the refusal invariant) of `briefs/22c-ways-back-after-update.md`. Stage 1a is complete and its two review rounds are closed: `REVIEW-3.md` (gpt-6-astra high on `e051dd59`) says SAFE. Three additions, decided since the brief was frozen:

## 1. The full model does not run in every hosted run

The model test (963,003 states, about 15 minutes) made the hosted checks-only job take 33 minutes instead of 10; its limit was raised to 40. On main every branch of every session would pay that. REVIEW-3's advice, now the rule:

- Every hosted checks-only run keeps the focused tests and a **deterministic, bounded slice** of the model (same seed and order every time, a fixed state budget, a few minutes at most).
- The **full model** runs when its dependencies change: `os/owner-tools/**`, `os/release/**`, the model, ledger, memo, host and fixture code of the ways-back tests, and the test infrastructure they import. Decide this inside the job from the diff against the merge base (the job has full history); classify anything uncertain as "changed". A workflow input forces the full model.
- Bring the checks-only job's limit back down to what the bounded run needs, with room.
- A test proves the classification: a change to a listed path selects the full model, a change elsewhere the slice.

## 2. The image and rehearsal jobs stop skipping the namespace tests

27c (PR #47) gave the checks-only job the step that lets its disposable runner create unprivileged user namespaces, guarded by `unshare -Urm true`. The image job and the rehearsal job also run the suite and still skip the 136 tests of `test_owner_update.ToolsUpdateTest` silently. Give them the same step, before their test step.

## 3. The tools install without the stick (owner, 2026-11-14, step 1 of "updates like a regular OS")

The owner decided that routine updates need neither the USB stick nor Windows (`STATE.md`, "Updates like a regular OS"). Step 1, for this package: the tools bundle can be installed from a local folder.

- Claude on the laptop copies the reviewed bundle from the repository checkout at the announced commit into a folder, and the owner approves the password prompt; the stick stays documented as the emergency route.
- The trusted start block changes only its source: instead of mounting `LABEL=ARESTOOLS`, it takes a folder path. Everything after that stays as it is: system tools only, a copy into a fresh root-only folder under `/run`, no links, no special files, the literal fingerprint checked against `SHA256SUMS`, every file checked, then `at install`. The folder may be writable by `ares`; only the verified copy is used.
- Keep one block that works for both sources, or two blocks that differ in exactly the source lines: say which and why. `bootstrap.py` generates it, the guide quotes it, the tests compare them.
- The guide's update route gets the stick-free way first ("Claude copies, you approve"), the stick as the fallback.
- Stage 2's rehearsal installs version 3 this way (and keeps one stick install somewhere in the walk).

## Steps and models

- **Step 1 (a Claude agent on Opus):** additions 1 and 2, then D (bundle, pins, bindings), B12, F, and addition 3's start block with its tests. Stop and report.
- **Step 2 (a Claude agent on Opus):** section C, the guides, written once against step 1's lines.
- Then a fresh review of stage 1b (Codex if any is left after 2026-11-17, otherwise Fable: addition 3 changes the trusted start), then stage 2.

Rules as in the brief. The hosted runs are the truth for `test_owner_update`; never run that module on the laptop.

## Decision after step 1 (integrator, 2026-11-14)

Step 1 found that a stick-free install needs more than a new source in the start block: `at install` and the tools update require the labelled ARESTOOLS stick (`tools_stick` in `owner.py`, used for the bundle's identity) and run "only from the physical recovery console" (`sys.stdin.isatty()`), while the owner wants Claude to run the commands and him to approve the password prompt. Replacing those two checks changes what the tools trust, so it gets its own small package, **22d: the owner tools without the stick, from Claude's terminal** (a design note first, Fable). For 22c:

- The folder start block that step 1 built stays generated and tested, but no guide routes to it and no rehearsal step uses it; the report marks it as waiting for 22d.
- The guides of step 2 keep the stick route as the way to install version 3. The stick-free route is 22d's.
- Stage 2's rehearsal installs version 3 from the stick, as the frozen brief says.
- Step 1's other findings: the budget ledger allows too few checks-only runs on this branch for stage 2 to start (raise it in step 2, say by how much and why; the runners are free for this public repository); the refusal checks run through cut 7, which the report records instead of the brief's reading; the host walk gets E's route in stage 2.
