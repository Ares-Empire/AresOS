1. **High — Choosing a fallback after a journalled restart blocks the commands needed to keep that fallback.**

   **Scenario:** Start on R27 with `[R27, R13, stock]`. Run `sudo /var/lib/ares/at previous`, then `sudo /var/lib/ares/at reboot`. At F12 → Bazzite → GRUB, choose stock. Run `sudo /var/lib/ares/at check`, then `sudo /var/lib/ares/at keep-stock`.

   A3 rejects unresolved journals; B4 explicitly requires a restart elsewhere to STOP. The previous-command journal expects R13, so neither command can complete the recovery. This also happens when R13 fails to boot and choosing stock is necessary. It contradicts B2’s promise that every reachable state has a command to select each installed system. [Draft rules](/var/home/ares/AresOS/reviews/councils/2026-11-13-22c-ways-back/BRIEF-DRAFT.md:23)

   **Impact:** A working fallback boots, but the tools cannot make it permanent or select another destination. Windows remains available; the Linux recovery route requires manual intervention.

   **Fix:** Separate “the requested boot was not confirmed” from “recovery mutations are forbidden.” After a restart, with a fully checked installed set and nothing staged, allow a destination command to archive the unsuccessful outcome and journal the recovery. Apply this to version 2 records too.

   **Check:** Rehearse `previous → restart → choose stock → keep-stock → restart → stock confirmed`, and the equivalent path following a failed new-release boot. Include both `intent` and `recorded` journals.

   **Basis:** Read AresOS source and bootc 1.16.13 [status source](/var/home/ares/AresOS/reviews/councils/2026-11-13-22c-ways-back/planner-material/bootc-1.16.13-status.rs:352). `rollbackQueued` derives from deployment ordering, not evidence of how the boot was chosen. An in-memory probe of today’s `outcome()` confirmed that the wrong post-restart boot refuses even with a same-command retry. No memory-based upstream claim.

2. **High — An interrupted `rollback` cannot resume after successfully reaching stock without an exception to the command’s side restriction.**

   **Scenario:** On R27, run `sudo /var/lib/ares/at rollback`. Its `ostree admin set-default` succeeds, making `[stock, R27, R13]` the order. Power fails before the result replaces the durable intent. Restart via F12 → Bazzite; stock boots. Try:
   
   ```bash
   sudo /var/lib/ares/at check
   sudo /var/lib/ares/at rollback
   sudo /var/lib/ares/at keep-stock
   ```

   Under A3–A5, `check` rejects the intent, `rollback` must refuse on stock, and `keep-stock` cannot continue another command’s unresolved journal. B4’s promise that “the same command continues” needs an explicit exception here. [Destination and journal rules](/var/home/ares/AresOS/reviews/councils/2026-11-13-22c-ways-back/BRIEF-DRAFT.md:36)

   **Impact:** A power cut turns a successful recovery into a persistent tools lockout.

   **Fix:** Reconcile an existing intent before applying restrictions for a *new* operation. Permit `rollback` on stock to record an exactly completed rollback without another deployment write, or explicitly let `keep-stock` settle that matching intent.

   **Check:** Cut power after the reorder and before the record write; boot stock and resolve through the documented command. Assert no second reorder, unchanged identities/pins, and subsequent working `check`, `update` and `reboot`.

   **Basis:** Read ostree 2026.4 [set-default source](https://github.com/ostreedev/ostree/blob/v2026.4/src/ostree/ot-admin-builtin-set-default.c). It moves the selected deployment to the front and writes the list before returning; the owner’s later journal write is separate. The deadlock follows from the draft’s rules, not an observed v3 implementation.

3. **Medium — Abandoning an interrupted layout finish from stock leaves the original AresOS with mixed settings and no supported repair command.**

   **Scenario:** On R27, run `layout begin us-intl`, complete the fresh tty4 `layout proof`, then run `layout finish` from the original session. Power fails after `localectl set-keymap` succeeds but before `set-x11-keymap`. Restart and choose stock in GRUB. Run `layout abandon`, then `keep-stock`; restart and confirm stock. Run `update`; restart into R27. Now run `layout begin de` or `layout abandon`.

   The existing abandonment path restores persistent settings only when running the trial’s original deployment. From stock it clears `layout-pending.json`. R27 therefore retains US International console settings with German X11 settings. `layout begin` rejects that mixed profile; `layout abandon` has no pending record. A7 does not specify how returning to that deployment repairs it. [Abandonment code](/var/home/ares/AresOS/os/owner-tools/owner.py:1806)

   **Impact:** The new return-from-stock route exposes an unfinished configuration that the normal layout commands cannot repair.

   **Fix:** Preserve a deployment-specific deferred restoration when abandoning an interrupted finish elsewhere. Allow recovery travel, then restore the original deployment’s recorded settings when it is booted. Keep stock’s settings untouched.

   **Check:** Inject the cut between the two persistent writes, abandon on stock, return to R27, and verify restoration plus a successful subsequent layout trial. E2’s reset during a trial does not require this cut.

   **Basis:** Read AresOS source; an isolated in-memory probe reproduced `Unsupported finished system layout; get help` after abandonment and return. For deployment-local `/etc`, I read [OSTree documentation](https://ostreedev.github.io/ostree/deployment/); reordering does not perform the configuration merge associated with creating a deployment.

4. **Medium — Acceptance never exercises a new release’s staging and shutdown finalization from the newly permitted reordered triple.**

   **Scenario:** Follow E4: R27 → `rollback` → restart stock → `update` → restart R27. The order is now `[R27, stock, R13]`. Install a future bundle targeting R28, run `update`, then `reboot`.

   This is an intended production transition, but every v3 `update` in E is a reorder of already installed R27. The preceding R13 → R27 staging uses version 2 and only a pair. Thus the acceptance run cannot establish that v3’s changed staging validation and completion logic agree with actual shutdown finalization. [Rehearsal](/var/home/ares/AresOS/reviews/councils/2026-11-13-22c-ways-back/BRIEF-DRAFT.md:76)

   **Impact:** The first real execution of this integration can otherwise be the owner’s second update—the deployment-changing operation this package is intended to make recoverable.

   **Fix:** Add a disposable VM third-image fixture, or explicitly require this exact transition in the next release’s rehearsal before its laptop update.

   **Check:** Observe staging, shutdown and `[R28, R27, stock]` afterward; verify the named removed deployment, stock identity/pin, recovery login, configuration inheritance, and both return routes. Include interrupted finalization followed by recovery.

   **Basis:** Read ostree 2026.4 [finalization source](https://github.com/ostreedev/ostree/blob/v2026.4/src/libostree/ostree-sysroot-deploy.c) and [retention source](https://github.com/ostreedev/ostree/blob/v2026.4/src/libostree/ostree-sysroot.c). They support retaining the booted/merge deployment and pinned stock independently of stock’s position. This finding is a concrete missing acceptance test; I found no source-backed order-dependent deletion defect.

No files were changed. Validation was source review and read-only, in-memory probes; no VM or host deployment commands were run.