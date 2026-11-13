No **FIX** findings in `14a2ff43..8bfe75ec`, excluding the brief, under the owner’s stated bar.

- **Expiry remains exercised.** The sweep still advances to `expires_at + 1`; maintenance advances by 86,401 seconds. The separate required tests for the 900-second limit and expiry during adapter checks are unchanged. Freezing ordinary replay scenarios keeps approvals unexpired, so expiry cannot accidentally substitute for replay protection.
- **Protecting assertions remain intact.** AST comparison confirmed unchanged recovery, replay, single-execution, duplicate-copy, completion and preservation checks. Untrusted marking and credential protections are unchanged; their existing tests remain selected.
- **Coverage selection is preserved.** The same 23 flows retain every discovered primary fault point, single/persistent modes, cleanup pairs and exact trace-prefix assertions. The two new regressions join the existing required sweep module. No CI selection or workflow changed.
- **No production code changed.** Clock/calendar/UUID patches are confined to fixtures. In-memory checks passed for deterministic but distinct IDs, nested time advancement, patch restoration, constructor-failure cleanup and the owner-oracle subclass exemption.

Verification: all **six CI-selection tests passed**, along with the AST and fixture-isolation checks. Storage setup was stubbed only for those isolation checks; I did not rerun the storage sweep or run containers.

**KNOWN LIMIT — validation evidence:** final-head CI was still running when inspected, including all eight [Mail jobs](https://github.com/Ares-Empire/AresOS/actions/runs/43162099390). Two complete green passes and Linux before/after coverage counts remain unverified here. This verdict covers the scoped security fix, not completion of CI acceptance.

SAFE