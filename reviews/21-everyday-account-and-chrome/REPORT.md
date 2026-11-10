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
    (`AUTH_ADMIN_KEEP`): Flatpak app/runtime install and uninstall, gvfs admin file operations
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
- **PATH** (`/etc/profile.d/aresos.sh`, read by login shells and by `aresos-session`): `~/.local/bin`, then
  `/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin`, then Homebrew's `bin`/`sbin` and the user and system Flatpak
  export bins when they exist. System commands stay ahead of Homebrew's.
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
    write the prefix, finds `/usr/bin/brew` and Homebrew on the login and session PATH, and an install without a
    password fails before brew runs.
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
   - Reversal: remove names from `aresosPasswordActions`; `polkit-check.js` then lists them for review.
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

## PLAN-GAP

- **`vm.py` can't pass its power-key step since package 14.** It now searches the serial log through
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
