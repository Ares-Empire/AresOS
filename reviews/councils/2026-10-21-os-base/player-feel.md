Reviewed design commit `c1908bc`. No files changed; no VM or hardware tests run.

1. **High — Shutdown protects the world but does not establish that other apps can safely close.** [Location](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:199)

   **Scenario:** The owner has an unsaved document open and selects Save and Shut Down. Minecraft exits, its backup succeeds, and the helper calls logind. Nothing specifies how the document gets a save/cancel opportunity. “No automatic force-close” does not supply that missing step.

   **Impact:** A successful world-save test can conceal loss of ordinary desktop work.

   **Fix:** Before stopping Minecraft, request normal app closure and let the owner resolve remaining windows. For the first version, a simple cancellable “close your apps first” flow is sufficient; automatic detection of every app’s unsaved state is unnecessary.

   **Check:** Shut down with an unsaved editor document and a browser form. Cancel must preserve both and leave a usable desktop; completing shutdown must not silently discard either.

2. **High — Hiding Sleep until qualification does not prevent lid and power-button actions from bypassing the helper.** [Location](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:119)

   **Scenario:** During the initial SSD trial, the owner closes the lid or briefly presses the power button. The design specifies no policy for intercepting these events. Upstream logind defaults include lid-triggered suspend and power-button shutdown; lid handling also ignores high-level suspend blockers by default. [systemd documentation](https://www.freedesktop.org/software/systemd/man/latest/logind.conf.html)

   **Impact:** An unqualified suspend path can run despite the advertised shutdown fallback, or power-off can bypass the acknowledged save/backup sequence.

   **Fix:** Define lid, sleep-key and power-key handling before the first hardware trial, including behavior when the helper fails. Route supported actions through the same save protocol; explicitly disable unqualified sleep paths and explain the temporary lid behavior during setup.

   **Check:** Exercise these events during loading, editing, saving and helper failure. Before qualification, none may trigger suspend; power-off must follow the defined save policy.

3. **High — The package order postpones the decisive hardware evidence until after substantial optional work.** [Location](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:249)

   **Scenario:** P1–P9 build and review successfully, including a custom updater and Plymouth presentation. P10 then discovers that the selected signed NVIDIA stack or external boot path does not work on this LOQ.

   **Impact:** A student spends limited review time approving infrastructure before discovering whether the core experience is viable. P8 also couples essential backups to a much larger update system.

   **Fix:** Split P10 into an early boot/driver trial and a later daily-use qualification. Preserve P3’s isolation, target checks and boot protections. Then combine the minimum session, first-run networking/login, exact-world launch, clean shutdown and tested backup into one end-to-end milestone. Defer the custom release updater, splash artwork, Bluetooth pairing polish, suspend, NVMe migration and in-game settings. A short, pinned prototype can use controlled maintenance without first building its own update service.

   **Check:** The first milestone should demonstrate F12 → controllable Nether hub → open/close one app → clean shutdown → normal Windows boot, plus restoration of a changed test world. Optional polish must not be a prerequisite.

4. **Should-fix — The suspend contract stops Minecraft but has no corresponding resume contract.** [Location](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:197)

   **Scenario:** Sleep records an intentional stop, exits Minecraft, backs up and suspends. On wake, the intentional-stop rule still suppresses restart; no RESUMING transition launches the world again. Simply adding a relaunch would also impose game loading and the README’s return-to-hub behavior.

   **Impact:** Waking can produce an empty session, or turn every short lid closure into another loading screen and relocation.

   **Fix:** Keep sleep deferred for the first milestone. Before enabling it, choose explicitly between retaining the saved/paused game process and stopping/relaunching it. Specify wake handling, foreground-app preservation, player position and a wake-to-input target. The existing test of suspending a loaded shader world must match the chosen lifecycle.

   **Check:** Sleep while away from the hub and while a browser is foreground. Wake must restore the specified position and focus without duplicate game instances or manual recovery; measure time until input works.

5. **Should-fix — There is no memory budget or acceptance test for Minecraft sharing this 16 GB laptop with real work.** [Locations: graphics](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:53), [acceptance trials](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:227)

   **Scenario:** The shader world passes its standalone test. The owner then opens browser tabs, a video call and an editor. Memory pressure makes switching sluggish or terminates a process; restarting Minecraft adds pressure again.

   **Impact:** The desktop works in demonstrations but becomes unreliable during the activity it exists to launch.

   **Fix:** Select a measured Java heap and render/simulation-distance baseline, reserve headroom for apps, and define recovery under memory pressure. Any swap must stay on AresOS storage. Avoid adding a sophisticated resource manager before measuring the ordinary workload.

   **Check:** Run a representative study session with Minecraft resident. Record total memory, swap activity and switching latency; require no lost app state, restart cycle or inaccessible recovery UI.

6. **Should-fix — Frame-rate caps are specified, but inactivity and acceptable battery/heat behavior are not.** [Locations: power policy](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:61), [measurement trial](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:239)

   **Scenario:** The owner reads notes for an hour while Minecraft renders behind the browser, or leaves the visible hub unattended. Five FPS and disabled shaders can satisfy the configuration while the laptop still consumes unacceptable power. NVIDIA documents that GPU and video-memory power states depend on workload and retained resources, not just an FPS setting. [NVIDIA documentation](https://download.nvidia.com/XFree86/Linux-x86_64/580.95.05/README/dynamicpowermanagement.html)

   **Impact:** Persistent fan noise, heat and short battery life can make the desktop unpleasant despite every functional test passing.

   **Fix:** Define separate active-world, app-focused and idle behavior, including display blanking and whether world simulation/audio continue. Measure reduced or stopped rendering when fully hidden. Establish an owner-accepted power/comfort limit and a fallback if it fails; reporting measurements alone is not acceptance.

   **Check:** Compare the same browser workload with Minecraft stopped, hidden and visible, on AC and battery. Include idle periods and charger transitions; record whole-system draw, temperatures, fan behavior and return responsiveness.

7. **Should-fix — The return-to-world rule can steal focus when a background app closes.** [Location](C:/Users/pab/AresOS-02-os-base-design/docs/design/OS-BASE.md:191)

   **Scenario:** A terminal task finishes and its last window closes while the owner is typing in the browser. The stated final-window rule focuses Minecraft even though the owner did not leave the browser.

   **Impact:** Keystrokes reach the world, interrupting work and potentially triggering movement or app actions.

   **Fix:** Return to Minecraft when the closing window owned the active interaction. Background closure must preserve current focus. Retain the intended “close the foreground app → world” behavior, and clear held game inputs during transitions.

   **Check:** Close a background terminal while continuously typing in another app; focus must remain unchanged. Separately verify foreground closure, dialogs, Alt+Tab and Super+Home, including pointer capture and held keys.