Checked only `a684496..ece0d22` against the four findings and regressions from their fixes.

1. **Fixed — failed-save cleanup.** [files.py:150](/Users/pab/AresOS-18-control-base/control/aresos_control/files.py:150) truncates and fsyncs the pinned inode without unlinking a pathname. [Regression tests](/Users/pab/AresOS-18-control-base/control/tests/test_files.py:181) cover preserving replacements, emptying outside aliases, and reporting rollback failures. Empty remnants are explicitly reported.

2. **Fixed — expiry during adapter checks.** [engine.py:106](/Users/pab/AresOS-18-control-base/control/aresos_control/engine.py:106) rechecks expiry immediately before `submitting`, records `failed`, and calls `drop`. Tests cover both checks for send/delete, no effects, repeated approval, and restart.

3. **Fixed — positive delivery evidence.** [engine.py:96](/Users/pab/AresOS-18-control-base/control/aresos_control/engine.py:96) durably records `unknown` before fetching evidence details. Tests cover cancellation, expiry, restart, replay, and detail-fetch failure; none revert to “nothing submitted.”

4. **Fixed — large hook input.** [hooks.py:27](/Users/pab/AresOS-18-control-base/control/aresos_control/hooks.py:27) reads complete stdin and parses inside error handling. Subprocess tests exercise both hooks with inputs over 190 KiB; malformed input receives explicit exit-2 feedback.

No regressions found within the requested scope.

Independent in-memory expiry, evidence, replay, and hook checks passed; artifact drift checking passed. Both saved final-head CI logs show 40 tests passing. I did not rerun the Linux container suite or verify CI live; GitHub was unreachable.

SAFE