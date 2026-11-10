- **Medium — [test_owner_update.py:1042](C:/Users/pab/AresOS-22-update-route/os/tests/test_owner_update.py:1042): a hung bounce still passes.** `works()` replaces the first result whenever stdout contains `not the installed entry`, even when `timed_out=True`; a successful rerun hides that hang. The refusal assertions at lines 1185, 1219 and 1228 likewise ignore timeouts and accept partial text. **Fix:** require termination and the complete expected refusal before accepting or retrying; add regressions for refusal text followed by a hang.

The confirming task snapshot closes the reported handoff race; I found no new unconditional refusal or whole-PR recovery blocker. `reached()` now requires markers, and intentional sleepers are separate. Payload hashes, fingerprint pins, both bootstrap blocks and exactly 17 pending bindings match.

Static review only: Python unavailable; WSL access denied. No files edited.

CHANGES-NEEDED