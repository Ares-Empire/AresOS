The plan needs changes: **7 BLOCKING findings and 6 NON-BLOCKING findings**, consolidated from the members’ 22 findings.

Reviewed commit `c1908bca7f9d929b2aa40d1b56213977a47c72c6`, the council question, all four member reviews, and the relevant design and briefs. External evidence was checked on 2026-10-21. No files changed; no hardware, VM or game tests run.

**Council question 1: Base choice**

**Recommend qualifying a maintained NVIDIA atomic image as the preferred base**, with Ubuntu retained if the owner requires strictly no new trust keys. For an owner with limited maintenance time, retaining a complete previous OS deployment is worth evaluating before accepting package repair as the normal recovery strategy.

| Base | Council decision |
|---|---|
| **Fedora Atomic / community NVIDIA image** | Preferred candidate. Use Bazzite’s documented desktop `bazzite-nvidia` image as a concrete comparison, pinning an exact digest during qualification. Its NVIDIA integration and documented customization route make this more concrete than building an unspecified bootc distribution. AresOS still needs its own labwc session, controlled updates and installer safeguards. [NVIDIA image](https://github.com/ublue-os/bazzite/blob/main/README.md), [custom images](https://docs.bazzite.gg/Advanced/creating_custom_image/) |
| **Ubuntu 26.04 recipe** | Reasonable under a firm no-new-keys constraint, provided the exact Canonical-signed kernel/module combination works. Its recipe can constitute OS as code, but upgrades and recovery need additional enforcement. [Ubuntu driver paths](https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/) |
| **NixOS** | Strong declarative fit, but defer it here. The evaluated Lanzaboote procedure requires firmware setup mode and key enrollment, adding boot-trust work beyond the documented shim MOK path. This does not establish that every possible NixOS installation requires that procedure. [Lanzaboote instructions](https://github.com/nix-community/lanzaboote/blob/master/docs/getting-started/enable-secure-boot.md) |

**MOK ruling:** enrollment is a persistent trust change in shim’s MOK variables. It does not inherently overwrite Windows’ firmware trust keys or write its SSD. Bazzite documents installation-time enrollment with Secure Boot enabled; its separate post-installation recovery method involves toggling Secure Boot and should not become AresOS’s default procedure. [Shim variables](https://raw.githubusercontent.com/rhboot/shim/main/MokVars.txt), [Bazzite enrollment](https://docs.bazzite.gg/General/Installation_Guide/secure_boot/)

**A zero-BitLocker-prompt guarantee remains unproven.** Shim measures MOK-related state into TPM registers, including trust used during boot; Microsoft documents PCR-dependent validation. My inference is that directly booting unchanged Windows Boot Manager avoids shim’s additional boot-path measurements. That is insufficient to certify this Lenovo’s firmware and policy. Preserve the recovery-key prerequisite and test direct Windows return. [Shim measurements](https://raw.githubusercontent.com/rhboot/shim/main/README.tpm), [Microsoft validation profiles](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/configure)

Atomic rollback also needs precise language: Bazzite documents selecting a previous deployment; bootc requires additional health-check policy for automatic recovery. Persistent application data still needs separate backups. [Bazzite rollback](https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/rolling_back_system_updates/), [bootc health checks](https://bootc.dev/bootc/building/bootc-container-runtime.7.html), [persistent state](https://bootc.dev/bootc/bootc-filesystem.7.html)

**Council question 2: Silent failures**

The strongest examples are successful backups whose credentials die with the SSD; successful world shutdown that discards an editor document; an old kernel that boots without compatible NVIDIA userspace; fresh-install tests that miss upgrade leftovers; and window-close tests that miss focus theft during actual work. These require failure and transition tests, rather than more happy-path boot tests.

**Council question 3: Proportionality and the shortest safe path**

The components are mostly proportionate. Requiring P1–P9 before the first hardware evidence is not.

The shortest safe sequence is:

1. **P1–P3 essentials:** select the base candidate, build a minimal image, and prove target identification, isolated provisioning, its own ESP, protected-disk refusal and unchanged BootOrder. Define safe power-event defaults immediately.
2. **One end-to-end milestone:** combine the necessary parts of P4–P7 with P8’s backup/restore work: labwc, recovery terminal, networking and authentication, native Prism, exact-world launch, the mod/helper interface, one working app, clean shutdown and a tested off-device backup. Use a disposable Nether hub; brief 01 explicitly excludes Nether spawning, so include that small mod dependency.
3. **Early P10 trial:** after one-time setup, demonstrate **F12 → controllable Nether hub on NVIDIA → open/close one app → clean shutdown → ordinary Windows boot**, with USB present and absent. Restore a deliberately changed test world.
4. Then add release-update automation, broader device qualification, presentation and daily-use tuning.

Defer custom updater UI, Plymouth artwork, Bluetooth polish, suspend, internal NVMe migration, in-game settings and second-theme abstractions. A short prototype can use controlled manual maintenance; timely security maintenance must still have an owner and procedure.

**Council question 4: Safety**

The existing installation boundary is sound as a specification: isolated target, independent ESP, no Windows mounts/swap, no boot-order rewriting, explicit recovery mode and independently accessible BitLocker key. The council found no additional concrete Windows-write scenario that those rules already leave unaddressed. Their implementation remains untested.

The unresolved safety problems concern power events, recoverable backups, complete recovery state and ordinary app work. Atomic deployment does not remove these obligations. An AresOS boot failure must leave direct Windows boot available; an unexpected BitLocker prompt fails the stated acceptance goal.

**Council question 5: Experience**

**labwc + Prism + the helper is a plausible fit**, provided the helper controls actual windows and the mod participates in pointer, focus and lifecycle transitions. Borderless Minecraft, independent app processes and recovery outside the game are appropriate choices.

Daily irritation will come from focus theft, relaunch loops, memory pressure, background heat, authentication interruptions and poorly specified wake behavior. Prove the real mod-to-helper-to-app path early. Neither launcher success nor a compositor test alone demonstrates “Minecraft is the desktop.”

The findings below are ranked by severity. **BLOCKING means the plan must change before implementation.** Deferred capabilities can retain later implementation gates; these amendments do not require finishing the updater or suspend support before the prototype.

1. **BLOCKING — Off-device backups can survive while their recovery credentials disappear.**  
   **Where:** [Backup contract](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:205).  
   **Scenario and impact:** Restic backups and local restore tests pass, then the AresOS SSD dies with the only repository password and backend credentials. The surviving snapshots cannot restore the world. Restic requires a repository password. [Restic documentation](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html)  
   **Fix:** Require independently retained repository location, recovery credentials, instructions and matching game manifest before keeping valuable saves. Keep secrets outside Git.  
   **Check:** Restore on a fresh system with the original SSD unavailable; verify known builds, inventory and player identity.

2. **BLOCKING — Lid, power-key and critical-battery events can bypass clean saving.**  
   **Where:** [Power controls](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:115), shutdown contract at line 199.  
   **Scenario and impact:** Sleep is hidden, but closing the lid suspends during a save; a power-button request shuts down before saving completes. Logind documents these defaults and a five-second default delay-inhibitor limit. [Logind documentation](https://www.freedesktop.org/software/systemd/man/latest/logind.conf.html)  
   **Fix:** Specify event ownership and system-level defaults, including helper failure. Disable unqualified sleep paths. Route ordinary shutdown through saving; give critical battery a bounded emergency policy prioritizing saving over backup transfer.  
   **Check:** Inject these events during loading, saving and maintenance, including saves exceeding five seconds and a failed helper. Verify the resulting world reopens.

3. **BLOCKING — Shutdown has no checkpoint for unsaved work in other apps.**  
   **Where:** [Shutdown contract](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:199).  
   **Scenario and impact:** Minecraft saves successfully, then power-off discards an unsaved document or browser form. “No automatic force-close” does not define how shutdown waits or cancels.  
   **Fix:** Before stopping Minecraft, request ordinary app closure and let the owner resolve remaining windows. A cancellable “close your apps first” flow is sufficient initially.  
   **Check:** Attempt shutdown with an unsaved editor and browser form. Cancellation must preserve both and leave a usable desktop; completion must not silently discard work.

4. **BLOCKING — Recovery lacks a complete, independently usable previous system and private-state contract.**  
   **Where:** [Recovery policy](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:140), state boundary at line 182.  
   **Scenario and impact:** An interrupted update leaves root unbootable without internet. Retained payloads lack OS dependencies; an older kernel may mismatch updated NVIDIA userspace. Root reinstall preserves `/home` but loses Wi-Fi profiles or recovery credentials. [NVIDIA compatibility](https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/), [NetworkManager storage](https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html)  
   **Fix:** Before enabling updates, require independent recovery media and a complete previous compatible OS/driver set. Inventory machine settings outside `/home`, assigning selective restore or explicit reprovisioning policies. Preserve the existing root-only recovery safeguards.  
   **Check:** Offline, recover separately from broken root and damaged AresOS ESP. Verify NVIDIA rendering, networking, recovery login, world access and unchanged protected-disk/BootOrder state.

5. **BLOCKING — Release ownership does not enforce either controlled updates or convergence.**  
   **Where:** [Updates](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:136), package contract at line 178.  
   **Scenario and impact:** A native updater changes packages before the save gate, or upgrading A→B leaves an obsolete supervisor enabled while a clean B installation passes. The installed release then behaves differently from the tested release. Ubuntu documents automatic security installation and affected-service restarts. [Ubuntu updates](https://ubuntu.com/server/docs/how-to/software/automatic-updates/)  
   **Fix:** Define one maintenance authority covering package additions/removals, managed configuration and service enablement. Integrate or disable competing installation mechanisms, including those inherited from an atomic image, while retaining security-update cadence.  
   **Check:** Compare fresh B with upgraded A→B; include a removed package, renamed service, configuration migration and native timers firing outside maintenance.

6. **BLOCKING — The base decision accepts recurring recovery work without comparing a concrete signed-NVIDIA atomic candidate.**  
   **Where:** [Base comparison](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:43).  
   **Scenario and impact:** A driver regression requires owner-operated repair after Ubuntu was selected chiefly to avoid an enrollment whose implications were insufficiently distinguished. Maintained compatible kernel/module packages and an enrollment path exist. [Universal Blue integration](https://github.com/ublue-os/akmods/blob/main/README.md)  
   **Fix:** Apply the base recommendation above: compare one pinned atomic candidate against Ubuntu, including session customization, trust, update ownership and recovery effort.  
   **Check:** Demonstrate signed-driver loading, isolated installation, F12 discovery, direct Windows return and offline previous-deployment recovery. Documentation alone cannot qualify the laptop.

7. **BLOCKING — The OS-owned app interface conflicts with the frozen mod brief without a migration contract.**  
   **Where:** [Helper contract](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:186), [first-app brief](/C:/Users/pab/AresOS-02-os-base-design/briefs/01-first-app.md:13).  
   **Scenario and impact:** The mod follows its command-based `apps.json`/`ProcessBuilder` brief while the helper expects registered IDs. Both pass isolated tests, but app activation bypasses window tracking and GPU-environment isolation.  
   **Fix:** Specify the small versioned interface before these components diverge. Preserve existing app IDs; place Linux launch definitions in the OS adapter and Minecraft appearance/world behavior in the mod.  
   **Check:** Exercise the real mod→helper→app path, existing-config migration and incompatible-version rejection. A second-theme implementation is unnecessary for this milestone.

8. **NON-BLOCKING — Memory pressure can disable both the desktop and its recovery path.**  
   **Where:** [App isolation](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:193).  
   **Scenario and impact:** Minecraft, shaders, browser tabs and a call exhaust 16 GB; recovery becomes unresponsive or the game restarts into the same shortage.  
   **Fix:** Measure a conservative Java/render baseline, provide an explicit swap/OOM policy on AresOS storage, separate game and recovery resource groups, and suppress pressure-driven restart loops.  
   **Check:** Run a representative study workload plus controlled memory pressure. Require responsive recovery, preserved app work and no repeated game restart.

9. **NON-BLOCKING — The restart limit permits endless slower crash loops.**  
   **Where:** [Supervisor states](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:197).  
   **Scenario and impact:** Minecraft reaches the world, crashes every four minutes, and never exceeds three failures in five minutes. The broken desktop continually reopens the save.  
   **Fix:** Add a consecutive-failure budget that resets only after sustained healthy operation or explicit retry.  
   **Check:** Simulate repeated ready-then-crash cycles four minutes apart, including supervisor restart; require a finite transition into persistent recovery.

10. **NON-BLOCKING — Closing a background app can steal active typing focus.**  
    **Where:** [Final-window rule](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:191).  
    **Scenario and impact:** A terminal finishes while the owner types in a browser; its last window closes and Minecraft receives subsequent keys.  
    **Fix:** Return to Minecraft when the closing window owned the active interaction. Background closure preserves focus; transitions clear held game inputs.  
    **Check:** Close a background terminal during continuous browser typing, then separately test foreground closure, dialogs, Alt+Tab and pointer capture.

11. **NON-BLOCKING — Hardware feasibility is tested after substantial optional investment.**  
    **Where:** [Package order](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:249).  
    **Scenario and impact:** P2–P9 succeed before P10 discovers an unusable signed graphics stack or undiscoverable removable boot path. Considerable base-specific work needs revisiting.  
    **Fix:** Split P10 into early feasibility and later qualification; separate essential backups from update automation in P8. Use the shortened milestone above.  
    **Check:** Require the early end-to-end hardware demonstration before investing in the remaining base-specific polish.

12. **NON-BLOCKING — Sleep specifies intentional exit without a matching resume transition.**  
    **Where:** [Lifecycle and sleep](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:197).  
    **Scenario and impact:** Sleep stops Minecraft intentionally; wake leaves it stopped. An improvised relaunch instead reloads the game and may relocate the player to the hub.  
    **Fix:** Keep suspend deferred. Before enabling it, choose retained-process versus stop/relaunch behavior and specify position, foreground focus and wake-to-input expectations.  
    **Check:** Sleep away from the hub and with a foreground browser. Verify the chosen position/focus behavior, no duplicate instance and measured wake latency.

13. **NON-BLOCKING — FPS settings do not establish acceptable daily heat, noise or battery use.**  
    **Where:** [Power policy](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:61), measurements at line 239.  
    **Scenario and impact:** Five background FPS passes configuration checks while an hour of reading still produces unacceptable fan noise and drain.  
    **Fix:** Define active-world, app-focused and idle behavior, including simulation/audio and display blanking. Set an owner-accepted comfort/power limit and a fallback if measurements fail it.  
    **Check:** Compare the same browser workload with Minecraft stopped, hidden and visible, on AC and battery; measure whole-system consumption and return responsiveness.

GAPS-FOUND (13)