Reviewed commit `59da088348b3fdafe5585a1b3620d8e21f3fb571`, read-only: no files changed; no helper, tests or builds executed.

Scope: `c22ecd87..HEAD` in the requested helper, tests and report section. Test and mutation-test assessments are from static inspection; reported execution results were not independently reproduced.

| Point | Status | Reason |
|---|---|---|
| 1 | OPEN | The original cache-feedback loop is closed: rejected targets no longer supply the saved stat, wrong-kind objects normally retain inode/kind only, and cached conversions avoid chmod. However, an absolute link within the refused path can hide a later replacement, and parent-directory changes can repeat an unchanged index’s warning. Both findings are below FIX severity. |
| 2 | CLOSED | Confined dangling candidates are recorded as missing. Creating their target changes the signature and permits one pass; outside targets remain excluded. |
| 3 | CLOSED | A follow-up requires both a quota refusal and successful pruning of a counted file. A cache full of retained pictures settles without periodic retries. |
| 4 | CLOSED | Missing header, missing `Directories`, and an empty directory list now trigger the logged fixed-layout fallback. Unusable individual Size/Scale entries remain omitted. |
| 5 | OK | Readable opens retain descriptor-based confinement. Picture ordering, converter sandbox and limits, and pruning’s deletion selection are unchanged. No changes outside picture code were found; `shell-1.1` example messages are unchanged. |
| 6 | OK | The asserted regressions follow from the old code, and the report identifies preservation controls. Fixtures and executable stand-ins avoid dependence on Breeze or the registry’s installed programs. FIFO cases do not read the FIFO. The two cases below lack coverage. |

1. **SHOULD — An absolute intermediate link hides replacement of a later refused link.**

   **Where:** `os/config/usr/libexec/aresos-shell:1287` and `:1301`.

   **Scenario:** Let `R` be an icon root. `R/breeze/index.theme` points by an absolute symlink to `R/metadata/index.theme`, which itself points outside the allowed roots. Pictures exist under Breeze’s indexed layout, but not its fixed layout.

   The refused-path walk records the outer link, resets `current` to `/`, then stops at the first absolute-path component outside `R`. It never records `R/metadata/index.theme` or its parent.

   Replace only that inner link with a valid regular index. This changes `R/metadata`, but neither `R`, the Breeze directory nor the outer link. The saved signature remains equal, so no pass runs and the pictures remain missing.

   Handle absolute targets within allowed roots without prematurely stopping at their filesystem ancestors, and add this two-link replacement case. This is a persistent missing-picture defect in a rare layout, so it is **SHOULD**, not FIX.

2. **NIT — An unchanged rejected index can warn again when its parent changes.**

   **Where:** `os/config/usr/libexec/aresos-shell:1294` and `:1434`.

   **Scenario:** `R/breeze/index.theme` is an unchanged symlink outside its root. After the first warning, create an unrelated file directly in `R/breeze`.

   The parent directory’s timestamps are part of the index’s saved “way.” Its signature therefore changes, and `warned[path] != self.seen[path]` emits another warning despite the index link being unchanged. The existing warning test changes a picture in a different directory and misses this case.

   Use an index/link identity suitable for warning suppression separately from the broader invalidation dependency. This produces unnecessary logging, without self-sustaining retries or owner-data harm.

The traversal’s limits need precise documentation. The new walk stops after at most 40 symlink expansions and does not read FIFOs. However, `note()` first calls `realpath()` (`:1396`), which can probe metadata beyond an outbound link; `open_confined()` also obtains a metadata-only `O_PATH` descriptor before rejecting the resolved location. Thus the report’s claim that nothing behind a refused link is ever looked at is too broad. Readable content and directory listings remain confined. A dead mount can still stall the icon worker, while helper serving remains separate. Rapid path swaps and hostile same-user interference remain the documented timing limits, not new FIX findings.

VERDICT: SAFE with documented known limits