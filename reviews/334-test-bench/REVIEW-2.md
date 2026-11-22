# Review 2: the test bench's design note

**Verdict:** NOT READY

## Blocking

1. **The tier 1 worked example cannot run as written: the laptop home quits on a headless output.**
   - **Where:** `docs/design/TEST-BENCH.md` §2: the "Missing" list (lines 57–62), the worked example steps 3–7 (lines 90–96) and step 4's acceptance test (line 285). Also §3's example, step 4 (line 182).
   - **What:** `os/config/usr/libexec/aresos-laptop-home` picks its monitor with `laptop_monitor`: the first connector that starts with `eDP` (lines 594–595). With no such monitor, `activate` prints "laptop display unavailable" and quits (lines 2565–2572). Headless labwc names its outputs `HEADLESS-n`. The VM's only output is `Virtual-1` (`briefs/321-deskflow-image.md` line 42). So in the desk the home never maps, and no house can be clicked. Step 4's test "Section 2's example is green" can never pass.
   - The §3 promise fails the same way. 23c starts the home only when an `eDP` output is on (`docs/design/LAPTOP-HOME.md` §6, "Start"), and `STATE.md`'s 23c entry says "the VM has one output". Until 23c, the VM's helper also has no view token.
   - **Why it matters:** the brief names this exact flow as tier 1's worked example. The note never mentions the `eDP` rule, so step 4's builder runs into it unplanned.
   - **The fix:** the repo has already solved this. `os/tests/laptop_home_headless.py` `fixture_main` (lines 486–540) loads the program as a module and calls `run(token, select_monitor=<HEADLESS-1>, …)`. It sets the output to 1920×1080 with `wlr-randr`. The same file drives labwc's virtual pointer and keyboard with a German keymap (`virtual_input`, lines 270–333) and has a test channel that returns the scene's hit boxes. `os/tests/laptop_home_helper.py` has a stand-in helper (`StandIn`) and a home generator (`town`).
     - Put a bench-only launcher of that kind into the desk image (never into `os/config`), and name it under "Missing" and in step 4.
     - Take house positions from that channel's model rather than re-deriving them from section 3's rules.
     - Rewrite the §3 line: the laptop home is tested in tier 1 (with the override) and in tier 3 (the real `eDP`). In the VM it runs only with the same override and a bench helper, or not at all.
     - Add "the `eDP` choice itself is tested only in tier 3" to Known limits.

2. **The laptop VM's memory protection does not do what the note promises the owner.**
   - **Where:** §3 "Memory (laptop)" (lines 156–162), the cost table (line 168) and Owner decides 2 (line 295: "is the first thing killed if memory runs short").
   - **What:** the note says a user scope with `MemoryMax=5G` and `MemorySwapMax=0` means "the VM dies first, never his game". The code doesn't support that:
     - `MemoryMax` only caps QEMU's own cgroup. It chooses no victim when the pressure comes from outside it.
     - `MemorySwapMax=0` keeps the VM's 4–5 GiB in RAM. Under system-wide pressure, reclaim then swaps out his game's and his apps' pages instead, which is the opposite of the brief's rule.
     - The image runs systemd-oomd with managed memory pressure on `user@1001.service` (`os/ci/overlay/checks.py`, `memory_protection`, lines 237–241). Only the session scope carries `oomd_avoid` (lines 222–236). His game's scope (`aresos.slice/aresos-game-*.scope`, line 176) and a bench scope are siblings under the same user manager. oomd kills by reclaim activity, not by who caused the pressure.
     - `checks.py`'s pressure test (lines 263–336) shows that a hog which keeps growing gets killed. It says nothing about a fixed-size VM next to a growing game or Chrome.
     - Memory is checked only at start and right before QEMU. After that nothing watches. "Thirty minutes without a step" is an idle limit, not a memory one.
     - "His game" detection copies `mod/dev/env.sh`, which finds only Lunar Client's Java (lines 59–68). On AresOS the hub JVM runs whenever his desktop does.
   - **Why it matters:** his game pushed into swap, or killed by the kernel or by oomd, is exactly the harm the brief's Memory limit forbids. He would also answer decision 2 based on a promise the design doesn't keep.
   - **The fix:**
     - Keep the start gate and the cap.
     - Add a watcher that checks `MemAvailable` and `/proc/pressure/memory` every 1–2 s. Below a floor it sends `system_powerdown`, and it kills the scope a few seconds later.
     - Start QEMU with `oom_score_adj=1000` (`choom`; an unprivileged process may raise its own value).
     - Drop `MemorySwapMax=0`, or say why that trade is right.
     - Detect his game as Lunar's Java or the AresOS desktop JVM (`aresos-desktop status`'s `jvm_pid`, or an `aresos-game-*.scope`).
     - Give step 6 an acceptance test: the watcher stops a stand-in VM when a fake `/proc/meminfo` or `/proc/pressure/memory` crosses the floor, and stops it while a stand-in game keeps running.
     - Rewrite decision 2 to say what the watcher does and what it cannot promise.

## Should fix

1. **The bench code would land in an image layer.**
   - §6 puts the code in a new `os/bench/` (line 263). `os/Containerfile`'s `packages` stage runs `COPY . /tmp/aresos/` (line 35), and the shipped `aresos` stage is built `FROM packages`.
   - `os/.containerignore` excludes only `manifest/ci/`, `README.md`, `ci/` and `release/`. Its own comment says CI code must never reach any image layer. Line 39 asserts only `test ! -e /tmp/aresos/ci`. Brief 321 hit the same problem (line 51).
   - This is not blocking: nothing from it is installed or enabled, and `/tmp/aresos` is gone from the final image (`os-image.yml` line 362). The bytes sit inert in a lower layer.
   - Fix: add `bench/` to `os/.containerignore`, add `test ! -e /tmp/aresos/bench` beside line 39, and add the bench paths to the release-isolation list. These are `linux-aresos`'s files.
2. **The reuse list misses existing code.** `os/tests/laptop_home_headless.py` and `os/tests/laptop_home_helper.py` already provide a stand-in helper, a home generator, made-up instance and token, virtual input and pictures. For `ü`, the typing helper is `os/ci/owner_keys.py`: `os/ci/keyboard_vm.py`'s `physical_keys` refuses anything that isn't ASCII (line 67). Shrink "Missing" and steps 2–4 to match.
3. **The desk image list is incomplete.**
   - Notepad runs `/usr/bin/kwrite` (`os/config/usr/share/aresos/apps/notepad.json`), so the example needs KWrite (KDE Frameworks, which affects the 1–2 GB estimate).
   - It also needs the fonts (Space Grotesk, JetBrains Mono, Jersey 10), `wlr-randr`, at-spi2-core and `bwrap`.
   - The headless output must be set to 1920×1080, as `fixture_main` does.
4. **Tier 1's systemd and container lifetime.**
   - If the spike runs systemd as the container's init, 316's `no_sockets` check (`os/input-portal/harness/in-container.sh` lines 31 and 46) fails before anything starts. Run the checks before systemd, or allow-list its sockets on purpose.
   - "A trap removes that one container (`run.sh`)" cannot cover `up`, `step` and `down` as separate commands. Use podman's `--timeout`, an idle limit like tier 2's, and cleanup by the run's container name.
5. **Tier 1 has no memory cap.** With `--cgroups=disabled`, podman cannot enforce `--memory`. Wrap `podman run` in `systemd-run --user --scope -p MemoryMax=…`, as `env.sh`'s `aresos_scope_start` does; with cgroups disabled the container stays inside that scope. Check for his game as in blocking 2.
6. **Owner decides 5 is not the owner's call.** `os/ci/rehearsal-packages.json`, the file the note cites, says in its 22c, 22d and 42 entries that "the runners are free for this public repository; the caps exist to stop runaway loops". So the dispatch cap is the lead's call. Move it to the build plan; the note's "I could not read in code" is wrong. Decision 6 is optional: the brief already allows read-only probes ("read-only unless he says go").
7. **The password claim contradicts the reused code.** "The bench disk is built with no password for any account" (line 204), but the note reuses `os/ci/prepare-disk.py`. That script gives `root` a per-run password (lines 11–22), and `vm.py` uses it for its recovery check (lines 22 and 137). Either say that root has a synthetic, masked, per-run password, or give bench mode its own config.
8. **Step 7's sizes and setup.**
   - The 40 GB cap leaves out several large items:
     - the AresOS image in rootless storage (12.5 GB unpacked, `os/ci/stock_image.py` line 47);
     - its build stages (the labwc RPM build, and the mod's Gradle build in Temurin);
     - the OCI archive for the share (5.6 GB);
     - the builder VM's own disk;
     - the guest's second deployment for `bootc switch`.
   - `stock_image.py` reserves 88 GiB free for a comparable copy (line 52).
   - Name the builder VM's boot image, and put the local build under the client-test lock and memory gate, since it runs Gradle.
   - Say that the 9p share is the bench volume only, never the worktree, which sits in his home. Note also that `stock_image.py`'s share is written by the guest; it is not read-only.
   - Then recompute decision 4.
9. **Step 1's test "The release check finds no bench file" can't run.** Release jobs only run on release branches (`os-image.yml` lines 264, 421 and 532). Make it a unit test that the release-isolation lists name the bench paths, plus a bench-mode check that `localhost/aresos:check` holds none.
10. **Hosted CI gaps.** `tesseract-ocr` is installed only in the rehearsal job (`os-image.yml` line 847); step 3 must add it to `check-build`. Brief 321's `check_build=deskflow` edits the same bound files (`os/ci/check-build.sh`, `os-image.yml`), so name the merge order and the rebind.
11. **Tier 3 can't read Wi-Fi, Bluetooth or the touchpad.** §5 promises them (line 208), but its read table has no source for them. Add `rfkill list`, `nmcli` on the system bus, `/sys/class/bluetooth`, `/proc/bus/input/devices`, and `/sys/class/drm/*/modes` for the external screen.
12. **Citation fixes.**
    - "never `nvidia-smi`: a query wakes the card (`STATE.md`, package 47)": package 47's entry (line 148) doesn't say that.
    - "built environment … `client-test.sh`, `ISOLATE`": `ISOLATE` (lines 117–118) only removes named variables from an inherited environment. Cite `driver.py`'s `ENV` (an allow-list) as the pattern instead.
    - §10's "stray lines": this checkout's `briefs/334-test-bench.md` ends at "7. **Known limits.**" with nothing after it.

## Known limits to add

- **The bench uses `ares`'s user manager, as `env.sh` does today.** The `systemd-run --user` and `systemctl --user` calls, and podman's cgroup manager if step 4 enables cgroups, reach the same user manager that runs his session. They should only create and stop the bench's own named scopes. They should never reach his session's `dbus-run-session` bus (brief 321 line 43). Build the bench's own environment from an allow-list before making those calls.
- **Another rig injects input outside a container.** `os/tests/laptop_home_headless.py` drives virtual input into a private labwc inside bwrap, over a read-only host root (lines 200–208). List it in §10 beside the mod's rig.
- **The desk shows the real battery.** The desk's laptop home reads the host's `/sys/class/power_supply` (lines 559–577). It is only a read, but the battery level in desk pictures is the laptop's.
- **bwrap may not start inside the rootless container.** The icons then show without pictures (`aresos-shell` lines 1802–1804; `aresos-laptop-home` lines 228–232).
- **KWrite's accessibility tree needs the a11y bus switched on** (`QT_ACCESSIBILITY` or `org.a11y.Status`). An empty tree is a setup fault, not a pass.
- **The image's `rc.xml` keeps live bindings in the desk.** `W-C-Escape` and the brightness keys run commands there. They reach nothing of his, but they can make a step fail noisily.
- **`aresos-desktop status` opens his live supervisor's socket.** It is a read, but it is a connection into his running session.
- **`/dev/kvm` may already be open to `ares`.** On Fedora it is often world-writable, which could make decision 8 unnecessary (not checked).
- **1920×1080 in the VM is untested here.** Setting it through `virtio-vga` has not been tried in this repo; `control_vm.py` saw 1280×800.

## Claims checked

| Claim | File read | Holds |
|---|---|---|
| 316 harness: no network, no `-v`/`--device`/`--env`, tar in and out, plain-file evidence, `--cgroups=disabled` | `os/input-portal/harness/run.sh` 66–84 | yes |
| Isolation checks and `UNUSABLE` | `os/input-portal/harness/in-container.sh` 28–47, 85–87 | yes |
| `start_bus`, `start_labwc`, `ENV`, `check`, `VInput`, `randr_outputs`, exits 0/1/2 | `os/input-portal/harness/driver.py` | yes |
| Helper speaks 1.2, starts apps in user scopes, `DESKTOP_APP_IDS` | `os/config/usr/libexec/aresos-shell` 1–85, 150, 2285 | yes |
| Laptop home draws with Cairo only; 61 MiB in headless labwc | `docs/design/LAPTOP-HOME.md` §4 | yes |
| Laptop home runs under headless labwc / in the VM (implied by the examples) | `aresos-laptop-home` 594–595, 2565–2572 | no |
| `vm.py`: screendump, send-key, `-m 6144`, `-nic user`, fresh overlay | `os/ci/vm.py` 28, 40–45, 98–106 | yes |
| `Guest`, `CHROME_STEPS`, `click`, `agent_title`, `password_hash`, reboot step, 1280×800 | `os/ci/control/control_vm.py` | yes |
| German typing through `physical_keys`; `yz-/!ü` | `keyboard_vm.py` 57–68; `owner_vm.py` 34, 39 | partly (`ü` needs `owner_keys.py`) |
| Read-only job token; evidence under 180 MB; release tests for `aresos-ci` | `.github/workflows/os-image.yml` 189–197, 251–255, 354–373 | yes |
| `registry_auth.create` has no owner-token fallback | `os/ci/registry_auth.py` 63–74 | yes (org release path) |
| `ares` is locked; greetd logs in `ares` without a password | `os/tests/guest.sh` 10–15; `os/config/etc/greetd/config.toml` | yes |
| Bench disk has no password for any account | `os/ci/prepare-disk.py` 11–22 | no |
| Lid ignored in all three cases; every sleep request refused | `os/tests/power-events.py` 55–59, 107–113 | yes |
| "VM dies first, never his game" | `checks.py` 219–241, 263–336; `mod/dev/env.sh` 59–89 | no |
| `disk_args` asserts a regular file under the work folder | `os/ci/two_disk_vm.py` 153–156 | yes |
| Read-only share as in `stock_image.py` | `os/ci/stock_image.py` 9–13 | partly (the guest writes into it) |
| Rounds of 26–68 min; boot to channel 28–44 s | `reviews/18c-image-test/REPORT.md` 538–548 | yes |
| Hosted minutes can't be read from code | `os/ci/rehearsal-packages.json` (22c, 22d, 42 entries) | no |
| Brief 321: second screen, bus from labwc's environment, 8-dispatch cap | `briefs/321-deskflow-image.md` 43–44, 104 | yes |
| `nvidia_wmi_ec_backlight` 0–800; "inert until 23c" | `STATE.md` 143, 170 | yes |
| `nvidia-smi` wakes the card (package 47) | `STATE.md` 148 | no (not stated there) |
| `rc.xml` binds Alt+F4 to Close; `--session` copies `rc.xml` | `rc.xml` line 20; `mod/dev/client-test.sh` line 191 | yes |
| `os/bench/` stays out of the image (implied) | `os/Containerfile` 34–39; `os/.containerignore` | no |
| The brief ends with stray lines | `briefs/334-test-bench.md` | no |
