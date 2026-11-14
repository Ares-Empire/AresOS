Reviewed commit `991c0e5643ef1fc518a6956b82d54cb09fcb2018` — read-only review of `81ac8dd0..HEAD`; no files changed and no builds, tests or game runs performed.

| Point | Status | Reason |
|---|---|---|
| 1. Whole-town freeze | CLOSED | The seal rule covers restored subsets, restored empty files, missing `town.dat` with a remaining seal, older-mod saves and interrupted writes. A whole-world copy retains its seal; foreign records with the same home fail the fingerprint check. C5’s empty-town exception is implemented as specified. The freeze blocks reconciliation, rebuilding, road paving and doorway restoration, survives saves and reopening, and ends through host-only trust. |
| 2. Hand-built signs | CLOSED | New gates persist optional position and text evidence. Removal requires matching display type, position and text; missing evidence preserves the entity and produces the retained-sign reply. The historical packages 33–35 codec matches the test’s model: it reads the gate and drops the unknown field when re-encoding. |
| 3. Picture-reader cleanup | CLOSED | The single-thread executor barrier runs after the read task completes its synchronous cleanup callback, before the test checks `waiting()`. |
| 4. Existing behavior | OK | No regression found in refusal and load validation, light ownership, town sign/zone checks, picture shutdown, names, doorway recovery, first-build aggregation or package 33 gates. C2 correctly allows My apps to announce newcomers while frozen. The changes preserve apps.json and hub.dat formats and town.dat’s encoded shape. |
| 5. Tests and suite safety | OK | The principal regression claims hold by inspection. Tests cover omitted and empty records, frozen save/reopen, trust renewal, non-host rejection, persisted refusal and sign preservation. Fixtures use plot-relative locations and their own chunk tickets. Client-test ordering is unchanged. Remaining coverage gaps are described below. |

No new FIX, SHOULD or NIT findings.

The freeze is enforced before assignment, picture lookup, saved-place changes, removal, renewal, doorway recovery and roads in `TownKeeper.keep` (`mod/src/main/java/dev/aresos/hub/TownKeeper.java:311`). The scheduler also stops before starting picture work while frozen. `Town.build` and `Town.remove` provide additional guards. App removal, changed names or pictures, and repeated passes therefore cannot create a second logo from an incomplete ledger. The rebuild command checks the freeze before the complete-list requirement and returns its line.

`HubData.sealable()` excludes frozen and refused towns. Consequently, saving a frozen town does not repair its seal. Pre-server seal carrying changes only the timestamp of a previously matching seal; it does not repair a mismatched town fingerprint. Trust clears the boolean, requests a fresh pass and allows the next save to seal the resulting records. The parsed `hub` node requires `AppCommands.allowed`, and the trust handler independently checks the host and rejects refused files. No other production path found clears an existing freeze.

Hand-built `/aresos logo` gates remain available as explicitly required. Their removal uses their own saved sign plan; town removal reconstructs its plan from the town record, and immediate build rollback uses the plan just built. All reach the same `made` check, which now rejects missing evidence. No reviewed cleanup path discards a text display on its UUID alone. Blank short names normalize to null without changing rendered text, fixing equality after rejoin. Town records deliberately omit the new hand-built sign field, preserving their fingerprint representation.

The report’s “from reading” regression claims are sound:

- Restoring the previous per-logo behavior permits another Discord logo in the subset scenario and a Mail logo in the older-mod scenario; the new assertions detect both.
- Restoring the empty-ledger bypass defeats the empty-file freeze assertion.
- Restoring UUID-only hand-built cleanup removes the edited, relocated/reused-ID and legacy-record signs that the new test requires to remain.
- The non-host trust assertions exercise an existing restriction and appropriately are not claimed as a newly failing regression.
- The picture-reader race is removed by ordering; its old failure was nondeterministic.

One narrower test limitation: `AppZoneTest.java:53` checks that a blank short name decodes as null, but that assertion alone would still pass without the constructor normalization, because encoding already omits blanks. The existing package 33 client rejoin equality assertion is the meaningful regression check for `a857e8a7`, consistent with the report.

The most important remaining untested path is **host trust through the real command followed solely by scheduler ticks**. The server regression calls `TownKeeper.trust` and then explicitly invokes `fake.pass` (`TownGameTests.java:1021–1024`); it would not detect a missing scheduler wake-up. Inspection confirms the current `ask()` wiring. There is also no targeted frozen-world test with an already-missing doorway, nor an end-to-end check of C2’s My apps announcement. The guards and announcement routing are correct by inspection.

The builder’s reported runs were not reproduced. The four documented limits remain accepted: failed level-data writes, crashes during saves, explicit trust adopting the available records, and concurrent external world-folder writers.

VERDICT: SAFE with documented known limits