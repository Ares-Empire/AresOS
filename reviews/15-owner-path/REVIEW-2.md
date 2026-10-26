Reviewed `089c7c4..e4c62c6`, limited to the fixes and touched areas.

1. **FIXED — Battery action.** Starts with stopping use and safely disconnecting external power, separates the already-open case, and retains no handling/reconnection and service clearance. Sources now follow the [LOQ guide’s safety-reference chain](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/read_first.html).

2. **FIXED — Guarded reboot.** Step 7 uses the canonical command. Static checks found no noncanonical owner invocations and confirmed expected results beside all eight reboot occurrences. New mutations reject bare inline reboot and extra arguments; existing equality assertions remain.

3. **FIXED — Boot-order STOPs.** All three anomalies explicitly lead to Help and name step 8 as the return destination.

4. **FIXED — Reported context-dependent returns.** Keep-stock records return through keep-stock completion to step 8. AresOS layout recovery follows revert → fresh proof → finish → completion → step 8. Mutation tests cover wrong destinations and skipped finish.

5. **FIXED — Release boundaries.** Historical R06 results and current R13/13f evidence are explicitly separated, preserving drive-order, recovery-menu and physical-test limits.

**New problem — should-fix:** The new mandatory [calling-context table](C:/Users/pab/AresOS-15-owner-path/docs/INSTALL-RECORD.md:209) omits everyday boot-order restoration. [Step 8](C:/Users/pab/AresOS-15-owner-path/docs/INSTALL.md:187) requires record B, but its caller has no matching return row; the table instead requires unknown callers to STOP. Add an everyday boot-order caller returning to step 8 and test that successful route.

Exactly 27 screenshots were deleted, all under `reviews/15-owner-path/screenshots/`; no other screenshot changed. The step-5 gate and its existing regression assertions remain unchanged. `git diff --check` passed. Python tests could not be rerun: no installed Python, and WSL returned `E_ACCESSDENIED`.

CHANGES-NEEDED