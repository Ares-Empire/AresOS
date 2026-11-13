# 27 REPORT: The first update release (packages 21, 22 and 24)

Built by a Claude agent (Opus 5.5). Brief: `briefs/27-first-update-release.md` (empire brief 266).

**Outcome.** Release 27 is published privately and keyless-signed:
`ghcr.io/ares-empire/aresos@sha256:5fad242fceac7244563913eed96cd72dfcd300fec5e458cdb2ba81bce00d944c`
([run 42842793096](https://github.com/Ares-Empire/AresOS/actions/runs/42842793096), source `b216f28f`).
The image diff against release 13 explained all 915 changed paths. **The owner's update route passed in the VM:** update rehearsal run 14 ([43302603386](https://github.com/Ares-Empire/AresOS/actions/runs/43302603386), head `c9072528`) started from the laptop's state (corrected pinned stock, switched to release 13 by the 15f tools), updated the tools through the guide's bootstrap, then ran `at update`, `at title` and `at reboot`. Release 27 booted with release 13 as rollback and stock still pinned. The run then set the admin password with `sudo passwd ares`, proved package 21's rules, and walked `at previous` back to release 13. Every protected-disk audit was unchanged.

Tools manifest fingerprint: `851eb742bfe20bd4b47370b9f2558494edf4b74056d7023cc0d412e32fee6f33`. The first records commit pinned `167f587c…`; JUDGMENT-CALL 11 (`os/release/update.sh`) renewed it to `daa31228…`, review 1's fix to `e4dedbb6…`, review 2's stop routine to `f85084b6…` and review 3's fix (`owner.py`) to this one.

## Done

### A. The release image (`release_27`, job `release-27` in `os-image.yml`)

- **Build:** main's image through package 21's reviewed check build (`os/ci/check-build.sh build`: `podman build os/Containerfile`, the in-image checks, the CI-only VM layer and its one VM pass), then the release-isolation check of release 13's job (no CI service, both passwords locked). Same pinned base `ed93d215…`, same locks. No pin had vanished (all locked RPMs and the Chrome RPM answered on their pinned URLs on 2026-11-10), so no pin was renewed.
- **Image diff** (`os/ci/release_diff.py`, run privileged through `build_tools.py`). Release 13 is verified with its cosign identity and pulled with the job token. Then base, release 13 and the new image are mounted and compared:
  - **packages:** added NEVRAs must equal the lock change since release 13's source (`775be05b`) plus the Chrome pin. Every removed NEVRA must be replaced by a locked one of the same name and arch, and every changed name has a reviewed reason (package 21; its JUDGMENT-CALL 4 for util-linux; its JUDGMENT-CALL 10 for xdg-desktop-portal-wlr).
  - **files:** the complete inventories (mode, owner, type, xattrs, hash, link target) of both images. Every changed path must match one rule:
    - `config`: bytes equal the changed `os/config` file, mode from build.sh. It never explains a mode or owner change of an existing directory.
    - `policy`.
    - `manifest`: lock, Chrome pin, package list, updater audit.
    - `build`: each package 21 build.sh step is checked on its own. Polkit defaults are recomputed from the base bytes with build.sh's own edit. Chrome under `/usr/lib/opt` is checked against Chrome's RPM file list, and the Chrome links against their exact targets. `/etc/default/google-chrome` must have exact bytes. The empty `/var/opt` and `cron.daily` are removed. The `aresos-subids` enable link is checked. `ares` is added to wheel and nothing else changes in group/gshadow. Shadow changes only in creation dates. There is one subid range. The Flatpak and brew-completion base files are restored, and the three Flatpak helper units are unmasked.
    - `package`: owned by a changed RPM, or a Chrome install-script icon/menu file.
    - exact rules for twelve paths found by release run 2. Each covers one path with one exact before/after; a near miss stays unexplained.
    - `generated`: rpm database, dnf5 history/state/log, ld cache, desktop and icon caches, SELinux store, `/run` leftovers. Listed path by path.
  - **units:** every changed path under a `systemd/` directory is listed with its rule, and none may be only `generated`.
  - **image metadata:** OCI runtime configuration equal, labels changed only in the revision, base ancestry of both images.

  Anything unexplained writes `status: stopped` with the full list and stops the job before publishing.
- **A fix the diff found:** release run 2 stopped because `/etc/sudoers.d` had become mode 0755 (package 21 writes `aresos-everyday` there, and the directory's mode followed the build's umask). `os/build.sh` now restores `root:root 0750` after writing the file, `os/ci/image-checks.sh` checks it in the image, and `test_everyday_account` covers it. In the published image's inventories (run 5), no directory present in both images changed mode or owner.
- **Publish** (`os/ci/publish.sh`): only from `pkg/13-keyboard-layout` or `pkg/27-first-update-release` (a `case`, not "any branch"). Tag `27-<sha>`, private, keyless-signed by this repo's workflow at this branch's ref and verified with that identity. The guard allows the branch's release dispatches (cap 5, see the budget) and **one publish**.
- **Job-token read:** CI read the private org package with `GITHUB_TOKEN` (`job_token_read: passed`, `owner_token_used: false`). `GHCR_READ_TOKEN` stays until the owner removes it.
- **Mirror patience** (release job only): `os/ci/install-tools.sh` takes `ARESOS_APT_RETRIES` (5) and `ARESOS_APT_TIMEOUT` (60 s per request) from the job, and the job's tool step may take 40 minutes. Release runs 3 and 4 failed on the Ubuntu snapshot mirror (HTTP 500, then 504).

### B. Records (commit `933f2d35`, written by `reviews/27-first-update-release/records.py`)

- `os/manifest/releases/27.json` and `os/manifest/release.json`: digest, tag, source, base, signature identity, run, image diff summary, job-token read, `daily_wheel: true` and the source trees as `{tree, path}` rows.
- `os/owner-tools/history.json`: release 27 appended with `daily_wheel: true`.
- Payload regenerated (`bundle.py --refresh`). Fingerprint `851eb742…` (after `167f587c…`, `daa31228…`, `e4dedbb6…` and `f85084b6…`) pinned in both copy checks and both bootstrap blocks of `docs/INSTALL.md`, in `commands.json` and in INSTALL-STATUS. Step 6's exact release line names release 27.
- INSTALL-STATUS: labels R27 (current) and R13 (previous, on the laptop). The update-route row carries the announcement: `daily_wheel: true`, so the one-time password box applies.
- `verify_release.py` binds release 27 by those Git trees (JUDGMENT-CALL 7) and checks the row shape.

### C. The update rehearsal (`rehearsal=update`, `os/ci/owner_vm.py`)

- **Laptop state:** corrected Bazzite stock, paused and pinned, then switched to release 13 by the release-13-era tools (15f tools `3ef85c4a…` from `17fe261c`), as on 2026-11-08/09.
- **Step 8 by typing:**
  - the new bundle is copied with `Copy-AresOwnerTools` and its fingerprint check, then installed by the guide's bootstrap (the tools update themselves);
  - `at update`, `at title`, `at reboot`, the guide's boot-menu choice, then `at check`;
  - `sudo passwd ares` in the root console;
  - package 21's rules on the booted release:
    - wheel; sudo asks every time and keeps no ticket (`sudo -l -U ares`, `sudo -n true` refused, then a fresh tty4 login as `ares` with `sudo -v`);
    - no passwordless polkit rule: package 21's `guest.sh` checks its sample. Then polkitd answers **every installed action** for his active desktop session (`pkcheck`), and every action he may take without his password must be on package 21's reviewed list (`os/ci/polkit-review.json`). This also covers `/etc` kept from release 13;
    - Chrome starts (headless, as `ares`, renders a page);
    - the PATH his AresOS terminal really exports (typed in foot), the hub terminal's argv, the session's system PATH;
    - `aresos-shell` lists its apps;
  - `at previous`, `at reboot`, `at check`, then `at update` refused (JUDGMENT-CALL 2).
- **Audits** (package 11's) at every stage: the stand-in Windows disk and its boot entry, stock deployment untouched and pinned, and the deployment shape.
- **Hidden input:** `owner_hidden.py` has a `passwd` reader; `owner_login.py` logs in the user it is given (`ares` on tty4 for the sudo proof).
- **Bindings:** the run records its own bound sources (`27-bound-sources.json`); `reviews/27-first-update-release/rebind.py record` writes them to `os/manifest/ci/27/source-bindings.json` and empties `pending-rebind.json`. `checkout_sources.py` prefers package 27's tables when they exist.
- **Host walk** (`os/manifest/ci/27/host-walk.json`, `walk-host.py`): both local walks (qualification and update route, 250 sources) on the rehearsal head; `owner_vm.py` refuses a stale walk.

### D. Tests

`test_owner_login`: `UtilLinuxVersionTest` (both versions accepted through the real init path, a third refused before any observer starts, the rule in the guest program, the harness scan). `test_owner_walk`: `TerminalPathTest` (switch, foot wait, round trip, active session and settle before typing; one retry; a second miss stops; the guest probe program). `test_owner_update`: `UpdateStopTest` (see F). `test_release27` (new): package diff, accounts, polkit transform against build.sh, classifier (each rule, each exact rule with its near miss, also under umask 077), guard ledger, apt patience, publish branch, the release-27 verifier, the dispatch matrix. Updated: `test_owner_walk` (update route), `test_owner_equality`, `test_checkout_sources`, `test_owner_step_limits`, `test_owner_path`, `test_owner_update`, `test_owner_tools`, `test_everyday_account`, the retained-machine tests (pinned to release 13) and the workflow pins.

**The update job's gates** (`UpdateJobGatesTest`, after rehearsal run 1 stopped at `owner_capabilities.py`):
- It reads every step of the rehearsal job that runs for an update dispatch on this branch, with the environment that step really gets (workflow, job and step env, GitHub's variables, `env -u`), the shell branches that run and each script's own arguments.
- `GateScan` follows the code each script surely runs from its entry point, into the os/ci modules it imports. It evaluates every `assert` and `observations.check` that depends only on that environment and those arguments. Code under unknown branches, loops and handlers is skipped.
- On `87990bc1` it fails at exactly `owner_capabilities.py:147` (run 1's stop) and `owner_devices.py:359`, which would have been the next stop. Both now allow `update`; `owner_media.require_runner()`, which each calls first, limits it to package 27's branch.
- It now evaluates 17 gates and all of them pass.

**The VM step's package and mode decisions** (after run 2 stopped at the installer):
- `installer_webui.py` names the owner VM harness packages once (`OWNER_VM_PACKAGES = ('14', '16', '27')`, `KEYBOARD_PACKAGES`) for its six branches.
- `OwnerHarnessPackagesTest` requires every `REHEARSAL_PACKAGE` set in `os/ci` that names 14 or 16 to name 27. It also requires the installer's `start()` and `readback()` to drive the guest for 27 exactly as for 14.
- `VmStepDecisionsTest` reads every module the VM step imports (30). It finds each comparison, prefix test or lookup on `REHEARSAL_PACKAGE`, `REHEARSAL_MODE`, `GITHUB_REF_NAME` or the mode argument (40 decisions) and requires each whole condition to decide alike for package 27's update rehearsal and package 14's owner-tools qualification. The exceptions are seven reviewed decisions, each with its reason.
- Shell scripts, the overlay and guest templates read none of these names.
- For the update rehearsal only, the rehearsal job's tool install has the release job's mirror patience (JUDGMENT-CALL 10).

A test-only fix: `test_owner_entry`, `test_owner_diagnostics` and `test_owner_update` called `owner.main()` in-process, which sets umask 077 for the rest of the test process. Under discover's order that made one near miss in the exact-rule test a no-op, so the test failed once and passed on rerun. Replaying discover's order showed `test_owner_entry` as the only module that changed process state (umask 022 to 077). The calls now restore the umask (`common.kept_umask`), and the test sets every mode it relies on. The replay at `53dc5fec` then passed (74 modules before `test_release27`, no state change).

### E. After rehearsal runs 4 to 13 (brief `27-rehearsal-fixes-1.md`)

Run 4 booted release 27 and then stopped at its first console login: the harness's login observer
(`os/ci/owner_login.py`) accepted only util-linux 2.41.5, and release 27 ships 2.41.6 (package 21's JUDGMENT-CALL 4).

- **util-linux v2.41.5 to v2.41.6, compared before accepting it.**
  - **Upstream** ([compare](https://github.com/util-linux/util-linux/compare/v2.41.5...v2.41.6), tag commits
    `230de59f` to `02822c93`): 14 commits and 33 files.
    - `login-utils/login.c` and `term-utils/agetty.c` are not among them. Their raw files are byte-identical at
      both tags (sha256 `c367d286…` and `d6a26ddf…`).
    - The only shared library change is `ul_open_no_symlinks`/`ul_openat_resolve` in `lib/fileutils.c`. Neither
      file calls it; libmount and loopdev do.
  - **Fedora:** Koji's source commits are `4689efd5` for 2.41.5-1.fc44 and `976ba396` for 2.41.6-1.fc44.
    - Both carry the same two login patches, lastlog `O_CREAT` and the `/run/motd.d` path, with identical hunks.
    - The new patches touch libmount, nsenter, `lib/fileutils`, wall and a config-gen profile.
    - The spec otherwise changes only its version and a comment.
  - **The three behaviours the observer relies on are unchanged:**
    - login.c's `LOGIN_TIMEOUT` default of 60, read from `login.defs` and then `alarm(timeout)`;
    - agetty's own `case CTL('U')` line kill;
    - agetty's `case CTL('D'): exit(EXIT_SUCCESS)`, which never reaches login.
  - The other 2.41.6 changes (`openat2(RESOLVE_NO_SYMLINKS)` for loop backing files, the restricted libmount mode)
    apply only to non-root mounts or NOFOLLOW loop setups. The harness's `losetup` runs on the Ubuntu host.
- **The observer accepts exactly 2.41.5 and 2.41.6.** `login_version()` parses `<tool> from util-linux X` and
  accepts only those two. It is part of the prepared guest program. The observer's recorded semantics now name both
  versions.
- **No other harness pin on a version package 21 changed.** `stock_probe` and `two_disk_vm` pin rpm-ostree, uupd,
  ostree and grub2-common, `firmware_contract` pins OVMF on the host, and none of these changed. The walk only
  records Chrome's version. `image-checks.sh` and `check-resolve.sh` are package 21's own build checks.
  `UtilLinuxVersionTest` keeps it so: it scans `os/ci` and `os-image.yml` for every version package 21 removed
  (util-linux 2.41.5, xdg-desktop-portal-wlr 0.8.4) and finds only the observer's pair and the release diff's reason text.
- **Run 5 ([43120759117](https://github.com/Ares-Empire/AresOS/actions/runs/43120759117)) passed that login** on
  release 27, and then `at check`, `at title`, `at records` and public typing on the console and in foot. It then
  stopped at the terminal PATH proof (`terminal_path`, its first run on a real VM, since release 27 is the first
  image with package 21).
  - The typed `python3 /run/aresos-path.py` never ran: `terminal_path` typed right after Ctrl+Alt+F1, because its
    "tty1 active and foot running" check is true at once.
  - `kb.foot`, which typed into the same foot on the same boot, has two serial round trips between the switch and
    typing. The keys most likely arrived while labwc was still taking its seat back.
- **`terminal_path` now waits before typing** (integrator-approved, 2026-11-12):
  - the order is switch, foot wait, the probe preparation (a serial round trip), then until ares's seat0 session is
    `Active=yes` and `State=active` (guest.sh's lookup), then one second for labwc;
  - this step proves his PATH, not the keyboard (`kb.foot` proved typing in foot earlier on the same boot), so a
    probe missing after 20 s gets one guarded retry: a screenshot (`-path-miss`), Ctrl+U, the same idempotent line
    again, and `retried: true` in the evidence and the rehearsal result. A second miss stops as before;
  - a screenshot (`-path`) follows a found probe;
  - `TerminalPathTest` checks the order, the retry, the stop on a second miss, and the guest probe program itself.
- **The other steps that first ran on a real VM in runs 7, 9 and 14** were checked for the same kind of problem (typing right
  after a VT switch or session change without a readiness wait). None has it:
  - guest.sh and the polkit sweep send no keys (serial only), and now follow the session wait;
  - `sudo passwd ares` is typed on tty3, a kernel console, after `select` and a prompt wait over serial;
  - his sudo on tty4 waits for the `login:` line and for the prepared login reader's fresh prompt before the username;
  - package 21's rules send no keys (serial only);
  - `at previous`, `at title` and `at reboot` use `Console.run`'s prompt waits;
  - the previous-13 stage uses login, prompt waits, `kb.foot` (worked on release 13 and 27 in run 5) and `logout`'s
    prompt and `login:` waits.
- **Run 6 ([43136407300](https://github.com/Ares-Empire/AresOS/actions/runs/43136407300)): an observed VM stall.** It
  stopped before any changed step. Release 27's boot after `at update` never showed `login:` on the serial console
  within 300 s.
  - **Where the serial log ends:** right after systemd 259's console probes: XTGETTCAP `ESC P+q6E616D65`, then
    `ESC[6n ESC[32766;32766H ESC[6n`. The VGA screenshot ends at the same line.
  - **Run 5, same boot:** next came `ESC[24;80H …` (systemd's fallback after the reply timeout), then the banner,
    then login.
  - **Just before the stop:** `clocksource: Watchdog remote CPU 1 read timed out`.
  - **Reading:** either PID 1 sat in its terminal-size (DSR) reply wait, or a vCPU stalled while holding the console
    lock. Either fits frozen serial and VGA output with no later RCU-stall or hung-task message. The 1339 MiB the
    boot read don't prove it kept booting: most may have come before the stall (initrd, composefs).
  - **Why only the VM:** these probes go out only because the VM's kickstart adds `console=ttyS0`
    (`os/ci/two_disk_vm.py:435`). On the laptop `/dev/console` is a VT, and systemd uses `TIOCGWINSZ` there.
  - The integrator chose an unchanged rerun (run 7). The same boot passed in runs 5, 7, 9 and 14; run 12 hit the
    same stall at stock's first boot (below).
- **Run 7 ([43148798803](https://github.com/Ares-Empire/AresOS/actions/runs/43148798803)), the unchanged rerun.**
  - **Passed:** release 27's boot, the console login with util-linux 2.41.6, the terminal PATH proof on its first
    try (`retried: false`, his session `Active=yes`, `State=active`) and guest.sh.
  - **Stopped at:** package 21's homebrew check, `runuser -u ares -- brew --version`.
  - **Cause:** the command started from the VM's root shell's directory, which ares cannot read, and Homebrew 7.0.9
    refuses that: "The current working directory must be readable to ares to run brew". ares-recovery's identical
    line just before passed.
  - **Fix:** `os/tests/inherited-homebrew.sh` now runs from `/`, and package 21's rules start his commands from `/`.
  - **Sweep:** every `runuser -u ares` call the walk reaches for the first time after it was checked for a dependence on its
    working directory. guest.sh's passed in run 7; the polkit sweep runs only root tools; `sudo passwd ares` and his
    tty4 sudo are typed in login shells; previous-13 has none. `os/release` was not affected.
- **Run 8 ([43160633763](https://github.com/Ares-Empire/AresOS/actions/runs/43160633763)) never reached the VM.**
  - **Stopped at:** the hosted runner's unit step. One of 908 tests failed: `TerminalPathTest`'s order check saw an
    extra 1 ms sleep.
  - **Cause:** the test patches `time.sleep`, which is the time module's. A subprocess wait (the guest syntax check's
    `bash -n`) slept 1 ms inside it on the slower runner. Under a busy loop on all cores, the same check slept 898
    times.
  - **Fix:** only a sleep called by `terminal_path` itself is recorded. A probe of the threads alive after each of
    the 711 tests that run before it also found `test_aresos_shell`'s scope watcher left running; that test now
    stops it.
- **Run 9 ([43173190284](https://github.com/Ares-Empire/AresOS/actions/runs/43173190284)), on review 2's bundle.**
  - **Passed** on release 27: the terminal PATH, guest.sh, the homebrew check, the polkit sweep and `sudo passwd ares`.
    Then a fresh tty4 login as `ares` with the new password, `sudo -v` accepted and `sudo -n` refused. Every other
    package 21 rule held.
  - **Stopped at:** `ares_password_set`. It read `passwd -S ares` and wanted the old Red Hat passwd's `PS`, but
    Fedora 44's shadow-utils 4.19 `passwd` reports another status. The password itself worked.
  - **Fix:** the rule now reads the hash as package 21's own checks do (`getent shadow ares`). Only a crypt hash
    counts, never the image's locked `!*`.
  - **Sweep:** every later step, down to the end of the update job, was read for another check of a tool whose
    version or output format differs; none was found. sudo, polkit, systemd and shadow-utils are not among package
    21's 29 package changes. The tools' `lsblk`/`findmnt` reads had already run on release 27 (util-linux 2.41.6).
- **Run 10 ([43188392249](https://github.com/Ares-Empire/AresOS/actions/runs/43188392249)) stopped before any VM
  work.** snapshot.ubuntu.com answered 503 while the runner installed its pinned tools: a mirror outage, as in release
  runs 3 and 4.
- **Run 11 ([43219365492](https://github.com/Ares-Empire/AresOS/actions/runs/43219365492)) reran the same content.** It
  was dispatched once the pinned snapshot's three InRelease files had answered 200 on three checks in a row, five
  minutes apart. It timed out after 40 minutes in the same step: the mirror answered, but too slowly, and fell back
  to 503. Again this was before any VM work.
- **Run 12 waited for a stricter health check:** every 5 minutes, all three InRelease files answering 200 in under
  3 s and a timed download of `Translation-en.xz` at 2 MiB/s or more, four times in a row.
- **Run 12 ([43277139615](https://github.com/Ares-Empire/AresOS/actions/runs/43277139615)): the console stall again,
  now at stock Bazzite's first installed boot, before any AresOS release or tool ran.**
  - The serial log and the VGA screenshot both end at PID 1's `Relabeled /dev/, /dev/shm/, /run/` and then
    `ESC[6n ESC[32766;32766H ESC[6n`. That is systemd's size probe of `/dev/console`, here the serial port. The
    cursor restore never came. PID 1 had already got past its terminfo query. Run 6 ended the same way.
  - **Fix: the VM pins its serial console, so systemd never probes it.** `pin_serial_console()` runs after the
    install and before stock's first boot.
    - It attaches only the target image from the host, requires exactly one ext4 `/boot` and one boot entry, and
      appends `systemd.tty.term/rows/columns.console=vt220/24/80` and the same for `ttyS0` once to its `options`
      line. It reads the line back, unmounts and detaches; anything else STOPs.
    - systemd v259 skips both console probes with these args: `core/main.c` (`fixup_environment`),
      `terminal-util.c` (`reset_dev_console_fd`) and `core/exec-invoke.c` for ttyS0 services.
    - ostree carries the args into release 13 and release 27. 24×80 and vt220 are what the probe yielded.
    - The kickstart's `bootloader --append` turned out to be dead code: the real WebUI install keeps only
      Anaconda's preserved arguments.
  - **Also:** the harness now answers the terminfo query ("not supported"). Every boot records its kernel command
    line and the terminal queries it answered (evidence only). A boot that never shows `login:` now records the
    VM's run state, the vCPU threads' CPU time and a SysRq-W dump before it is closed.
- **Run 13 ([43293692038](https://github.com/Ares-Empire/AresOS/actions/runs/43293692038)): stopped after 11 minutes
  in the hosted regression tests, before any VM work.**
  - A rule test requires every function that scans a loop device's partitions (`losetup --partscan`) to wait with
    the shared `wait_loop_partitions()`. The new pin used `udevadm settle` and a glob instead. Review 5 had named
    the shared wait as sturdier; the test made it a must.
  - **Fix:** the pin calls `wait_loop_partitions()` once, right after the scan. That checks the loop is backed by
    the target image and waits for exactly its GPT's partitions, and the pin reads only those. It now unmounts only
    after a successful mount, with independent cleanup for the mount point and the loop (review 5's first nit),
    and a test injects a failed mount. The function joined the rule test's list.
  - The focused WSL set had missed it. Since then the full suite runs locally before a push.
- **Budget:** the update cap went from 5 to 6, 7, 8, 9, 10, 11, 12, 13, 14 and then 15, each integrator-approved, since every
  dispatch counts. The pending list and both host walks were regenerated for each head.

### F. Reviews 1 to 6 (CHANGES-NEEDED on `5335f8a4`, `f708c53f` and `976d0334`; SAFE on `5f3fd6b1`, `761d9ae7` and `c9072528`)

- **Blocking (reviews 1 to 3): every unsuccessful end of the update step goes through one stop routine.**
  - **Review 1:** `Host.script` ran `update.sh` through `subprocess.run(timeout=1800)`. A timeout SIGKILLed only
    bash, so its `EXIT` trap never ran and `bootc` could go on staging behind a STOP.
  - **Review 2 found four gaps in that first fix:**
    - a second Ctrl+C during the TERM grace cut the stop short;
    - a failed shell skipped the group stop;
    - a failed status read skipped the mask restore;
    - any staged deployment was removed without proving it was this update's.
  - **`owner.Step`** runs each release step in its own session and waits in short slices. Its stop sends TERM, then
    KILL, to every live process of the session or process group, and proves by a `/proc` scan that none is left.
    `Host.script` uses it, so every release step gets this.
  - **`Deferred`:** the update step runs under it. From the step's start to the end of its stop routine, SIGINT,
    SIGTERM and SIGHUP only note themselves. Ctrl+C, a closed window or a kill starts the routine and cannot cut it short.
  - **`Tools.stop_update`** is the one routine for a failed shell, the time limit, a signal or an exception:
    1. it prints "Stopping the update safely; this takes up to 11 minutes. Do not close this window or restart."
       11 minutes is its configured budget (632 s), not an exact ceiling: `/proc` scans and starting commands are not
       counted. Write errors after a closed window are ignored;
    2. it stops the step and tries to prove it empty (a stop it cannot prove means step 3 deletes nothing);
    3. `reconcile_update` removes a staged deployment only when all of these hold: both status views agree, no
       deployment client or transaction remains, the running, kept and pinned deployments are unchanged, and the only
       staged deployment is new, unpinned and this update's target. Otherwise it deletes nothing;
    4. in every case it tries to restore the finalizer masks and checks them, independently of step 3. With the
       masks back, a staged deployment cannot finalize;
    5. it claims a clean stop, after which nothing changes at the next start, only when every check passed.
       Otherwise it reports each error and says "Do not reboot; export records and get help".
  - **Tests:** `UpdateStopTest` drives the real `Step` with real bash and `update.sh` and a fake `bootc`. Cases:
    - the time limit, and staging that finished while the step runs into it;
    - Ctrl+C, and a second and third Ctrl+C in the TERM grace;
    - SIGHUP with a closed output, and SIGTERM;
    - a failed shell with a TERM-proof child that closed its pipes;
    - a status read that fails after the kill;
    - a foreign staged deployment;
    - a real process whose KILL never arrives;
    - a successful step.

    With `TerminalPathTest`, they passed 20 times in a row in WSL, the last time under a busy loop on all 16 cores.
  - **Revert proofs:** one behaviour reverted at a time; the constants the tests patch stay.
    - review 1's old runner (proved on `8ede6b95`): the hang fails on "the masks this run removed are not back", and the finished staging on
      "a staged deployment remained after the stop";
    - signals not deferred: the repeated Ctrl+C, SIGHUP and SIGTERM cases fail on "the masks this run removed are
      not back";
    - a failed shell not stopped: "a process of the step outlived the tool";
    - masks restored only after a clean reconcile: "the masks this run removed are not back";
    - no ownership check: "a foreign staged deployment was deleted";
    - no proof that the step is empty: "a survivor was not reported".
  - `IntentTest`: a failed update step is undone, so the same command retries it. The tools bundle was regenerated,
    with every pin.
- **Review 3 (blocking): an error inside the stop routine skipped the stop and the mask restore.**
  - **Cause:** `/proc/PID/stat` was decoded as text. A process name is 15 raw bytes and may cut a multibyte
    character. One such process anywhere raised `UnicodeDecodeError` while `stop()` built its targets, before the
    first signal and outside the routine's protection.
  - **Now:** `/proc` is parsed as bytes after the last `)`. A vanished process is gone; anything else unreadable is
    reported, so an incomplete scan is never taken for proof, and the scan never raises. `stop()` signals the step's
    process group first and scans after.
  - Every part of `stop_update` is protected on its own (`except Exception`): the stop, its diagnostics, the
    reconcile and the masks. A stop it cannot prove reconciles and deletes nothing, but the masks are still restored
    and checked. Every error is reported with "Do not reboot".
  - **Tests:** names that are not UTF-8 inside the step (bootc and its child) and outside it, under the time limit,
    Ctrl+C and a failed shell; an injected scan failure; an injected `stop()` failure together with a failed mask
    check, both reported. They passed 10 times in a row, once under a busy loop on all 16 cores.
  - **Revert proofs:** decoding as text fails on "a process of the step outlived the tool"; `stop()` outside the
    protection fails on "the masks this run removed are not back". Review 2's proofs still hold.
  - **Nits:** the KILL-survivor test leaked its process. PIDs are now captured, with their start times, before the
    fixture goes, and a class check finds nothing left. JUDGMENT-CALL 11 now says the masks are restored and checked,
    and that nothing changes at the next start only when every stop check passed.
- **Review 4 (on `5f3fd6b1`): SAFE.** It checked review 3's fixes, the password rule, the `851eb742…` pins and the `/proc`
  decoding elsewhere. Its nit and its qualification are recorded under PLAN-GAP as known limits, with no laptop impact.
- **Review 5 (gpt-6.1-sol high on `761d9ae7`, scoped to `bf2dd553..761d9ae7`): SAFE.** It checked the serial console pin,
  the terminfo answer and the boot-stall diagnostics. It listed four known limits (harness only). Two were fixed
  after run 13 (the pin's cleanup and its partition wait, see E); the other two are under PLAN-GAP.
- **Review 6 (gpt-6.1-sol medium on `c9072528`, scoped to `930d4b37..c9072528`): SAFE.** It checked run 13's fix (the
  shared partition wait, the mount-tracked cleanup and its test) and the cap 15 records. Its known limit (harness
  only) is under PLAN-GAP.
- **Should-fix (review 1): util-linux suffixes.** `login_version()` matched only the start of the version, so `2.41.6-rc1`
  passed. It now matches the whole line: the version, then only agetty's feature list. The tests refuse suffixed,
  extended and trailing forms.

## Verified

- **Release 27** ([release run 42842793096](https://github.com/Ares-Empire/AresOS/actions/runs/42842793096), source `b216f28f`):
  `ghcr.io/ares-empire/aresos@sha256:5fad242fceac7244563913eed96cd72dfcd300fec5e458cdb2ba81bce00d944c`. It is private and
  keyless-signed by `https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/pkg/27-first-update-release`
  (issuer `https://token.actions.githubusercontent.com`), and was verified with that identity in the job. The job token
  read the private package (`GITHUB_TOKEN`; no owner token used).
- **Image diff against release 13** (`os/manifest/releases/27.json`):
  - 2801 → 2806 packages; 29 package changes, each with its reason (package 21, its JUDGMENT-CALLs 4 and 10);
  - 915 changed paths: 0 unexplained, 0 problems, 13 generated;
  - runtime configuration equal, and base ancestry verified.
- **The owner's update route in the VM** ([run 43302603386](https://github.com/Ares-Empire/AresOS/actions/runs/43302603386), head `c9072528`, with tools bundle
  `851eb742…`):
  - **Starting state:** corrected pinned stock, switched to release 13 by the laptop's 15f tools.
  - **Tools:** they updated themselves from version 1 to 2
    through the guide's bootstrap.
  - **`at update`:** staged release 27 and was confirmed after the restart, with release 13 as rollback and stock pinned
    throughout.
  - **Password and sudo:** `sudo passwd ares` was typed; his new password signed him in on tty4; `sudo -v` accepted
    it; `sudo -n` was refused (no ticket).
  - **Package 21's rules on release 27:** `ares` in wheel: yes; sudo asks for his password
    every time: yes; no sudo ticket kept: yes; his
    password set: yes; Chrome (`Google Chrome 157.0.8103.50`) started:
    yes; the session's system PATH `/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin`; the hub terminal reads his
    PATH; `aresos-shell` lists browser, notepad, terminal.
  - **His AresOS terminal's PATH:** `/var/home/ares/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:/var/lib/flatpak/exports/bin` (retried: false).
  - **polkit:** 401 actions asked for his active desktop session; 132 need no
    password, all on package 21's reviewed list.
  - **Return:** `at previous` went back to release 13 and was confirmed after the restart. `at update` then refused
    (no forward route; JUDGMENT-CALL 2) and changed nothing.
  - **Audits:** every protected-disk, NVRAM and BootNext audit was unchanged.
  - **Evidence:** the run's `two-disk-evidence` artifact. Its result is committed as
    `reviews/27-first-update-release/runs/update-43302603386/update-rehearsal-result.json`.
- **Bindings:** `rebind.py record` wrote `os/manifest/ci/27/source-bindings.json` (6 tables,
  250 unique sources, run 43302603386). `os/manifest/ci/16/pending-rebind.json` now lists no files.
- **INSTALL-STATUS:** the update-route row says VM REHEARSAL PASSED, with the run links.
- **Unit tests** (WSL Ubuntu, clones of the branch, run detached):
  - focused set (19 modules) at `5f3fd6b1`: Ran 356, OK;
  - full suite with `-B` at `c9072528`, before run 14: Ran 932, only the WSL-only failures listed next;
  - full suite with `-B` at `29440cfd`: Ran 932, only the WSL-only failures: `test_greeter` 3 errors, `test_inherited_homebrew` 1 failure and 7 errors, `test_sysusers` 2 errors (all three pass on the hosted runner);
  - the stop tests: 20 of 20 in a row (round 2) and 10 of 10 (round 3), with runs under a busy loop on all 16 cores;
  - the revert proofs in F.
- **Hosted:** run 43302603386's qualify step ran 932 tests on `c9072528`, all passing (136 skipped:
  namespace tests the runner cannot run; WSL runs them), with its py_compile, `bash -n` and PowerShell owner-tools
  checks. The checks-only run [43336083190](https://github.com/Ares-Empire/AresOS/actions/runs/43336083190) on `29440cfd`
  ran 932 tests: no failures, 136 skipped and 9 errors.
  - **The 9 errors** are all reads of older commits that the job's depth-1 checkout does not have (`bad object 775be05b`,
    or `os/tests/guest.sh` not in `3fd79165`): `test_release27`'s `ClassifierTest` (4) and `PackageDiffTest` (2),
    `test_owner_walk`'s update route (ps2 off and on) and `test_owner_equality`. The rest passed, including
    `test_greeter`, `test_inherited_homebrew` and `test_sysusers`, which WSL cannot run.
  - **The same suite with full history passed** in run 14's qualify step on `c9072528` and locally on `29440cfd`
    (WSL-only failures aside). `c9072528..29440cfd` changes only records and docs (INSTALL-STATUS, the pending list,
    the source bindings, REVIEW-6 and run 14's result); `os/ci`, `os/tests/audit.py` and `.github` are unchanged.
  - **Its later steps were skipped** (the job stopped at its unittest step). They are covered this way:
    - py_compile, `bash -n` (`os/owner-tools/at`, the `os/ci` and `os/release` scripts) and the PowerShell owner-tools
      tests: run 14's qualify step ran them on `c9072528`, unchanged since;
    - the extra `bash -n` loop and py_compile: the integrator ran both locally on `29440cfd`. `bash -n` passed on
      `os/ci/*.sh`, `os/release/*.sh`, `os/ci/overlay/updater-generator`, `os/build.sh`, `os/tests/*.sh`,
      `aresos-session`, `aresos-terminal` and `os/owner-tools/at`; py_compile passed on 61 files (`os/ci`,
      `os/ci/overlay`, `os/owner-tools`, `os/tests/audit.py` and `power-events.py`);
    - the private package: run 14's registry preflight (`registry_auth.py:77`) asserted its visibility is private;
    - the release inputs and the candidate upstream signature concern the next Bazzite base, not release 27; the
      hosted `systemctl` query reads unchanged code.
  - The integrator accepted this result with no second checks-only run (option 1); the depth-1 checkout is a known
    limit under PLAN-GAP.


## Not verified

- The real laptop: step 8 is the owner's own step, guided. The VM shows the route, not his hardware (NVIDIA, backlight, power button stay package 21b's).
- Chrome's start is proved by its process and window in the VM, not by browsing.
- His own passphrase: the VM types a generated one through the same hidden prompts.

## JUDGMENT-CALL

1. **The pins went in before the rehearsal, not after it** (brief: release.json and the guide's digest only after). Package 22's tools carry `release.json` inside the fingerprinted bundle and refuse a bundle whose newest history record is not `release.json` (`lineage()`); the rehearsal walk types the guide's bootstrap, whose line 8 is the fingerprint. So the bundle the rehearsal installs, and the guide it types, must already hold release 27. I pinned `release.json`, `history.json`, the payload, the fingerprint in every page and step 6's digest in the commit the rehearsal ran on, so the rehearsed bytes are exactly the bytes that get merged. What waited for the pass: the INSTALL-STATUS gate (PENDING → PASSED with the run links), the rebinding, and the report. Nothing reaches the laptop before the merge either way. Alternative rejected: rehearse a separately built bundle and pin a different fingerprint afterwards (the pinned bytes would not be the rehearsed ones). Changing it later: none needed; a later release can follow the same order.
2. **No "forward again" after `at previous`.** Package 22's tools refuse it: `previous` only returns from an update, and `update` stops with "Target release is already deployed; get help" (reviewed, owner-accepted design, its JUDGMENT-CALL 3 and report line "refuses the reverse"). The rehearsal walks previous and its confirmation, then types `at update` once and proves it refuses with nothing changed; the walk ends on release 13 with release 27 beside it. Rejected: adding a forward route to the reviewed tools in a release package (new mutation path, needs its own review; it belongs in 22c), or faking the end state by restoring a disk snapshot. Cost: if the owner ever runs `at previous`, he stays on release 13 until the next release (or 22c). The laptop does not run previous on the normal route.
3. **The image diff for a full rebuild classifies rather than equates.** Release 13 was a two-file overlay; release 27 rebuilds everything, so the diff cannot require equality. Each changed path must match a rule, and every rule except `generated` checks content (see Done). `generated` covers databases the package transaction rewrites in every build (rpm database, dnf5 history and log, ld cache, desktop and icon caches, SELinux store, `/run` leftovers); their content is not compared, every such path is listed in the result, and no systemd unit may be explained by it. Rejected: comparing only package lists (misses build.sh effects) or requiring byte equality for unchanged packages' files only (would not catch build.sh effects on base files). Changing it later: one rule table in `release_diff.py`.
4. **The admin password and his sudo:** `sudo passwd ares` is typed in the root console exactly as the guide says, with both hidden values proved (a new reader kind `passwd` in `owner_hidden.py`, the same reader required at "Retype new password:"). His password is then proved by a **fresh login as `ares` on tty4**, `sudo -v` there, and `sudo -n true` refused, instead of "in foot": the hidden-input proofs observe consoles only. The login observer now takes the username (`ares-recovery` stays the default).
5. **No separate probe for package 27.** Package 14's owner-tools qualification needs a passing probe on the same commit; with three rehearsal runs a failed qualification would leave no room for a new probe plus a qualification. The update rehearsal instead proves its own native step (the full unit suite, the native device and counter checks, the release verifier) in the same run before any VM, through the guard's existing current-run native check.
6. **Package 27 stays outside the organization billing gate.** The repo is public and uses standard runners (free). The local billing read showed every Actions SKU with `netAmount` 0, but now includes a macOS SKU from another org repo and a 1e-8 storage rounding value, which package 14's reviewed SKU list stops on. I did not widen that reviewed list; the CI guard still enforces this package's dispatch caps (release and update dispatches as the integrator raised them, one checks-only run, one publish).
7. **`verify_release.py` binds release 27 by its source trees**, not by commit ancestry: `releases/27.json` records the Git tree of each image source path at the release commit as `{tree, path}` rows (object ID first: the privacy check read a path key followed by a tree ID as a secret), and the verifier requires the same trees at HEAD. A squash merge keeps the trees, so later rehearsals on main still verify release 27 without a new squash binding (release 13 needed one).
8. **Release-13-era tests pin release 13.** Tests that replay retained package 13 machines (switch, finalize, retained parsers, walk states, the 15e login evidence) now read `os/manifest/releases/13.json`, and two use a bundle of the current tools whose newest release is 13 (`release13_bundle`). Their assertions are unchanged.
9. **The release job runs one VM pass, not two.** Release run 1 (42807087845) failed in a second fresh VM pass: after `/dev/nbd0` was reconnected, `offline_journal.py` could not read the filesystem types. Package 21's reviewed check build runs one pass, and the brief asks for that build, so the release job keeps its single pass (`os/ci/check-build.sh build`), followed by release 13's isolation check. Rejected: re-probing the device between passes (a change to package 11's VM tooling inside a release package). Cost of changing later: one more pass in the job, after the device handling is fixed (PLAN-GAP).
10. **The release job waits longer for the Ubuntu snapshot mirror.** Release runs 3 and 4 failed while installing the pinned host tools (HTTP 500, then 504 from the snapshot mirror). The release job alone sets `ARESOS_APT_RETRIES=5` and `ARESOS_APT_TIMEOUT=60` (apt `Acquire::Retries` and an http/https timeout per request), and its tool step may take 40 minutes instead of 20. Other jobs keep the old defaults (3 retries, no timeout). The pinned snapshot, package versions and hashes are unchanged. Cost of reversing: remove two env lines and the step timeout.

11. **`at update` unmasks the two staging finalizers (reverses a lockdown choice from the first image; owner board #175).** Every AresOS image masks `ostree-finalize-staged.service` and `bootc-finalize-staged.service` (`os/policy/masked-system-units.txt`, since #3). bootc cannot stage a release while they are masked, so `at update` could never work from a running AresOS (rehearsal run 42940741765; the earlier switch worked only from stock, where both are static).
    - Chosen: `os/release/update.sh` (in the tools bundle, so it fixes R13 to R27 on the laptop) removes exactly those two `/dev/null` links right before `bootc switch`, reloads systemd and requires both static. Before that it requires each to be exactly the image's mask, or already unmasked by an earlier update, and every other system and user updater the image masks to be masked; anything else stops with nothing changed. If anything fails before staging, both masks are restored and the tools say "do not reboot".
    - A failure, a timeout, Ctrl+C, a closed window or a kill is covered too (reviews 1 to 3). The update step runs in its own session, and one stop routine handles each of those ends. Those signals only note themselves until it ends, and an error in one of its parts never skips the next. It stops every process of the step and tries to prove none is left. Only then does it remove a staged deployment, and only one that is exactly this update's. In every case it tries to mask the two again and checks that they are masked. It always STOPs and says whether every check passed. Nothing changes at the next start only when all of them passed; otherwise it says what is left and not to reboot. Before, a timeout SIGKILLed only the shell, so its restore never ran and staging could go on. This fulfils what the owner accepted on board #175; it is not a new call.
    - The removal carries into R27's `/etc` through ostree's merge, so the next update finds them unmasked. R13's own `/etc` keeps the removal too. Both units fetch and apply nothing by themselves: ostree starts the first only to finalize a deployment that was already staged, and the second is bootc's composefs counterpart. All automatic updaters stay masked.
    - Rejected: re-masking after staging (the finalizer must run at shutdown to finish the update); a non-staged deploy (`ostree container image deploy`; changes what `at check` and the title expect); a new image that stops masking them (out of scope for this release; PLAN-GAP).
    - The tools on AresOS never audited unit masks (`at check`, `at title` and the records read none; `paused_state` runs on stock only), so they accept this state. The update route itself now stops on any other unmasked updater. Package 21's `guest.sh` (the rehearsal's policy check) accepts exactly these two only when unmasked by that route.
    - Cost of changing later: the next image can drop the two masks (then `update.sh`'s check finds them static) and add them to the reviewed updater allowlist.

## PLAN-GAP

- **The brief's order (pin after the rehearsal) and package 22's tools disagree.** The bundle carries `release.json` and its history must end with it, and the walk types the guide's fingerprint, so the pins sit in the rehearsed commit (JUDGMENT-CALL 1).
- **"Forward again" after `at previous` has no route** in package 22's tools (JUDGMENT-CALL 2). If wanted, 22c should add it (for example `at update` queueing an already deployed newer release with `bootc rollback`), with its own rehearsal.
- **Package 23 (PR #36) in the next release:** its mod must be built before the image (`os/ci/build-mod.sh` before `podman build`). The release job here runs `os/ci/check-build.sh build` only; the next release package must add that step (and its evidence) to the release job and to the image diff's `config`/`build` rules.
- **The next release's diff:** `release_diff.py` compares with release 13 (`PREVIOUS`, `PREVIOUS_SOURCE`, the package reason table). The next release must compare with release 27 instead and list its own package changes.
- **`offline_journal.py` and a reused `/dev/nbd0`:** a second `vm.py` pass in the same job failed to read filesystem types after reconnecting the device (run 42807087845). One pass per job works; a job that needs two passes should settle or re-probe the device first.
- **The update route's "announcement"** is the maintainer's message. INSTALL-STATUS's update row now carries it for release 27 (`ares` is an administrator there, so the one-time password box applies); the guide itself is unchanged.
- **Package 14's owner-tools qualification would stop at `guest.sh` on release 27.** Package 21's `guest.sh` requires ares's desktop session to be active (`loginctl ... Active = yes`). `common_boot(..., ares=True)` runs it right after `public_typing`, which leaves the root console (tty3) in front, so the next qualification on release 27 would stop there. The update rehearsal is not affected: `terminal_path` leaves his desktop in front before `guest.sh` and the polkit sweep. Fix before the next qualification: bring the desktop to the front in `common_boot` before `guest.sh`, as `terminal_path` does. I did not change it here because the rehearsal's bindings cover `owner_vm.py`, and the qualification is not rehearsed in this package.
- **Organization billing check:** package 14's reviewed SKU list stops on the org's new macOS SKU (another repo) and on a 1e-8 storage rounding value; any package that still uses the local billing read needs that list reviewed.
- **Old evidence that names release 13 as current** (package 15e's login policy, the retained 13f machines) stays release 13's; tests now read `os/manifest/releases/13.json` for it.

- **Stop masking the two staging finalizers in the image (next release).** Remove `ostree-finalize-staged.service` and `bootc-finalize-staged.service` from `os/policy/masked-system-units.txt`, review them in `updater-allowlist.json`, and keep `image-checks.sh` and `guest.sh` in step. Fresh installs then match updated laptops (JUDGMENT-CALL 11).
- **Package 22 had no VM run of `at update` from a running AresOS**; the masked finalizer showed only in this rehearsal.
- **The VM harness sees a booted guest only through its serial console**, so a stalled console looks the same as a
  hung boot (runs 6 and 12; see E). The installed VM now pins the console so systemd does not probe it, and a boot
  that never shows `login:` records diagnostics. The root cause of the hang in the probe stays unproved; if it
  comes back, those diagnostics are where to start.
- **Known limits after review 4 (harness or scope only; no laptop impact):**
  - The injected-stop-failure test (`UpdateStopTest`) can leave the stage-then-run fixture's `sleep 3600` child
    running, because the cleanup kills only recorded PIDs. Fix later: keep the fixture's session and empty it.
  - `Host.script()` catches exceptions from its stop calls, but is not exception-proof around `wait()` or its
    diagnostics for the other release steps. The update itself goes through the protected `Host.start()`/`Step` route.
  - `/proc` text decoding elsewhere: `deployment_processes` (pause-stock-updates.sh, pin-stock.sh) decodes argv as
    UTF-8, but only for selected bootc, rpm-ostree and ostree processes, so an unrelated process cannot refuse the
    update. A failure there reaches the STOP handler (`UnicodeDecodeError` is a `ValueError`) and cannot skip the
    stop or the masks. Parse it as bytes in a later package, as the stop routine now does.
- **Known limits after review 5 (harness only; no laptop impact; the other two were fixed after run 13):**
  - A failure inside the boot-stall diagnostics (for example `td.save()`) can replace the boot's original
    `TimeoutError`. The run still fails; only the diagnosis suffers. Fix later: wrap the whole diagnostic call and
    re-raise the original.
  - Late terminal replies have no consumption acknowledgement and could in theory reach serial login input. That
    would fail a run, never pass one, and pinning the console removes those probes on the installed boots.
- **Known limit after review 6 (harness only; no laptop impact):** in `pin_serial_console`'s cleanup, an
  `umount`, `rmdir` or `losetup --detach` failure can replace the original exception as the primary error. The
  exception chain keeps the original, and a run cannot pass because of it. Injected `umount`, `rmdir` and detach
  failures are untested. Fix later: keep the original error and collect cleanup errors as secondary.
- **Known limit (harness only; no laptop impact):** the checks-only job checks out with depth 1, so the tests that
  read older commits cannot run there (checks-only run 43336083190, see Verified). Fix later: `fetch-depth: 0` on
  that job's checkout.

## Open questions

- None beyond the JUDGMENT-CALLs for the owner (1 and 2 above).

## Budget

The repo is public, so every run used standard GitHub-hosted runners at no cost. Nothing needed a paid runner or other spending. GHCR received one private publish; nothing was deleted.

The brief planned one build-and-publish, one checks-only run and three rehearsals. Each release dispatch after the first was approved by the integrator, who raised the cap to 3, then 4, then 5. The update cap went from 3 to 5, then one at a time to 15, each raise integrator-approved (see E).

| # | Run | Kind | Head | Result |
|---|---|---|---|---|
| 1 | [42807087845](https://github.com/Ares-Empire/AresOS/actions/runs/42807087845) | release | `1b17080e` | failed: second VM pass could not read filesystem types on a reused `/dev/nbd0` (JUDGMENT-CALL 9) |
| 2 | [42817411051](https://github.com/Ares-Empire/AresOS/actions/runs/42817411051) | release | `8fc6e350` | stopped by the image diff before publish: `/etc/sudoers.d` 0755 (fixed in build.sh) and 12 paths without an exact rule |
| 3 | [42831158090](https://github.com/Ares-Empire/AresOS/actions/runs/42831158090) | release | `e2c14696` | failed: Ubuntu snapshot mirror HTTP 500 while installing host tools |
| 4 | [42835704653](https://github.com/Ares-Empire/AresOS/actions/runs/42835704653) | release | `31da87f9` | failed: snapshot mirror HTTP 504 (JUDGMENT-CALL 10) |
| 5 | [42842793096](https://github.com/Ares-Empire/AresOS/actions/runs/42842793096) | release | `b216f28f` | **passed and published** release 27 (the one publish) |
| 6 | [42924871252](https://github.com/Ares-Empire/AresOS/actions/runs/42924871252) | update rehearsal 1 | `87990bc1` | failed after 11 minutes, before any download or VM: `owner_capabilities.py` still allowed only probe and owner-tools (fixed, with `UpdateJobGatesTest`) |
| 7 | [42933781975](https://github.com/Ares-Empire/AresOS/actions/runs/42933781975) | update rehearsal 2 | `35e58911` | every pre-VM step passed, then it failed 3 minutes into the VM: `installer_webui.py` opened the WebUI transport only for packages 14 and 16 (fixed, with `OwnerHarnessPackagesTest` and `VmStepDecisionsTest`) |
| 8 | [42940741765](https://github.com/Ares-Empire/AresOS/actions/runs/42940741765) | update rehearsal 3 | `fb06ccde` | reached step 8 (install, stock, switch to R13 with the laptop tools, tools update to v2 all passed; every disk audit unchanged), then `at update` failed: the image masks `ostree-finalize-staged.service`, which bootc needs to stage (fixed, JUDGMENT-CALL 11) |
| 9 | [42973044866](https://github.com/Ares-Empire/AresOS/actions/runs/42973044866) | update rehearsal (guard stop) | `194372ec` | stopped in the guard's first step after about 1 minute: the update cap was still 3 (raised to 5 in fd7d9895) |
| 10 | [42974982988](https://github.com/Ares-Empire/AresOS/actions/runs/42974982988) | update rehearsal 4 | `e3a67619` | **`at update` staged R27 from R13, then title and reboot; R27 booted**, with every disk audit unchanged. It then failed at the first R27 console login: the harness login observer (`os/ci/owner_login.py:148`) accepts only util-linux 2.41.5, and R27 has 2.41.6 (package 21 JUDGMENT-CALL 4). Next: compare v2.41.5..v2.41.6 for login.c and agetty.c, let the observer accept both versions, raise the cap to 6, then run 5 |
| 11 | [43120759117](https://github.com/Ares-Empire/AresOS/actions/runs/43120759117) | update rehearsal 5 | `9ee933d9` | passed the R27 console login (util-linux 2.41.6), check, title, records and public typing; stopped at the terminal PATH probe (keys typed right after the VT switch; fixed) |
| 12 | [43136407300](https://github.com/Ares-Empire/AresOS/actions/runs/43136407300) | update rehearsal 6 | `5335f8a4` | R27's boot after `at update` froze both consoles after systemd's serial terminal probes (an observed VM stall, see E); unchanged rerun |
| 13 | [43148798803](https://github.com/Ares-Empire/AresOS/actions/runs/43148798803) | update rehearsal 7 | `dd7da09e` | passed R27's boot, login, terminal PATH and guest.sh; stopped at the homebrew check (brew refuses an unreadable working directory; fixed) |
| 14 | [43160633763](https://github.com/Ares-Empire/AresOS/actions/runs/43160633763) | update rehearsal 8 | `f708c53f` | stopped in the hosted unit step on a flaky test (fixed), before any VM |
| 15 | [43173190284](https://github.com/Ares-Empire/AresOS/actions/runs/43173190284) | update rehearsal 9 | `976d0334` | passed through `sudo passwd ares`, his tty4 login and sudo, and every package 21 rule but the `passwd -S` format check (fixed) |
| 16 | [43188392249](https://github.com/Ares-Empire/AresOS/actions/runs/43188392249) | update rehearsal 10 | `5f3fd6b1` | stopped before any VM work: snapshot.ubuntu.com answered 503 (a mirror outage) |
| 17 | [43219365492](https://github.com/Ares-Empire/AresOS/actions/runs/43219365492) | update rehearsal 11 | `33498543` | timed out after 40 minutes installing the pinned tools from the slow mirror, before any VM work |
| 18 | [43277139615](https://github.com/Ares-Empire/AresOS/actions/runs/43277139615) | update rehearsal 12 | `bf2dd553` | stock Bazzite's first installed boot hung in systemd's serial console size probe (as run 6); fixed by pinning the VM's console |
| 19 | [43293692038](https://github.com/Ares-Empire/AresOS/actions/runs/43293692038) | update rehearsal 13 | `761d9ae7` | stopped after 11 minutes in the hosted regression tests, before any VM work: the new serial console pin scanned partitions without the shared loop wait (fixed) |
| 20 | [43302603386](https://github.com/Ares-Empire/AresOS/actions/runs/43302603386) | update rehearsal 14 | `c9072528` | **passed**: tools update, `at update`, title, reboot, R27 confirmed, `sudo passwd ares`, his sudo, package 21's rules, `at previous` confirmed, the forward update refused, every audit unchanged |
| 21 | [43336083190](https://github.com/Ares-Empire/AresOS/actions/runs/43336083190) | checks-only | `29440cfd` | 932 tests, no failures, 9 errors: all reads of older commits that its depth-1 checkout lacks (see Verified); the same suite passed with full history in run 14 and locally |
| | | | | |
| | **Total** | | | 5 release dispatches (1 publish), 15 update dispatches (14 rehearsals and 1 guard stop), 1 checks-only run; 982 of 1200 minutes |
