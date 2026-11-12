# 22: review fixes, round 7

Follow-up on `pkg/22-update-route` (PR #32). Read `reviews/22-update-route/REVIEW-7.md` (CHANGES-NEEDED: two Medium findings, no High; the entry switch, legacy exclusion, pins and bindings hold). Fix both as the review proposes:

1. **The worker-handoff race in `process_absent()`.**
   - Before returning "absent" for a thread group whose leader has exited, confirm whole-group termination **independently** of the `task/` snapshot: e.g. `/proc/<pid>/status` shows `Threads: 0`, or the process directory itself is gone, or re-enumerate `task/` until two consecutive reads agree and every thread is Z/X.
   - Any doubt counts as in use.
   - Add a synchronized regression: a worker creates a new worker and exits between enumeration and the `cwd` read. The group must still count.
2. **A hung entry must not count as working.**
   - `reached()` fails on a timeout. A pass requires an explicit marker (the 15f marker, or the new tools' own check output) or the exact expected bounce/refusal text.
   - Keep the intentional sleeper fixtures separate from this helper.

Keep the fingerprint, the pins and `pending-rebind.json` exact if the payload changes. Run the focused owner suites. Run a full WSL suite only with at least 5 GB free and nothing heavy running; otherwise report it as pending. Add a "Review fixes 7" section to the REPORT, then push.
