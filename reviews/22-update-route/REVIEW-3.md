- **High — [owner.py:1746](/C:/Users/pab/AresOS-22-update-route/os/owner-tools/owner.py:1746): legacy exclusion still races.** `tools/at` remains executable after the final process scan, allowing a 15f command to start before the swap. A command that starts and finishes after `system_ready()` also escapes detection, leaving stale preflight results. **Fix:** block all legacy entry paths before draining/scanning, rerun system preflight under that exclusion, and test invocations at the final scan/swap boundary.

Intent journalling and retry wording look correct. Interrupted entry renames resume through the matching bootstrap. Payload hashes, fingerprint pins and all 17 pending bindings match. No additional whole-PR recovery blocker found.

Tests unavailable: no Python installed; WSL access denied. No files edited.

CHANGES-NEEDED