# Test bench: how Claude tests AresOS changes itself

**Status:** design note for brief 334, step 1, revision 3 (2026-11-22). It answers `reviews/334-test-bench/REVIEW-3.md` and keeps the owner's answers on board T499 to T502. Nothing here is built. A file name after a claim is where I read it. *Assumption* marks what I did not check in code.

## 1. Summary

| Tier | What Claude can test | Where | Allowed by | Hosted route instead |
|---|---|---|---|---|
| 1. Hidden desk | Session programs that need no restart: the app helper, the laptop home, the indicator plate, window rules, key bindings, dialogs | The laptop, in a throwaway container with its own invisible desktop | Containers on the laptop: yes (T499) | None with a live loop. The same steps can run inside the tier 2 VM. |
| 2. Bench VM | What needs a new image or a restart: boot, auto-login, units, the session after a reboot, shutdown, an update inside the guest | On GitHub's runners in batches. Live on the laptop only after step 6's memory checks pass. | Runners: nothing needed. Laptop VM: yes, "if they fit and work", with the KVM step and the disk space (T500) | Yes: the hosted pass. It stays if the laptop route fails. |
| 3. Real laptop | Hardware: GPU, brightness, lid, battery, Wi-Fi, Bluetooth, touchpad, screens | The laptop, after his own update and restart | Read-only readings after each update (T501). About ten minutes of his hands per release (T502). | None: it is the hardware. |

- The bench never drives his real session. Tiers 1 and 2 are disposable. Tier 3 only reads, unless he says go.
- **First value:** the hosted bench pass (build step 1).
- **The interactive goal:** the laptop VM (steps 7 and 8). It needs the memory checks in step 6 and the disk budget in step 2. The local image build also needs the egress checks in step 4.

**What binds, and what is new**

| Source | What it says |
|---|---|
| `AGENTS.md`, "Environment" and "Verification" | No sudo. Nothing installed system-wide. No window and no input in his session. One heavy step at a time. Never the module `test_owner_update`. |
| `CLAUDE.md`, "Owner decides" | Disks, boot settings, system software, money and publishing are his calls. A CI image that is built and thrown away needs no OK. |
| New permissions | Containers (T499) and a VM (T500) on the laptop. No rule in the repo forbade them. The laptop list in brief 334 came from one lead's prompts, not from `AGENTS.md`. |
| The bench's own rule | Never `rpm-ostree`, `bootc`, `ostree`, the owner tools or a `test_owner_*` module against the real laptop. A `bootc` call runs only inside a guest. No OK lifts this. |

## 2. Tier 1: the hidden desk

**What it is.** A rootless Podman container started from the bench's own image store under the owner's account. Its image is the AresOS image the bench builds locally for the VM (section 4), run as a plain container. So KWrite, the fonts, labwc, `grim`, `wlr-randr` and `bwrap` are the shipped ones. No systemd runs in it.

A slim Fedora image was the first draft's choice. Its packages would differ from the image's, and the local image is in the store anyway. It stays the fallback if the local build proves impossible (step 7). A laptop fetch of either image needs step 4 to pass.

**Start, in two phases**
1. As the container's root:
   - run the isolation checks;
   - unpack the checkout's files from a tar stream;
   - lay the changed files over their image paths, as `os/Containerfile` does (`cp -a … /`);
   - put stand-ins at `/usr/bin/systemd-run` and `/usr/bin/systemctl`. The helper calls both by full path (`os/config/usr/libexec/aresos-shell`, `SYSTEMD_RUN`, `SYSTEMCTL`).
2. Drop to a non-root user with no capabilities. Then:
   - start a private session bus and a headless labwc with one output;
   - set it to 1920×1080 with `wlr-randr`, as `os/tests/laptop_home_headless.py` (`fixture_main`) does;
   - check the Wayland globals and the real output size before any test, as `os/input-portal/harness/driver.py` (`setup`) does.

**Native tests.** The native test list stays empty. A module name never grants approval. `bench test <module>` makes that decision before any import. Changed code, including imports, runs only in the desk container, the VM or on hosted runners. The fixed hardware recorder in section 5 reads state on the laptop.
- `bench test` accepts only `test_*.py` modules. It refuses `test_owner_*` and anything under `os/ci/` before import.

**Can test:** `aresos-shell` flows (list, open, views), the laptop home, the indicator plate, `rc.xml` bindings and window rules, covers, dialogs.

**Cannot test:**
- The real game. The mod's rig stays `mod/dev/client-test.sh`.
- GPU, sound, greetd, logind, system units, anything across a restart.
- Real app scopes: the desk has stand-ins, so scopes are tier 2's.
- The laptop home's own choice of the `eDP` screen: tier 3.

**How Claude sees, acts and reads**

| Need | How | Read in |
|---|---|---|
| Screenshot | `grim` on the private compositor | `os/ci/overlay/checks.py`, `cover_start`, uses it the same way in the VM |
| Buttons and text | The accessibility tree (AT-SPI) on the private bus: role, name, box. The accessibility bus must be switched on for Qt and GTK. An empty tree is `UNUSABLE`, never a pass. | New. *Assumption:* the image ships the AT-SPI bus. |
| The laptop home | It draws with Cairo only, so it has no tree (`docs/design/LAPTOP-HOME.md`, section 4). Each house's `box` comes from the program's own scene model, through a test channel. | `os/config/usr/libexec/aresos-laptop-home`, `build_scene`; `laptop_home_headless.py`, `install_channel` |
| Pointer and keys | labwc's virtual pointer and keyboard, with a German keymap | `laptop_home_headless.py`, `virtual_input` |
| State | A watching view on the helper (`apps_running`, `get_home`, `list_apps`); the home's scene model; logs; `wlr-randr` | `aresos-shell`, `report_running`; `install_channel` |

**Reuse**

| What | From |
|---|---|
| Container shape, tar transport and `--timeout` | `os/input-portal/harness/run.sh`, `run_tests` |
| Isolation checks, `UNUSABLE` | `harness/in-container.sh` |
| Private bus, allow-list environment, PASS/FAIL lines, exit 0/1/2 | `harness/driver.py` (`start_bus`, `ENV`, `check`) |
| The laptop home on a headless output, its test channel, virtual input | `os/tests/laptop_home_headless.py` (`fixture_main`, `install_channel`, `virtual_input`) |
| Home fixture rows | `os/tests/laptop_home_helper.py`, `town` |

**Missing**
- A bench launcher for the laptop home, modelled on `fixture_main`. It picks `HEADLESS-1` and passes a fixed battery reading. It lives in the bench's code, never in `os/config`. The stock program picks only an `eDP` screen and quits without one (`aresos-laptop-home`, `laptop_monitor`, `activate`).
- A stand-in desktop (section 3), with a made-up instance, nonce and view token.
- The two systemd stand-ins.
- A long-lived container with a step loop.
- A text-to-key table for the virtual keyboard.

**How the limits are kept**
- **Process and user:** `podman run` is rootless. After setup the bench runs under a non-root UID mapped to a sub-UID. Every `podman exec`, including evidence return, uses that verified user without `CAP_NET_ADMIN`. *Assumption:* the owner has a sub-UID range.
- **Isolation:** `--network=none` by default. See section 6 for network options. No host folder, device or environment is passed in. The bench builds the `podman run` line from a fixed template. A test pins it. Steps travel over `podman exec -i`.
- **Returned evidence:** a bounded extractor accepts only regular files at fixed member paths. It checks paths, types, file count, and per-file and total sizes before creating evidence files. It rejects links, devices, absolute paths and `..`. The `grep -qv` pipeline in `os/input-portal/harness/run.sh` can return early and make `tar` fail. Under `pipefail` that can bypass rejection, so the bench uses the extractor for every return.
- **Checked before anything starts** (`in-container.sh`):
  - none of its eight session variables is set, `WAYLAND_DISPLAY` and `DBUS_SESSION_BUS_ADDRESS` among them;
  - no `/dev/input`, `/dev/uinput`, `/dev/dri`, `/run/user` or home;
  - no socket anywhere; only the loopback interface.
- **Checks the bench adds:**
  - Every line of `/proc/self/mountinfo` must be one the template expects. `no_host_mount` in `in-container.sh` looks for four named folders only.
  - Not UID 0 after the drop. No `/dev/kvm`.
  - A failed check ends the run as `UNUSABLE`.
- **His helper and user manager are out of reach:** his runtime folder is not in the container. `os/tests/check_aresos_shell_headless.py` links the real user manager's socket into its rig; the desk does not use that file.
- **Memory:** the `podman run` sits in a capped scope of the bench's slice (section 3, "Memory"), started the way `mod/dev/env.sh`'s `aresos_scope_start` starts things. *Assumption:* with `--cgroups=disabled` (`run.sh`) the container stays inside that scope. Start is refused under 3 GiB available.
- **It ends by itself:** podman's `--timeout`, ten minutes without a step, and `down` or `clean` by the run's exact container name. One `trap` cannot cover `up`, `step` and `down` as separate commands.

**Cost.** On the laptop.
- Memory: about 0.5 to 1 GiB (*assumption*; the laptop home alone measured 61 MiB in such a compositor, `LAPTOP-HOME.md` section 4). Capped at 1.5 GiB.
- Disk: the local image, temporary writes and bounded evidence (section 3).
- Start: seconds.

**Worked example: the open-app flow against a changed `aresos-shell`**
1. Claude edits `os/config/usr/libexec/aresos-shell` in its worktree. `bench test test_aresos_shell_views.py` loads the module in the desk container.
2. `bench desk up --files os/config`. The isolation lines pass. The changed helper lands at `/usr/libexec/aresos-shell`. `wlr-randr` shows `HEADLESS-1` at 1920×1080.
3. `act home`:
   - The bench starts the changed helper with a made-up instance, nonce and view token.
   - The stand-in desktop says hello, publishes a three-app home with `notepad` in it and reports `world_ready`.
   - The launcher starts the real laptop home on `HEADLESS-1`. It connects as the view `laptop-home`.
   - The bench connects a second view, `bench-watch`.
4. `shot` gives `001.png`. Claude reads Notepad's `box` from the scene model.
5. `click` in that box: a virtual pointer move and a left button press.
6. `wait`:
   - The scene model shows Notepad's house `opening`, then `running`, and the typing line shows no error.
   - On `bench-watch`, `apps_running` gains `notepad`.
   - `app_state` is not awaited there. The helper sends it only to the client that asked (`aresos-shell`, `set_state`). A second hello under the home's name would cut the home off (`hello`).
7. `shot`: KWrite is open and the house is lit. `tree` names KWrite's buttons.
8. `keys alt+F4` (`os/config/usr/share/aresos/labwc/rc.xml` binds `A-F4` to Close). `apps_running` loses `notepad`.
9. `bench desk down`. The evidence lands in `.work/bench/<run>/` and the container is gone.

A helper that raises fails step 6, with the helper's log in the evidence.

## 3. Tier 2: the bench VM

Two routes run the same script.

- **Hosted (first value).** A new mode `check_build=bench` beside `control` (`os/ci/check-build.sh`). The job builds the image from the ref, adds a bench layer, makes a disk, boots it and plays one script. It is a batch: one round per dispatch.
- **Laptop (the interactive goal).** The same guest in QEMU with KVM. QEMU, OVMF, the driver and any stub servers run inside one rootless container, so nothing is installed system-wide. The route stays disabled until step 6's measured checks pass.

**Can test:** boot to the session, units, auto-login, real app scopes, the supervisor's states, shutdown, a restart, an update done inside the guest.

**Cannot test:**
- The real game or Prism sign-in. A fresh VM has no account and stays in `SETUP` (`checks.py`, `desktop_session`).
- Hardware.
- The laptop home, for now:
  - The helper gets its view token only with package 23c (`LAPTOP-HOME.md` section 5, PLAN-GAP).
  - After 23c it runs only with the launcher's screen override: the VM's one output is `Virtual-1` (`briefs/321-deskflow-image.md`), not `eDP`.
- The real installer route. That stays with the two-disk rehearsal (`os/ci/two_disk_vm.py`) and under the install hold (`docs/INSTALL-STATUS.md`).

**How Claude sees, acts and reads**

| Need | How | Read in |
|---|---|---|
| Screenshot | QMP `screendump` to PNG | `os/ci/vm.py`, `screenshot` |
| Shot inside the session | `grim` as `ares` | `checks.py`, `cover_start` |
| Buttons and text | AT-SPI dump as `ares`, on the bus address read from labwc's environment | New. The bus rule is from brief 321 only. |
| Dialogs, pre-desktop screens | Glyph match; OCR | `os/ci/control/control_vm.py`, `agent_title`. `tesseract-ocr` is installed only in the rehearsal job (`.github/workflows/os-image.yml`); step 6 adds it to `check-build`. |
| Keys | QMP `send-key`. German text through `os/ci/owner_keys.py`, whose table has printable ASCII and `ü`. `os/ci/keyboard_vm.py`'s `physical_keys` refuses anything that is not ASCII. | `vm.py`, `keys`; `owner_keys.py`, `maps` |
| Pointer | QMP `input-send-event` on the USB tablet | `control_vm.py`, `Guest.click` |
| Power key, reboot | `system_powerdown`; power off, then boot the same overlay | `control_vm.py`, `Guest.poweroff`, the `reboot` step |
| Guest state | Framed JSON over a virtio port; commands as `ares` through `runuser … env -i` | `os/ci/channel.py`; `checks.py`, `AS_ARES` |
| Logs | The serial log; the guest's journal | `vm.py` |

**Reuse**

| What | From |
|---|---|
| Image from the ref, disk recipe, boot | `check-build.sh`; `vm.py` |
| Guest object and step list | `control_vm.py` (`Guest`, `CHROME_STEPS`) |
| A stand-in started through the real wrapper | `os/ci/overlay/guardian.py`, `arm`, with `GuardianGame.java` |
| Password windows | `control_vm.py`, `password_hash`, `type_password` |
| Terminal sessions as `ares` | `os/ci/control/sessions.py` (tmux through `runuser`) |
| Pinned QEMU and OVMF on runners | `os/ci/toolchain.json` |

**Missing**
- **The bench layer:**
  - Its own Containerfile on the plain image (`localhost/aresos:check`), built from a context that holds only the agent's files.
  - It does not extend the CI overlay, which carries a US keymap, debug drop-ins and shadow programs (`os/ci/overlay/Containerfile`).
  - So `checks.py`'s `layer_actions` loader is not there. The bench brings a minimal agent with the same frames and handshake (`channel.py`; `checks.py`, `main`) on a port of its own.
- **The agent's actions:**
  - `status` (boot ID, image revision, session facts), `shot`, `tree`, `journal`;
  - `exec` as `ares`;
  - fixed root actions: `reboot`, `switch`, `files`, `test-password`.
- **A bench disk config** with no user block, so `root` and `ares` stay locked as the image ships them (`os-image.yml`, the release-isolation step). `os/ci/prepare-disk.py` cannot be reused as is: it gives `root` a per-run password for `vm.py`'s recovery check.
- **The stand-in desktop** (step 5):
  - It is a single-file Java program, started through `/usr/libexec/aresos-desktop-java` as `GuardianGame.java` is. That way it gets the instance and the launch nonce, as `checks.py`'s `desktop_jvm` shows for its JVM.
  - It says hello to the helper, publishes a home, reports `world_ready`, sends heartbeats and can send `open_app`.
  - `GuardianGame.java` cannot do this; `guardian.py` uses it for the save and shutdown path.
- **The script runner and the hosted selector:**
  - A second workflow input, `bench_script`, must match `reviews/<package>/bench/<name>.json` and exist in the dispatched commit.
  - It travels as an environment variable, as `CHECK_BUILD_MODE` does. It is never pasted into a shell line.
  - The job writes `run.json`: the commit, the script's SHA-256, the image's revision label (`os/Containerfile`, `org.opencontainers.image.revision`) and the guest's own report of it.
  - `bench vm run --hosted` refuses evidence whose commit is not the head it pushed.
- **The workflow side:**
  - `check_build=bench` goes into `check-build.sh` and `os-image.yml`.
  - The VM pass is its own step with its own time limit, as Control's is ("Control VM pass").
  - Both files are `linux-aresos`'s and bound (`rebind.py pending`, `STATE.md`, 27b).
  - Brief 321's `check_build=deskflow` edits the same two files. Whichever lands second merges `main` first and keeps both modes.
- **An evidence gate:**
  - Only a fixed set of regular evidence files can be uploaded. Check their paths, sizes and contents before upload, with a total under 180 MB. The release jobs also gate uploads (`steps.evidence.outputs.safe`).
  - Raw guest output stays out of retained job logs.
  - Today `check-build` uploads with `always()`, even when its size check failed.
- **Release protection:**
  - The code lives in `os/ci/bench/`. `os/.containerignore` already excludes `ci/`, and `os/Containerfile` already asserts `test ! -e /tmp/aresos/ci`.
  - The first draft's `os/bench/` would have landed in a layer under the shipped image: the `packages` stage runs `COPY .`, and `os/build.sh`'s last `rm -rf /tmp/aresos` hides files but leaves their bytes in the earlier layer.
  - A unit test checks for bench files outside `os/ci/` among image and build inputs. Scripts under `reviews/` are allowed as runner inputs.
  - A unit test checks that every release-isolation block in `os-image.yml` names the bench layer's paths. Release jobs run only on release branches, so this is a test over the workflow's text.
  - Bench mode uses a distinct tag for the image with the bench layer. It scans the plain image's final files and raw layers for bench paths. A planted file in a layer must fail the scan.
  - Bench dispatch is exclusive with release, rehearsal and published-image switch inputs. Step 1 adds the missing guard to the `image` job.

**How the limits are kept**
- **Network:** off by default on both routes: the guest has no NIC. Section 6 has the two levels a test can ask for. `vm.py`'s `-nic user`, where the guest reaches the host's loopback (`control_vm.py`, `Guest.boot`), is never used on the laptop outside a network-less container.
- **Disks:**
  - Only files in one named volume of the bench's own store. It is the QEMU container's only mount, and `/dev/kvm` its only device.
  - No step takes a disk path.
  - The driver asserts a regular file under its work folder, as `two_disk_vm.py`'s `disk_args` does.
  - No `/dev/nvme*` can be named.
- **Credentials:** none go in.
  - No account in the guest has a usable password. A script that needs a password window sets a per-run made-up one inside the guest.
  - The hosted job has `contents`, `packages` and `actions` at `read`, no `id-token` and no secret but the job token; its checkout keeps no credentials (`os-image.yml`, `check-build`). Bench mode adds no step that takes a token.
- **Host system:** the bench's own rule from section 1.
- **Memory and disk space on the laptop:** the next two blocks.

**Memory (laptop).** The laptop VM route stays disabled until step 6's measured checks pass.
- **One heavy thing at a time, across worktrees.** The bench, `mod/dev/client-test.sh`, `mod/dev/build.sh` and `mod/dev/run-hub.sh` all take the same lock. Use the shared client-test lock from `mod/dev/env.sh`. The bench returns exit 75 when the lock is busy, before starting heavy work.
- **Start gate.**
  - VM: 7 GiB available for a 4 GiB guest.
  - Local build: 6 GiB, the dev rig's floor (`ARESOS_MIN_AVAILABLE_KIB`).
  - Checked at start and again right before the heavy process, as `client-test.sh` calls `aresos_check_room` more than once.
  - Exit 75, and no `--force`.
- **Refused outright:**
  - while Lunar Client's Java runs (`aresos_lunar_game_pids`);
  - on battery;
  - without KVM, because software emulation would burn his CPU.
- **His home screen's game** runs whenever his desktop does, so it cannot be a refusal.
  - The bench finds it as an `aresos-game-*.scope` in the cgroup tree (the name is in `checks.py`, `desktop_jvm`). That is a file read, not a call into his session.
  - While it runs, the guest gets two CPUs.
  - Another lead is working on turning the home screen off. That frees memory. The design does not depend on it.
- **One slice bounds the whole bench tree.** Podman, its helpers, QEMU and the builder VM stay in scopes of one user slice with `MemoryMax` (5 GiB in VM mode), low CPU weight and `nice`. Step 6 checks that the whole tree stays inside the cap. The tree stops if the watcher dies.
- **OOM settings.** QEMU starts with `oom_score_adj=1000`. That affects the kernel's choice among eligible processes. systemd-oomd chooses by cgroup. The bench leaves swap enabled.
- **Early stop.** A watcher outside the slice reads `MemAvailable` and system-wide memory pressure. It stops the VM early when memory runs low. The test disk is thrown away. Evidence already on the host is kept.
- **Measured checks.** Step 6 sets a measurable early-stop threshold. It checks swap growth and responsiveness in a stand-in game, refusal during a concurrent build and shutdown after watcher loss. Its report gives the measured detection and termination delays. A sudden spike can still beat the stop (section 9).
- Fifteen minutes without a step stops the VM and frees the lock.

The memory budgets and floors are starting values. Step 6 measures and sets them.

**Disk space (laptop).** Normal use stays well under the 40 GB cap (T500).
- **One store.** The bench owns its image store, disks and builder files. Step 2's brief settles where the store may live under the worktree rules in `AGENTS.md`. It does so before the store is used.
- **One lock.** Run, expiry cleanup and `bench clean` all take the shared lock. The lock lives outside the directory being deleted. Cleanup refuses an active store, and step 2 proves that cleanup works after an interruption. `bench clean` removes all bench data, including retained evidence.
- **Automatic clean-up:**
  - Only the newest bench image and its base disk are kept. The older one goes before a replacement is written.
  - Each test's disk is deleted when the test ends.
  - The export and the builder's scratch disk are deleted in the step that made them.
  - The build store goes after seven idle days.
- **Enforce the budget before writes.** Count all bench writes on each filesystem. Include the store, export, builder scratch, Podman temporary storage, allocated growth of sparse disks and evidence.
  - Give each phase an enforced peak. Count files that coexist and bound growth while the phase runs.
  - Refuse the phase before it writes if current use plus the additional peak would exceed 40 GB. Also refuse if the filesystem cannot fit the phase's writes and leave the 20 GB SSD reserve free.

| Item | Planning estimate (*assumption* unless cited) | Kept until |
|---|---|---|
| Bench disk, newest only | 6 to 10 GB (the owner's figure); 28 GiB virtual (`prepare-disk.py`) | A newer one replaces it |
| Test disk (overlay) | Up to 10 GB; a `switch` adds a second deployment | The test ends |
| Build store | About 17 GB; the base alone unpacks to 12.5 GB (`os/ci/stock_image.py`, comment at `STORE_BYTES`) | Seven idle days, or `clean` |
| Image export | 6 to 7 GB; the base is 5.6 GB compressed (same comment) | The disk is made or the switch is done |
| Builder VM: boot image; scratch disk | About 1 GB; up to 15 GB | One checked copy is kept; the scratch disk goes when the disk is made |
| Podman temporary storage | Included in the bound for each phase that uses it | The phase ends |
| Evidence, in the worktree's `.work/` | Under 180 MB a run, as on runners | Five runs |

At rest that is about 10 GB without the build store and about 27 GB with it. The table gives estimates for individual items. Step 7 checks the enforced phase limits against measured peaks. If the total will not fit, the phase is refused before it writes.

**Cost**

| | Hosted | Laptop |
|---|---|---|
| Memory | The runner's; guest `-m 6144` (`vm.py`) | 4 GiB guest; 5 GiB cap |
| Disk | The runner's | The table above |
| Time | Control's passes took 26 to 68 minutes a job and 28 to 44 s from boot to channel (`reviews/18c-image-test/REPORT.md`). The bench has no numbers of its own yet. | Boot under a minute, steps in seconds, a full build 30 to 60 minutes (*assumptions*) |

Each package brief caps its hosted dispatches at 8, as brief 321 does; the lead raises it. The bench counts the branch's bench runs before a dispatch. Standard runners are free for this public repo, and the caps exist to stop loops (`os/ci/rehearsal-packages.json`, the 22c, 22d and 42 budget notes).

**Worked example: the same change after a new image boots**
1. Claude pushes the branch with the changed helper and `reviews/NN-slug/bench/open-app.json` (network `none`).
2. `bench vm run reviews/NN-slug/bench/open-app.json --hosted` dispatches `check_build=bench` with that script. It waits with `gh run watch <id> --exit-status --interval 60` (`AGENTS.md`).
3. The job builds the image from that commit, adds the bench layer and boots the disk. greetd logs `ares` in.
4. The script:
   - waits for labwc;
   - `status` answers `SETUP`, and the helper runs;
   - starts the stand-in desktop through the real wrapper;
   - the stand-in says hello, publishes a home, reports `world_ready` and sends `open_app notepad`.
5. It checks:
   - the stand-in's own connection gets `app_state` for its launch;
   - KWrite is in the QMP shot;
   - `systemctl --user` shows a real `app-aresos-notepad-…` scope (`aresos-shell`, `ScopeLauncher.unit`);
   - `tree` lists KWrite's buttons.
6. `reboot`. The boot ID is new. After auto-login the same steps pass, and `journal` holds no traceback from the helper.
7. Claude fetches the evidence with `gh run download` and reads `run.json`, `results.txt` and the pictures.

On the laptop the same script runs step by step after `bench vm up`. A click on a house in the VM waits for 23c.

## 4. Tier 2, "just like the laptop"

| Part | How close | Gap |
|---|---|---|
| Image | The same `os/Containerfile` at the same commit, plus one agent service | A root-run agent exists. The build is throwaway. On the laptop it is built rootless. |
| Apps | Everything in the image: KWrite, Chrome, foot, Prism | His own programs in his home are absent |
| Settings | `/etc` as shipped. A made-up profile can be laid in. | None of his files, ever |
| Keyboard | German as shipped; the bench layer sets no US keymap | Printable ASCII and `ü` only |
| Screen | `virtio-vga` asked for 1920×1080 | Untested here; `control_vm.py` saw 1280×800. One screen, no `eDP`, no refresh rates. |
| The home | A stand-in desktop and a published home | No Microsoft account, no real Minecraft, no NVIDIA card |
| Network | Off or fake per test. Real internet is hosted-only until step 4 passes (section 6). | Not the laptop's Wi-Fi |
| Hardware | Virtual disk and GPU; a uinput lid | Tier 3 |

**Where the VM image comes from**
- **Hosted:** CI builds it from the ref, fresh on every run. `vm.py` demands a fresh overlay.
- **Laptop, full route:**
  1. **Build.** A rootless `podman build` of `os/Containerfile` in the bench's store.
     - It runs under the lock, the gate, the watcher and the budget, because its mod stage runs Gradle.
     - It pulls the pinned public base by digest with no credentials, as `stock_image.py`'s `fetch_command` does on runners.
     - Fetches and build steps that need the internet run on hosted runners until step 4's egress checks pass. The first local image build waits for that gate.
  2. **Layer and export.** Add the bench layer. Export one folder that holds only that image.
  3. **First disk.**
     - A builder VM with no network boots a pinned Fedora CoreOS image: public, signature and checksum checked, one copy kept.
     - It gets the export read-only and an empty file as its target.
     - Inside, the image's own `bootc install to-disk` writes the target.
     - The host needs no root, no registry and no token.
     - The builder is needed only for a disk from scratch.
  4. **Later images** reach a running guest with `switch`.
     - The export is attached read-only: 9p with `readonly=on`, mounted `ro`, the pattern of `two_disk_vm.py`'s owner-auth share and `os/ci/rehearsal_auth.py`'s `guest_mount_command`.
     - The guest uses a writable import of the export on its own disk as the source for `bootc switch`.
     - The new image carries the bench layer too, so the agent survives.
     - After the reboot the step requires a new boot ID, the expected revision and a working channel.
     - `stock_image.py`'s share is no pattern for this: the guest formats and writes a store file on it.
  5. The export lives in the bench store only. The worktree, which sits in his home, is never shared into a guest.
- **Offline source contract.** Step 7's brief specifies how the read-only OCI export becomes the offline source for install and switch. It names where the writable imports and scratch live, with their disk bounds. It says how the builder's inputs arrive before the builder boots with networking disabled. Step 8 uses that same contract for `switch`.
- **Laptop, quick route:**
  - `files` sends changed files under `os/config` over the channel into a lasting overlay of the guest's system folders (`ostree admin unlock --hotfix`). Then reboot and test.
  - It takes seconds instead of a build.
  - Its results are marked `quick`. A review cites only full-route or hosted evidence, because `os/build.sh` never ran over those files.
- ***Assumptions,* each proven by step 7 or 8, or the step stops:**
  - the rootless build gives the same files and modes as CI's;
  - `bootc install to-disk` works in the builder with no network;
  - the hotfix overlay works on this image.
- **Fallback for the disk:** the pinned image builder (`os/manifest/base.json`, `builder`, as `check-build.sh` runs it) inside the same builder VM.
- **Not chosen:** downloading CI's disk. `prepare-disk.py` says the disk is never uploaded, and an artifact of this public repo would make a private image public. This stays out; it is not an owner question.

**How a test reaches the desktop without his password.** greetd's `initial_session` starts `/usr/bin/aresos-session` as `ares` with no password (`os/config/etc/greetd/config.toml`). The agent is a root unit in the guest and acts as `ares` through `runuser`.

## 5. Tier 3: the real laptop

**Can test, with the owner:** the lid, brightness keys, power key, battery and AC, Wi-Fi and Bluetooth state, touchpad, the external screen, the NVIDIA card, the real game with his account.

**Cannot:**
- Alone, anything that needs hands or eyes.
- Sleep. The image refuses every sleep request today (`power-events.py`), so there is nothing to test until a package changes that.

**How Claude reads.** All as `ares`, and none through his Wayland socket or session bus.

| What | Read from | What is kept |
|---|---|---|
| Lid, lid policy, inhibitors | logind on the system bus: `busctl get-property`, `systemd-inhibit --list`, as `power-events.py` does in the VM | `LidClosed`; the three policy words; whether AresOS holds a lid block |
| Brightness | `/sys/class/backlight/*/brightness` (`STATE.md`: device `nvidia_wmi_ec_backlight`, 0 to 800) | Numbers |
| Battery, AC | `/sys/class/power_supply/*`: type, online, capacity, status | Numbers and fixed words |
| Screens | `/sys/class/drm/*/status`, `enabled`, `modes` | Connector kind, yes or no, mode list |
| Wi-Fi, Bluetooth | `/sys/class/rfkill/*`; a network device's `operstate`; `/sys/class/bluetooth` | Radio blocked or not; link up or not; adapter present |
| Touchpad | `/proc/bus/input/devices` | Present or not |
| Session alive | `/proc`: labwc's and the game's Java | PID and start time |
| Journal | `journalctl` for logind's unit, from a cursor, matched against fixed lid patterns | The matched kind and its time |
| Sleep | `systemctl show` for the fixed sleep targets and services in `os/tests/power-events.py` (`sleep_state`) | `ActiveState` and `ActiveEnterTimestampMonotonic` |
| Supervisor | `/usr/libexec/aresos-desktop status` | `state`, `ready`, `latched`, `stopping`, `lid_block`, `jvm_pid` |
| NVIDIA card | The PCI device's `power/runtime_status` | One word |

**The evidence boundary**
- The recorder captures stdout and stderr in memory. It keeps only the third column, after checking types and fixed vocabularies. Raw output never reaches a file, the agent's output or the checkout.
- `status` also returns the names of open app windows and of leftover world folders (`os/config/usr/libexec/aresos-desktop`, `status`). The recorder drops everything but the six fields.
- Never read: network names, paired device names, serial numbers, `edid`. `nmcli` is not used, because it prints network names.
- If `ares` cannot read the journal, those lines are `unverified`. No privilege is added to fix that.
- Missing, unreadable or malformed readings give a fixed `unverified` reason. The reason includes no text from the source.
- Approved real-screen captures and the owner's free-text observations stay outside the automated evidence bundle.
- The bench never runs `nvidia-smi`. *Assumption:* a query wakes a sleeping card. `STATE.md` (package 47) records only that test runs once cycled the card's power dozens of times.

**How Claude acts.** It does not.
- The recorder has no `exec` and no input verb. Its command list is fixed, word for word. A test fails on any other command.
- **Never, and no OK lifts it:**
  - `rpm-ostree`, `bootc`, `ostree` or the owner tools;
  - any input into his session;
  - the input portal's allow-list or sharing switch;
  - `aresos-level`;
  - any supervisor command but `status`.
- **With his direct OK for one named step,** Claude may run that one step: one capture of his screen, or one labwc reload (brief 334's hard limits). A picture of his screen stays outside the repo (`briefs/29-linux-dev-rig.md`).
- A go is his own word in the session, never another session's message (`docs/design/CONTROL.md`, rule 4.8).

**Consent, recorded apart from the code.**
- He gave a standing yes to the read list after each update (T501).
- He gave about ten minutes of his hands per release, in the release's "try this" (T502).
- Step 10 builds and tests the recorder on fake inputs only. Its first real use is the lead's step at R29's laptop checks.

**Who checks what**

| Thing | The recorder reads | Only the owner can say |
|---|---|---|
| Lid | `LidClosed`, logind's lid records, sleep-unit state and timestamps | The panel came back and sound kept playing |
| Brightness keys | The value before and after | The screen changed; the plate showed |
| Battery, AC | Online, capacity, status | He pulled and plugged the cable |
| Wi-Fi | Radio blocked or not, link up or not | Pages load |
| Bluetooth | Adapter present, blocked or not | The headset connects and plays |
| Touchpad | Device present | The pointer moves; gestures work |
| External screen | Connected, enabled, modes | The picture is there and in the right place |
| NVIDIA card | Runtime status | The game is smooth |

**Reuse and missing.** Use the read-only sleep-unit check in `os/tests/power-events.py` (`sleep_state`). Missing: the recorder and a checklist per release that says who does what.

**Cost.** His time, about ten minutes per release.

**Worked example: lid close and reopen with the game running**

Expected today, from code: logind's policy is `ignore` for all three lid cases (`power-events.py`). So "pass" means nothing happens to the session.

1. He has updated and restarted (his own step, `CLAUDE.md`). He stands in his home and says go.
2. `bench laptop probe` records:
   - the three policy words; any word but `ignore` stops the test;
   - `status`: ready, not latched, not stopping; otherwise the result is `unverified`;
   - both PIDs with their start times;
   - the state and activation time of each sleep unit;
   - `LidClosed=false`;
   - AC or battery.
3. `bench laptop watch --seconds 90` starts. Claude asks him to close the lid, count to twenty and open it.
4. Pass when all hold:
   - the journal has logind's lid-closed and lid-opened records;
   - `LidClosed` went true and back;
   - the sleep units remain inactive and their activation times stay unchanged;
   - both PIDs and start times are unchanged;
   - `status` is still ready and not latched.
   
   A reading that is missing makes the result `unverified`.
5. Only the owner can say whether the panel came back and the sound kept playing. Claude asks both and records the answers outside the automated evidence bundle.
6. What the VM already shows:
   - `power-events.py` sends close and open on a virtual lid and checks that the session's processes and the sleep units did not change. That session has no game.
   - `guardian.py`'s `lid` closes the lid once during a save and holds it closed.
   - No VM pass today closes and reopens the lid with a game running. The bench can add one with the stand-in (step 5).
   - The laptop adds the real switch, panel and controller.

## 6. How Claude drives the bench

```
bench test   <module>
bench desk   up [--files os/config] | step <json> | down
bench vm     run <script> --hosted  | build | up [--quick] | step <json> | down
bench laptop probe | watch --seconds N
bench status | clean
```

- **Steps:** `shot`, `tree`, `click`, `keys`, `type`, `act`, `wait`, `expect`, `reboot`, `power-key`, `net`, `files`, `switch`. A script names its network level and lists steps, shaped like `CHROME_STEPS` (`control_vm.py`).
- **Output:** one JSON line per step, for example `{"n":4,"kind":"shot","ok":true,"file":"004.png"}`.
- **Evidence:** `.work/bench/<run>/` holds numbered pictures, trees, logs and a `results.txt` of PASS and FAIL lines. `.work/` is ignored by git (`.gitignore`).
- **Exit codes:** 0 pass, 1 fail, 2 unusable (`driver.py`), 75 not now (`env.sh`).
- **Code:** `os/ci/bench/` (section 3, "Release protection").

**Network: a per-test option, off by default**

The owner asked for this with T499. A test names one of three levels.

| Level | What the test gets | How a rootless container does it |
|---|---|---|
| `none` (default) | Nothing but loopback | `--network=none`: a network namespace of its own that holds only `lo` (`run.sh`; `in-container.sh`, `only_loopback`). The VM has no NIC. |
| `fake` | Made-up servers that can be up, down, slow or wrong | Still `--network=none`, so nothing can leave. See "Level `fake`" below. |
| `internet` (level b) | Real internet, outbound only | Hosted only until step 4 verifies the laptop egress policy. |

**Level `fake`**
- **Desk:** stub servers listen on the container's own loopback. Names point there through the container's `/etc/hosts`. A per-run CA signs their certificates. `net down` stops the stubs.
- **VM:** QEMU's user-mode NIC, inside the network-less QEMU container.
  - The guest then reaches exactly one place: that container's loopback, as 10.0.2.2.
  - `control_vm.py` reaches its fixture servers the same way, and Control's layer writes their names into the guest's `/etc/hosts` (`os/ci/control/Containerfile`).
  - `net down` pulls the virtual cable (QMP `set_link`), so the guest's own network service sees it go.

**Level `internet`**
- **Hosted only until step 4 passes.** Real internet stays off on the laptop until the egress policy is verified. This covers tests, image fetches and build steps. A failed or missing check keeps them hosted.
- **Fail closed.** The policy blocks the laptop's own addresses and routes into the home network, including routes to public addresses. It also blocks the home's public address when the router reflects it back inside. The run stays offline if the policy cannot be applied or those destinations cannot be accounted for. No port is published and the relay exposes no host loopback or gateway mapping.
- **Verify every entry path.** Confirm the controlled endpoints are listening before probing them. Show that blocked destinations are unreachable and an allowed public destination works. Check the desk startup and step loop, every `podman exec` path, the VM and the image fetch and build paths. Use the same guarded entry paths when the later steps add their real workloads. Every `podman exec` uses the verified unprivileged user without `CAP_NET_ADMIN`. The test user cannot change the policy.
- **Start clean.** Use a fresh app profile and a clean credential store. Set clean proxy and DNS settings for each run. Chrome always gets a fresh profile. Network filtering does not protect credentials left in a profile.

**Rules for both levels**
- **Accounts:** synthetic only.
  - No file, variable or token of his is in the container; the same checks as at level `none` run.
  - Scripts live in the public repo, so no script can hold a secret.
  - A made-up account's password is generated per run.
  - A test that needs one of his logins is refused. It belongs to tier 3, with him.
- **Runners:**
  - `none` and `fake` mean the same there: the driver, the stubs and QEMU start in a network namespace with only loopback.
  - `internet` uses the runner's own network, as today's passes do (`vm.py`, `-nic user`). No home network sits behind a runner.
- Results record the level. `internet` results are marked: the outside world can change between runs.
- ***Assumptions:*** which rootless relay is available and how to enforce the policy on every path. Step 4 verifies both before enabling the laptop route for real internet.

**Read-only towards everything that is not disposable**
- No step takes a socket path, display name, PID, device or disk path. A target is only what this bench run made.
- Every child gets an environment built from an allow-list, never an inherited one (`driver.py`, `ENV`).
- `bench laptop` holds a fixed list of read commands (section 5).
- The bench is not an MCP server and never opens the control service's sockets (`CONTROL.md`, section 2).
- Nothing the bench drives is his. So no asking action of the control layer is involved, and no second path into his apps exists (`CONTROL.md`, sections 2 and 3).
- Chrome in the desk or the VM starts with a fresh profile made for the run.
- Text from screens, trees, pages and logs comes back in fields marked `untrusted` (`CONTROL.md`, rule 4.8). It never changes the task.
- Pictures of disposable desktops may be committed under `reviews/NN-slug/`. A picture of his screen never is.

## 7. Build plan

Each step is one builder with a fresh review. Step 10 is independent and can start with step 1.

| # | Step | Rough size | Acceptance |
|---|---|---|---|
| 1 | **Hosted pass (first value):** bench layer, minimal agent, bench disk config, script runner, `check_build=bench` with `bench_script`, evidence and release protection | About 600 lines plus workflow lines | Boot with no NIC. Verify the active auto-login session and helper health. Take a QMP shot. Require a new boot ID and helper health again after reboot. The broken-helper dispatch fails at health. Reject oversize evidence and token-shaped strings before upload. Check release protection as listed below. `run.json` matches the head. |
| 2 | **Laptop safety pieces** (hosted tests): the capped tree, shared lock, watcher, disk budget and cleanup | About 500 lines | Test the gates with fake memory, pressure and free space. Low memory, battery and a stand-in for Lunar give exit 75. Refuse a disk phase before it writes when its bounded peak cannot fit. Cleanup refuses an active store and succeeds after an interruption. The brief settles the store location under `AGENTS.md`. |
| 3 | **Private network levels** | Part of the network work | `none` has only loopback on the container and no guest NIC. At level `fake`, reach a stub by name and observe `net down`. No traffic leaves. |
| 4 | **Real-internet egress gate** | Steps 3 and 4 together are about 500 lines | Build the guarded entry paths and exercise them with test fixtures before adding the real workloads. Section 6's controlled endpoint checks pass from each path, including fetch and build. A missing policy fails closed. Verify the unprivileged user on every `podman exec` and the clean settings. Real-internet work stays hosted until this gate passes. |
| 5 | **Stand-ins:** the Java stand-in desktop, a home fixture | About 500 lines | Hosted, twice, the stand-in opens KWrite in a real app scope and gets `app_state`. The QMP shot shows KWrite. Repeat after reboot with a new boot ID and check the helper journal. |
| 6 | **Seeing and the laptop VM memory gate** | About 400 lines for seeing, plus the measured checks | Run the full example in section 3 on hosted runners, including `tree`. Button boxes match the shot. An empty tree gives `UNUSABLE`. `yz-/!ü` arrives as typed (`owner_vm.py`). Verify 1920×1080. Probe KVM inside the real rootless container and run section 3's memory checks on the capped launch path with a stand-in game and an offline VM fixture. Keep the laptop VM route disabled until the checks pass. |
| 7 | **Laptop disk:** the local build and builder VM | About 600 lines | Steps 4 and 6 pass before the first local image build. Measure peak memory and disk under the lock, gate, watcher and budget. Compare the image's file list and modes with the hosted build of the same commit. Make the first disk offline with no host `sudo`. List what is left over 500 MB (`AGENTS.md`, rule 7). |
| 8 | **Laptop VM, live:** `up`, `step`, `down`, the quick route, `switch`, the idle limit | About 600 lines | Step 1's script and the full worked example pass locally. With networking off, probes to the laptop, gateway and a public address fail. The VM stops after `down`, a killed CLI, the idle limit and the watcher. The test disk is deleted when the test ends. An offline `switch` gives a new boot ID, the expected revision and a working channel. Only the newest image and base disk remain. |
| 9 | **The desk:** two-phase start, launcher, systemd stand-ins, step loop | About 600 lines | Every isolation check passes. A planted `WAYLAND_DISPLAY`, an extra mount, or UID 0 after the drop gives `UNUSABLE`. Reject malformed evidence before any returned files are written. Section 2's example passes. The container stops after `down`, a kill or the timeout. The memory cap holds. |
| 10 | **Laptop recorder and checklist** | About 350 lines | Use fake inputs for the fixed read list, sleep-unit checks and evidence projection. Test valid readings and errors, including malformed output on both streams. Window and world names stay out. Missing or unreadable sources give a fixed `unverified` reason. |

### Carried into the step briefs

**Step 1**
- Make the pass hosted-only. Boot explicitly with no NIC and verify that the auto-login session is active.
- Check health with an authenticated, read-only request to the actual session helper. Keep launch credentials inside the guest. After reboot, require a new boot ID and a fresh successful health check.
- The negative commit preserves helper import and `--list`, which `os/ci/image-checks.sh` runs before the VM boots. The deliberate failure appears at the VM health check.
- Make bench dispatch exclusive with release, rehearsal and published-image switch inputs. Give the bench image a distinct tag. Scan the plain image's raw layers with a planted-file case that must fail. Limit the bench-file rule to image and build inputs so the runner can take scripts under `reviews/`.
- Gate upload on a bounded set of regular evidence files. Keep raw guest output out of retained job logs.

**Step 2**
- Settle the store location against the worktree rules in `AGENTS.md`. List all writes and enforced peaks by phase. Specify the shared lock outside the store and prove refusal while active and cleanup after interruption.

**Step 4**
- Name the controlled listening endpoints and the entry paths each one checks. Include the laptop's addresses, home routes and the home's public address reflected by the router. Include fetches and build steps. Verify the user, capabilities and clean settings from section 6.

**Step 6**
- Check the shared lock across all four entry points and refuse a concurrent build. Verify that Podman, its helpers and the VM stay in the capped tree. Kill the watcher and verify the whole tree stops.
- Measure the early-stop threshold, swap growth and game responsiveness with a fixed-size VM beside a growing stand-in game. Report detection and termination delays. Include the worked example's `tree` assertion here.

**Step 7**
- Specify the source for offline install and switch from the read-only OCI export. Name the writable import and scratch locations and their limits. Specify how the builder's inputs arrive before its network is disabled.

**Step 9**
- Keep the native list empty. Test that changed imports run only in isolation. Test the bounded desk extractor with links, devices, `..`, unexpected paths and oversized files.

**Step 10**
- Use read-only sleep-unit state and activation timestamps as in `os/tests/power-events.py`. Logind supplies the lid events. A missing source gives `unverified`.
- Test successful projection and errors. Capture stdout and stderr in memory. Check types and fixed vocabularies and return a fixed `unverified` reason on malformed output. Keep approved real-screen captures and the owner's free-text observations outside the automated evidence bundle.

## 8. Owner decides

**Answered (2026-11-22)**

| Board | Question | His answer | Built in as |
|---|---|---|---|
| T499 | Hidden desk containers on the laptop? | Yes. "For things requiring network, doesn't it make sense to include functions like that?" | Sections 2 and 6. Network is off by default. Real internet stays hosted until step 4 passes. |
| T500 | A test VM on the laptop? | Yes, "if they fit and work", with the KVM step and the disk space. The 40 GB is a cap, not a reservation. | Sections 3 and 4. Steps 6 to 8 cover the measured checks and laptop VM. |
| T501 | Read-only hardware readings after each update? | Yes | Section 5, inside its evidence boundary. |
| T502 | About ten minutes of his hands per release, in the release's "try this"? | Yes | Section 5. |

- **What the watcher does.** It stops the VM early when memory runs low. Step 6's report gives the measured detection and termination delays. A sudden spike can still beat it.
- **What the bench keeps.** Normal use stays well under 40 GB. Only the newest image is kept. Each test's disk is deleted when the test ends. `bench clean` removes all bench data.
- **The KVM step** (inside T500). If the owner's account lacks KVM access, the owner can grant it. The bench never calls `sudo`. Step 6 writes the exact command. The lead shows it to the owner and waits for approval. The owner types the password (`CLAUDE.md`, hard rule 1). Without access the hosted route remains.

**No longer his questions**
- CI uploading the bench disk: it stays out (section 4).
- Hosted minutes: free on standard runners. The dispatch cap is the lead's.
- Guest size, caps and floors: technical, in section 3.

**Still open**
1. **If virtualisation is switched off in the firmware.** Turning it on is the owner's call (`CLAUDE.md`, "Owner decides"). *Advice:* decide only if step 6's probe finds it. The hosted route and the desk remain available if the owner declines.
2. **Is the home connection unmetered?** A full local build downloads about 6 GB. *Advice:* if yes, nothing changes. If not, the bench keeps the build store longer and asks before each full build.

Anything he would see in tier 3 still asks each time. That is a standing rule, not a question.

## 9. Known limits

Low-harm edge cases live here, by the brief's safety bar (decision 24).

**What the bench cannot show**
- No real Minecraft, Prism sign-in or NVIDIA rendering in tiers 1 and 2. A stand-in plays the game. The mod's behaviour stays with its own tests.
- No backlight, battery, real lid, Wi-Fi, Bluetooth, touchpad or firmware in the VM. A virtual lid is not the real switch.
- The laptop home's `eDP` choice is tested only in tier 3. The bench launcher overrides it.
- The laptop home, the covers and the game have no accessibility tree. Claude works from pictures, the scene model and the helper's protocol.
- The desk has no systemd. App scopes are tested only in tier 2.
- The stand-in desktop maps no window, so focus-return checks are out of scope until a step adds one.
- At level `fake` the desk shows server states only. "Wi-Fi off" is the VM's.

**Seeing**
- AT-SPI on the real GTK and KDE clients still needs proof in each target: finding the accessibility bus, and mapping reported boxes onto the screenshot.
- KWrite's tree needs the accessibility bus switched on. An empty tree is a setup fault.
- 1920×1080 in the VM is untested in this repo.
- `control_vm.py`'s glyph match fits the KDE polkit title at 1280×800 only.
- A screen text or a web page could mislead Claude's reading. The harm ends at the disposable desktop.

**The desk**
- `bwrap` may not start inside the rootless container. Icons then show without pictures (`aresos-shell`, the icon cache's start; `aresos-laptop-home`, `run_sandboxed`).
- The image's `rc.xml` keeps live bindings there. `W-C-Escape` and the brightness keys run commands that reach nothing of his but can fail noisily.
- A desk test of the battery reading itself must use a fake `/sys` folder. The launcher passes a fixed reading so that pictures never show the laptop's.
- Headless labwc aborts when an output with a custom mode is switched off and on while a client holds the output manager (`reviews/316-input-portal/KNOWN-LIMITS.md`). The desk never switches an output off.

**The laptop VM**
- A memory pressure test covers the load and timing it exercised. A sudden allocation or a stalled watcher can still beat the shutdown. The timing shown to the owner comes from step 6's measurements.
- The bench creates and stops its own named scopes in `ares`'s user manager, as `env.sh` does. That manager also runs his session's units. The bench's environment comes from an allow-list, so his session's bus address is never in it.
- Step 6 probes whether the rootless container can open KVM.
- SELinux may refuse `/dev/kvm` inside the container (section 10).
- The laptop's QEMU is not the runners' pinned 8.2.2 (`os/ci/toolchain.json`).
- The laptop's disk is laid out by `bootc install`. CI uses the image builder. The rootless build may differ in file ownership or labels. Step 7 compares them.
- The quick route is not a new image.

**Hosted**
- The hosted route is not live: one round per build.
- Its times are Control's, not the bench's own.

**Network**
- If level `internet` is later enabled on the laptop, public destinations see the home connection's public address. The configured resolver sees test DNS queries.
- A clean profile protects local stored credentials. Sign-in tests still use synthetic accounts and fixtures.
- Results there are not repeatable.

**Tier 3**
- `aresos-desktop status` opens his live supervisor's socket. It is a read by code, but it is a connection into his running session.
- Sanitized readings show observable state. A link can be up without connectivity. The same PIDs can remain while the panel or audio fails to recover. Those observations belong to the owner.
- Reading a connector's status on the NVIDIA card might wake it (*assumption*, not checked).

**What I relied on without reading the code**
- Brief 321 for the second screen, `Virtual-1` and the session-bus rule. Its code is not in this checkout.
- Not read for this revision: `docs/design/HUB.md`, `docs/control/`, `os/ci/install-tools.sh`, and most of `aresos-desktop`.

## 10. For the lead

- **Write the rules down.** Brief 334's laptop list is not a rule on `main` (section 1). Put the two new permissions, with their board numbers, and the bench's own rule into `AGENTS.md`, "Environment", so later builders do not have to work it out again.
- **Two rigs already inject input outside a container.**
  - `mod/dev/client-test.sh --session` moves virtual pointers in a private headless labwc. It removes named variables from an inherited environment (`ISOLATE`).
  - `os/tests/laptop_home_headless.py` drives virtual input into a private labwc inside `bwrap`, over a read-only host root with its own network namespace (`Headless.__enter__`).
  - The brief's hard limit (a container or a VM only) is stricter. The bench leaves both alone. Say whether they stay.
- **The store location.** Step 2's brief settles where the store can live under the worktree rules in `AGENTS.md`. It does so before any store writes.
- **`linux-aresos`'s files.** Step 1 touches `check-build.sh` and `os-image.yml`: the mode, the input, the evidence gate, the `image` job's condition, the release-isolation lines. Each is its own commit, listed for `linux-aresos`, with a `rebind.py pending` note.
- **SELinux.** If it denies KVM access inside the container, turning off the label for that container lowers its confinement. Step 6 stops and reports the denial.
- **Made-up accounts on real services** at level `internet` may break a service's terms. That is a per-case call of yours.
- **Length.** This revision is well over the brief's 3,500 words, because both reviews asked for detail. Say what to move out if the limit binds.
- **A correction.** The first draft said `briefs/334-test-bench.md` ends with two stray lines. It does not; the bullet is gone.
