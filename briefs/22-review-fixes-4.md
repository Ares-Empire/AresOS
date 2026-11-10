# 22: review fixes, round 4

Follow-up on `pkg/22-update-route` (PR #32). Read `reviews/22-update-route/REVIEW-4.md` (CHANGES-NEEDED: two High findings, both in the tools self-update). Four rounds have now found gaps in this one step, so fix it by two invariants instead of more special cases. State both invariants in the REPORT, and write a test that drives each one.

1. **Always one working toolset.**
   - At every instant, including after an interruption at any rename or write, exactly one complete, verified toolset is either in place, or restored automatically by the next run of the same bootstrap or by any refusal.
   - Order the swap so the old tools are retired **only after** the new tools are published and verified. A refusal, or a resumed refusal, before publication restores the held or retired verified copy, durably and resumably.
   - Test: an interruption between every pair of renames, followed by a refusal, leaves `bash /var/lib/ares/at` working (old or new tools, never none). Also cover a persistent preflight failure.
2. **Detect broadly; false positives only refuse.**
   - A legacy command counts as running if any process has an argument that resolves, relative to that process's `/proc/<pid>/cwd`, into the installed tools directory or the held or retired copies. This covers any interpreter flags (`-B` without `-I` and so on) and relative paths.
   - Also count a process whose cwd or an open file descriptor lies there.
   - When in doubt, refuse.
   - Test a real legacy invocation without `-I`, one with a relative script path, and one started through each entry path, across the block/swap boundary.

Keep the fingerprint, the pins and `pending-rebind.json` exact. Rerun the focused owner suites and one full WSL suite, plain and `-B` (package-unique names, at least 4 GB free, one suite at a time). Add a "Review fixes 4" section to the REPORT, then push.
