# Step 3: fixes for REVIEW-4 (2026-11-17)

Builder: Codex, gpt-6.1-sol (xhigh), branch `fix/42-s3`. This note supersedes the step 3 claims identified below
in the older progress report. PROGRESS.md and the package 27 rebind tables are left to the lead. No owner-tools
code changed. No push, dispatch, VM, privilege escalation or running-system update was performed.

## Per finding: what, where, regression test

1. **Deferral and final qualification.** `os/ci/release28_walk.py`, `real_commit()` and `rehearsal()`:
   deferral requires the verified v4 tools tree, release blob and guide fingerprint lines. Only an explicitly
   preparatory local walk permits it, recording `equal: false`, `deferred: true`, `qualified: false`. Any changed
   bundle, including v5 with the wrong newest reference, must compare equal to the announced stand-in. The VM
   requires the real comparison before starting the route. Tests in `test_release28_rehearsal`:
   `test_only_verified_v4_may_defer_and_never_qualifies`,
   `test_a_new_bundle_with_another_newest_reference_must_not_defer`,
   `test_changed_v4_tools_or_release_are_not_an_unchanged_baseline`,
   `test_vm_route_cannot_accept_the_uncut_baseline`. The local walk uses the real R28 record once it exists,
   so a subsequently cut payload is compared with that record rather than a made-up digest.

2. **Real guide binding.** `release28_walk.matches()` binds the real commit's OWNER-TOOLS.md line 1 to the
   rehearsed version and short fingerprint and line 3 to its full fingerprint. Other guide text may change.
   Announced receipt rows carry the fingerprint and version as well as the tree/blob hashes. Tests:
   `test_a_real_commit_matches_only_with_the_same_tree_and_release_blob`,
   `test_real_guide_binds_line_one_and_full_fingerprint_but_allows_other_text` (each fingerprint line can fail
   independently; unrelated prose remains allowed).

3. **Step 2 handoff, intentionally not implemented here.** After PR #58 merges, use its real checker through
   its supported interface, bind the checker source, retain and validate its results and the state-folder
   metadata, prove that Control adds no login-ordering dependency, and repeat the Control checks on the final
   R28 boot. Remove the step 2 pending guard only with that implementation and its regression tests, then enable
   CONTROL_RIDES and regenerate the receipt. The assumed installed checker and its canned success response are
   removed. Step 3 reports `control_checked: false`; enabling Control cannot qualify a VM before step 2 is done.
   The sites-list persistence preparation still runs locally in both configurations. Tests:
   `test_control_qualification_stays_blocked_until_step_two`,
   `test_only_sites_persistence_runs_when_control_rides`.

4. **Runtime polkit and terminal PATH.** `release28_walk.rehearsal()` calls package 27's `terminal_path()` after
   reopening the terminal, then `polkit_sweep()` while that desktop session is active. Both results are retained.
   `WalkTest.test_every_stage_of_brief_b_passes` requires both calls in that order; the owner-walk failure test
   injects a missing daily PATH and an extra passwordless polkit authorization, and requires a STOP.

5. **Usable home-state fixture and persistence.** `release28_walk.APPS_CONFIG`, `HOME`, `home()` and
   `home_unchanged()` plant a schema-4 representative pinned Terminal helper app, including a saved town place,
   names and baseline. The fixture is owned by ares; a separate program executed as ares opens required files,
   traverses required directories/links and checks that apps.json is readable and writable. Snapshots include
   SHA-256, UID/GID, permissions, file type and symlink targets, including directory metadata. Required files
   include instance.cfg, mmc-pack.json, the managed marker, game options, libraries/mods/saves and apps.json.
   The R27 boot must preserve every entry. After forward, every stable entry must still match. Explicit allowances:
   instance.cfg's `lastLaunchTime`, `lastTimePlayed`, `totalTimePlayed` values; content/presence under
   `minecraft/logs` and `minecraft/crash-reports`. Existing mutable entries retain their metadata; all entries
   must remain owned by ares. Timestamps are not compared. No other instance files are exempted.
   Tests: `WalkTest.test_every_stage_of_brief_b_passes`,
   `Release28ProbeTest.test_injected_guest_failures_stop_the_route` (wrong ownership, permissions, missing
   mmc-pack.json, changed stable content and changed instance-directory mode),
   `test_explicit_prism_allowances_preserve_stable_files` (allowed content changes pass).

6. **Receipt setting.** `reviews/42-release-28/walk-host.py` explicitly passes CONTROL_RIDES to the local walk
   and records it in host-walk.json. `owner_vm.main()` calls `release28_walk.receipt_setting()` before guest setup
   or saving the package's binding table; missing, malformed or mismatching settings STOP. Tests:
   `ReceiptTest.test_generator_records_the_production_setting_and_passes_it_to_the_walk` (both settings),
   `test_vm_driver_rejects_an_opposite_setting_before_guest_setup` (actual driver entry).

7. **Execute submitted probes.** `os/tests/test_owner_walk.py`, `Release28Session`, now evaluates the submitted
   Python programs using an isolated temporary filesystem and controlled imports/process interfaces. It executes
   the session/theme/font, foot-ending, terminal, home (including its ares child), JVM/cgroup, polkit and PATH
   programs. Unmodelled process commands fail; they cannot reach the laptop. Sites writes are parsed from the
   submitted command and hashes are calculated from fixture bytes. The injected failures change those process
   or filesystem observations, not returned probe answers. `test_injected_guest_failures_stop_the_route` covers
   retained foot, changed sites bytes, wrong ownership, missing instance file, bad permissions, changed stable
   file, changed directory mode, wrong memory.high, extra polkit grant and broken PATH. Every case must raise
   STOP. `test_removing_the_submitted_kill_no_longer_gets_a_canned_success` also removes pkill from END_FOOT and
   requires the route to stop. These are local regression checks, not guest evidence.

8. **Installer fidelity.** `Release28Local.run()` recognizes an identical fingerprint before checking versions,
   returning the real tools' no-change message without altering the installed entry, journal or receipts.
   `Release28InstallerTest` separately covers identical bundle, same-version/different bundle, downgrade and
   newer bundle; refusals and the no-op preserve the model's installed state, while the newer bundle records
   both fingerprints and versions.

## Verification

Commands were run one module at a time from the worktree root, using exactly:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'
```

| Module | Result printed |
| --- | --- |
| test_release28_rehearsal | Ran 38 tests in 34.828s; OK |
| test_owner_walk | Ran 34 tests in 289.728s; OK |
| test_tools_local_wiring | Ran 42 tests in 59.703s; OK |
| test_release27 | Ran 41 tests in 7.408s; OK |
| test_release28 | Ran 59 tests in 14.394s; OK |
| test_ways_back_probe | Ran 57 tests in 154.413s; FAILED (failures=2) |
| test_rehearsal_budget | Ran 4 tests in 0.035s; OK |
| test_rehearsal_auth | Ran 9 tests in 0.075s; OK |
| test_owner_capabilities | Ran 6 tests in 0.166s; OK |

The two ways-back failures are the `reorder-probe` and `ways-back` cases of
`RunnerTest.test_the_probe_reads_package_22cs_host_walk_and_refuses_a_stale_one`, both at owner_vm's unchanged
`Host walk is stale` assertion. A read-only comparison of that test's effective receipt against the worktree
identifies exactly `os/ci/owner_vm.py` and `os/tests/test_owner_walk.py`: their hashes in the lead-owned pending
list predate these fixes. That list was not refreshed and no test was bypassed. The lead must refresh it after
merging, as instructed, then rerun the module. This run is not a claim that all nine modules are green.

Before each test_owner_* invocation, the two required pgrep commands printed nothing. Running them initially
inline matched only the sandbox's own command wrapper; no owner module started on that result. Subsequent
checks used a worktree-local script to avoid that self-match, and reported `Owner-tools preflight: no matches`.
The same preflight is used for receipt generation, which invokes the local owner walk.

Receipt regeneration, after the final source changes:

```text
PYTHONDONTWRITEBYTECODE=1 python3 reviews/42-release-28/walk-host.py
PASS package 42 host walk (release-28): 267 sources; no VM started
```

A separate read-only hash comparison printed `PASS receipt: 267 source hashes match; Control false; 8 boots`.
The receipt records 176 checks, 822 commands and 542 typed blocks. `git diff --check` passed with no output;
`git diff --exit-code -- os/owner-tools/ reviews/42-release-28/PROGRESS.md` also passed with no output.
The closing `find .work -type f -size +500000000c` check printed nothing: no files over 500 MB remain there.

**Commit blocked by the environment.** Both `git add` and the intended local `git commit` failed with
`Unable to create .../index.lock: Read-only file system`. The worktree's Git admin directory is mounted
read-only in this session, despite the repository files being writable. No commit was created and nothing
was pushed. The intended implementation commit's last message line was exactly
`Codex-Model: gpt-6.1-sol (xhigh)`; the notes and regenerated receipt were intended as a second local commit
with the same trailer. All changes remain in this worktree for the lead to commit with that trailer.

Early development runs of `test_release28_rehearsal.py` reported 26 tests with 1 failure and 2 errors, then 26
with 1 error: the new match contract required fingerprint/version in its test records, the test needed to
expect baseline deferral refusal, and the controlled Path fixture needed its Python 3.14 initializer and /tmp
directory. Those were fixed. Subsequent runs reported 35 tests OK and 36 tests OK before the last regression
cases were added. No assertion was weakened to make a failure pass.

The first `test_owner_walk.py` run reported 34 tests in 282.320s, with 1 failure and 1 error in the injected
wrong-owner and permission cases. The controlled Path now overrides lstat as well as stat, so snapshots observe
injected ownership; simulated permissions also let the root snapshot read while denying the ares child, rather
than denying the laptop user access to the temporary file. The same failure assertions remain in place.

## Not verified / judgments 4 and 6

- **Judgment 4:** starting the Terminal app's exact argv in SETUP, with the session environment, does not prove
  clicking its app in the Minecraft hub works. That remains an owner/real-game check.
- **Judgment 6:** the paused real-JVM wrapper probe in a future VM run can prove scope placement and memory.high;
  it does not prove a real Minecraft world starts, that Minecraft loads apps.json, or that the home screen looks
  right. No VM or JVM was started in this fix run; local process observations are fixtures.
- The real R28 announced commit is still uncut here. Its equality check and the complete guest round trip remain
  for the permitted VM runs in step 6. Local baseline deferral is not final release qualification.
- Control's checker, metadata and login ordering remain step 2 work after PR #58. No Control qualification is
  claimed here. Full hosted checks and mod/client tests were not run; this change touches only the OS rehearsal.

No new owner-facing design choice. The explicit mutable-file allowances and the pending Control guard are
reversible rehearsal constraints. Open questions remain with the lead's step 2 and step 6 work.
