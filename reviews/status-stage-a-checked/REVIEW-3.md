**Should-fix — `reviews/status-stage-a-checked/REVIEW.md:1,3,5` and `REVIEW-2.md:9`: all six review links remain broken.** Targets such as `../../docs/INSTALL-STATUS.md:21` treat `:21` as part of the filename, which does not exist. Remove the `:number` suffix from each target; keep line numbers in the link labels.

Otherwise, checked `de537d6`: the full PR diff contains no local absolute paths or Windows user-folder name. `git diff 565bcd1..HEAD` touches only the two review files; installation documents and tests are unchanged. `git diff --check main...HEAD` passes. No files edited; tests not run.

CHANGES-NEEDED