Reviewed **f708c53f**, read-only. The original timeout path is substantially improved, but finding 1 is not fully closed.

1. **Blocking — another Ctrl+C can interrupt process-group shutdown.**  
   **Where:** [owner.py:267](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:267), [owner.py:1386](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:1386).

   `stop_group()` runs before SIGINT is ignored. A second Ctrl+C during its 15-second TERM grace period raises another `KeyboardInterrupt`, skipping SIGKILL and the group-gone check. `abandon_update()` then encounters the surviving bootc through `idle()` and exits before restoring masks. On the laptop, staging can continue after STOP—the failure this fix was meant to eliminate.

   Also, a normal nonzero shell exit bypasses `stop_group()` entirely. If a surviving child has closed its captured pipes, `communicate()` returning does not prove the group is empty.

   **Fix:** protect the entire termination-and-reconciliation sequence against repeated SIGINT, and verify/terminate remaining group members on unsuccessful shell exits too. Add real-runner tests for repeated Ctrl+C during TERM grace and shell failure with a surviving child.

2. **Should-fix — reconciliation errors prevent even attempting mask restoration.**  
   **Where:** [owner.py:1390](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:1390).

   A failed status read, failed pending cleanup, or deployment comparison failure skips `restore_masks()`. For example, staging can finish at timeout, the shell can be killed, and a subsequent status timeout leaves both masks removed. The outer handler does give STOP, diagnostics and “do not reboot,” but the independent mask recovery is unnecessarily abandoned.

   **Fix:** attempt and verify mask restoration independently of deployment reconciliation, preserving both errors if necessary. Claim successful cleanup only when every required check passes.

3. **Should-fix — pending cleanup does not establish ownership before deleting.**  
   **Where:** [owner.py:1392](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:1392).

   Any observed staged deployment triggers `cleanup --pending`; its reference, digest and identity are not checked first. The owner lock excludes another `at` command, but not a direct administrative deployment command. A foreign pending deployment could therefore be deleted, and the subsequent comparison could still pass.

   `--pending` itself is appropriate for the expected deployment layout: it preserves the booted deployment, rollback deployments behind it, and pinned stock. It does not establish who created the pending deployment. [Upstream implementation](https://github.com/coreos/rpm-ostree/blob/main/src/daemon/rpmostree-sysroot-core.cxx#L258).

   **Fix:** before removal, require agreement between both status views, unchanged retained deployments, and exactly one new, unpinned staged deployment matching this update’s target. Refuse unexpected state before deleting it.

The other requested checks look sound:

- **Success path:** successful staging still leaves the finalizers unmasked for reboot.
- **Bounds and messages:** cleanup commands have explicit timeouts; a genuinely surviving group produces a clear STOP/get-help response rather than deployment cleanup underneath it. That exceptional refusal is reasonable.
- **Tests:** the three timeout/interruption cases use real `Host.script()` and real Bash/update.sh with fixture commands. Reconciliation is modelled; the surviving-group case merely injects `Unstoppable`. They miss the paths above. A literal production-code revert also removes constants the tests patch, so it fails setup rather than demonstrating the requested named safety-assertion failures.
- **Version check:** whole-line matching accepts only 2.41.5/2.41.6, with the optional feature list; suffix rejection cases are present.
- **Fingerprint:** all 15 payload/source hashes and SHA256SUMS agree with **`e4dedbb63ed49313bd9625b92c02418002a5b3daf83b4e8039c4a2a9080da7f6`**. Active pins agree; old `daa31228…` references are historical. Both source-record lists also match.
- **Harness cwd fixes:** neither bypasses the relevant assertions. They remove an inaccessible inherited root-home directory while retaining account, permissions, password, PATH and application checks.

No files changed. I could not execute Python/Linux tests: Python is unavailable and WSL returned access denied. Run 8 evidence remains outside this check. Code/docs whitespace checks passed; the full diff reports only two Markdown hard-break lines in REVIEW-1.

CHANGES-NEEDED