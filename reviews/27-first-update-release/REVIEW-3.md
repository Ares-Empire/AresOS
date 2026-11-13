Reviewed **976d0334**, limited to the specified fixes and touched code. **One blocking gap remains.** No files changed.

1. **Blocking — an exception inside process shutdown still bypasses both shutdown and mask recovery.**  
   **Where:** [owner.py:332](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:332), [owner.py:339](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:339), [owner.py:1509](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:1509); identical payload copy.

   `step.stop()` runs outside the error-handling blocks in `stop_update()`. A concrete trigger is a non-UTF-8 process name anywhere on the machine: `members()` decodes every `/proc/PID/stat` using `read_text()`, but does not catch `UnicodeDecodeError`. Linux process names are byte strings truncated to 15 bytes, which can split a multibyte character. [Linux documentation](https://man7.org/linux/man-pages/man2/PR_SET_NAME.2const.html).

   Crucially, `stop()` evaluates `self.members()` while constructing its target tuple **before invoking even the first `killpg()`**. On timeout or interruption, that exception therefore exits with bootc potentially still running and the finalizers still unmasked. The outer STOP message does not repair this. This reproduces the laptop consequence of REVIEW-2 finding 1 through an exception rather than another signal.

   **Fix:** parse the numeric `/proc/stat` suffix as bytes; distinguish vanished processes from inspection failures; and put termination inside the protected recovery structure. An inability to prove termination must prevent reconciliation, while mask restoration is still attempted and checked. Preserve termination and mask errors together. Add regressions for an undecodable process name and a shutdown/scan exception.

2. **Nit — the real-survivor test leaks its surviving process.**  
   **Where:** [test_owner_update.py:1930](C:/Users/pab/AresOS-27-review/os/tests/test_owner_update.py:1930), [test_owner_update.py:1987](C:/Users/pab/AresOS-27-review/os/tests/test_owner_update.py:1987).

   `addCleanup()` receives a PID-file path inside `run_stopped()`’s temporary directory. That directory is deleted before unittest executes the cleanup; `path.exists()` is then false. The intentional KILL-survivor case consequently leaves its real loop running. This affects the harness, not the installed update tool, and is not a laptop blocker.

   **Fix:** capture the process identity before removing the directory and clean it up after the survivor assertions, or retain the fixture until unittest cleanup completes.

3. **Nit — JUDGMENT-CALL 11 overstates unsuccessful-stop guarantees.**  
   **Where:** [REPORT-draft.md:107](C:/Users/pab/AresOS-27-review/reviews/27-first-update-release/REPORT-draft.md:107).

   “Proves both masked in every case” and “nothing changes at the next start” are unconditional, although the code explicitly supports failed restoration and incomplete stopping. That wording could mislead the owner about a STOP requiring help.

   **Fix:** say restoration is *attempted and checked*, and that nothing changes at the next start **only when all stop checks pass**. This corrects the description without widening the accepted judgment call.

The remaining checks:

- **Signals and closed terminals:** the production update path installs all handlers before spawning and retains them through stopping, reconciliation and restoration. Handler installation/restoration introduces no exposed interval while an unsuccessful step is awaiting cleanup. Repeated SIGINT/SIGTERM/SIGHUP only record signals during that interval. `say()` handles EPIPE/EIO. The exception gap above is separate.
- **Process accounting:** re-parenting and changing process groups within the session remain covered. Creating a new session escapes this scan; Linux explicitly changes both session and group identity on `setsid()`. [Linux documentation](https://man7.org/linux/man-pages/man2/setsid.2.html). The independent deployment-client scan should refuse cleanup behind an escaped bootc, but does not terminate it. Numeric PID signalling also lacks protection against reuse between inspection and signalling. I found no evidence these occur in the fixed update script, so I am not treating these theoretical containment limits as additional blockers under the owner’s bar.
- **Mask recovery and cleanup ownership:** ordinary reconciliation failures now independently reach restoration, and both errors are retained. The pending-deployment guard checks agreement, idle state, unchanged retained rows, one new unpinned staged identity and matching target digest before deletion. It satisfies the requested snapshot checks. It cannot establish absolute provenance against another administrator staging the same digest or racing those checks.
- **Success:** successful staging bypasses `stop_update()` and keeps finalizers unmasked. The subsequent success checks are retained.
- **Bounds:** the configured stop budget totals **632 seconds**, rounded to 11 minutes. That is a nominal budget, not an unconditional wall-clock ceiling: process scans and subprocess creation/reaping are not bounded by that arithmetic. Python documents timeout limitations around process creation and waits for termination after a timeout. [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html).
- **Tests:** update tests now exercise the actual production `Host.start()`/`Step` path, real Bash and update.sh with fixture commands—not literally `Host.script()`, which production update also bypasses. The survivor is real, with KILL delivery suppressed. The timing changes preserve the relevant conditions: staging exists when timeout occurs, and later interrupts fall within TERM grace. Status/reconciliation remain modelled. These tests do not cover finding 1; I could not establish the requested per-behaviour revert proof.
- **Terminal flakiness fixes:** filtering sleeps by the actual `terminal_path` caller preserves the VT → foot round trip → preparation → active seat0 session → settle → typing assertions. Stopping the shell test’s watcher does not weaken its assertions.
- **Fingerprint:** all **15 payload/source hashes**, SHA256.json/SHA256SUMS, active documentation/command pins, and both source-record lists match **`f85084b636f4fb2b056a06f8681a69957d9968d8de3e6516e66506fbd776aa6d`**. Source and payload owner.py are identical. The old fingerprint remains only in the historical review and follow-up brief; `test_release27` contains no stale fingerprint pin.

Verification was static plus PowerShell hash checks and `git diff --check` (passed). Python is not installed locally; WSL returned `E_ACCESSDENIED`, so I did not execute Linux tests or reproduce the exception dynamically. Run 9 evidence remains outside this review.

CHANGES-NEEDED