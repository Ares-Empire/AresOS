# 21 REPORT: Everyday account like Windows, Chrome, daily-use fixes

Built by a Claude agent (Opus 5.5). Brief: `briefs/21-everyday-account-and-chrome.md` (empire board brief 262).
Branch `pkg/21-everyday-account-and-chrome`, PR #31. Review: Codex gpt-6-astra (high), fresh context.

Nothing was pushed, signed or published to a registry. The release pin is unchanged.

## Done

### A. The everyday account `ares`

- **wheel** (`os/config/usr/lib/sysusers.d/aresos.conf`): `m ares wheel`. Boot-time sysusers adds `ares` to the
  laptop's existing `/etc/group` and `/etc/gshadow` and leaves passwd/shadow alone. The image still locks the
  password, so `sudo` fails and auto-login is unchanged until the owner sets one (package 22's guide).
- **sudo** (`os/config/etc/sudoers.d/aresos-everyday`, mode 0440): `Defaults:ares timestamp_timeout=0` (since the
  review fixes; it was `timestamp_type=ppid`). Fedora's `%wheel ALL=(ALL) ALL` asks for his own password, every time:
  sudo keeps no ticket, so nothing can reuse a password he typed (JUDGMENT-CALL 2). `build.sh` fails on any
  `NOPASSWD` or `!authenticate` rule left after the old updater-grant cleanup, and runs `visudo --check`.
- **polkit** (`os/config/usr/share/polkit-1/rules.d/00-aresos-maintenance.rules`, sorts first):
  - Denied to `ares` even with the password: `org.projectatomic.rpmostree1.*`, `org.freedesktop.sysupdate1.*`,
    `org.freedesktop.fwupd.*`, `org.bazzite.*`, modem firmware, logind's next-boot and firmware-setup choices
    (`set-reboot-to-firmware-setup`, `set-reboot-to-boot-loader-entry`/`-menu`, `set-reboot-parameter`; added in the
    review fixes), and starting `uupd.service`/`uupd-manual.service` (the base's `uupd.rules` lets anyone start
    them; they stay masked anyway).
  - The base ships rules that let any wheel member act **without a password**. For `ares` these now ask for it
    (since review 2: each action's own uncached default per session kind, in `aresosWheelGrantDefaults`; it was
    `AUTH_ADMIN_KEEP`): Flatpak app/runtime install and uninstall, gvfs admin file operations
    (`org.gtk.vfs.file-operations-helper`, in effect root file access), NetworkManager system connections,
    firewalld configuration, Thunderbolt (bolt), CoreCtrl's helper and KDE's clock (JUDGMENT-CALL 3).
  - The old denies on all Flatpak actions and on `manage-unit-files` are gone; those follow their defaults, which
    ask for his password.
- **Flatpak**: `flatpak` is no longer `chmod 0700`. `flatpak-system-helper.service` (system) and
  `flatpak-portal.service` and `flatpak-session-helper.service` (user) are unmasked and reviewed by name in
  `os/policy/updater-allowlist.json`. Every automatic Flatpak, Homebrew and OS updater stays masked. This also ends
  the `/etc/profile.d/flatpak.sh: Permission denied` message and the failing `60-flatpak` user generator.
- **OS updaters stay root-only**: `uupd ujust topgrade bazzite-updater bazzite-portal bazaar plasma-discover
  gnome-software` keep `0700`. About **Bazaar**: its RPM requires `libflatpak` and nothing from rpm-ostree or bootc,
  so it manages Flatpaks and can't change the OS image. It also ships a `bazaar-daemon` that could update apps in the
  background, so it stays blocked as the brief says.
- **Homebrew** (JUDGMENT-CALL 1): the inherited prefix stays owned by the stock UID 1000 administrator.
  `aresos-inherited-homebrew.conf` now grants `u:1001:r-x`; tmpfiles `a+` turns the laptop's existing
  `u:1001:---` deny into that grant at the first boot of the new image. New `/usr/bin/brew` runs read-only commands
  (`--version`, `list`, `info`, `search` and similar) directly and everything else as the prefix owner with
  `sudo -u '#1000' -H`, which asks for his own password. `HOMEBREW_NO_INSTALL_FROM_API` is removed (without a tapped
  core, Homebrew can't install with it set); `HOMEBREW_NO_AUTO_UPDATE=1` stays.
- **Rootless containers**: sysusers-made accounts get no `/etc/subuid`/`/etc/subgid` ranges, and the installer's
  local copies survive image updates. New `/usr/libexec/aresos-subids` and `aresos-subids.service` (enabled, before
  user sessions) add one free 65536-ID range for `ares` to whichever file lacks one and never change an existing
  entry. The image itself gets `ares:524288:65536`.
- **Polkit agent**: the base image's KDE agent, `/usr/libexec/kf6/polkit-kde-authentication-agent-1`, starts from the
  labwc autostart before the terminal.
- **PATH** (`/etc/profile.d/aresos.sh`, for his login and interactive shells, AresOS terminals included):
  `~/.local/bin`, then `/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin`, then Homebrew's `bin`/`sbin` and the
  user and system Flatpak export bins when they exist. System commands stay ahead of Homebrew's. Since review 5 the
  session itself (greetd's wrapper, `aresos-session`, labwc and what it starts) keeps the system PATH and runs only
  absolute paths, so nothing in `~/.local/bin` can take away the desktop or its recovery terminal.
- **Terminal** (`aresos-terminal`, `/usr/share/aresos/bashrc`): after the banner and the AresOS prompt, his own
  `~/.bashrc` is sourced, so his settings win. A syntax error in it ends only that `source`. The recovery terminal
  (Super+Ctrl+Escape, now `aresos-terminal --recovery`) never reads it (JUDGMENT-CALL 5).
- **foot**: `/etc/xdg/foot/foot.ini` sets `font=monospace:size=16`, the value he chose in real use. foot reads only
  the first `foot.ini` it finds, so `~/.config/foot/foot.ini` still replaces it.
- **Tools and keys**: `script` (`util-linux-script`), `qrencode` and `brightnessctl` in `os/packages.lock.json`
  (JUDGMENT-CALL 4 covers the util-linux upgrade this forces). `rc.xml` binds `XF86MonBrightnessUp/Down` to
  `brightnessctl` (5 % steps, never below 1) and `XF86AudioRaiseVolume/LowerVolume/Mute/MicMute` to `wpctl` (volume
  capped at 100 %). No backlight kernel argument (21b).

### B. Google Chrome

- **Pin** (`os/google-chrome.lock.json`): `google-chrome-stable-157.0.8103.50-1.x86_64`, its `dl.google.com` URL,
  SHA-256 `e378bf27…e3d5` (equal to Google's own repository metadata), and Google's public key
  `os/keys/google-linux-signing-key.pub` (SHA-256 `54dea5f6…b27c`, primary fingerprint
  `EB4C1BFD4F042F6DDDCCEC917721F63BD38B4796`; the RPM is signed by its subkey `FD533C07C264648F`, valid to 2028).
- **Package step** (`os/build.sh packages`): the Fedora discipline is unchanged (download --resolve from
  `fedora`/`updates` only, exact set and hashes; a mismatch now also prints the actual resolution). Chrome comes only
  from its pinned URL. The build checks the key file's hash, the RPM's hash and NEVRA, imports the key, and requires
  `rpmkeys --checksig` to report `key fingerprint: eb4c1bfd…4796: OK` with every other line OK. Chrome and the
  locked Fedora RPMs then install in one `dnf5` transaction with all repositories disabled and
  `localpkg_gpgcheck=True`. Chrome's only Fedora dependency, `liberation-fonts-all`, is in the lock. Afterwards
  `rpmkeys --delete` removes the key again, so the image trusts no new key.
- **`/opt` on bootc**: Chrome's files move from `/var/opt/google` to `/usr/lib/opt/google` (rpm-ostree's own
  convention) and `/var/opt` is removed from the image. `/usr/bin/google-chrome-stable` and `google-chrome` point
  straight there (the alternatives entry is removed), so Chrome works after an image switch without any `/var`
  content. `aresos-google-chrome.conf` links `/var/opt/google -> /usr/lib/opt/google` at every boot for anything
  that names `/opt/google`.
- **No side updater**: `/etc/default/google-chrome` sets `repo_add_once="false"` before install, so Chrome's install
  script adds no repository, and the build fails if a Google repository file appears anyway.
  `/etc/cron.daily/google-chrome`, which would re-add the repository and key, is deleted. The base has no cron
  daemon either.
- **Links**: `/usr/share/applications/aresos-mimeapps.list` makes Chrome the default for http, https and HTML in the
  AresOS session (`XDG_CURRENT_DESKTOP=AresOS`); his own `~/.config/mimeapps.list` wins. `/etc/opt/chrome/policies`
  is left alone for the control layer.

### C. Verification code

- `os-image.yml`: new `check_build` input (`resolve` | `build`) and job with `permissions: contents: read` and no
  secrets, so it can't push, sign or publish. Evidence artifact `check-build-evidence`, kept 3 days.
- `os/ci/check-build.sh`: `resolve` inventories the pinned base and resolves package inputs (`check-resolve.sh`);
  `build` builds `os/Containerfile` into runner storage and runs `check-image.sh`.
- `os/ci/image-checks.sh` runs inside the built image (22 PASS lines). `os/ci/check-image.sh` adds a rootless podman
  probe for `ares` and `os/ci/polkit-check.js` with `polkit-review.json`: it evaluates the image's real polkit rules
  for `ares` with and without wheel, in polkitd's order, and fails on any OS-change action that isn't denied and on
  any action that becomes passwordless only because of wheel. The same evaluation without the AresOS rule must fail.
- New `os/tests/test_everyday_account.py`: subid ranges, terminal and `~/.bashrc`, PATH, policy files, keys, foot,
  Chrome pin and build steps, lock contents.
- **Tests changed to pin the new decision** (none deleted or skipped):
  - `test_sysusers`: expects `ares` in wheel (group and gshadow), still locked, idempotent; new test that an
    existing `ares` joins wheel on upgrade without passwd/shadow changes.
  - `test_inherited_homebrew`: expects `u:1001:r-x` (read and run, never write) with owner and content unchanged;
    new test that the earlier `u:1001:---` entry is replaced.
  - `os/tests/guest.sh` (VM policy): `ares` in wheel with `(ALL) ALL` and `timestamp_timeout=0`, no passwordless
    rule, `sudo -n` failing; `flatpak` and `brew` executable; the other updaters still not.
  - `os/tests/inherited-homebrew.sh` (switch and rehearsal VMs): `ares` reads and runs the inherited brew, can't
    write the prefix, finds `/usr/bin/brew` and Homebrew on the login PATH, sees the system PATH in the labwc
    session (review 5), and an install without a password fails before brew runs.
  - `test_shell_assertions`: the guest-policy and Homebrew-login cases follow those scripts.
  - The updater audit (`audit.py`) is unchanged; only its policy lists changed, as in A.
- Bound sources: `.github/workflows/os-image.yml` is bound by the package 16 walk. Its new checkout bytes are in
  `os/manifest/ci/16/pending-rebind.json`, generated with `checkout_sources.records`.

### D. Docs

- `docs/design/DESIGN.md`: both owner decisions, with the date and his words.
- `docs/design/OS-BASE.md`: a dated revision at the top that supersedes the locked daily account, plus notes at the
  section 8 account split and the A1 daily-account rule.
- `os/README.md`: the account, the Homebrew route, the Chrome pin and the `check_build` path.

## Verified

CI runs on this branch (`https://github.com/Ares-Empire/AresOS/actions/runs/<id>`):

| Run | What | Result |
|---|---|---|
| 42700611570 | `check_build=resolve`: base inventory, Chrome repository metadata, signature, requires | Done. Showed `util-linux-script` exists only as 2.41.6 and Chrome lacks only `liberation-fonts`. |
| 42702327832 | `resolve` with the exact transaction | 25 packages; the 10 existing pins resolved to identical hashes; install preview clean. Committed as the lock. |
| 42704153862 | `check_build=build` | Image built; Chrome checksig `key fingerprint: eb4c1bfd…4796: OK`; lint 11 passed, 3 warnings. The checks stopped at the first `runuser` (no PAM session in an unprivileged container). Fixed: checks run `--privileged`. |
| 42706256548 | `build` | All 22 in-image checks, the rootless probe and the polkit evaluation passed; a final byte comparison of the lock failed (build.sh re-serializes it). Fixed: JSON comparison. |
| 42709631386 | `build` plus one VM boot (since reverted) | Container checks passed again. The VM booted this image: guest policy passed (`Daily account is in wheel`, the sudo policy, `sudo: a password is required`, flatpak and brew executable, live updater audit `1087 system/user units inspected`, `ARESOS_GUEST_CHECKS_PASSED`); power events, the recovery shortcut and the tty3 recovery login passed; `aresos-subids.service` finished at boot. It then stopped in `vm.py`'s journal readiness wait, a pre-existing harness bug (PLAN-GAP). Evidence: `runs/vm-42709631386/`. |
| **42715519293** | **final `build` on `e05b97fd`** | **Success.** `IMAGE_CHECKS_PASSED` with 22 PASS lines, `ROOTLESS_MAPPING_PASSED` (`0 1001 1`, `1 524288 65536`), `polkit: 21 rule files, 401 actions, 0 change with wheel, 57 denied to ares`, `POLKIT_CHECK_PASSED`, the check without the AresOS rule fails as expected, manifest locks equal, `CHECK_BUILD_PASSED`. Evidence: `runs/build-42715519293/`. |
| 42718023916 | `checks_only=true` on `e05b97fd` (full suite natively, with sudo) | 712 tests, 2 failures, both in `test_sysusers`: systemd-sysusers writes wheel members sorted (`ares,ares-recovery`). Fixed the tests to compare membership. `test_inherited_homebrew` passed natively. |
| **42718699822** | **`checks_only=true` on `20ff4bce`** | **Success.** `Ran 712 tests` `OK` natively with sudo, including `test_sysusers` (both tests), `test_inherited_homebrew` (all four) and `test_everyday_account`; Python compile and Bash syntax sweeps, the live hosted system-manager query (`437 unit files, 473 unit names`), release-input resolution and the upstream signature check passed. |

The 22 in-image PASS lines of the final build (`runs/build-42715519293/checks.txt`) cover:

- `ares` is in wheel; the image sets no password for it (`!*`); `sudo -l` shows `(ALL) ALL` with
  `timestamp_type=ppid` and no passwordless rule; `visudo` parses; `sudo -n true` as `ares` says
  `a password is required`.
- `uupd`, `ujust`, `topgrade`, the Bazzite updater/portal and the stores are not executable by `ares`; `flatpak` and
  `brew` are; every policy mask holds; the Flatpak helpers are not masked; the static updater audit passes.
- Chrome's NEVRA matches its pin; every packaged `/opt` file is under `/usr/lib/opt`; `google-chrome --version` as
  `ares` prints `Google Chrome 157.0.8103.50`; tmpfiles links `/opt/google`; no Google repository, cron job or trusted
  key; `xdg-mime` gives `google-chrome.desktop` for http and https in the AresOS session; `/etc/opt/chrome/policies`
  can be created.
- The daily login PATH is `/var/home/ares/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin`, plus
  `/home/linuxbrew/.linuxbrew/bin` and the user Flatpak export bin when they exist, with nothing printed to stderr;
  the `60-flatpak` generator runs cleanly; on an inherited prefix carrying the old deny, tmpfiles turns it into
  `user:1001:r-x`, `brew --version` runs directly, and `brew install` goes to `sudo` as the owner and fails without a
  password before brew runs.
- foot size 16; the polkit agent exists and is autostarted; the six key bindings point at executables and at keysym
  names libxkbcommon knows; `script`, `qrencode` and `brightnessctl` run; `ares` has `ares:524288:65536` in both
  files and the enabled subid service changes nothing on a second run.

WSL (Ubuntu 24.04, pushed branch cloned into `/tmp`, `python3 -m unittest discover -s os/tests`):

- Full suite on `3b1f8f5f`, plain and with `-B`: both `Ran 712 tests`, `FAILED (failures=1, errors=12)`. Every
  failure is in the known WSL-only suites, all with `sudo: a password is required`: `test_greeter` 3 errors,
  `test_inherited_homebrew` 1 failure + 7 errors, `test_sysusers` 2 errors. All other suites pass, including
  `test_checkout_sources`, `test_everyday_account` and `test_shell_assertions`.
- Before/after for the two touched WSL-only suites (`-B`, focused): main `87ff8731`: `test_sysusers` 1 test, 1
  error; `test_inherited_homebrew` 3 tests, 1 failure + 5 errors. Branch: `test_sysusers` 2 tests, 2 errors;
  `test_inherited_homebrew` 4 tests, 1 failure + 7 errors. The growth is the two new tests. Both suites run natively
  in CI (above).
- Focused on `e05b97fd`, after the later build.sh and CI-script commits: `test_everyday_account` 24 OK,
  `test_shell_assertions` 8 OK, `test_checkout_sources` 4 OK. A second full WSL run was not started: free memory stayed between 1.5 and 2.6 GB while the owner played, below the 4 GB rule; the native CI run above covers the same suite.

Local: `node os/ci/polkit-check.js` on the base inventory's rules (Windows, Node 24) passed with the AresOS rule and
failed without it, listing the 17 wheel-only grants. The `/usr/bin/brew` logic ran against a temporary prefix in WSL:
read-only commands ran directly, `install` went to `sudo -u '#1000'`, a missing prefix exited 127.

## Not verified (needs the laptop or a human)

- A real labwc session on the laptop: the KDE polkit agent's dialog and his password in it; GUI Flatpak installs.
  The VM boot showed the session and terminals, not the agent's window.
- Setting the password (`sudo passwd ares` as `ares-recovery`, package 22's guide), then real `sudo` on the laptop
  and `brew install` through the owner with the real Homebrew 7.0.9. CI used a stand-in brew script, a fixture UID
  1000, and a throwaway password set only inside the check container.
- The updated laptop's own `/etc`: sysusers adding `ares` to an existing wheel line and the subid service writing next
  to `ares-recovery`'s ranges are covered by tests, a fresh image and a fresh VM, not by an updated installed system.
- Real rootless podman and distrobox containers (CI proved the user-namespace mapping only).
- Chrome's window on NVIDIA/Wayland, signing in, and `xdg-open` from foot's URL mode or Claude Code's sign-in.
- Brightness keys (no backlight device until 21b) and the volume, mute and mic keys on the real keyboard.
- The util-linux 2.41.6 upgrade under the owner tools on the laptop (PLAN-GAP).

## JUDGMENT-CALL

1. **Homebrew: run it as its stock owner through `sudo`.**
   - Chosen: the prefix stays UID 1000's, so a rollback to stock keeps a fully working Homebrew. `ares` reads and
     runs it; `/usr/bin/brew` runs mutating commands as UID 1000 after `sudo` asks for his password. Homebrew's own
     docs suggest this shape for shared machines (a role account owns `/home/linuxbrew`).
   - Rejected: chown the prefix to `ares` (breaks `ares-recovery`'s Homebrew after a rollback); shared group or ACL
     write access (Homebrew assumes one owner: chmod by a non-owner fails, git refuses "dubious ownership", files
     drift between owners); a second prefix in his home (no bottles, so everything compiles, and the image has no
     compiler).
   - Cost: every `brew install` or `upgrade` asks for his password, and Claude can't install brew packages alone.
     Homebrew runs as `ares-recovery`, which his password already allows. Relative paths given to brew resolve from
     the prefix, not from his directory.
   - Reversal: delete `/usr/bin/brew` and the tmpfiles line; `sudo setfacl -x u:1001 /var/home/linuxbrew`.
2. **sudo asks for his password every time (`timestamp_timeout=0`).** Corrected in the review fixes.
   - The first version used `timestamp_type=ppid` and claimed Claude Code couldn't reuse a typed password. That was
     wrong: a program started from his shell can `exec sudo -n …`, keep the shell as sudo's parent and reuse the
     ticket, as sudo documents. The in-image check now proves the reuse under the old setting and its refusal under
     the new one.
   - Chosen: no ticket at all, like Windows' Yes prompt. Every `sudo`, and so every `brew install`, asks for the
     password; for several admin steps in a row he can use one `sudo -s` or `sudo bash -c '…'`.
   - Rejected: sudo's default per-terminal ticket and the per-parent ticket (both reusable by a program he starts).
   - Limit: Claude runs as `ares` and can edit his dotfiles, so a password typed into a shell Claude has tampered with
     could be captured. That holds for any agent running as the same user; no sudo setting fixes it.
   - Reversal: delete `/etc/sudoers.d/aresos-everyday`.
3. **Upstream "wheel without a password" rules ask `ares` for it.**
   - Chosen for every action listed in A, including system-wide NetworkManager connections and system-wide Flatpak
     installs. `flatpak --user` installs need no password, and Flatpak app updates stay passwordless as for any
     active user.
   - Rejected: keeping the passwordless grants (Claude could then write any file as root through gvfs admin,
     reconfigure the firewall or add a VPN).
   - Cost: a password prompt when he saves a new Wi-Fi as a system connection or installs a system-wide Flatpak.
   - Reversal: remove names from `aresosWheelGrantDefaults`; `polkit-check.js` then lists them for review.
4. **`script` moves the util-linux family from 2.41.5 to 2.41.6.**
   - Fedora `updates` no longer carries `util-linux-script-2.41.5-1.fc44`; the only one is 2.41.6-1.fc44, which needs
     the matching `util-linux-core`. The lock therefore upgrades 11 base packages: `util-linux`, `util-linux-core`,
     `libblkid`, `libmount` and `libuuid` (x86_64 and i686), `libfdisk`, `libsmartcols`, `liblastlog2`. Kernel and
     NVIDIA packages are unchanged (the build's driver comparison passed).
   - Rejected: Fedora's Koji archive for the exact 2.41.5 build (a new source outside the lock discipline, and Koji
     serves unsigned copies by default); dropping `script`.
   - Cost: the owner tools parse util-linux output (`lsblk`, `blkid`, `sfdisk`). A patch release rarely changes
     formats, but the release rehearsal must exercise them on this image.
5. **The recovery terminal skips his `~/.bashrc`**, so Super+Ctrl+Escape always gives a plain shell. Rejected:
   reading it there too (a broken file would take away that escape route). Reversal: one line in `rc.xml`.
6. **Chrome's place and trust.** `/usr/lib/opt/google` with direct `/usr/bin` links and a boot-time `/opt` link
   (rpm-ostree's convention). Rejected: making `/opt` a real image directory (it would hide other `/var/opt` content)
   or relying on copies in `/var`. Google's key is used only during the build and not left trusted.
7. **Small defaults**: foot size 16 (his own value; 12 to 14 would also read well); Chrome as the default browser
   through a desktop-specific list; `flatpak-oci-authenticator.service` and the NVIDIA Flatpak runtime sync stay
   masked (Flathub apps need neither).

8. **No polkit authorization is cached, for any account** (review fixes 2).
   - Chosen: rewrite the installed defaults, so no process can reuse an authorization, for any action, parameters or
     account. This was simpler and more complete than a 227-entry per-action table in the rule, and CI keeps it whole.
   - Cost: every privileged step asks again. A system-wide `flatpak install` can ask once for the runtime and once for
     the app; `systemctl restart x` asks each time; `ares-recovery` loses caching too. `flatpak --user` installs need
     no password.
   - Reversal: drop the rewrite in `build.sh`; `polkit-check.js` then reports every cached default.

9. **His PATH is for his shells; the session keeps the system PATH** (review fixes 5).
   - Chosen: `~/.local/bin`, Homebrew and the Flatpak export bins are on the PATH of his login and interactive shells,
     AresOS terminals included. greetd's non-interactive profile wrapper, `aresos-session`, labwc and everything labwc
     starts get `/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin`, and the startup scripts run only absolute paths.
   - Rejected: giving labwc his PATH and pinning only our own commands. labwc's `sh` autostart, dbus-run-session's
     `dbus-daemon` lookup and the base image's profile scripts would still look things up in `~/.local/bin`.
   - Cost: a program labwc itself starts (today only the terminals and the polkit agent; later keybinds or a launcher)
     doesn't see `~/.local/bin` or Homebrew unless started from a terminal.
   - Reversal: set the daily PATH in `aresos-session` again; the CI shadow check then shows what it exposes.

10. **Renew a vanished Fedora pin: `xdg-desktop-portal-wlr` 0.8.4 to 0.8.5** (review fixes 6).
    - Fedora 44's updates repository replaced 0.8.4 with 0.8.5 on 2026-11-10, so no build could use the old pin.
      The lock moves only this package, a patch release of the wlroots screen-sharing portal; the build still checks
      the resolved set, the bytes and Fedora's signature.
    - Rejected: Fedora's Koji archive for the exact 0.8.4 build (as in JUDGMENT-CALL 4, a source outside the lock
      discipline) and leaving the throwaway build broken.
    - Cost: a portal version that real use hasn't seen yet; the release rehearsal exercises it.
    - Reversal: none while Fedora serves only 0.8.5; a later pin renewal moves it again.

## PLAN-GAP

- **`vm.py` couldn't pass its power-key step since package 14** (fixed in review fixes 3). It now searches the serial log through
  `strip_kernel_lines`, which also removes the journal follower's `short-monotonic` lines, because they start with the
  same `[   73.458055] ` prefix as kernel records (`runs/vm-42709631386/serial-journal-ready-excerpt.txt`).
  `vm.py` last ran for package 13, before that change. Suggested fix for the release package: also accept the token
  in the raw transcript, or match it only after a `bazzite aresos-ci[` prefix. `vm.py` is a bound release-harness
  file, so this package didn't change it. Commit `fc74f8ba` shows how `check_build=build` can boot one VM pass once
  it is fixed.
- **Releases**: `verify_release.py` refuses a rehearsal or switch-only run when `os/config`, `os/policy` or the lock
  differ from the pinned release's source. After this merges, those runs on main stop there until the release
  package builds and pins a new image. That's by design, but the release package must plan for it.
- **Pins expire**: `dl.google.com` keeps a Chrome RPM only for a while, and Fedora `updates` drops superseded builds.
  Either makes a later build fail closed; the release package will probably start with `check_build=resolve` to
  renew the pins.
- **Package 22** also changes package-16-bound files, so `pending-rebind.json` will need a hand merge. Its guide
  should set the password with `sudo passwd ares` as `ares-recovery`, and can say that the old Homebrew deny entry is
  replaced at the first boot of the new image.
- The updater audit covers systemd units only, not cron; Chrome's cron job is checked explicitly instead.
- The labwc session's `XDG_DATA_DIRS` lacks Flatpak's export share directories (only login shells get them from
  `flatpak.sh`), so Flatpak apps may not appear as `xdg-open` handlers in the session. Not asked here.
- The base's `empower.rules` gives every polkit action to members of a group `empower`; `ares` isn't a member.
- `bootc container lint` passes with 3 warnings (leftovers of the package step's dnf in `/run` and `/var`); not
  compared with earlier builds.
- `.work/` holds nothing: no large downloads were kept on the laptop.

## Open questions

- None blocking. The JUDGMENT-CALLs above go to the owner before merge.

## Review fixes (review 1: CHANGES-NEEDED at `80458b47`; brief `21-review-fixes.md`)

Owner question board #156 is still open, so its points keep their current behaviour: Homebrew through UID 1000, and
system-wide Wi-Fi and Flatpak installs asking for the password.

1. **Blocker: sudo password reuse.** Fixed.
   - `aresos-everyday` is now `Defaults:ares timestamp_timeout=0`: every `sudo` asks for his password and sudo keeps
     no ticket. The review was right that `timestamp_type=ppid` let a program started from his shell `exec sudo -n`
     and reuse the shell's ticket; JUDGMENT-CALL 2 is corrected above.
   - New in-image test (`os/ci/image-checks.sh`): inside the check container only, `ares` gets a throwaway password
     (read from a 0600 file, kept out of the trace). One shell authenticates with `sudo -S`, then a child keeps that
     shell as sudo's parent and runs `exec sudo -n true`. Control first: with the old `timestamp_type=ppid` ticket the
     child gets in, so the probe can see reuse. Then, with the image's real setting, the child is refused with
     `a password is required` (exit 1, not the probe's own 90). The account is locked again afterwards.
   - `guest.sh`, its shell-assertion fixture, `test_everyday_account`, `os/README.md` and OS-BASE follow
     `timestamp_timeout=0`.
2. **Blocker: passwordless boot and firmware control.** Fixed.
   - `00-aresos-maintenance.rules` now denies `ares` outright, with or without the password:
     `org.freedesktop.login1.set-reboot-to-firmware-setup`, `set-reboot-to-boot-loader-entry`,
     `set-reboot-to-boot-loader-menu`, `set-reboot-parameter` (all `allow_active=yes` by default, so `yes` in the
     earlier evidence) and `org.freedesktop.ModemManager1.Firmware` (modem firmware; `auth_admin` before). No other
     boot or firmware action was `yes` in the evidence. Power off, reboot and suspend are unchanged.
   - `polkit-check.js` now requires `no` both with and without wheel for the OS-change prefixes, for the new
     `denied_actions`, and for any action whose name matches a boot/firmware pattern
     (`firmware|boot-?loader|reboot-to|reboot-parameter|bootconfig|bios|kargs`), because inherited defaults never
     show up as a wheel difference. `polkit-review.json` pins power-off, reboot and suspend as still passwordless.
   - Checked locally against the real rules extracted from run 42715519293's image: the previous rule fails on
     exactly these five actions; the new rule passes (62 actions denied to `ares`).
3. **Should-fix: `foot` through PATH.** Fixed. `aresos-terminal` runs `/usr/bin/foot` with `/usr/bin/bash`.
   - New tests: `test_everyday_account` runs the real wrapper, normal and recovery, with a broken `foot` first on
     PATH and checks it never runs; `image-checks.sh` replaces `/usr/bin/foot` in the check container with a
     recording stand-in, puts a broken `foot` in `~/.local/bin` (first on his login PATH), runs both terminals as
     `ares` and checks that only `/usr/bin/foot` ran, with `ARESOS_TERMINAL` `recovery` and `normal`.
   - Not changed: the recovery terminal still inherits his session PATH; only `foot` and the shell are pinned.

Verification of the fixes:

| Run | What | Result |
|---|---|---|
| 42721423312, 42721664820 | `build` | Cancelled by me before the checks ran, to fix the reuse probe first (password out of the trace; child kept out of bash's exec-in-place). |
| 42721773111 | `build` | Failed at writing the throwaway password: root may not write into an `ares`-owned file in sticky `/tmp`. Moved to `/run`. |
| **42723594272** | **`build` on `9c606fda`** | **Success.** 24 in-image PASS lines, including the two new ones: `after a successful sudo, a child exec of sudo -n is refused (the old ppid ticket allowed it)` and `both terminals run /usr/bin/foot even with a broken foot first on PATH`. `sudo -l` shows `timestamp_timeout=0`. `polkit: 21 rule files, 401 actions, 0 change with wheel, 62 denied to ares`, `POLKIT_CHECK_PASSED`, the check without the AresOS rule still fails; rootless mapping and lock equality pass. Evidence: `runs/build-42723594272/` (the trace shows the control's successful reuse and the real setting's `sudo: a password is required`). |
| **42724943196** | **`checks_only=true` on `9c606fda`** | **Success.** `Ran 713 tests` `OK` natively with sudo (the new tests included), compile and syntax sweeps, live system-manager query. |

- WSL, focused on the pushed `368e5510` (same tests as the final head): `test_everyday_account` 25 OK,
  `test_shell_assertions` 8 OK, `test_checkout_sources` 4 OK; `test_sysusers` 2 errors (WSL's `sudo` needs a password,
  as before). No full WSL suite: free memory stayed at 1.5 GB, under the 4 GB rule; the native run covers the suite.
- Tests added: the reuse probe with its `ppid` control and the `/usr/bin/foot` stand-in check (`image-checks.sh`);
  `test_a_broken_foot_first_on_path_is_never_run`; the denied-action list, its match with `polkit-review.json` and the
  unchanged power actions in `test_polkit_rule_denies_os_changes_and_asks_for_upstream_wheel_grants`; the
  `polkit-check.js` rules for denies with and without wheel and the boot/firmware name pattern. Changed:
  `test_sysusers_adds_wheel_and_sudo_asks_for_the_password_every_time`, `guest.sh` and its shell-assertion fixture.

## Review fixes 2 (review 2: CHANGES-NEEDED at `5f1099e2`; brief `21-review-fixes-2.md`)

Board #156 is still open, so its behaviours stay: Homebrew through UID 1000, system-wide Wi-Fi and Flatpak installs
asking for the password.

1. **Blocker: TuneD as a passwordless route to boot changes.** Fixed.
   - Every `com.redhat.tuned.*` action except 15 read-only queries (`aresosTunedReadOnly`: profiles, active profile,
     plugin docs, verification) is now denied to `ares` in every session kind, with and without wheel. That covers
     `switch_profile`, `auto_profile`, `start`, `stop`, `reload`, `disable`, the `instance_*` changes and log capture.
     New TuneD actions in a later base are denied until reviewed.
   - The power-profile switch stays passwordless, because tuned-ppd only maps it to the profiles in
     `/etc/tuned/ppd.conf`. A new in-image check resolves every mapped profile and its includes and proves none has a
     bootloader section or `cmdline` option: `balanced`, `balanced-battery-bazzite`, `balanced-bazzite`, `powersave`,
     `powersave-battery-bazzite`, `powersave-bazzite`, `throughput-performance`, `throughput-performance-bazzite`.
   - The check no longer relies on a name pattern alone: every action that stays passwordless for `ares` (131 in this
     base) is listed by name with a reason in `polkit-review.json` under `passwordless`, and `polkit-check.js` fails
     on any unlisted passwordless action and on stale entries.
2. **Blocker: cached admin authorization.** Fixed.
   - `build.sh` rewrites every installed polkit default from `auth_admin_keep`/`auth_self_keep` to
     `auth_admin`/`auth_self` (333 defaults across 227 actions, including systemd unit management and GVfs) and fails
     if any remains. No account gets a cached authorization any more (JUDGMENT-CALL 8).
   - The AresOS rule never returns a cached result. Upstream wheel grants now give `ares` the action's own uncached
     default per session kind (`aresosWheelGrantDefaults`; CI checks the table against the image). This also fixes a
     round-1 slip: returning `AUTH_ADMIN_KEEP` everywhere loosened GVfs (`no` by default) outside an active local
     session.
   - `polkit-check.js` now evaluates remote, local inactive and local active sessions with and without wheel, and
     fails on any cached result, on anything weaker than polkit's own uncached default, and on any boot, firmware,
     OS-change or TuneD-change action that isn't `no`. Run locally against the previous image, the round-1 rule fails
     with 153 findings and the unrewritten defaults fail on every cached one.
   - New live regression in `image-checks.sh`: a real `polkitd` on a private system bus, a text agent on a pty, and the
     throwaway password. `ares` authorizes once with `pkcheck --allow-user-interaction`, then the same process checks
     again without interaction. Control: a check-only action with a cached default is reused (exit 0), so the probe
     can see reuse. NetworkManager system settings and firewalld configuration, both cached by the base in this
     session kind, are asked again (exit 2, "requires authentication"). Without logind every subject counts as
     remote; the static evaluation covers the active local session for all 401 actions.

JUDGMENT-CALL 8 (no cached polkit authorization for any account) is in the JUDGMENT-CALL list above.

Verification of the fixes:

| Run | What | Result |
|---|---|---|
| **42727378915** | **`check_build=build` on `e83362d3`** | **Success.** 26 in-image PASS lines, including `polkit: after ares authorizes once, the same process is asked again (a cached control action is reused)` and `every power profile ares can switch to leaves the bootloader and kernel arguments alone`. Build log: `polkit: 333 cached defaults made uncached`. `polkit: 21 rule files, 401 actions, 0 change with wheel, 73 denied to ares, 131 reviewed passwordless, 0 cached defaults in the image`, `POLKIT_CHECK_PASSED`; the check without the AresOS rule still fails. Evidence: `runs/build-42727378915/`. |
| **42729131585** | **`checks_only=true` on `0659e6bc`** | **Success.** `Ran 714 tests` `OK` natively with sudo, including `test_build_makes_every_polkit_default_uncached_and_refuses_leftovers` and the updated polkit test; compile and syntax sweeps and the live system-manager query passed. |

- WSL, focused on `e83362d3` before the last test-only commit: `test_shell_assertions` 8 OK, `test_checkout_sources` 4 OK, `test_sysusers` 2 errors (WSL sudo, as before); `test_everyday_account` found the deny-clause assertion that `0659e6bc` fixed (6 policy tests OK locally after it).
- Full WSL suite on `0659e6bc` (the last code commit; later commits change only `reviews/`), after another agent's suite finished and with 5.7 GB free: plain and `-B` both `Ran 714 tests`, `FAILED (failures=1, errors=12)`, only in the known WSL-only suites (all `sudo: a password is required`): `test_greeter` 3 errors, `test_inherited_homebrew` 1 failure + 7 errors, `test_sysusers` 2 errors. Everything else passes, including `test_everyday_account` (26 tests).

## Review fixes 3 (review 3: CHANGES-NEEDED at `4c93ac33`; brief `21-review-fixes-3.md`)

Board #156 is still open, so its behaviours stay: Homebrew through UID 1000, system-wide Wi-Fi and Flatpak installs
asking for the password.

1. **polkit `imply` (Medium): fixed by neutralizing the one implication.**
   - polkitd grants an action when the subject is authorized outright for an action that implies it
     (`org.freedesktop.policykit.imply`, one level deep). Flatpak 1.18.4's passwordless `app-update` implied
     `runtime-install`, so an active `ares` could install any system-wide runtime without the password.
   - Chosen: `build.sh` drops only `runtime-install` from `app-update`'s implication; `runtime-update` stays. Updates of
     apps he installed system-wide stay passwordless; an update that needs a new runtime asks for the password once,
     like any system-wide install; `flatpak --user` stays passwordless. The build stops for review if upstream changes
     the annotation. This applies to every account (`ares-recovery` too).
   - Rejected: an `ares` rule requiring `auth_admin` for `app-update`. That would also close the hole, but every
     routine system-wide app update would ask for the password.
2. **The audit follows implications.** `polkit-check.js` now applies `org.freedesktop.policykit.imply` as polkitd does
   (one level, the implying action authorized outright) in every session kind, with and without wheel, and judges each
   action by what `ares` really gets. The rerun inventory adds `org.freedesktop.login1.set-wall-message`, granted
   through the passwordless power-off and reboot (sets the shutdown broadcast message); 132 passwordless actions are
   reviewed by name. On the review-2 image the audit now reports `runtime-install` as `yes (implied by
   org.freedesktop.Flatpak.app-update)`. No other implication gives `ares` anything: every other implying action is
   itself password-gated or denied, or implies only actions that are already passwordless.
3. **Live active-session regression.** `os/tests/guest.sh`, the VM policy step, now asks polkitd about a process in
   `ares`'s real active local seat0 session (checked `Active=yes`, `Remote=no`, and the process's session scope):
   `app-update` and `runtime-update` are allowed (pkcheck 0), `runtime-install`, `app-install` and `manage-units` need
   the password (2), and `set-reboot-to-firmware-setup` and TuneD's `switch_profile` are refused (1).
   `check_build=build` boots one VM pass again and requires that result.
   - That needed `vm.py`'s journal readiness wait fixed (the PLAN-GAP above): it now also accepts a complete
     follower line carrying the token. `vm.py` is bound by the package 16 walk; its new checkout bytes are in
     `pending-rebind.json`, like `os-image.yml`'s.

Verification of the fixes:

| Run | What | Result |
|---|---|---|
| **42731965403** | **`check_build=build` on `dcf6d577`, now with one VM boot** | **Success.** Build log: `polkit: Flatpak app-update now implies only: org.freedesktop.Flatpak.runtime-update`. 26 in-image PASS lines and `IMAGE_CHECKS_PASSED`; `polkit: 21 rule files, 401 actions, 0 change with wheel, 73 denied to ares, 132 reviewed passwordless, 0 cached defaults in the image`, `POLKIT_CHECK_PASSED`; the check without the AresOS rule still fails. VM pass: guest policy with `ARESOS_ACTIVE_SESSION_POLKIT_PASSED` in session 1 (`Seat=seat0`, `Remote=no`, `Class=user`, `Active=yes`): `app-update` 0, `runtime-update` 0, `runtime-install` 2, `app-install` 2, `manage-units` 2, `power-off` 0, `set-reboot-to-firmware-setup` 1, `tuned.switch_profile` 1. Power events, the recovery shortcut, the tty3 recovery login and the offline power-key check passed too (`PASS: offline logind power-key path`, `UEFI VM checks passed`), so `vm.py` runs to the end again; `CHECK_BUILD_VM_PASSED`. Evidence: `runs/build-42731965403/`. |
| **42735828754** | **`checks_only=true` on `dcf6d577`** | **Success.** `Ran 715 tests` `OK` natively, including `test_build_drops_only_the_runtime_install_implication_of_flatpak_app_update`. |

- Locally against the review-2 image's real policies: the new audit reports `runtime-install` as passwordless "implied by
  org.freedesktop.Flatpak.app-update" and fails; with the build's edit applied it passes. After the fix the only action
  an implication raises for `ares` is `set-wall-message`.
- Full WSL suite on `dcf6d577` (memory 5.7 GB free, no other suite running; scripts and temp folders now named
  `pkg21-…`): plain and `-B` both `Ran 715 tests`, `FAILED (failures=1, errors=12)`, only in the known WSL-only suites:
  `test_greeter` 3 errors, `test_inherited_homebrew` 1 failure + 7 errors, `test_sysusers` 2 errors.
- Tests added: the live active-session polkit block in `guest.sh` (VM policy step); implication handling and the
  wheel-grant "no implied extra" check in `polkit-check.js`; `test_build_drops_only_the_runtime_install_implication_of_flatpak_app_update`
  (runs the build's edit on a sample and checks it refuses a changed upstream).

## Review fixes 4 (review 4: CHANGES-NEEDED at `7e900863`; brief `21-review-fixes-4.md`)

Review 4 found no remaining passwordless root, image, boot, kernel-argument or firmware bypass. Board #156 is still
open, so its behaviours stay.

1. **`build.sh` Flatpak guard (Medium): fixed.** Before the edit, `app-update`'s implication must be exactly
   `org.freedesktop.Flatpak.runtime-install org.freedesktop.Flatpak.runtime-update` (Flatpak 1.18.4); after it,
   exactly `org.freedesktop.Flatpak.runtime-update`, with the rest of the file unchanged. Anything else stops the build
   for review. `test_build_drops_only_the_runtime_install_implication_of_flatpak_app_update` runs the build's own
   block on samples: the reviewed pair is edited exactly; an added target (`app-install`, `systemd1.manage-units`),
   either target alone, the reversed order, a repeated target and an empty list all stop it.
2. **`vm.py` readiness (Medium): fixed.** The gate is now `os/ci/journal_ready.follower_ready`: only a complete,
   newline-terminated `aresos-ci[<pid>]` record whose message, without journalctl's colour codes, is exactly
   `ARESOS_JOURNAL_READY` counts. `vm.py` uses only that gate and no longer imports `serial_search`. New
   `os/tests/test_journal_ready.py`: the real coloured record (with `\r\n` and `\n`); chunked input in 1, 3, 7 and
   64-character pieces, which counts only once the record's newline has arrived; false markers (`FAILED
   ARESOS_JOURNAL_READY`, `ARESOS_JOURNAL_READY_NOT`, extra spaces, other words, other tags, a line without the
   timestamp, a record not at the line start); and unterminated records. `vm.py`'s checkout bytes in
   `pending-rebind.json` are regenerated with `checkout_sources.records`.

Verification of the fixes:

| Run | What | Result |
|---|---|---|
| **42737640035** | **`check_build=build` on `6cc07158`, with the VM boot** | **Success.** `polkit: Flatpak app-update now implies only: org.freedesktop.Flatpak.runtime-update`; 26 in-image PASS lines; `polkit: 21 rule files, 401 actions, 0 change with wheel, 73 denied to ares, 132 reviewed passwordless, 0 cached defaults in the image`, `POLKIT_CHECK_PASSED`. VM pass through the new readiness gate: guest policy with `ARESOS_ACTIVE_SESSION_POLKIT_PASSED`, `PASS: offline logind power-key path`, `UEFI VM checks passed`, `CHECK_BUILD_VM_PASSED`. Evidence: `runs/build-42737640035/`. |
| **42740827813** | **`checks_only=true` on `6cc07158`** | **Success.** `Ran 720 tests` `OK` natively, including the five `test_journal_ready` tests and the extended implication test. |

- Full WSL suite on `6cc07158` (`pkg21-wsl-suite.sh` in a `mktemp` folder, started once no other suite ran and 4 GB
  were free): plain and `-B` both `Ran 720 tests`, `FAILED (failures=1, errors=12)`, only the known WSL-only suites
  (`test_greeter` 3 errors, `test_inherited_homebrew` 1 failure + 7 errors, `test_sysusers` 2 errors). Focused on the
  same head: `test_journal_ready` 5 OK, `test_everyday_account` 27 OK, `test_shell_assertions` 8 OK,
  `test_checkout_sources` 4 OK (with the regenerated `vm.py` binding).

## Review fixes 5 (review 5: CHANGES-NEEDED at `6cc07158`; brief `21-review-fixes-5.md`)

Review 5 confirmed the Flatpak guard and `vm.py`'s pending hash and found no further passwordless root, image, boot,
kernel-argument or firmware bypass. Board #156 is still open, so its behaviours stay (Homebrew through UID 1000,
system-wide Wi-Fi and Flatpak installs ask for the password).

1. **`journal_ready.py` spans line breaks (Medium): fixed.** The record pattern is now
   `^\[[ \t]*\d+\.\d+\] [^\s]+ aresos-ci\[\d+\]: ([^\r\n]*)\r?\n`: only spaces and tabs pad the timestamp, and no
   part before the terminating newline can match `\r` or `\n`. New regression
   `test_no_line_break_may_sit_anywhere_before_the_message` puts `\n`, `\r` and `\r\n` at every position from the
   timestamp to the message start of a good record, plus the review's `[\n 1.0] ...` case; all are rejected.
   `journal_ready.py` isn't bound and `vm.py` didn't change, so `pending-rebind.json` stays as it is
   (`test_checkout_sources` passes).
2. **Session start resolved commands through his PATH (Medium): fixed, and widened to everything session start
   runs.**
   - `aresos-session` no longer sources the daily profile. It exports `/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin`
     and execs `/usr/libexec/aresos-keyboard /usr/bin/dbus-run-session --dbus-daemon=/usr/bin/dbus-daemon --
     /usr/bin/labwc ...`. labwc and what it starts (its `sh` autostart, the polkit agent, both terminals, keybinds)
     inherit that system PATH, and dbus-run-session no longer looks up `dbus-daemon`.
   - `aresos-keyboard` calls `/usr/bin/busctl`, requires an absolute compositor path and uses `os.execve` (no PATH
     search). The `brew` shim (`stat`, `id`, `getent`, `cut`, `sudo`, `env`), `aresos-subids` (`/usr/sbin/usermod`)
     and `/etc/profile.d/aresos.sh` (`/usr/bin/id`) run absolute commands too. `aresos-terminal`, the autostart
     lines and the `rc.xml` commands already did.
   - greetd's session wrapper is a non-interactive `/bin/sh` that sources `/etc/profile` before
     `/usr/bin/aresos-session`, so the base image's profile scripts ran with his PATH. `aresos.sh` now sets the daily
     PATH only in his interactive and login shells, so that wrapper keeps the system PATH.
   - His AresOS terminal applies `/etc/profile.d/aresos.sh` before his `~/.bashrc` (`/usr/share/aresos/bashrc`); the
     recovery terminal keeps the system PATH and still never reads his file. JUDGMENT-CALL 9 records the trade-off.
   - New tests: `StartupPathTest` (the session's exact exec line, the terminal's exec line, every autostart and
     `rc.xml` command absolute, `busctl`/`execve` in the keyboard helper, the shim's and subids' commands, the VM
     layer's shadow list); `DailyPathTest` now covers login, interactive (`bash -i`, a `-sh` login) and the wrapper
     shapes (`sh -c`, `bash -c`), with `/usr/bin/id` swapped for a stub only in a temporary copy;
     `test_session_keeps_the_system_path_and_terminals_add_his_own`.
   - In-image checks (`image-checks.sh`): the normal terminal's PATH starts with `~/.local/bin` and the recovery
     terminal's is the system PATH; the real `/etc/profile` run as greetd runs it keeps the system PATH while a login
     shell adds his; and every absolute command the greeter, session, terminals, keybinds and helpers name exists
     in the image (21 of them). `inherited-homebrew.sh` (switch and rehearsal VMs) now expects the system PATH in
     labwc's environment.
   - VM shadow test: the disposable CI layer (`os/ci/overlay/shadow-path.*`, `shadow-names.txt`) writes a broken
     program for each of `sh`, `bash`, `dash`, `dbus-run-session`, `dbus-daemon`, `dbus-broker-launch`, `labwc`,
     `busctl`, `foot`, `id`, `python3`, `env`, `xdg-open`, `Xwayland`, `polkit-kde-authentication-agent-1`,
     `aresos-terminal` and `aresos-session` into `/var/home/ares/.local/bin` before greetd starts; each records that
     it ran and exits 97. After Super+Ctrl+Escape, the `shortcut` check requires both terminals to run `/usr/bin/foot`
     with a live `/usr/bin/bash`, all 17 shadows in place and none of them run. A probe last in `/etc/profile.d`
     records the PATH every profile run sees for `ares`; the wrapper's must be the system PATH.
3. **Reruns.**

| Run | What | Result |
|---|---|---|
| 42743387255 | `check_build=build` on `631c7f5d` | Failed before the build: `snapshot.ubuntu.com` answered 503 while installing the pinned runner tools (infrastructure; the next run passed that step unchanged). |
| **42743949300** | **`check_build=build` on `f8777b8c`, with the VM boot** | **Success.** 31 in-image PASS lines, including `normal AresOS terminal PATH: /var/home/ares/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/home/linuxbrew/.linuxbrew/bin:...`, `recovery AresOS terminal PATH: /usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin`, `greetd's profile wrapper keeps the system PATH (/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin); his login shell adds his own (...)` and `all 21 absolute startup commands exist`; `POLKIT_CHECK_PASSED` with the same counts as round 4. VM pass: guest policy with `ARESOS_ACTIVE_SESSION_POLKIT_PASSED`; the shortcut check with all 17 shadows in place and none run, both terminals `/usr/bin/foot --title=AresOS /usr/bin/bash --rcfile /usr/share/aresos/bashrc -i` with a `/usr/bin/bash` child, and greetd's wrapper seen once as `/bin/sh` (flags `hBc`, not a login shell) with PATH `/usr/local/bin:/usr/bin:/usr/local/sbin`; the recovery TTY and PAM check; `PASS: offline logind power-key path`; `UEFI VM checks passed`; `CHECK_BUILD_VM_PASSED`. Evidence: `runs/build-42743949300/` (`vm-pass-1/shortcut-result.json` holds the terminals, shadows and profile PATHs). |
| **42748566373** | **`checks_only=true` on `f8777b8c`** | **Success.** `Ran 725 tests` `OK` natively, including the six `test_journal_ready` tests, `StartupPathTest` and the new `DailyPathTest` shell shapes. |

- Full WSL suite on `631c7f5d` (`pkg21-wsl-suite.sh`, started once no other suite ran and 4.7 GB were free): plain
  and `-B` both `Ran 724 tests`, `FAILED (failures=1, errors=12)`, only the known WSL-only suites (`test_greeter`
  3 errors, `test_inherited_homebrew` 1 failure + 7 errors, `test_sysusers` 2 errors). Focused on `f8777b8c`, which
  adds the profile guard: `test_journal_ready` 6 OK, `test_everyday_account` 31 OK, `test_shell_assertions` 8 OK,
  `test_checkout_sources` 4 OK.

## Review fixes 6 and main merge (review 6: SAFE at `023bf077`, one Low; brief `21-review-fixes-6.md`)

Review 6 found both review-5 findings fixed and JUDGMENT-CALL 9 sound, with no privilege, boot, firmware or session
blocker left. Owner answers: board #156 "Yes to all" covers JUDGMENT-CALLs 1 to 3; calls 4 to 9 wait on board #163
and are unchanged here. JUDGMENT-CALL 10 is new (item 4).

1. **Main merged (package 24, `7cf0541b`).** Merge commit `cf0576b1`, no rebase or force-push. The one conflict, the
   `os/build.sh` chmod line, keeps both sides: 21's `/usr/bin/brew` and `/usr/libexec/aresos-subids` with its
   `sudoers.d` and subids lines, and 24's `/usr/libexec/aresos-shell`. No bound file changed, so
   `pending-rebind.json` stays exact (`test_checkout_sources` 4 OK at every head of this round).
2. **21 and 24 together.**
   - The helper doesn't depend on PATH: `#!/usr/bin/python3`, `/usr/bin/systemd-run` for launches,
     `/usr/bin/systemctl` for scope checks, a fixed `/usr/local/bin:/usr/bin` for desktop-entry lookups, and app files
     whose `argv[0]` is absolute (`/usr/bin/google-chrome`, `/usr/bin/kwrite`, `/usr/bin/foot`). It ships no unit, no
     polkit action and no updater: the polkit check and the static updater audit pass unchanged on the merged image.
     Package 23's supervisor will start it, so the VM boot doesn't start it yet; the VM shadow check is unchanged.
   - **Fixed, the one misfit:** the hub's Terminal app ran plain `foot`, whose bash inherited the session's
     environment. Since review 5 that is the system PATH, so `~/.local/bin` (where tools like Claude Code's native
     installer go) and Homebrew's commands were missing in the hub terminal. `terminal.json` now runs
     `/usr/bin/foot --app-id=aresos.terminal /usr/bin/bash --rcfile /usr/share/aresos/bashrc -i`, which applies his
     daily PATH and then his `~/.bashrc`. The banner and the AresOS prompt now print only in terminals that
     `aresos-terminal` starts (`ARESOS_TERMINAL` set), so the hub terminal stays plain, as package 24's call 4 chose
     (owner: board #155). Its app_id stays `aresos.terminal`.
   - Tests: `test_hub_terminal_is_plain_but_reads_his_bashrc`, `test_app_helper_and_its_apps_run_absolute_commands`,
     and `test_aresos_shell`'s registry and launch-argv assertions moved to the new terminal command.
   - In-image checks: a `hub` row in the terminal PATH check (daily PATH, no banner) next to `normal` and `recovery`
     (both now also require the banner); the exact `terminal.json` command; `aresos-shell` (listed by name, since no
     session file names it yet), its commands and the app files' commands join the absolute startup commands that
     must exist (26 now); and the helper, run as `ares` under the system PATH with broken `python3`, `systemd-run`,
     `systemctl`, `foot`, `bash`, `kwrite`, `google-chrome`, `google-chrome-stable`, `sh` and `env` first on it, lists
     all three apps as available and builds each launch from absolute paths, without running a shadow.
3. **Review 6's Low: fixed.** The `shortcut` check now fails when the profile probe is missing or holds no
   non-interactive, non-login (greetd wrapper) record, then checks that record's PATH. Run 42743949300 had that
   record, so its evidence stands.
4. **Forced pin renewal (JUDGMENT-CALL 10).** Fedora 44 pushed `xdg-desktop-portal-wlr-0.8.5-1.fc44` to stable on
   2026-11-10, and its updates repository dropped 0.8.4, so the first build at the merged head (42788867155) stopped
   in the package step: `No package "xdg-desktop-portal-wlr-0.8.4-1.fc44.x86_64" available`. Main's lock has the same
   pin, so main's image builds stop there too. The lock now pins 0.8.5 (`bcc5a77d…`, the RPM from
   dl.fedoraproject.org); `build.sh` still requires the resolved set, the bytes and Fedora's signature to match, and
   they did. No other package changed.

| Run | What | Result |
|---|---|---|
| 42788867155 | `check_build=build` on `7477615c` | Failed in the package step: the Fedora pin above had vanished. |
| 42791257661 | `check_build=build` on `04cf5888` (pin renewed) | Package step and the new hub-terminal and wrapper checks passed; then the startup-command check failed, because it looked for `/usr/libexec/aresos-shell` among paths that session files name, and none names it yet. Fixed in `5846f803` by listing it by name. |
| **42792865417** | **`check_build=build` on `5846f803`, with the VM boot** | **Success.** 33 in-image PASS lines, including `hub AresOS terminal PATH: /var/home/ares/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/home/linuxbrew/.linuxbrew/bin:...`, `all 26 absolute startup commands exist` and `the app helper resolves browser, notepad and terminal and launches by absolute paths under the system PATH with shadows first` (the three `HELPER_LAUNCH` lines show the `systemd-run` commands); `static updater audit passes`; `POLKIT_CHECK_PASSED` with round 4's counts; the image's lock shows `xdg-desktop-portal-wlr-0.8.5-1.fc44`. VM pass: `ARESOS_ACTIVE_SESSION_POLKIT_PASSED`; the shortcut check with all 17 shadows in place and none run, both terminals with a `/usr/bin/bash` child, and the greetd wrapper record (`/bin/sh`, flags `hBc`, PATH `/usr/local/bin:/usr/bin:/usr/local/sbin`) now required; `PASS: offline logind power-key path`; `UEFI VM checks passed`; `CHECK_BUILD_VM_PASSED`. Evidence: `runs/build-42792865417/`. |
| **42798151752** | **`checks_only=true` on `5846f803`** | **Success.** `Ran 791 tests` `OK` natively, with package 24's suites and the new tests above. |

- Focused WSL suites on `7477615c` (fresh clone): `test_journal_ready` 6 OK, `test_everyday_account` 33 OK,
  `test_aresos_shell` 64 OK, `test_shell_assertions` 8 OK, `test_checkout_sources` 4 OK; `test_sysusers` 2 errors
  (WSL-only, as before). After the pin renewal, from the worktree: `test_everyday_account` 33 OK, `test_owner_path`
  36 OK, `test_release_squash_binding` 7 OK, `test_checkout_sources` 4 OK.
- Full WSL suite on `5846f803` (`pkg21-wsl-suite.sh`, started once package 22's suites had finished and 5.1 GB were
  free): plain and `-B` both `Ran 791 tests`, `FAILED (failures=1, errors=12)`, only the known WSL-only suites
  (`test_greeter` 3 errors, `test_inherited_homebrew` 1 failure + 7 errors, `test_sysusers` 2 errors).
