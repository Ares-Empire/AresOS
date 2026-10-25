1. **High — Following the stock-title link can skip the Windows safety checkpoint.** [docs/INSTALL.md:515](../../../docs/INSTALL.md:515), [docs/INSTALL.md:641](../../../docs/INSTALL.md:641)

   **Scenario:** After first-login pinning, the owner follows the checkpoint link into §6. Its next heading says “Authenticate the private pull” and “Continue”; nothing sends them back to §5.
   **Impact:** They can switch before recording Crucial’s installed EFI mapping, restoring Windows as default, or proving an unattended Windows boot.
   **Fix:** Give each checkpoint invocation an explicit return destination. Put a clear §5 completion requirement immediately before authentication/switching. Move later layout changes and recovery procedures out of the initial installation sequence.
   **Check:** Have a phone reader follow every link without using browser Back. They must encounter and complete §5 before reaching the switch.

2. **High — The prescribed input method requires hundreds of lines of root-shell transcription.** [docs/INSTALL.md:102](../../../docs/INSTALL.md:102), [docs/INSTALL.md:281](../../../docs/INSTALL.md:281), [docs/INSTALL.md:573](../../../docs/INSTALL.md:573)

   **Scenario:** The owner hand-types the 83-line keyboard block, then the 232-line pin block twice: 547 lines including indentation, quotes, hashes and heredoc terminators. A mistyped terminator leaves a continuation prompt; a Python indentation error prevents execution. Neither situation has a novice recovery instruction.
   **Impact:** Installation stalls in an unfamiliar shell state, and transcription errors make the executed procedure differ from the reviewed scripts.
   **Fix:** Provide a versioned, verified helper bundle with an explicit acquisition route and short invocation commands. Keep implementations in the existing script files; retain every validation, clear success/STOP output, and instructions for interrupted execution.
   **Check:** Complete the phone-only, German-keyboard walkthrough without an editor or clipboard. Include a deliberately mistyped command and interrupted invocation.

3. **High — The recovery identity checkpoint prints more information than the prescribed text console can usefully present.** [docs/INSTALL.md:603](../../../docs/INSTALL.md:603), [docs/INSTALL.md:731](../../../docs/INSTALL.md:731)

   **Scenario:** On tty3, the owner runs the four commands, then must compare JSON identities and associate each BLS title with its resolved target. The saved [13f status artifact](../../../os/manifest/ci/13/qualification-3/evidence/two-disk/aresos-rpm-ostree-status.json) contains about 142 KB—over 1,200 wrapped rows at 120 columns. The guide supplies no paging, capture or retrieval instructions. Upstream’s JSON implementation writes directly to standard output. [rpm-ostree source](https://raw.githubusercontent.com/coreos/rpm-ostree/v2026.3/src/app/rpmostree-builtin-status.cxx)
   **Impact:** Required identities disappear off-screen; the owner must stop or risk recording the wrong recovery title.
   **Fix:** Supply a checked, compact identity/title report that preserves checksum, serial, stateroot and transaction checks, while saving full diagnostics separately.
   **Check:** Exercise it on a fixed-size text console with the real large output, duplicate stock checksums, staged switching and queued rollback. A novice must obtain the correct record without guessing row numbers.

4. **High — The emergency card directs first-login pinning before the mandatory keyboard repair.** [docs/EMERGENCY.md:9](../../../docs/EMERGENCY.md:9), [docs/INSTALL.md:91](../../../docs/INSTALL.md:91)

   **Scenario:** At first stock login, the owner follows the card’s direct pause-and-retain instruction. Later they reach keyboard repair, whose checks explicitly reject already-pinned stock at [INSTALL.md:130](../../../docs/INSTALL.md:130).
   **Impact:** The wrong preparation order leaves unrepaired stock pinned and the documented repair route refusing to proceed.
   **Fix:** Make both documents require successful keyboard repair before the first pin. Prefer one preparation entry point that enforces the order; explicitly prohibit using pinning to continue after keyboard repair stops.
   **Check:** Walk both documents independently from first stock login. Both must produce repair → successful verification → pin, including when repair fails.

5. **Medium — EMERGENCY.md does not function as a quick phone card.** [docs/EMERGENCY.md:5](../../../docs/EMERGENCY.md:5), [docs/EMERGENCY.md:73](../../../docs/EMERGENCY.md:73)

   **Scenario:** With a frozen or black laptop screen, the owner opens roughly 1,750 words. About 740 words of preparation, deployment history and qualification detail precede “The three rules”; actionable situations appear still later in a dense table.
   **Impact:** Finding the safe Windows escape competes with technical explanations and context-specific “do not reboot” instructions.
   **Fix:** Lead with short symptom-based actions: Windows escape, frozen-machine shutdown, failed first switch, unavailable Windows entry, and prohibited destructive actions. Keep account/layout reminders beside relevant actions. Move VM history, serial examples and preparation details into linked reference material.
   **Check:** On a narrow phone screen, ask an unfamiliar reader to find the correct action for a freeze, failed first switch and stale recovery title within 30 seconds, without horizontal scrolling.

6. **Medium — Recovery shortcuts omit the laptop’s function-key mode and German key labels.** [docs/EMERGENCY.md:96](../../../docs/EMERGENCY.md:96), [docs/INSTALL.md:727](../../../docs/INSTALL.md:727)

   **Scenario:** The owner presses the key marked F3 while FnLock makes it perform its hotkey function. No login console appears, and the card offers no keyboard-mode fallback. Lenovo documents that FnLock reverses the function/hotkey behavior. [Lenovo LOQ manual](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/intro_fnlock.html)
   **Impact:** A working recovery route appears broken, encouraging unnecessary shutdown or abandonment.
   **Fix:** Explain `Ctrl = Strg`, provide the appropriate Fn-modified alternative, and describe the expected text login prompt before entering credentials. Apply the same clarification to returning with F1.
   **Check:** Add both FnLock states to the existing physical keyboard trial; require successful console entry, login and return.

7. **Medium — The USB-writing instructions omit German labels and the final erase confirmation.** [docs/INSTALL.md:49](../../../docs/INSTALL.md:49)

   **Scenario:** German Windows launches a localized writer, while the guide lists only English controls. After “Schreiben”, another destructive confirmation appears although the guide has already told the reader to wait. Version 5.3.2 selects the system locale and opens a warning dialog at this point. [Locale source](https://raw.githubusercontent.com/FedoraQt/MediaWriter/5.3.2/src/app/main.cpp), [write-flow source](https://raw.githubusercontent.com/FedoraQt/MediaWriter/5.3.2/src/app/qml/DrivePage.qml)
   **Impact:** The reader must improvise at the final erase decision.
   **Fix:** Add German/English control pairs and explicitly describe the target recheck, confirmation, cancellation condition and successful completion screen. Upstream German strings include “.iso-Datei auswählen”, “Weiter”, “USB-Laufwerk”, “Schreiben” and “Löschbestätigung”; confirm their pinned-version rendering during the existing media trial. [German translation source](https://raw.githubusercontent.com/FedoraQt/MediaWriter/main/po/mediawriter_de.po)
   **Check:** Follow the exact 5.3.2 flow on German Windows using expendable media, including cancellation at the erase dialog.

8. **Medium — Superseded qualification statements and boot-order rules remain presented as current requirements.** [docs/INSTALL.md:83](../../../docs/INSTALL.md:83), [docs/INSTALL.md:553](../../../docs/INSTALL.md:553), [docs/design/OS-BASE.md:331](../../../docs/design/OS-BASE.md:331)

   **Scenario:** The reader encounters installed-account/two-drive qualification marked OPEN, although the later gate records completed VM installations. The binding design specification says Windows-first is the initial default, while INSTALL explicitly expects Linux first until §5. OS-BASE also retains an unqualified “GRUB recovery promotion remains untested” statement.
   **Impact:** The owner cannot reliably distinguish an unmet prerequisite, historical evidence and an expected screen; a correct Linux-first boot can appear to violate the binding rules.
   **Fix:** Reconcile these statements into one current status table distinguishing VM results, source checks and outstanding laptop trials. Update the binding boot sequence. Move historical qualification narratives into reports, leaving owner actions and current stop conditions in the installation path.
   **Check:** Cross-check every OPEN/PASSED/UNTESTED claim and boot-order instruction against the current gate and evidence. Each owner-facing stop must identify a genuinely outstanding condition.