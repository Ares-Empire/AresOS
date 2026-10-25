Reviewed head `1c4a249`. Three findings:

1. **Blocking — Later layout changes do not follow into recovery stock.**  
   Where: [INSTALL.md:218](C:/Users/pab/AresOS-13-keyboard-layout/docs/INSTALL.md:218), [keyboard_vm.py:271](C:/Users/pab/AresOS-13-keyboard-layout/os/ci/keyboard_vm.py:271).  
   The command changes only the running deployment’s keyboard configuration in `/etc`. The retained stock deployment keeps its earlier settings; rollback restores that copy. This follows [bootc’s deployment-specific `/etc` model](https://bootc.dev/bootc/bootc-filesystem.7.html#etc). Change AresOS from German to US, then recover stock: the recovery keyboard returns to German, potentially making the layout-sensitive password appear incorrect. The VM hides this mismatch by restoring German **before** rollback.  
   **Fix:** provide an identity-checked mechanism that also updates retained stock’s keyboard configuration, and test rollback while US remains selected. Otherwise obtain explicit approval to narrow the “one setting everywhere” requirement and document the recovery-layout exception.

2. **Should-fix — The recorded recovery title becomes stale as soon as rollback is queued.**  
   Where: [INSTALL.md:625](C:/Users/pab/AresOS-13-keyboard-layout/docs/INSTALL.md:625), [INSTALL.md:633](C:/Users/pab/AresOS-13-keyboard-layout/docs/INSTALL.md:633), [EMERGENCY.md:70](C:/Users/pab/AresOS-13-keyboard-layout/docs/EMERGENCY.md:70).  
   The owner records stock as `Bazzite (ostree:1)` after switching. Queuing rollback immediately moves stock to `(ostree:0)` and AresOS to `(ostree:1)`, even before the rollback boot succeeds. No step refreshes the saved recovery title. If that boot fails, following the card’s recorded title can select AresOS. Both menu labels still look familiar, so the “changed menu” warning may not catch this.  
   **Fix:** resolve and record the stock title again after the rollback transaction, before rebooting. Make the card explicitly invalidate the previous title after any deployment reorder, including a queued rollback.

3. **Should-fix — The reboot instructions omit the one-time Linux selection that makes the VM succeed.**  
   Where: [INSTALL.md:218](C:/Users/pab/AresOS-13-keyboard-layout/docs/INSTALL.md:218), [INSTALL.md:596](C:/Users/pab/AresOS-13-keyboard-layout/docs/INSTALL.md:596), [INSTALL.md:625](C:/Users/pab/AresOS-13-keyboard-layout/docs/INSTALL.md:625).  
   After §5, an unattended reboot starts Windows. Nevertheless, the switch instructions say to reboot and then expect labwc; layout changes and rollback similarly omit the immediate F12 step. The harness supplies Linux `BootNext` selection automatically in [two_disk_vm.py:64](C:/Users/pab/AresOS-13-keyboard-layout/os/ci/two_disk_vm.py:64). The later-layout command also needs an explicit `ares-recovery` context because daily `ares` cannot use sudo.  
   **Fix:** spell out recovery-account login → command → reboot → F12 → Linux at each affected step, while preserving Windows as the firmware default.

The keyboard repair block exactly matches its script. Frozen runtime paths match the published source, and both keyboard-file hashes match the retained image-diff manifest; I found no contradictory release-derivation claim.

No files changed. Tests could not be rerun: native Python was unavailable and WSL returned access denied.

CHANGES-NEEDED