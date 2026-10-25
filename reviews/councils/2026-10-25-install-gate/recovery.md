Reviewed `6eb2d0b29822434f692ce6be74625d806d7c8137`. Four should-fix gaps, ranked by recovery impact. This was a read-only review of source and retained evidence; no fresh VM or hardware tests ran.

1. **Layout changes discard the working administrator session before proving the password remains enterable.** [docs/INSTALL.md:245](../../../docs/INSTALL.md:245), [docs/EMERGENCY.md:96](../../../docs/EMERGENCY.md:96)

   **Scenario:** The owner creates a German passphrase containing umlauts or layout-sensitive punctuation, then selects US. The guide reboots before checking physical input and requires another administrator login before checking the layout. The console setting also controls input before login. [localectl documentation](https://www.freedesktop.org/software/systemd/man/latest/localectl.html)

   **Impact:** The owner sees repeated login failures and cannot run the repair commands; daily `ares` cannot administer the system. Windows remains reachable, and the frozen German stock deployment offers recovery, but the card has no “password rejected after layout change” branch directing them there.

   **Fix:** Keep an authenticated administrator session available while testing the new console layout and a second password login. Supply the exact restore procedure and an explicit stock-recovery route for login failures. Preserve the approved frozen-backup layout.

   **Check:** Exercise a German passphrase containing umlauts and punctuation, plus a partially failed console/X11 change. Require recovery without guessing keys or outside help. The VM used an ASCII password and layout-aware input automation ([os/ci/keyboard_vm.py:203](../../../os/ci/keyboard_vm.py:203)); its successful typing does not establish this owner-facing recovery path.

2. **The owner’s “checked rollback command” omits the executable identity checks used by CI.** [docs/INSTALL.md:774](../../../docs/INSTALL.md:774), [docs/EMERGENCY.md:96](../../../docs/EMERGENCY.md:96)

   **Scenario:** After selecting stock through GRUB, a confused owner resumes at the short rollback block. Its only substantive command is `bootc rollback`, which can queue AresOS again. The prose correctly warns against this, but `set -e` cannot reject a successful command targeting the wrong deployment.

   **Impact:** A recovery action changes the next Linux boot away from working stock and invalidates the saved title. The post-command inspection can detect this only after the change.

   **Fix:** Make the owner block enforce the expected booted image and saved rollback checksum, serial, stateroot, digest and pin before mutation. Refuse an already-booted stock recovery and direct the owner to stock promotion. Use the same guarded block in CI and INSTALL.

   **Check:** Assert zero mutations when invoked from stock, with the wrong rollback identity, or with a same-checksum/wrong-serial deployment. Add exact owner-block equivalence coverage. Current qualification invokes [os/release/rollback.sh:3](../../../os/release/rollback.sh:3), including reference/digest checks absent from the guide’s block; see [os/ci/keyboard_vm.py:275](../../../os/ci/keyboard_vm.py:275).

3. **Permanent undo leaves the private-pull token active, including on a removed or partition-erased SSD.** [docs/INSTALL.md:656](../../../docs/INSTALL.md:656), [docs/INSTALL.md:970](../../../docs/INSTALL.md:970)

   **Scenario:** The owner abandons the trial after authenticating GHCR, then follows “Done” in default undo or removes/reuses Crucial. Neither route instructs them to revoke the installation token.

   **Impact:** The unencrypted SSD retains reusable credentials. The guide correctly says that clearing its partition table is not secure sanitisation, but supplies no credential retirement step. The token’s scope is also broader than this single package.

   **Fix:** On permanent abandonment, direct the owner to revoke the installation token through GitHub from Windows or their phone—even when Linux cannot boot. Remove reachable local credentials as cleanup, without treating file or partition deletion as revocation.

   **Check:** Walk through abandoned-pull and broken-Linux undo cases. Verify the retired token cannot authenticate, while existing stock/AresOS deployments remain bootable.

4. **First-login preparation has conflicting entry points and puts updater handling behind a prerequisite that rejects updater activity.** [docs/EMERGENCY.md:9](../../../docs/EMERGENCY.md:9), [docs/INSTALL.md:91](../../../docs/INSTALL.md:91)

   **Scenario:** Following the emergency card’s direct link, the owner runs pause/pin first. Returning to INSTALL’s keyboard repair then produces the deliberate “already pinned” refusal at [os/release/system-keyboard.sh:29](../../../os/release/system-keyboard.sh:29). Conversely, following INSTALL first encounters a STOP if an updater has already staged work: repair rejects that state before the later pause/discard procedure can handle it.

   **Impact:** Ordinary first-login conditions strand preparation without a documented continuation. The owner is told not to reboot or change pins, despite following a documented route. This is a safe refusal, but not a self-contained recovery procedure.

   **Fix:** Provide one preparation sequence: pause and establish idle, handle only the permitted pending update, repair the booted stock serial, then pin and record it. Both documents should link to that same entry point. A verified helper with a short invocation would remove the need to transcribe the current 315 lines of preparation code before completing this checkpoint.

   **Check:** Start independently from INSTALL and EMERGENCY with clean stock, two stock serials, an active updater and the retained staged-update fixture. Require the same corrected, pinned identity or a precise recoverable STOP. Successful 11k/11n runs had no actual cancellation/discard, as disclosed in [reviews/11-two-disk-rehearsal/REPORT.md:3096](../../../reviews/11-two-disk-rehearsal/REPORT.md:3096); they do not prove this combined failure path.