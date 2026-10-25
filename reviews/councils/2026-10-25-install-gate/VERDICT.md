At commit `6eb2d0b29822434f692ce6be74625d806d7c8137`, **the guide is not ready for the owner’s laptop-side gates: seven BLOCKING and four NON-BLOCKING findings remain. Physical installation stays NOT RELEASED.**

I checked all three reviews against the cited source and retained evidence. Token retirement and preparation-order duplicates are merged below. No files were edited; no fresh VM or hardware tests ran. The checks below describe acceptance criteria.

1. **BLOCKING — The stock-title link bypasses the mandatory Windows checkpoint.**  
   [INSTALL.md:515](../../../docs/INSTALL.md:515), [INSTALL.md:641](../../../docs/INSTALL.md:641).

   **Scenario:** After first pinning, the owner follows the title-checkpoint link and continues into authentication and switching. The §5 prerequisite at line 557 is above the destination.  
   **Impact:** Switching can precede the installed EFI mapping, Windows-default restoration and unattended Windows verification.  
   **Fix:** Give every checkpoint an explicit return destination; require completed §5 immediately before authentication/switching.  
   **Check:** Follow every installation link without browser Back. No route may reach switching before §5 passes.

2. **BLOCKING — The owner’s rollback block omits CI’s executable target checks.**  
   [INSTALL.md:774](../../../docs/INSTALL.md:774), [rollback.sh:3](../../../os/release/rollback.sh:3).

   **Scenario:** Having recovered stock through GRUB, the owner resumes at the short rollback block. Its only substantive command is `bootc rollback`; `set -e` cannot reject a successful operation on the wrong target. Rollback changes deployment ordering. [Bootc manual](https://bootc.dev/bootc/man/bootc-rollback.8.html).  
   **Impact:** Recovery can change the next Linux boot and invalidate the saved title. The prose warning helps, but the executable does not enforce it.  
   **Fix:** Share one guarded implementation between owner and CI: verify booted AresOS, saved stock checksum/serial/stateroot, digest, reference, pin and pending state before mutation. CI’s existing reference/digest guard alone is insufficient.  
   **Check:** Wrong booted image, wrong serial, wrong target or pending work must produce zero mutations; verify owner/CI equivalence.

3. **BLOCKING — Layout changes reboot before proving the administrator password remains enterable.**  
   [INSTALL.md:245](../../../docs/INSTALL.md:245), [EMERGENCY.md:96](../../../docs/EMERGENCY.md:96).

   **Scenario:** A German passphrase contains umlauts; the owner selects US, reboots, then cannot enter it. Keyboard settings govern console input before login. [Systemd documentation](https://www.freedesktop.org/software/systemd/man/latest/localectl.html).  
   **Impact:** The working administrator session is lost; daily `ares` cannot repair the setting. Windows remains available.  
   **Fix:** Keep an authenticated administrator session, prepare restoration of the old settings, and prove physical typing plus a fresh second login before reboot. Add a password-rejected branch using valid stock recovery or Windows/help.  
   **Check:** Exercise umlauts, punctuation and partial console/X11 failure. The [CI password at keyboard_vm.py:203](../../../os/ci/keyboard_vm.py:203) is ASCII; its automated success does not establish this recovery path.

4. **BLOCKING — Permanent abandonment does not retire the private-pull token.**  
   [INSTALL.md:656](../../../docs/INSTALL.md:656), [INSTALL.md:970](../../../docs/INSTALL.md:970).

   **Scenario:** After authenticating, the owner abandons AresOS and leaves, removes or repartitions Crucial. None of these undo branches requires token revocation.  
   **Impact:** Recoverable credentials remain usable until expiry or revocation; `read:packages` permits downloading accessible private images. [GitHub documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).  
   **Fix:** Require revocation from Windows or the phone on permanent abandonment, including when Linux cannot boot. Local deletion is supplementary cleanup.  
   **Check:** With disposable credentials, exercise abandonment after authentication and broken-Linux undo. Fresh authentication/private pulls must fail after revocation; installed deployments must remain bootable offline.

5. **BLOCKING — First-login preparation has contradictory ordering and cannot handle the pending-update state it promises to handle.**  
   [EMERGENCY.md:9](../../../docs/EMERGENCY.md:9), [INSTALL.md:91](../../../docs/INSTALL.md:91), [system-keyboard.sh:29](../../../os/release/system-keyboard.sh:29).

   **Scenario:** EMERGENCY directs pinning first; keyboard repair then rejects pinned stock. Following INSTALL instead rejects an already-staged update before reaching its cleanup procedure.  
   **Impact:** Normal first-login conditions strand preparation. These are safe refusals, but the documented continuation is missing.  
   **Fix:** Provide one sequence: pause/establish idle → validate and discard only permitted pending work → repair and verify booted stock → pin and record. This requires separating cleanup from pinning, not merely rearranging existing links.  
   **Check:** Both entry points must handle clean stock, two stock serials, updater activity and the retained staged-update fixture. Successful runs with no cancellation/discard do not prove these branches.

6. **BLOCKING — Preparation depends on hundreds of lines of privileged manual transcription.**  
   [INSTALL.md:102](../../../docs/INSTALL.md:102), [INSTALL.md:573](../../../docs/INSTALL.md:573).

   **Scenario:** Reading from a phone, the owner enters the 83-line keyboard block and 232-line pin block twice: **547 lines**, confirmed against the scripts. A mistyped heredoc terminator leaves an unfamiliar continuation prompt.  
   **Impact:** Execution stalls or differs from the reviewed implementation, without a documented recovery procedure.  
   **Fix:** Supply a versioned, integrity-verified helper bundle with an explicit acquisition route, short invocations, clear results and interruption instructions. Preserve every validation.  
   **Check:** Complete the German-keyboard, phone-only walkthrough without an editor or clipboard, including a mistyped invocation and interruption.

7. **BLOCKING — The mandatory recovery checkpoint is impractical on the prescribed text console.**  
   [INSTALL.md:603](../../../docs/INSTALL.md:603), [INSTALL.md:731](../../../docs/INSTALL.md:731).

   **Scenario:** On tty3, the owner must recover identities from unpaged JSON and manually resolve BLS targets. The [retained status file](../../../os/manifest/ci/13/qualification-3/evidence/two-disk/aresos-rpm-ostree-status.json:1) is **141,867 bytes**, approximately **1,229 wrapped rows at 120 columns**. JSON goes directly to stdout. [rpm-ostree source](https://raw.githubusercontent.com/coreos/rpm-ostree/v2026.3/src/app/rpmostree-builtin-status.cxx).  
   **Impact:** Required fields disappear off-screen, forcing a stop or unreliable recording.  
   **Fix:** Produce a compact, checked identity/title report and save full diagnostics separately. Preserve serial, stateroot, pin, transaction and provisional-title checks.  
   **Check:** Replay large output, duplicate stock checksums, staged switching and queued rollback on a fixed-size console; require correct records without guessing indices.

8. **NON-BLOCKING — The emergency card buries immediate actions beneath preparation and evidence history.**  
   [EMERGENCY.md:5](../../../docs/EMERGENCY.md:5), [EMERGENCY.md:90](../../../docs/EMERGENCY.md:90).

   **Scenario:** With a frozen laptop, the owner searches a 1,753-word phone document; 744 words precede its three rules.  
   **Impact:** Finding Windows escape or shutdown instructions takes unnecessary navigation. The required actions do exist, so length alone does not establish unsafe recovery.  
   **Fix:** Put symptom-based actions first; move preparation, examples and CI history into references.  
   **Check:** In the existing novice trial, find freeze, failed-first-switch and stale-title actions within 30 seconds on a narrow phone screen.

9. **NON-BLOCKING — Recovery shortcuts omit German labels and Fn-mode alternatives.**  
   [EMERGENCY.md:96](../../../docs/EMERGENCY.md:96), [INSTALL.md:727](../../../docs/INSTALL.md:727).

   **Scenario:** F3 produces its hotkey function, so the documented console shortcut appears broken. Lenovo documents FnLock’s reversal of primary/secondary functions. [Lenovo manual](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/intro_fnlock.html).  
   **Impact:** A working recovery route appears unavailable.  
   **Fix:** Explain `Ctrl = Strg`, supply the Fn-modified alternative and expected login prompt, and cover F1 return.  
   **Check:** Extend the existing physical keyboard trial to both FnLock states; prove console entry, login, logout and return.

10. **NON-BLOCKING — The USB-writing walkthrough omits localization and the post-Write warning.**  
    [INSTALL.md:49](../../../docs/INSTALL.md:49).

    **Scenario:** German Windows localizes the writer; clicking Write opens another warning when the guide says to wait. Both behaviors are present in the pinned sources. [Locale selection](https://raw.githubusercontent.com/FedoraQt/MediaWriter/5.3.2/src/app/main.cpp), [write flow](https://raw.githubusercontent.com/FedoraQt/MediaWriter/5.3.2/src/app/qml/DrivePage.qml).  
    **Impact:** The owner must improvise at confirmation. Existing labelled-stick and disconnection rules constrain the risk.  
    **Fix:** Document verified German/English controls, target recheck, confirmation/cancellation and completion. Do not treat translations from `main` as verified 5.3.2 rendering.  
    **Check:** Exercise the exact German Windows flow, including cancellation, during the existing expendable-media trial.

11. **NON-BLOCKING — Historical qualification statements conflict with current evidence and boot timing.**  
    [INSTALL.md:83](../../../docs/INSTALL.md:83), [INSTALL.md:553](../../../docs/INSTALL.md:553), [OS-BASE.md:140](../../../docs/design/OS-BASE.md:140), [OS-BASE.md:331](../../../docs/design/OS-BASE.md:331).

    **Scenario:** Installed-account/two-disk checks still say OPEN, GRUB promotion says untested, and the binding specification says Windows-first initially; later evidence and INSTALL describe completed VM checks and Linux-first until §5.  
    **Impact:** The reader cannot consistently distinguish an outstanding condition from historical status.  
    **Fix:** Use one current status table and reconcile the binding boot sequence. Preserve each result’s drive-order, release and physical-test limits.  
    **Check:** Audit every status claim against retained results, including the [11n promotion pass](../../../os/manifest/ci/11n/b-1/two-disk/grub-promotion.json:1).

The evidence supports the latest gate’s conservative physical-release status and its explicit disclosure that US→stock rollback was not run. It does not support the broader claim that all status wording is consistent. No additional literal Micron-write path was substantiated by the member findings.

For proportionality, the **minimal owner version, after release**, is one linear checklist with short verified commands, expected screens/results, private records and explicit STOP/return destinations. Keep backups and recovery-media tests; encryption/power preparation; fitting stops; same-session disk and EFI identification; installer-plan review; corrected-stock preparation; account/signature checks; §5’s unattended Windows proof; deployment/title checks; recovery login; and token retirement.

Move helper implementations and verbose diagnostics into the verified bundle, with CI exercising the exact owner commands. Move qualification chronology, audit counts, historical screenshots and source reasoning into reports linked from one current gate table. Put later layout changes, stock promotion and optional removal/erasure in separate procedures; retain their checks there. The initial path can keep German throughout and use default undo that leaves Crucial installed. Preserve the frozen backup, account split, Windows default after §5 and failed-first-switch Windows escape. None of these reductions closes an existing laptop-side gate.

GAPS-FOUND (11)