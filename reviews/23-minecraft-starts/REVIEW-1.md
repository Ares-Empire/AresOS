Reviewed `d08fde0f` against `6978dc3c`. I would not approve this for the owner’s desktop yet.

1. **Blocking — OOM can trigger automatic restarts.**  
   [aresos-desktop:997](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:997)

   Only a reported SIGKILL suppresses restarting. When systemd-oomd kills the whole scope, it kills the wrapper too, leaving no exit report. `finish_jvm()` treats that unknown exit as an ordinary crash and restarts after five seconds, then ten seconds. This directly contradicts B5. Systemd explicitly documents killing every process in the selected cgroup. [Upstream documentation](https://raw.githubusercontent.com/systemd/systemd/main/man/systemd-oomd.service.xml)

   **Fix:** reconcile the scope’s termination/OOM result, and conservatively latch unexplained whole-scope deaths. Require explicit Retry and the specified 60 seconds of cleared pressure. Test killing the entire scope, not only Java.

2. **Blocking — A damaged Nether home passes validation and can be declared ready.**  
   [aresos-desktop:465](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:465)

   `check_world()` checks gzip readability, not NBT contents or the marker’s `enabled` value. It never checks `data/aresos/nether_home.dat`, and accepts a missing provisioning-complete file. Remove the saved Nether home from an otherwise valid hub: preflight passes, while the existing mod explicitly disables home arrival when that data is missing. The desktop marker can still produce `world_ready`, so the supervisor reports IN_WORLD without the required home behavior.

   The tests conceal this: their “valid world” contains gzip-compressed strings `level` and `marker`, not valid saved data.

   **Fix:** validate the actual desktop/home data and completed provisioning before unattended opening. Use real-format fixtures covering missing home data, disabled markers, malformed NBT and interrupted provisioning. Refuse recovery cases without rewriting the save.

3. **Blocking — The new image build prerequisite is absent from the release path.**  
   [build.sh:127](C:/Users/pab/AresOS-23-minecraft-starts/os/build.sh:127), [check-build.sh:25](C:/Users/pab/AresOS-23-minecraft-starts/os/ci/check-build.sh:25)

   The image now requires the ignored `os/minecraft/aresos.jar`. Only the throwaway build path creates it; the release integration does not. A clean image build without that preliminary step deterministically fails. REPORT’s PLAN-GAP 1 acknowledges this, but leaves the regression for another package.

   **Fix:** make mod generation and hash verification a shared prerequisite of every applicable image-build entry point. Update bound-source records where necessary and exercise the release build preparation without publishing.

4. **Should-fix — The real JVM is not guaranteed to receive the memory scope.**  
   [aresos-desktop:496](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:496)

   The scope surrounds the newly invoked Prism process. Prism forwards `--launch` to an already-running Prism using the same data directory and exits. Java then inherits the existing Prism’s cgroup. Likewise, launching AresDesktop directly from Prism’s UI is explicitly accepted without creating or verifying a game scope. Thus a supported re-login/manual-launch path bypasses `MemoryHigh=5G`. [Prism 11.1.1 forwarding implementation](https://raw.githubusercontent.com/PrismLauncher/PrismLauncher/11.1.1/launcher/Application.cpp)

   **Fix:** enforce the scope at the wrapper/JVM boundary, or verify and establish its membership before allowing launch. Test with Prism already open outside the desktop scope and assert the **Java PID’s** cgroup and limit.

5. **Should-fix — A game that dies while the supervisor is down escapes exit accounting.**  
   [aresos-desktop:737](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:737)

   Startup adopts a live recorded JVM, but if that JVM has died, it immediately starts another launch. It never reconciles the previous launch’s exit record. A SIGKILL recorded during the keeper’s restart interval therefore does not latch recovery; a crash does not increment the consecutive count.

   Additionally, `exit_status()` matches only PID even though the wrapper records a launch ID, allowing an old record to match a reused PID.

   **Fix:** reconcile each unfinished launch exactly once before launching again, binding records to launch ID and process identity. Test supervisor downtime followed by normal exit, crash, SIGKILL and missing exit report.

6. **Should-fix — Manual Prism launches bypass pin and world preflight.**  
   [aresos-desktop:924](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:924)

   After a previous launch, `on_jvm_start()` accepts a manual launch based on instance name and Java path. It does not recheck image hashes or the managed instance. Even a damaged or missing hub merely selects `mode='setup'`; it does not refuse launch. Changes made in Prism after the supervisor’s earlier preflight therefore evade the promised mismatch-to-recovery behavior.

   **Fix:** apply a common validation gate to every new JVM authorization, including UI launches. Validate the actual instance directory, not just `INST_ID`, and refuse damaged or unexpectedly missing worlds.

7. **Should-fix — Failed spawn or PID handoff can leave STARTING indefinitely.**  
   [aresos-desktop-java:122](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop-java:122), [aresos-desktop:1026](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1026)

   Authorization sets `launch.accepted=True` before Java is spawned. If `Popen()` raises, or the PID handoff is lost/refused, no JVM PID is recorded. Prism exit handling then ignores the accepted launch, while the startup timeout requires a JVM PID. The result can be no game and no recovery window indefinitely.

   **Fix:** add an explicit launch-failure report and a bounded authorization-to-PID handshake. Watch wrapper death and recover failed handoffs. Test spawn failure and connection loss between authorization and `jvm_started`.

8. **Should-fix — Download pinning stops short of the executable game dependency set.**  
   [aresos-desktop:317](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:317), [aresos-desktop:438](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:438)

   Prism, Java, Fabric libraries, Fabric API and the mod have explicit pins. However, the provisioned pack leaves LWJGL resolution to Prism’s metadata, and validation explicitly accepts **any** `org.lwjgl3` version. Minecraft/Prism component metadata and the resulting native-library set are not bound to the reviewed lock. A version string alone does not reproduce that dependency set. Prism resolves missing component versions from downloaded requirements. [Upstream resolver](https://raw.githubusercontent.com/PrismLauncher/PrismLauncher/11.1.1/launcher/minecraft/ComponentUpdateTask.cpp)

   **Fix:** lock the component metadata and executable dependency versions/hashes, including LWJGL natives. Continue downloading Minecraft through authenticated Prism; pinning metadata does not require redistributing Mojang assets.

9. **Should-fix — Recovery memory protection required by B5 is missing.**  
   [aresos-desktop:498](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:498), [autostart:5](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/share/aresos/labwc/autostart:5)

   The change establishes the game’s soft limit but adds no corresponding protected resource arrangement for the compositor, supervisor and recovery terminal. There is no ancestor-aware recovery memory protection or verification of the inherited oomd selection policy. A working shortcut in an idle VM does not establish that recovery survives memory pressure on the 16 GB laptop.

   **Fix:** configure and inspect the effective resource hierarchy, including ancestor protection and kill boundaries. Add a disposable-VM pressure test proving the recovery terminal remains usable when the game group is terminated.

10. **Should-fix — Readiness remains misleading after heartbeat loss.**  
    [aresos-desktop:1074](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1074)

    `heartbeats_stopped()` clears only the healthy-reset timer. It leaves `launch.ready=True` and state IN_WORLD. If the helper exhausts its restart budget after the hub was initially ready, no recovery window appears. An adopted JVM also bypasses the prepared-start timeout entirely.

    **Fix:** represent lost readiness visibly without killing or repairing the world. Clear the ready indication, show the helper/heartbeat failure, and retain a bounded readiness check after adoption. Test helper exhaustion after IN_WORLD and adoption of a permanently unready JVM.

11. **Should-fix — Automatic restoration does not preserve foreground apps.**  
    [rc.xml:20](C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/share/aresos/labwc/rc.xml:20)

    The comment promises a desktop below normal apps, but the rule only removes decorations and maximizes. Neither the supervisor nor this rule preserves an editor/browser’s foreground position when Minecraft is restarted. B2 explicitly requires a restored desktop to wait below the foreground app. Labwc exposes focus-request controls, but none are configured here. [Labwc window rules](https://labwc.github.io/labwc-config.5.html)

    **Fix:** coordinate restoration with package 24’s window tracking so an existing foreground app remains active. Test a crash/restart while typing in an editor, including pointer capture and the recovery shortcut.

On package 21’s rules, the normal automatic path uses absolute executable paths and restores the system PATH. The recovery rcfile avoids the owner’s `.bashrc`. I found no new elevation route. Package 24’s nonce/instance handoff and private status pipe are coherent; the problems are the lifecycle gaps around that contract.

My assessment of every JUDGMENT-CALL:

| # | Assessment |
|---|---|
| 1 | **Agree with the first-run interaction.** Reusing the seed chooser preserves the owner’s choice and existing creation safeguards. It should remain explicitly documented as an interactive first start. |
| 2 | **Agree.** Removing the routine login terminal matches the brief, provided recovery remains dependable. |
| 3 | **Agree.** A successful process exit should not immediately reopen Minecraft. Guardian shutdown behavior remains separate. |
| 4 | **Agree.** Showing recovery while allowing a slow world load to finish is safer than killing it. |
| 5 | **Agree as a degraded fallback.** Intel rendering can retain access, but does not satisfy NVIDIA hardware qualification. |
| 6 | **Agree with the managed-instance design.** Image-backed inputs and an explicit reset are sensible; findings 6 and 8 expose incomplete enforcement. |
| 7 | **Agree.** The official pinned bundle with updater and portable mode removed fits the brief. |
| 8 | **Agree.** The headless Java runtime is appropriate for this LWJGL-based client; the real launch still needs qualification. |
| 9 | **Agree.** Keeping the loader aligned with the tested mod is preferable to an unrelated version bump. |
| 10 | **Disagree.** Treating whole-scope unknown exits as restartable crashes defeats the OOM policy. |
| 11 | **Agree.** A fresh nonce per launch and stable session instance identity fit the helper’s authentication and journal contract. |
| 12 | **Agree.** Reboot must not silently clear a crash latch. |
| 13 | **Agree with a bounded keeper, not the current recovery completeness.** Dead-launch reconciliation and adopted readiness need fixing. |
| 14 | **Agree.** A digest-pinned CI builder is a reasonable canonical jar build. Every image-build path must invoke it and enforce the resulting pin. |

Verification limits: I inspected the diff, implementation, tests, recorded evidence and relevant upstream source. Production-source `git diff --check` passed; the full diff reports whitespace in captured evidence logs. I could not rerun Python/WSL tests because WSL returned `E_ACCESSDENIED` and Windows had no registered Python interpreter. No real Minecraft launch, image rebuild or laptop pressure trial was performed in this review. The worktree remains unchanged.

CHANGES-NEEDED