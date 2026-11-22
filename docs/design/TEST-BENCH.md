# Test bench: how Claude tests AresOS changes itself

**Status:** design note for brief 334, step 1 (2026-11-22). Nothing here is built. A file name after a claim is where I read it. *Assumption* marks what I did not check in code.

## 1. Summary

| Tier | What Claude can test | Where | What the owner must allow |
|---|---|---|---|
| 1. Hidden desk | Session programs that need no restart: the app helper, the laptop home, the indicator plate, window rules, key bindings, dialogs | The laptop, in a throwaway container with its own invisible desktop | Containers on the laptop (rootless, no network, nothing of his mounted) |
| 2. Bench VM | What needs a new image or a restart: boot, auto-login, units, the session after a reboot, shutdown | First on GitHub's runners, in batches. Later also live on the laptop | Nothing for the runners. For the laptop: a VM, a container, `/dev/kvm`, about 5 GiB of memory while it runs, disk space |
| 3. Real laptop | Hardware: GPU, brightness, lid, battery, Wi-Fi, Bluetooth, touchpad, screens | The laptop, after his own update and restart | A standing yes to read-only probes; his hands for lid, keys and cables; a yes each time for anything he would see |

- The bench never drives his real session. Tiers 1 and 2 are disposable. Tier 3 only reads, unless he says go.
- **First value:** the hosted bench pass (build step 1). It needs no rule lifted.

**Which rule each tier needs lifted**

| Tier | Rule (as brief 334 lists the laptop rules) | Hosted route instead |
|---|---|---|
| 1 | "no container" | None with a live loop. The same steps can run inside the tier 2 VM. |
| 2 on runners | None. A thrown-away CI image needs no OK (`CLAUDE.md`, "Owner decides"). | This is the hosted route. |
| 2 on the laptop | "no VM", "no container"; KVM access; `sudo` once only if `ares` cannot open `/dev/kvm` | Yes: the hosted pass. |
| 3 | None for reading. Each visible or changing step needs his go. | None: it is the hardware. |

## 2. Tier 1: the hidden desk

**What it is.** A rootless podman container started by `ares`. It holds a private session bus, a headless labwc and a throwaway user. The checkout's changed files go in as a tar stream and are installed at their image paths, as package 316's harness installs its backend (`os/input-portal/harness/in-container.sh`).

"Test live" stays narrow: the changed program's own test module (`python3 -m unittest discover -s os/tests -p 'test_<name>.py'`, `AGENTS.md`) and read-only looks at the running system. Nothing is installed into his session.

**Can test:** `aresos-shell` flows (list, open, focus, views), the laptop home, the indicator plate, `rc.xml` bindings and window rules, covers, dialogs.

**Cannot test:**
- The real game. The mod's rig stays `mod/dev/client-test.sh`.
- GPU, sound, greetd, logind, system units, anything across a restart.

**How Claude sees, acts and reads**

| Need | How | Read in |
|---|---|---|
| Screenshot | `grim` on the private compositor | `os/ci/overlay/checks.py`, `cover_start`, uses it the same way in the VM |
| Buttons and text | The accessibility tree (AT-SPI) on the private bus: role, name, box | New. *Assumption:* GTK and Qt expose it under headless labwc. |
| The laptop home | It draws with Cairo only, so it has no tree. Positions come from its layout rules and the helper's `get_home`. | `docs/design/LAPTOP-HOME.md`, sections 3 to 5 |
| Pointer and keys | `wl-harness input pointer` or `keyboard`: `abs`, `rel`, `btn`, `axis`, `key` | `os/input-portal/harness/clients/wl-harness.c`, header; `driver.py`, `VInput` |
| State | A second view connection to the helper (`list_apps`, `get_home`, `apps_running`, `app_state`); logs; `wlr-randr --json` | `os/config/usr/libexec/aresos-shell`, docstring; `driver.py`, `randr_outputs` |

**Reuse**

| What | From |
|---|---|
| Container shape, tar in and out, time limit, cleanup | `os/input-portal/harness/run.sh`, `run_tests` |
| Isolation checks before anything starts | `harness/in-container.sh` (`must`, `no_host_mount`, `no_sockets`) |
| Private bus, headless labwc, built environment, PASS/FAIL lines, exit 0/1/2 | `harness/driver.py` (`start_bus`, `start_labwc`, `ENV`, `check`) |
| Pinned Fedora with package 311's labwc RPM | `harness/Containerfile` |
| The image's `rc.xml` in a private labwc | `mod/dev/client-test.sh --session` copies it |

**Missing**
- A desk image with GTK 4, gtk4-layer-shell, the fonts, foot, grim and AT-SPI.
- A long-lived container with a step loop.
- A stand-in desktop that speaks `aresos-shell/1.2` (hello with instance and nonce, `publish_home`, `world_ready`, heartbeat) and maps a window with app ID `aresos-desktop` (the helper's `DESKTOP_APP_IDS`).
- A launcher with a made-up instance, nonce and view token.
- A text-to-key table.

**Two choices**
- **Desk image:** slim pinned Fedora first, the locally built AresOS image later (build step 7). Slim starts in seconds and needs no 12 GB image store. Its package versions can differ from the image's (Known limits).
- **App scopes:** a real systemd user manager inside the container. The helper starts every app in a systemd user scope (its docstring), so a stand-in would test a fake.
  - 316's `run.sh` avoids cgroups (`--cgroups=disabled`), so build step 4 must first prove that delegation works from an agent's shell.
  - If it does not, the desk gets stand-ins for `systemd-run` and `systemctl` inside the container image only, and scope behaviour moves to tier 2.

**How the limits are kept**
- **Process and user:** `podman run` by `ares`, rootless. Inside, everything runs as a non-root UID that maps to a sub-UID, not to `ares`. *Assumption:* `ares` has a sub-UID range; 316's harness ran as the container's root.
- **No way in or out:** `--network=none`, no `-v`, no `--device`, no `--env` (`run.sh`). Steps travel over `podman exec -i`. Evidence comes out as a tar, unpacked only if it holds plain files and folders (`run.sh`).
- **Sockets:** only the container's own bus and `wayland-0`.
- **Checked before anything starts** (`in-container.sh`):
  - no `WAYLAND_DISPLAY`, `DISPLAY`, `DBUS_SESSION_BUS_ADDRESS` or `XDG_RUNTIME_DIR`;
  - no `/dev/input`, `/dev/uinput`, `/dev/dri`, `/run/user` or home;
  - no socket anywhere, no host mount.
  
  A failed check ends the run as `UNUSABLE`. The bench reuses these unchanged and adds: not UID 0, no `/dev/kvm`.
- **The real helper is out of reach:** his runtime folder is not in the container.
- **It ends by itself:** a time limit and a trap remove that one container (`run.sh`).

**Cost.** On the laptop.
- Memory: about 0.5 to 1 GiB (*assumption*; the laptop home alone measured 61 MiB in such a compositor, `LAPTOP-HOME.md` section 4).
- Disk: image 1 to 2 GB (*assumption*).
- Start: seconds. Refused under 2 GiB available.

**Worked example: the open-app flow against a changed `aresos-shell`**
1. Claude edits `os/config/usr/libexec/aresos-shell` in its worktree and runs that helper's test module.
2. `bench desk up --files os/config`. The isolation lines pass; labwc starts headless at 1920×1080; the changed helper lands at `/usr/libexec/aresos-shell` in the container.
3. `bench desk act home`. The helper starts with made-up credentials. The stand-in desktop publishes a three-app home. The laptop home connects as a view.
4. `shot` gives `001.png`. Claude reads Notepad's place from `get_home` and works out its house from section 3's rule.
5. `click` on the house: a virtual pointer move and button 272.
6. `wait app_state notepad` on the watching view. `apps_running` now lists `notepad`.
7. `shot`: KWrite is open and the house is lit. `tree` names KWrite's buttons.
8. `keys alt+F4` (`rc.xml` binds Close). `apps_running` empties.
9. `bench desk down`. The evidence lands in `.work/bench/<run>/` and the container is gone.

A helper that raises fails step 6, with the helper's log in the evidence.

## 3. Tier 2: the bench VM

Two routes run the same script.

- **Hosted (first).** A new mode `check_build=bench` beside `control` (`os/ci/check-build.sh`). The job builds the image from the ref, adds a bench layer, makes a disk, boots it and plays the script. It is a batch: one round per dispatch.
- **Laptop (later, live).** The same guest in QEMU with KVM, started by `ares` inside a rootless container that holds QEMU and OVMF, so nothing is installed system-wide.

**Can test:** boot to the session, units, auto-login, real app scopes, the supervisor's states, shutdown and the guardian, a restart, an update done inside the guest.

**Cannot test:**
- The real game or Prism sign-in. A fresh VM has no account and stays in `SETUP` (`checks.py`, `desktop_session`).
- Hardware.
- The real installer route. That stays with the two-disk rehearsal (`os/ci/two_disk_vm.py`, `owner_vm.py`) and under the install hold (`docs/INSTALL-STATUS.md`).

**How Claude sees, acts and reads**

| Need | How | Read in |
|---|---|---|
| Screenshot | QMP `screendump` to PNG | `os/ci/vm.py`, `screenshot` |
| Shot inside the session | `grim` as `ares` | `checks.py`, `cover_start` |
| Buttons and text | AT-SPI dump as `ares`, on the bus address read from labwc's environment | New. The bus rule is from `briefs/321-deskflow-image.md` only. |
| Dialogs, pre-desktop screens | Glyph match; OCR | `os/ci/control/control_vm.py`, `agent_title`; the rehearsal job installs `tesseract-ocr` (`os-image.yml`) |
| Keys | QMP `send-key`; German layout through `physical_keys` | `vm.py`, `keys`; `os/ci/keyboard_vm.py` |
| Pointer | QMP `input-send-event` on the USB tablet | `control_vm.py`, `Guest.click` |
| Power key, reboot | `system_powerdown`; power off, then boot the same overlay | `vm.py`; `control_vm.py`, the `reboot` step |
| Guest state | Framed JSON over the virtio port `org.aresos.ci`; commands as `ares` through `runuser … env -i` | `os/ci/channel.py`; `checks.py`, `AS_ARES` |
| Logs | The serial log; the stopped guest's journal | `vm.py` |

**Reuse**

| What | From |
|---|---|
| Image from the ref, disk, boot | `os/ci/check-build.sh`, `os/ci/prepare-disk.py` |
| A test layer with its own actions and VM pass | `os/ci/control/Containerfile`; `checks.py`, `layer_actions` |
| Guest object and step list | `control_vm.py` (`Guest`, `CHROME_STEPS`) |
| Stand-in game through the real wrapper, seeded home, virtual lid | `os/ci/overlay/guardian.py` (`arm`, `seed_world`, `lid`), `GuardianGame.java` |
| Password windows | `control_vm.py`, `type_password`; `os/ci/tools_local.py` |
| Terminal sessions as `ares` | `os/ci/control/sessions.py` (tmux through `runuser`) |
| Pinned QEMU and OVMF on runners | `os/ci/install-tools.sh`, `os/ci/toolchain.json` |

**Missing**
- The bench layer: built from the plain image, with `channel.py`, one guest agent and its unit. It leaves out the CI pass's fixtures (US keymap, debug drop-ins, shadow programs: `os/ci/overlay/Containerfile`).
- The agent's actions: `exec` as `ares`, `shot`, `tree`, `journal`, `status`.
- The script runner.
- `check_build=bench` in `check-build.sh` and `os-image.yml`. Both are `linux-aresos`'s files, and the workflow is a bound file (`rebind.py pending`, as 18c did).
- A check that no release carries the bench layer. The release jobs already test that `/usr/libexec/aresos-ci` is absent (`os-image.yml`).

**How the limits are kept**
- **Network (laptop):** QEMU runs in a `--network=none` container with `/dev/kvm` as its only device. The guest has no route to the laptop, the LAN or the internet. On runners `vm.py` uses `-nic user`, where the guest reaches the host's loopback (`control_vm.py`). That must not exist on the laptop.
- **Disks:** only files in the bench's own podman volume. No step takes a disk path. The driver asserts a regular file under its work folder, as `two_disk_vm.py`'s `disk_args` does. No `/dev/nvme*` can be named.
- **Credentials:** none go in.
  - `ares` has a locked password in the image (`os/tests/guest.sh`).
  - Password windows get a per-run made-up password (`control_vm.py`, `password_hash`).
  - The hosted job has only its read-only job token (`os-image.yml`, `check-build`). `os/ci/registry_auth.py`'s `create` refuses without it and has no owner-token fallback.
- **Host system:** no owner tools, `rpm-ostree` or `bootc` on the host. A `bootc` call runs only inside the guest.
- **Memory (laptop):**
  - One VM, held by a lock beside the client-test lock (`mod/dev/env.sh`).
  - Guest 4 GiB. Start only with 7 GiB available, checked at start and again right before QEMU, as `aresos_check_room` is called more than once in `client-test.sh`. Otherwise exit 75, with no `--force`.
  - QEMU sits in a systemd user scope with `MemoryMax=5G` and `MemorySwapMax=0` (the property `checks.py`'s `pressure_command` uses), so the VM dies first, never his game.
  - Two CPUs while his game runs (found by reading `/proc`, as `env.sh` does).
  - No KVM: refuse. Software emulation would burn his CPU.
  - Thirty minutes without a step stops the VM.

**Cost**

| | Hosted | Laptop |
|---|---|---|
| Memory | The runner's; guest `-m 6144` (`vm.py`) | 4 GiB guest, about 1 GiB QEMU (*assumption*) |
| Disk | The runner's; evidence under 180 MB (`os-image.yml`) | Root of 28 GiB virtual (`prepare-disk.py`); 6 to 10 GB real per disk (*assumption*); cap 40 GB |
| Time | 26 to 68 minutes a round; boot to channel 28 to 44 s (`reviews/18c-image-test/REPORT.md`, the two control runs) | Boot under a minute (*assumption*); steps in seconds |

**Worked example: the same change after a new image boots**
1. Claude pushes the branch with the changed helper and `reviews/NN-slug/bench/open-app.json`.
2. `bench vm run open-app.json --hosted` dispatches `check_build=bench` and watches with `gh run watch <id> --exit-status --interval 60` (`AGENTS.md`).
3. The job builds the image from that commit, adds the bench layer and boots the disk. greetd logs `ares` in.
4. The script:
   - waits for labwc;
   - `act status` answers `SETUP`;
   - starts the stand-in game through `/usr/libexec/aresos-desktop-java`, which hands it the instance and nonce (`checks.py`, `desktop_jvm`);
   - the stand-in publishes the home and sends `open_app notepad`.
   
   Once package 23c starts the laptop home with its token (`STATE.md`: inert until 23c), the script clicks the house instead.
5. It checks: KWrite in the shot; a real `app-…` scope in `systemctl --user`; `apps_running` lists it.
6. `reboot`. After auto-login the same steps pass again, and `journal` holds no traceback from the helper.
7. Claude fetches the evidence with `gh run download` and reads `results.txt` and the pictures.

## 4. Tier 2, "just like the laptop"

| Part | How close | Gap |
|---|---|---|
| Image | The same `os/Containerfile` at the same commit, plus one agent service | A root-run agent exists; the build is throwaway, not the release |
| Apps | Everything in the image: KWrite, Chrome, foot, Prism | His own programs in his home are absent |
| Settings | `/etc` as shipped. A made-up profile can be laid in: `settings.json`, a seeded home (`guardian.py`, `seed_world`). | None of his files, ever |
| Keyboard | German, typed through `physical_keys` | The table covers what `keyboard_vm.py` lists |
| Screen | `virtio-vga` set to 1920×1080. `control_vm.py` saw 1280×800 by default. | One screen. A second one waits for 321's work (brief only). No panel, no refresh rates. |
| The home | A stand-in game and a seeded world | No Microsoft account, no real Minecraft, no NVIDIA card |
| Hardware | Virtual disk, network and GPU; a uinput lid | Tier 3 |

**Where the VM image comes from**
- **Hosted:** CI builds it from the ref, fresh on every run. `vm.py` demands a fresh overlay.
- **Laptop:** a local rootless build of the image. The disk is made inside a builder VM (`bootc install to-disk` there), so the host needs no root, no registry and no token. Later images reach the guest by `bootc switch` from a read-only share (the share pattern is `os/ci/stock_image.py`'s). *Assumption:* the image builds rootless on the laptop. Build step 7 proves it.
- **Not chosen:** downloading CI's disk. `prepare-disk.py` says the disk is never uploaded. An artifact of this public repo would make a private image downloadable, Chrome included (decision 3 below).

**How a test reaches the desktop without his password.** greetd's `initial_session` starts `/usr/bin/aresos-session` as `ares` with no password (`os/config/etc/greetd/config.toml`). The agent is a root unit in the guest and acts as `ares` through `runuser`. The bench disk is built with no password for any account.

## 5. Tier 3: the real laptop

**Can test, with the owner:** the lid, brightness keys, power key, battery and AC, Wi-Fi and Bluetooth state, touchpad, the external screen, the NVIDIA card, the real game with his account.

**Cannot:**
- Alone, anything that needs hands or eyes.
- Sleep. The image refuses every sleep request today (`os/tests/power-events.py`), so there is nothing to test until a package changes that.

**How Claude reads.** All as `ares`, and none through his Wayland socket or session bus.

| What | Read from |
|---|---|
| Lid, policy, inhibitors | `busctl get-property` on logind (system bus) and `systemd-inhibit --list`, as `power-events.py` and `guardian.py`'s `lid` do in the VM |
| Brightness | `/sys/class/backlight/*/brightness` (`STATE.md`: device `nvidia_wmi_ec_backlight`, 0 to 800) |
| Battery, AC | `/sys/class/power_supply/*` |
| Screens | `/sys/class/drm/*/status` |
| Session alive | `/proc`: labwc's and Java's PIDs |
| Journal | `journalctl` from a cursor (*assumption:* `ares` may read it as a `wheel` member) |
| Supervisor | `/usr/libexec/aresos-desktop status`, the JSON `checks.py` and `guardian.py` read (*assumption:* it changes nothing; I did not read `aresos-desktop`) |
| NVIDIA card | The PCI device's `power/runtime_status`, never `nvidia-smi`: a query wakes the card (`STATE.md`, package 47) |

**How Claude acts.** It does not.
- Never: `wlr-randr`, `grim` or any Wayland client against his compositor; uinput; `aresos-level`; `at`; `rpm-ostree`; `bootc`.
- With his direct OK for one named step, Claude may run that one step. A picture of his screen stays outside the repo (`briefs/29-linux-dev-rig.md`).

**Reuse and missing.** The pass rules come from `os/ci/guardian_host.py`'s `check` (journal order, no sleep record). Missing: a read-only recorder and a checklist per release that says who does what.

**Cost.** His time, about ten minutes per release.

**Worked example: lid close and reopen with the game running**

Expected today, from code: logind ignores the lid in all three cases (`power-events.py`). So "pass" means nothing happens to the session.

1. He has updated and restarted (his own step, `CLAUDE.md`). He stands in his home and says go.
2. `bench laptop probe` records both PIDs, `status`, `LidClosed=false`, the inhibitors, AC or battery.
3. `bench laptop watch --seconds 90` starts. Claude asks him to close the lid, count to twenty and open it.
4. Pass when all hold:
   - the journal has logind's lid-closed and lid-opened lines;
   - `LidClosed` went true and back;
   - no `systemd-sleep` record and no "Suspending" line;
   - both PIDs unchanged;
   - `status` is not latched.
5. Only he can say whether the panel came back and the sound kept playing. Claude asks both and records his words.
6. The VM ran the same pass lines first with a virtual lid (`guardian.py`, `lid`). The laptop adds only the real switch, panel and controller.

## 6. How Claude drives the bench

```
bench desk   up [--files os/config] | step <json> | down
bench vm     run <script> --hosted  | up | step <json> | down
bench laptop probe | watch --seconds N
```

- **Steps:** `shot`, `tree`, `click`, `keys`, `type`, `act`, `wait`, `expect`, `reboot`, `power-key`. A script is a list of them, shaped like `CHROME_STEPS` (`control_vm.py`).
- **Output:** one JSON line per step, for example `{"n":4,"kind":"shot","ok":true,"file":"004.png"}`.
- **Evidence:** `.work/bench/<run>/` holds numbered pictures, trees, logs and a `results.txt` of PASS and FAIL lines.
- **Exit codes:** 0 pass, 1 fail, 2 unusable (`driver.py`), 75 not now (`mod/dev/env.sh`).
- **Code:** `os/bench/`, a new folder, so no bound rehearsal file changes. `linux-aresos` reads the `os/` diff.

**Read-only towards everything that is not disposable**
- No step takes a socket path, display name, PID, device or disk path. A target is only what this bench run made.
- Every child gets a built environment, never an inherited one (`driver.py`, `ENV`; `client-test.sh`, `ISOLATE`).
- `bench laptop` holds a fixed list of read commands. A test fails on any command outside it.
- The bench is not an MCP server and never opens the control service's sockets (`docs/design/CONTROL.md`, section 2).
- In the desk and the VM the service has only made-up accounts, and Chrome a throwaway profile (`os/ci/control/chrome_actions.py`).
- Nothing the bench drives is his, so `control/settings/ask-rules.json` needs no entry and no second path into his apps exists (`CONTROL.md`, section 7).
- Text from screens, trees and logs comes back in fields marked `untrusted` (`CONTROL.md`, rule 4.8; `control/settings/CLAUDE.md`). It never changes the task.
- A go for tier 3 is the owner's own word, never another session's message.
- Pictures of disposable desktops may be committed under `reviews/NN-slug/`. A picture of his screen never is.

## 7. Build plan

Each step is one builder with a fresh review. Steps 1 to 3 and 5 need no owner decision.

| # | Step | Rough size | Acceptance |
|---|---|---|---|
| 1 | **Hosted pass (first value):** bench layer, agent (`exec`, `shot`, `journal`, `status`), script runner, `check_build=bench` | About 500 lines plus workflow lines | A script boots, shoots, reboots and passes. A broken helper fails. Evidence stays under 180 MB. The release check finds no bench file. Parser tests run in the hosted checks. |
| 2 | Stand-ins: the desktop client, a home fixture, the launcher | About 400 lines | Section 3's example is green twice. |
| 3 | Seeing: `tree`, click by name, German typing, glyph and OCR helpers | About 400 lines | KWrite's and a dialog's buttons are listed with boxes. A click by name lands. `yz-/!ü` arrives as typed (`owner_vm.py`'s text). |
| 4 | The desk: image, step loop, 316's checks; the scope spike first | About 600 lines | Every isolation line passes. A planted `WAYLAND_DISPLAY` or mount gives `UNUSABLE`. Section 2's example is green. Nothing runs after `down`, a kill or the time limit. |
| 5 | Laptop recorder and checklist | About 300 lines | Tests on a fake `/sys` and journal pass. The fixed-list test passes. First use at R29's laptop checks. |
| 6 | Laptop VM: QEMU container, memory gate, lock, scope limits | About 500 lines | Refuses under the floor (exit 75) and without KVM. The guest has no route out. The VM is gone after `down`, a kill or the idle limit. |
| 7 | Local image to disk: rootless build, builder VM, `bootc switch` in the guest | About 500 lines | The disk boots to the session with no `sudo` on the host. Only one cached image and disk over 500 MB remain (`AGENTS.md`, rule 7). |

Each brief caps its dispatches, as 321's does (8). Steps 6 and 7 start only if the hosted loop proves too slow.

## 8. Owner decides

1. **Containers on the laptop for the hidden desk?** Rootless, no network, nothing of his mounted, removed after each run. *Advice: yes.* Package 316's harness already ran this way on the laptop (`run.sh`, header).
2. **A VM on the laptop?** One at a time, 4 GiB, only with 7 GiB free; it stops itself and is the first thing killed if memory runs short. *Advice: not yet.* Use the hosted pass first and decide after two packages have used it.
3. **May CI upload the bench disk so the laptop can download it?** It would be a public artifact of a private image for one to three days. *Advice: no.* Build locally (step 7).
4. **Disk space:** up to 40 GB of the SSD for bench images, with a `bench clean`. *Advice: yes, with step 6.*
5. **Hosted minutes:** a bench run takes 26 to 68 runner minutes. *Assumption:* I could not read in code whether these count against the organisation's included minutes (`os/ci/rehearsal-packages.json` names 2,000). *Advice: allow 8 runs per package.*
6. **A standing yes to read-only probes on the real laptop**, section 5's table, after each update? *Advice: yes.* Anything he would see, and any picture of his screen, still asks each time.
7. **His ten minutes per release** for lid, keys and cables, folded into the release's "try this". *Advice: yes.*
8. **If `ares` cannot open `/dev/kvm`:** one `sudo` step with his password. *Advice: only if step 6 finds it necessary.*

## 9. Known limits

- No real Minecraft, Prism sign-in or NVIDIA rendering in tiers 1 and 2. A stand-in plays the game. The mod's behaviour stays with its own tests.
- No backlight, battery, real lid, Wi-Fi, Bluetooth, touchpad or firmware in the VM.
- The laptop home, the covers and the game have no accessibility tree. Claude works from pictures, layout rules and the helper's protocol.
- The slim desk image is not the shipped image, and its packages move, as 316's harness image does (`reviews/316-input-portal/KNOWN-LIMITS.md`).
- If the desk needs stand-ins for systemd, app scopes are tested only in tier 2.
- The hosted route is not live: one round per build.
- The laptop's QEMU would not be the runners' pinned 8.2.2 (`toolchain.json`).
- Headless labwc aborts when an output is switched off and on while a client holds the output manager (316's limits). The desk does not cycle outputs.
- A screen text could mislead Claude's reading. The harm ends at the disposable desktop.
- `aresos-desktop status` on the real laptop asks his session's supervisor a read-only question.
- A virtual lid is not the real switch.
- I relied on brief 321 for the second screen and the session-bus rule. Its code and its `KNOWN-LIMITS.md` are not in this checkout.
- Not read for this note: `docs/design/HUB.md`, `docs/control/TOOLS.md` and `FEATURES.md`, and `aresos-desktop` itself.

## 10. For the lead

- **Rule check.** Brief 334 lists the laptop rules as "no VM or container, nothing mounted, no Chrome against his profile, no `rpm-ostree`, `bootc` or `ostree`". This checkout's `AGENTS.md` says less:
  - "Environment": no sudo, nothing installed system-wide, no window or input in his session, one heavy step at a time.
  - `os/tests`: never the module `test_owner_update`.
  - Hard rule 4.
  
  I treated the brief's list as binding. Write it into `AGENTS.md`, with whatever decisions 1 and 2 change.
- **Precedents differ.** `run.sh` says 316's container harness ran on the laptop. 18c's report says no container or VM ran locally.
- **The mod's rig.** `client-test.sh --session` moves virtual pointers in a private headless labwc that is not in a container. The brief's rule (injection only in a container or a VM) is stricter. The bench leaves that rig alone; say whether it stays as it is.
- **The brief file.** `briefs/334-test-bench.md` ends with two stray lines, `</content>` and `</invoke>`.
