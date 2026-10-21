Reviewed commit `c1908bca7f9d929b2aa40d1b56213977a47c72c6`. Sources checked on 2026-10-21. No files changed; no hardware, VM, or game tests run.

1. **Blocking for the base decision — The comparison omits an available signed-NVIDIA atomic path before accepting Ubuntu’s recurring recovery burden.**

   **Where:** [Base comparison and owner decision](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:33).

   **Scenario:** A driver or system-library update breaks the desktop. The owner must repair packages or reinstall root, having chosen Ubuntu without a concrete comparison against a maintained atomic NVIDIA image.

   **Evidence:** Universal Blue publishes compatible kernel/NVIDIA module packages and their signing key; Bazzite documents enrollment during installation while Secure Boot is enabled. This is an existing integration path, not a requirement for AresOS to maintain its own driver-signing infrastructure. [Universal Blue akmods](https://github.com/ublue-os/akmods/blob/main/README.md), [Bazzite Secure Boot](https://docs.bazzite.gg/General/Installation_Guide/secure_boot/).

   MOK enrollment changes persistent trust, but its database is separate from firmware Secure Boot databases. It does not inherently replace the Windows trust keys or write the Windows SSD. [Red Hat’s MOK documentation](https://docs.redhat.com/de/documentation/red_hat_enterprise_linux/10/html/managing_monitoring_and_updating_the_kernel/signing-a-kernel-and-modules-for-secure-boot). Shim measures MOK-related state into TPM PCRs; Windows commonly uses PCR 7 and 11. My inference is that rebooting directly into unchanged Windows Boot Manager avoids shim’s additional measurements, but that does **not** establish a zero-prompt guarantee for this LOQ. [Shim measurements](https://github.com/rhboot/shim/blob/main/README.tpm), [Microsoft validation profiles](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/configure).

   **Impact:** The decision favors avoiding one enrollment over potentially repeated owner-operated recovery, without evaluating that trade adequately for an owner with limited time.

   **Fix:** Compare Ubuntu against one specific, maintained NVIDIA atomic image or derivative, including its signing trust, customization cost and update policy. My provisional preference is that atomic route if the owner accepts enrollment and hardware checks pass. Ubuntu remains reasonable under a strict **no new keys** requirement. NixOS’s documented Lanzaboote setup involves firmware-key enrollment and therefore remains a materially different option. [Lanzaboote setup](https://github.com/nix-community/lanzaboote/blob/master/docs/getting-started/enable-secure-boot.md). Describe bootc accurately: transactional deployment and rollback are available; unattended failure detection requires an explicit policy, and application data is not rolled back with the OS. [bootc updates](https://bootc.dev/bootc/bootc-upgrades.7.html), [filesystem boundaries](https://bootc.dev/bootc/bootc-filesystem.7.html).

   **Check:** Qualify a pinned candidate’s signed driver, isolated installation, F12 boot, direct Windows return and previous-deployment recovery. Record firmware-variable changes and actual BitLocker behavior rather than treating either distribution’s documentation as hardware proof.

2. **Should-fix — “OS as code” covers fresh installation, but does not require upgrades to converge to the same system.**

   **Where:** [Updates](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:134), [build contract](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:178), and [acceptance trials](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:229).

   **Scenario:** Release B replaces a supervisor package used by release A. A clean B installation passes CI. Updating A installs the new package but leaves the obsolete package and enabled service behind. Both supervisors now react to Minecraft exits. The documented fresh-install inventory check never exercises this path.

   **Impact:** Two machines claiming the same release can behave differently. A Minecraft or driver bump becomes dependent on installation history, undermining reproducibility and recovery.

   **Fix:** Define one release-application operation covering package additions **and removals**, managed configuration, service enablement, user-override migration and post-update inventory verification. Explicitly assign ownership of automatic updates: Ubuntu enables unattended security updates by default, so the signed AresOS release process needs an enforced relationship with those timers and package sources. [Ubuntu automatic updates](https://ubuntu.com/server/docs/how-to/software/automatic-updates/). An install recipe can satisfy “OS as code”; a manifest alone does not enforce the running state.

   **Check:** Compare fresh B with A→B after normal use. Assert equivalent managed packages, configuration and enabled services, allowing only documented private-state differences. Include a removed package, renamed service, configuration migration and an automatic-update timer firing.

3. **Should-fix — Root-only recovery does not preserve all the private state the design promises to retain.**

   **Where:** [Recovery policy](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:140), [partition boundary](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:182), and [reinstall mode](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:218).

   **Scenario:** The owner configures Wi-Fi, then repairs a broken release by formatting only root. `/home` and the world survive, but the saved network connection disappears: NetworkManager stores persistent system connection profiles under `/etc/NetworkManager/system-connections`, including potentially necessary credentials. [NetworkManager storage documentation](https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html).

   **Impact:** The advertised recovery restores files without necessarily restoring a usable appliance. Networking and recovery-account credentials can require reconstruction precisely when recovery needs them.

   **Fix:** Extend the state contract beyond “root versus home.” Inventory private machine settings and credentials outside `/home`; give each an explicit preserve, restore or re-provision policy. Store protected backups separately from world backups and repository artifacts. Restore selected settings rather than copying an entire potentially broken `/etc`.

   **Check:** Configure a network and recovery password, perform the documented previous-release root reinstall, and verify networking, recovery login and world access. Exercise recovery without depending on a fresh online download.

4. **Should-fix — The proposed OS-owned app interface has no transition from the mod’s existing command-owned interface.**

   **Where:** [Session/helper contract](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:186) versus [frozen first-mod brief](/C:/Users/pab/AresOS-02-os-base-design/briefs/01-first-app.md:13).

   **Scenario:** The mod follows its brief: `apps.json` combines commands, Minecraft item appearances and pinned state; Linux launches through `ProcessBuilder`. The OS follows this design: its helper owns a registered app list and launches by stable IDs. Both components pass their individual tests, but clicking an item either bypasses the helper or references an app it does not recognize.

   **Impact:** Window tracking and GPU-environment isolation can be bypassed. A second theme must either understand Minecraft-specific configuration or introduce a competing app catalogue. Independent mod/helper upgrades also have no stated compatibility check.

   **Fix:** Add an integration package before P4/P7 that establishes catalogue ownership and migrates existing IDs without breaking saved items. Keep platform launch definitions in the OS adapter and Minecraft appearances/world behavior in the mod. Specify a small versioned interface for listing/launching apps and reporting shell readiness/clean stop; keep Prism, world saving and Iris behavior behind the Minecraft adapter. Windows can implement the same public operations locally.

   **Check:** Test the real mod→helper→app path, migration of an existing `apps.json`, and safe rejection of incompatible interface versions. Run the same supervisor tests with a tiny non-Minecraft shell to demonstrate that a second theme does not require rewriting session management.

5. **Should-fix — The first hardware feasibility gate comes after most base-specific implementation.**

   **Where:** [P1–P12 order](/C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:249).

   **Scenario:** P1 confirms package availability, then P2–P9 build installation, settings, launching, supervision, updating and presentation. P10 finally discovers that the selected signed driver/compositor combination fails on this laptop or that the intended removable boot path is not discovered.

   **Impact:** The assumptions most likely to overturn the base choice are resolved after substantial investment. The first “F12 into my world” experience also waits for a custom updater and splash.

   **Fix:** Split P10 into an early feasibility trial and later full qualification. After installation safeguards pass, assemble only the necessary session, networking/recovery, Prism launch, clean exit and basic backup path. Use disposable world data. Defer custom release updating, splash polish and comprehensive device controls until that path works.

   **Check:** Before committing to the remaining base-specific packages, demonstrate F12→controllable test world on NVIDIA→clean exit→normal Windows boot, with the isolation and recovery-key requirements intact.