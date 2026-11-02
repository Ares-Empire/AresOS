# 14l: Owner's October margin decision, 2026-10-26

For package14 only: cap420, org reserve60; probe allowance6 and owner-tools2
stay unchanged, as does package13. The bound is230 consumed +6 for this push
+184 for probe/native, qualification and closing privacy. Org free at16:30Z
was251; fresh billing and complete history still decide whether dispatch fits.

Record this decision, settings, REPORT and refreshed bindings in one commit
and exactly one fast-forward push before dispatch, with pinned gitleaks first.
Then replay14e/14f and14i strict checks; require exact-head privacy, fresh
ledger/billing, probe6, and only after it passes qualification2 on that head.
Any guard refusal or run STOP means report, no retry or lower limit. No other
push before qualification finishes. After acceptance restore reserve150 and
update the cap/accounting note in a final commit; mark PR13 ready, never merge.
All inherited privacy, token, device, release and stop rules remain in force.
