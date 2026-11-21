# 42 step 3: fix check round 2 (Codex gpt-6-astra high, 2026-11-17)

Checks `23311f42` (REVIEW-6 fixes, notes in FIXES-6.md) at merged head `c39d48cc`. Read-only sandbox: test errors from temporary-file creation are environmental; the lead ran the modules locally (all OK, `c39d48cc`).

All three REVIEW-6 findings are **fixed**. No new blocking, should-fix or nit findings in the reviewed changes.

| Original finding | Verdict |
|---|---|
| Wrong instance layout | **Fixed.** Required links match the provisioner: instance-root `patches` and `libraries`, plus `minecraft/mods` and `minecraft/saves`. The fixture now obtains the layout from `expected_links()`. |
| R27 requires R28 targets | **Fixed.** Rollback verifies retained link text and home data without requiring R28’s image targets. Initial and final R28 checks still require those targets. The model now removes them during R27 boots. |
| Saved-world loss goes unnoticed | **Fixed.** The probe seeds level and region data, snapshots the resolved saves directory, and compares contents, ownership, permissions and entry types across both transitions. It also reads the data as `ares`. |

For these home-state checks, a correctly provisioned R28 and intact R27 rollback should pass without the previous false STOPs. Missing or redirected instance links, lost or changed `apps.json`, and deleted, corrupted or inaccessible synthetic save data stop qualification. The actual VM round trip remains unverified.

Verification:

- Ran `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p 'test_release28_rehearsal.py'`: **30 tests, 12 errors**, all caused by sandbox write restrictions—not counted as code failures. The new home tests could not execute.
- Skipped `test_owner_walk`: `ksshaskpass` preflight printed nothing, but the second `pgrep` matched the sandbox wrapper.
- All **268 receipt source hashes match**; `git diff --check` passed. No files edited.

SAFE