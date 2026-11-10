# 22: review fixes, round 3

Follow-up on `pkg/22-update-route` (PR #32). Read `reviews/22-update-route/REVIEW-3.md` (CHANGES-NEEDED; intent journalling, retry wording, interrupted renames, hashes and pins are confirmed). Fix the one High finding as the review proposes:

1. **Block first, then check.**
   - Before draining or scanning, make **every** legacy entry path unusable, `/var/lib/ares/at` and `/var/lib/ares/tools/at` alike, plus any other path the 15f tools can be started through. Then scan for running legacy commands, and only then rerun the full system preflight, all under that exclusion.
   - A command that started and finished before the block can't leave stale preflight results, because the preflight runs after the block.
   - Keep the guarantees from round 2: entries restored on a refusal and at completion, held again on a resume, and an interrupted rename recovers through the bootstrap.
2. **Tests at the boundary:**
   - an invocation through each legacy path at the final scan/swap boundary is impossible or refused;
   - a legacy command that starts and finishes between the old scan point and the swap doesn't leave the update on stale checks;
   - an interruption with the entries blocked recovers.

Keep the fingerprint, the pins and `pending-rebind.json` exact. Rerun the focused owner suites and one full WSL suite, plain and `-B`. Use package-unique script and `/tmp` names (e.g. `pkg22-…`), because agents share the scratchpad. Add a "Review fixes 3" section to the REPORT, then push.
