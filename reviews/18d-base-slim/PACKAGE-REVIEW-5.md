Reviewed `59def857..88151b1c`. Two FIX findings remain.

1. **FIX — Filesystem timestamps remain ambient and unguarded.** [sweep_scripts.py:25](control/mail_tests/sweep_scripts.py:25) does not cover the kernel-generated modification times read by [blob expiry](control/aresos_control/blobs.py:142). The export flows reach this code through retention checks; patching Python’s clock does not control their blobs’ filesystem timestamps.

   With all six scripts active, a focused production `Blobs.expire` probe changed only `st_mtime`: one case performed no writes; the other performed two unlinks and directory synchronization. Neither raised `AmbientRead`. The source audit and 91 mutation checks therefore miss an input that can change the write trace.

   **Fix:** script fixture blob timestamps, guard unscripted timestamp consumption, and add omission checks for every consuming flow, including fault/recovery paths. Preserve the real expiry writes.

2. **FIX — Nanosecond ordering still disagrees with float-backed notice ordering.** [sweep_scripts.py:101](control/mail_tests/sweep_scripts.py:101) freezes `time.time()` while advancing `time.time_ns()`. Recovery notices derive their timestamps from the float-backed retained creation time at [recovery.py:94](control/aresos_control/recovery.py:94).

   A focused in-memory probe using production warning creation and `notice_page` produced an earlier checked warning at `1794225600123456769`, then a later intent/recovery warning at `1794225600123456768`. The newest-first page displayed the earlier warning first. The [new ordering test](control/mail_tests/test_review23_sweep.py:721) compares only nanosecond reads, so it misses this reversal.

   **Fix:** coordinate every timestamp used for notice ordering through one scripted chronology. Test actual notice pages with checked warnings before and after later recovery sources, including expiry-clock restoration.

3. **KNOWN LIMIT — Final Linux acceptance remains pending.** The saved before/round-1 Linux logs independently match across all 23 flows: **6,642 points; 6,302 single, 6,302 persistent and 15,915 cleanup-pair cases**. Final-head [Mail run 43168691382](https://github.com/Ares-Empire/AresOS/actions/runs/43168691382) was still executing attempt 1 at review time. Final counts, two complete passing attempts and compliance with the 35-minute job limits remain unproven.

   **Resolution:** finish both attempts and record final per-flow counts and job durations.

No production code changed. AST comparison confirms unchanged flows, sweep modes, cleanup-pair enumeration and existing recovery/completion assertions. The originally failing lifecycle test now passes in [final-head Linux attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/43168691382/job/131016510335). The reported `Scenario` consumer list matches the source search.

Independently ran six CI-selection tests, the ambient-source guard test, generator verification and whitespace checks: all passed. Full filesystem sweeps were not rerun in this read-only review.

CHANGES-NEEDED