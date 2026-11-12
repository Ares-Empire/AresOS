# 21: review fixes, round 5

Follow-up on `pkg/21-everyday-account-and-chrome` (PR #31). Read `reviews/21-everyday-account-and-chrome/REVIEW-5.md` (CHANGES-NEEDED; the Flatpak guard and the `vm.py` hash are confirmed, and no bypass was found). Fix both Medium findings as the review proposes:

1. **`journal_ready.py`:**
   - Use `[ \t]*` instead of `\s*`, and make sure no part of the pattern can span a line break.
   - Add regressions that reject `\n` or `\r` inside the timestamp or anywhere before the message.
   - Regenerate the pending hash if a bound file changes.
2. **Session startup must not depend on PATH:**
   - `aresos-session`, `aresos-keyboard` and every other startup or recovery script use absolute system paths, e.g. `/usr/bin/dbus-run-session`, `/usr/bin/labwc` and `/usr/bin/busctl`, for everything they run.
   - Test: put broken shadowing executables for each of them first in `~/.local/bin` and check that the session and the recovery shortcut still start.

Rerun the native regressions and the in-image checks. If startup scripts changed, rerun the VM pass too. Commit the evidence. Board #156 is still open; keep its behaviours. Add a "Review fixes 5" section to the REPORT, then push.
