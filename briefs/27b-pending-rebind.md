# 27b, part 2: bound files may change again after a rehearsal

Follow-up to `briefs/27b-laptop-update-record.md`, on the same branch. The builder stopped where that brief told it to: `os/tests/test_owner_path.py` is bound by package 27's host walk, and `os/tests/test_checkout_sources.py` demands an empty waiting list for as long as package 27's bindings exist. So no bound file could change until the next rehearsal, which would block packages 23, 22c and 21b as well.

**Decision (integrator, 2026-11-13):** the waiting list reopens. `os/manifest/ci/16/pending-rebind.json` already states the rule: a bound file that changes after a rehearsal records its new bytes there deliberately, and the next VM rehearsal rebinds it and empties the list. The check that the list is empty exactly when package 27's bindings exist described the moment of that rehearsal; it is not a rule for the time after it. No rehearsal evidence is regenerated or edited.

**In scope:**

1. `os/tests/test_checkout_sources.py`: replace the "empties exactly when" check with rules that hold at any time:
   - every waiting path is a bound path, and no path is listed twice;
   - every bound file that is not waiting replays its walk bytes;
   - every waiting file differs from its walk bytes and matches the bytes recorded for it.
   The comment says what the list is: empty right after a rehearsal, one row per bound file changed since.
2. `os/manifest/ci/16/pending-rebind.json`: record the bound files this branch changes, with their new bytes. Its status says it waits for the next VM rehearsal. Keep the history of what package 27 rebound readable, and make it unambiguous which changes wait now. Its `approved` field records the owner's OK of 2026-11-08 for using changed tools on the laptop; that stays history. For 27b say what is true: only test files wait, no tool, guide or image file, by the integrator's decision of 2026-11-13.
3. `rebind.py pending` compares with package 16's tables only. If making it compare with the active tables (the ones `checkout.active_tables` returns) is a small change, make it and test it, so the next packages have a working tool. If it is larger or entangled, write the rows by hand and name it as a PLAN-GAP in the report.
4. One more cell in `docs/INSTALL-STATUS.md`: where the Physical installation row says which release is installed, add that the step 8 update to R27 passed on 2026-11-13. Leave the other rows; list in the report those that still describe the time before the update.

**Out of scope:** the bindings and host walk under `os/manifest/ci/27/`, any tool, guide or image file, a new rehearsal.

**Acceptance:**

- `test_checkout_sources`, `test_owner_path`, `test_owner_equality` and every module that reads `pending-rebind.json` pass.
- Revert proof for the new rule, shown in the report: a waiting file changed again without its row fails; a listed file that still equals its walk bytes fails; a listed path that is not bound fails; a bound file changed without a row fails.
- The first brief's acceptance still holds.

**If unsure:** keep the stricter check and say so in the report.

**Model:** the same Opus builder. Review: a fresh Codex context, told that this loosens a rule of the binding test and must not let an unrecorded change through.
