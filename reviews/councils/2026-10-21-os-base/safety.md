Reviewed commit `c1908bca7f9d929b2aa40d1b56213977a47c72c6`. Documentation/source review only; no files changed or hardware tests run.

1. **Blocking before keeping real saves: off-device backups can become unreadable when the AresOS SSD dies.**  
   **Where:** [Backup contract, lines 205–207](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:205), and the restore trial at line 235.

   **Scenario:** Automated restic backups succeed, and restore testing passes on the installed system. The repository password and remote-access credentials exist only on the AresOS SSD. That SSD fails. The remote snapshots survive, but the owner cannot decrypt or retrieve them. Restic explicitly requires the repository password for recovery. [Restic documentation](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html)

   **Impact:** Permanent world loss despite apparently successful off-device protection.

   **Fix:** Require independently accessible recovery credentials and instructions before treating any world as protected. Include the repository location, restic password, recoverable backend access and matching game manifest; keep secrets outside Git.

   **Check:** Restore into a fresh VM with the original AresOS disk completely unavailable, using only the off-device backup and independently retained recovery information. Open the restored world and verify player inventory and known builds.

2. **Blocking before the laptop trial: ordinary lid and power events can bypass the clean-save protocol.**  
   **Where:** [Sleep/shutdown protocol, line 199](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:199), battery policy at line 115, and P10 preceding suspend qualification in P11.

   **Scenario:** The first hardware image hides its Sleep action pending qualification, but the owner closes the lid. Logind’s documented default still suspends. Likewise, pressing the power button defaults to power-off without first entering the helper’s save/backup sequence. Merely listening for shutdown with a delay inhibitor is insufficient: its documented default allowance is five seconds. [Logind documentation](https://www.freedesktop.org/software/systemd/man/latest/logind.conf.html)

   **Impact:** Unqualified suspend can leave a black screen requiring forced power-off; shutdown can interrupt saving. Critical-battery handling can also exhaust the remaining charge while waiting for backup or manual recovery.

   **Fix:** Specify ownership of lid, power-key, ordinary system shutdown and critical-battery actions. Disable unqualified sleep paths and route normal requests through the save protocol. Define an emergency battery policy that prioritizes saving within a measured time budget and can defer backup.

   **Check:** Before P10, inject lid, power-key and critical-battery events during a deliberately slow save, with the helper both running and failed. Verify no unqualified suspend, no premature termination, and successful reopening of the saved world.

3. **Should-fix: Ubuntu’s automatic updater is not explicitly subordinated to the maintenance protocol.**  
   **Where:** [Update policy, lines 136–140](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:136), and snapshot locking at line 178.

   **Scenario:** The installed system retains Ubuntu’s default `unattended-upgrades` machinery. When an AresOS release advances the configured archive snapshot, eligible updates can be installed by its timer before the AresOS updater has stopped Minecraft and completed its backup. Snapshot pinning alone does not disable that competing installer. Ubuntu documents automatic security updates and automatic affected-service restarts. [Ubuntu documentation](https://ubuntu.com/server/docs/how-to/software/automatic-updates/)

   **Impact:** Package changes and service restarts bypass the promised maintenance boundary, potentially interrupting the session or leaving recovery necessary without the expected checkpoint.

   **Fix:** Make the AresOS updater the sole automatic package-installation authority. Explicitly disable or integrate unattended installation and service-restart behavior while retaining the planned security-update cadence.

   **Check:** Offer a newer test snapshot, trigger the distribution update timers while Minecraft is active, and verify that packages, services and boot files remain unchanged until the AresOS save/backup gate succeeds.