Reviewed commit `c1908bca7f9d929b2aa40d1b56213977a47c72c6` and the council’s referenced files. No files changed; no runtime or hardware trials performed.

1. **Blocking — Failed-boot recovery depends on resources that may be unavailable during the failure.**  
   Where: [§9 and Appendix A](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:140), particularly lines 140, 176 and 218.

   **Scenario:** An interrupted update leaves the root system unbootable while the owner has no internet. The recovery TTY cannot start. Reinstalling the previous recipe needs downloaded OS dependencies; retaining the previous AresOS/game payload does not retain those dependencies. No independently bootable, offline recovery kit is required.

   **Impact:** Windows may remain usable, but the owner cannot restore AresOS using the promised recovery path without connectivity and additional preparation.

   **Fix:** Before enabling updates, require a separate bootable recovery medium and a verified previous-release recovery bundle, including dependencies and instructions. Recovery must preserve data and repair only AresOS boot files when necessary. A fully offline *initial installer* can remain deferred.

   **Check:** Disable networking and make the installed root unbootable. Recover using only the prepared kit, then launch the prepared world. Separately damage the test AresOS ESP. Verify protected-disk hashes and firmware BootOrder remain unchanged.

2. **Blocking — Disabling the sleep UI does not disable lid-triggered suspend or make hardware power events save safely.**  
   Where: [Everyday needs and shutdown contract](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:119), lines 119–120 and 199.

   **Scenario:** Before P11 qualifies suspend, the owner closes the lid during a world save. Stock logind behavior suspends on lid closure and powers off on a power-button press. Its default delay-inhibitor allowance is only five seconds; lid handling also ignores ordinary high-level sleep blockers by default. [systemd documentation](https://www.freedesktop.org/software/systemd/man/latest/logind.conf.html)

   **Impact:** Untested suspend can produce a black screen requiring forced power-off. Hardware-triggered shutdown can bypass the intended save/backup sequence.

   **Fix:** Define the actual logind configuration and event ownership in P5/P7. Keep unqualified sleep disabled at the system level. Route supported power events through the save protocol, with a separate bounded policy for critical battery that prioritizes saving over backup completion.

   **Check:** Exercise lid closure, power/sleep keys and simulated critical battery while loading, saving and updating, including a save lasting longer than five seconds and a failed session helper.

3. **Should-fix — Retained kernels are not necessarily usable NVIDIA recovery environments.**  
   Where: [Update retention policy](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:138).

   **Scenario:** A driver update replaces NVIDIA userspace. The owner selects an older kernel after the new configuration fails, but that kernel retains an older NVIDIA module. Ubuntu explicitly documents failure when kernel-module and userspace versions differ. Conversely, updating both kernels’ modules to the new driver preserves no escape from that driver’s regression. [Ubuntu NVIDIA troubleshooting](https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/)

   **Impact:** The fallback kernel boots, yet Minecraft still cannot use NVIDIA. “Two known-good kernels” creates more confidence than the retained state supports.

   **Fix:** Define recovery in terms of a complete compatible OS/driver set. For Ubuntu, retain the exact previous packages and a rehearsed restoration operation; for an atomic base, retain the complete deployment. Label a kernel-only fallback accurately.

   **Check:** After each qualified driver update, deliberately select the recovery path offline. Verify module/userspace compatibility and Minecraft’s actual renderer—not merely successful kernel boot or driver installation.

4. **Should-fix — The update design does not explicitly control Ubuntu’s other package-update mechanisms.**  
   Where: [§9 and package locking](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:136), lines 136–138 and 178.

   **Scenario:** The installed system retains an enabled security repository and Ubuntu’s default unattended-upgrade configuration. Its timer installs updates outside the AresOS maintenance operation, potentially while Minecraft is running. Ubuntu documents automatic security updates and timer catch-up after startup. [Ubuntu automatic updates](https://ubuntu.com/server/docs/how-to/software/automatic-updates/)

   **Impact:** The running installation can diverge from the tested release without its backup, AC-power or maintenance checks. A manifest alone does not enforce runtime update ownership.

   **Fix:** Specify one authority for package mutation. Explicitly configure repository pinning, unattended-upgrades and any other shipped updater so they cannot bypass maintenance. Preserve timely security updates through that controlled path.

   **Check:** Offer a newer security package in a test repository and trigger the native timers outside maintenance. Assert that installed versions remain unchanged; then verify the authorized updater applies the approved release.

5. **Should-fix — Recovery has no resource protection against memory exhaustion.**  
   Where: [Session supervision and app isolation](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:193).

   **Scenario:** Minecraft, shaders and browser tabs exhaust the laptop’s 16 GB. The game is killed and automatically restarted into the same pressure, or the session becomes too unresponsive to open recovery. Independence from the game process does not itself provide memory isolation. systemd’s documentation specifically warns that unsuitable cgroup grouping can cause an OOM action to kill an entire session group. [systemd-oomd documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd-oomd.service.html)

   **Impact:** A routine workload can become a desktop freeze or repeated crash, potentially losing unsaved app work.

   **Fix:** Add a measured Java memory budget, an explicit swap/zram and OOM policy, and separate resource groups for the game and recovery components. Suppress automatic game restart while memory pressure remains excessive.

   **Check:** Apply controlled memory pressure with a world and browser open. Confirm recovery remains responsive, an OOM event is explained, and Minecraft does not repeatedly restart into exhaustion.

6. **Should-fix — The five-minute restart window permits endless slower crash loops.**  
   Where: [Supervisor state contract](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:197).

   **Scenario:** A regression reaches the world successfully, then crashes every four minutes. It never produces three failures within five minutes, so the stated cutoff never activates.

   **Impact:** A permanently broken desktop keeps relaunching and reopening the world without reaching a stable recovery state. Fast-crash tests can pass while this remains unnoticed.

   **Fix:** Supplement the short-window rate limit with a consecutive-failure budget. Reset that budget only after a defined period of healthy operation or explicit owner retry, rather than immediately upon `world-ready`.

   **Check:** Simulate launches that report ready and crash four minutes later. Verify that a finite number of attempts leads to persistent recovery, including across a supervisor restart.

7. **Should-fix — The base decision asks the owner to accept recurring repair work before qualifying a concrete MOK-based atomic alternative.**  
   Where: [Base comparison and owner decision](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:33), lines 33, 43–47 and 298.

   **Scenario:** A future package update requires manual repair or reinstall. Avoiding that burden was the principal reason to consider an atomic base, but the comparison stopped without evaluating an exact community NVIDIA image and its enrollment procedure.

   **Impact:** The owner may accept substantial ongoing recovery work to avoid a one-time operation whose actual implications remain insufficiently distinguished.

   **Evidence:** Universal Blue documents atomic images with NVIDIA support, and Bazzite documents installation-time MOK enrollment with Secure Boot enabled. Shim stores enrolled keys in its own `MokList`; this is distinct from replacing firmware Secure Boot keys. These facts establish a candidate worth evaluating, **not** a guarantee against BitLocker recovery on this LOQ. [Universal Blue](https://universal-blue.org/), [Bazzite enrollment](https://docs.bazzite.gg/General/Installation_Guide/secure_boot/), [shim variables](https://raw.githubusercontent.com/rhboot/shim/main/MokVars.txt), [Microsoft’s recovery conditions](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/countermeasures)

   **Fix:** Compare one exact signed NVIDIA atomic candidate against Ubuntu before final approval, including enrollment, maintenance and offline rollback. Distinguish manual previous-deployment selection from automatic failed-boot recovery; bootc requires additional health-check logic for the latter. [bootc health-check limitations](https://bootc.dev/bootc/building/bootc-runtime.html)

   **Check:** First rehearse update failure and rollback in a VM. In a separately authorized hardware trial, verify the recovery key, perform only the documented enrollment, check direct Windows boot and unchanged boot priority, and demonstrate offline recovery from a deliberately bad AresOS release.