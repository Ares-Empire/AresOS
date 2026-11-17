# 43 step 1: review (Codex gpt-6-astra high, 2026-11-17)

Reviews `8a18b688`. Read-only sandbox: test errors from temporary-file creation are environmental.

Two **should-fix** findings in `8a18b688`:

1. **should-fix — [owner.py:1936](os/owner-tools/owner.py:1936): predictable updater-mask refusals follow the announcement.**  
   If an updater is already unmasked, or a finalizer has an unexpected configuration, `newest` announces “installing … Restart to finish,” verifies the signature and writes the intent before [update.sh:25](os/release/update.sh:25) checks that configuration and refuses. These are existing, read-only facts that could have been checked before the announcement, contrary to D4.

   **Fix:** run the mask/policy preflight before announcing, retaining the script’s checks against subsequent changes. Add announcement-order tests for these refusals. The current `newest` fixture bypasses those shell checks when it extracts the staging command at [test_owner_update.py:284](os/tests/test_owner_update.py:284).

2. **should-fix — [owner.py:1815](os/owner-tools/owner.py:1815): the final instruction uses stale outer-survey facts.**  
   `forward()` rereads the deployments, but the appended sentence still uses the outer `installed` and `runs` values. I reproduced this entirely in memory: R21 runs, stock starts next, and the tools carry R30. An external deployment change replaces unbooted R13 with R30 between the surveys. The inner operation correctly announces switching to installed R30 with a restart required, but the final sentence says:
   > These tools also carry a newer version, AresOS 30. No restart is needed first. The next sudo /var/lib/ares/at newest installs it

   R30 is already installed, and a restart is required to run it.

   **Fix:** derive the suffix from the inner operation’s validated state, including its already-first path. Add a regression that changes installed membership between the two surveys.

Read-only checks passed for payload/source equality, fingerprint `2f939db9…`, generated commands, `newest` registration, release-record agreement, malformed-number refusals, history preservation, and D18 source scans. The worktree remains unchanged.

Single-module runs used the prescribed command form; all errors below were temporary-directory failures caused by the read-only sandbox:

| Module | Printed result |
|---|---|
| `test_owner_cwd.py` | 6 tests; errors=6 |
| `test_owner_session_program.py` | 2 tests; errors=4 |
| `test_owner_equality.py` | 11 tests; errors=3 |
| `test_checkout_sources.py` | 8 tests; errors=5 |

CHANGES-NEEDED