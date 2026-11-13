Reviewed `14a2ff43..8bfe75ec`, excluding the brief.

- **FIX — The determinism guard misses part of the clock script.** At [test_review23_sweep.py:628](control/mail_tests/test_review23_sweep.py:628), only ambient `time.time()` and `uuid.uuid4()` raise. Removing `scripted_calendar()` leaves real `time.time_ns()` and implicit `localtime()` available. Production warning records use nanoseconds; their values can change while their lengths—and therefore write traces—remain equal. Three trace comparisons cannot guarantee this regression fails every time.

  An initializer/production-warning probe with the calendar script removed produced three different `created_at` values, identical JSON lengths of 331, and no guard failure. This was a focused probe, not a full sweep execution.

  **Fix:** also reject ambient nanosecond and implicit calendar reads, and add mutation checks demonstrating that disabling each script component fails for every affected flow.

- **KNOWN LIMIT — Final Linux coverage and twice-run acceptance remain pending.** [REPORT.md:591](reviews/18d-base-slim/REPORT.md:591) correctly leaves the Linux before/after comparison outstanding. At review time, [final-head Mail run 43162099390](https://github.com/Ares-Empire/AresOS/actions/runs/43162099390) was still running. Local stubbed evidence cannot establish Linux count preservation. **Resolution:** complete both attempts on this head and record per-flow points, single/persistent cases, and cleanup pairs against the baseline.

The demonstrated mechanism supports the fix: changing timestamp precision with identical scripted IDs changes SQLite’s pre-fault write sequence. It does not identify the exact unrecorded historical timestamp.

AST comparison confirms the same 23 flows and unchanged sweep logic, fault modes, cleanup-pair enumeration, and assertions. Expiry, maintenance, and archive retain their time advances; settlement still uses visible Sent evidence. I found no newly hidden quiet-period or duplicate-detection behavior.

Required CI selects all seven tests, including both additions. Independently ran: six selection tests (**OK**), generator check (**match**), and diff whitespace check (**pass**). Full storage sweeps were not rerun in this read-only review.

CHANGES-NEEDED