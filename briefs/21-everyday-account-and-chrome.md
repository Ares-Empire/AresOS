# 21: Everyday account like Windows, Chrome, daily-use fixes

Empire board brief 262. Image package; it changes `os/` only (plus tests, docs and a throwaway CI build path).

**Builder:** a Claude agent (Opus 5.5). The owner asked on 2026-11-09 to use Claude agents while his Claude allowance lasts. **Review:** Codex gpt-6-astra (high), a fresh context.

## Why

AresOS is installed on the laptop (install steps 4–7 passed on 2026-11-08/09; see `STATE.md`). Claude Code now runs there as the daily user `ares`. Real use showed what the next image must change:

- `ares` can't install anything:
  - it is locked out of wheel;
  - `build.sh` makes `flatpak` and `brew` mode 0700;
  - polkit denies Flatpak and unit files;
  - an ACL denies UID 1001 the inherited Homebrew.
- `ares` has no browser. Firefox is a Flatpak, and Flatpak is blocked.
- Every login shell prints `/etc/profile.d/flatpak.sh: /usr/bin/flatpak: Permission denied`, and the user generator `60-flatpak` fails the same way.
- `~/.local/bin` is not on `ares`'s PATH. `/etc/profile.d/aresos.sh` sets a fixed PATH for UID 1001, and foot starts with `--rcfile /usr/share/aresos/bashrc`, so `~/.bashrc` is never read there.
- foot's default font is too small at 1920×1080. The owner set 16 in his own `~/.config/foot/foot.ini`.
- `script` (util-linux) and `qrencode` are missing.
- The brightness and volume keys do nothing:
  - `rc.xml` binds only three keys;
  - `brightnessctl` is missing;
  - there is no `/sys/class/backlight` device. The backlight driver is **not** in this brief; see "Out of scope".

## Owner decisions (2026-11-09, in session)

1. **Browser: Google Chrome**, built into the image. It is the same browser as on Windows, and the control layer's Chrome tool (brief 20) targets it.
2. **Admin rights: "Like Windows"**:
   - his everyday account gets admin rights behind his own password, like Windows' Yes prompt;
   - Flatpak apps and Homebrew work;
   - Claude can't use admin rights unless he types the password;
   - the recovery account `ares-recovery` stays as a spare administrator.

These replace the locked daily account in `docs/design/OS-BASE.md` (the account split around its section on the recovery handoff, and the updater policy list). Record the change there and in `docs/design/DESIGN.md` with the date and his words. Past decisions record reasoning; this one supersedes them.

## Build

### A. The everyday account `ares`

1. **wheel:** `ares` joins wheel, so `sudo` asks for `ares`'s own password.
   - The image sets no password. The owner sets it once after updating (package 22's guide).
   - Until then `ares` stays password-locked: sudo simply fails, and auto-login is unchanged.
2. **Software installs:**
   - Remove the 0700 lock on `flatpak` and `brew`, and the polkit denies that block normal installs (Flatpak, unit files).
   - Keep everything that changes the **OS image or firmware** out of the daily path: `rpm-ostree`/bootc, `fwupd`, the Bazzite updater/portal actions, `uupd`, `ujust` update paths and `topgrade`. The OS changes only through the signed release route (package 22) or an explicit `sudo` by the owner.
   - The app store (`bazaar`) stays blocked for now; note in the report whether it can touch the OS.
3. **Homebrew:** the inherited prefix `/var/home/linuxbrew` belongs to UID 1000, for stock rollback, and is ACL-denied to UID 1001 (`tmpfiles.d/aresos-inherited-homebrew.conf`, `test_inherited_homebrew`).
   - Find a route that lets `ares` use `brew` without breaking the stock rollback for `ares-recovery`.
   - Mark it **JUDGMENT-CALL**: what you chose, the alternatives, and the reversal.
4. **Containers:** check that rootless podman and distrobox work for `ares` (subuid/subgid ranges for a sysusers-made account). Fix it if not.
5. **Admin prompts:** a polkit authentication agent in the labwc session, so a GUI or Flatpak action that needs admin can ask for the password. Prefer an agent already in the base image.
6. **PATH and shell:**
   - `~/.local/bin` goes on `ares`'s PATH, plus Homebrew's and Flatpak's export bins when present.
   - The AresOS terminal also reads the user's own `~/.bashrc` after the banner, so his settings apply. His file must not be able to break the session start.
   - Login shells and the user generator no longer print Flatpak permission errors.
7. **foot:** an image default font size that reads well at 1920×1080. His own `foot.ini` still wins.
8. **Tools:** `script` and `qrencode` in the exact package lock (`os/packages.lock.json`), using the existing resolve-and-hash discipline.
9. **Keys:**
   - Add `brightnessctl`.
   - Add labwc bindings for `XF86MonBrightnessUp/Down` and `XF86AudioRaiseVolume/LowerVolume/Mute`, plus mic mute if the key exists. Use the tools already in the image, e.g. `wpctl`.
   - Brightness only starts working once a backlight device exists (brief 21b). Don't guess a kernel argument here.

### B. Google Chrome

1. Install **Google Chrome stable** from Google's official RPM with the same exact-pin discipline as the package lock: exact NEVRA and sha256, and Google's signing key pinned and checked. It can't come from `fedora`/`updates`, so extend the package step in a reviewed, explicit way. Don't widen what else may be installed.
2. **`/opt` on bootc:** on bootc/ostree systems `/opt` is `/var/opt` and not part of the image, but Chrome installs to `/opt/google/chrome`. Make Chrome live in the image (under `/usr`) at the path it expects, so it works on the laptop after an image switch without depending on `/var` contents.
3. **No side updater:** Google's RPM adds a repo file and a daily cron job that would change the system outside the release route. Neutralize both, so Chrome updates arrive with AresOS releases.
4. **Starting Chrome:** `ares` can start `google-chrome` from the terminal, and `xdg-open` opens links in it (Claude Code's sign-in, foot's URL mode). Leave the managed policy and native-messaging host to the control layer, but don't block `/etc/opt/chrome/policies`.

### C. Verification

- **Tests:**
  - Extend `os/tests`.
  - Tests that pin the old lockdown (`test_sysusers`, `test_inherited_homebrew`, the updater audit and so on) must change to pin the **new decision**, never be deleted or skipped. Name each such test change in the report.
- **Throwaway CI image build:**
  - Add a `workflow_dispatch` path in `.github/workflows/os-image.yml`, or a small new workflow, that builds the image on your branch **without pushing, signing or publishing anything**. Run it. Public repo, so the minutes are free. Also run the existing checks-only regressions if they apply.
  - In that build, check the built image itself:
    - `ares` is in wheel and sudo requires a password;
    - `google-chrome --version` runs and Chrome's files are under `/usr`;
    - no Chrome repo file or cron job is active;
    - `flatpak` is executable by `ares`, and the OS updaters stay blocked;
    - the polkit rule content is as intended;
    - a login shell for `ares` has `~/.local/bin` on PATH and prints no Flatpak error;
    - the foot default font is set;
    - `script`, `qrencode` and `brightnessctl` are present.
- **WSL suites (Linux tests):**
  - Run them as Claude does: clone your **pushed** branch into `/tmp` inside WSL and run `python3 -m unittest discover -s os/tests` there, both plain and with `-B`.
  - Write any script file with LF endings.
  - From Git Bash: `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu --exec bash /mnt/c/...`.
  - Known WSL-only failures, also on main: `test_greeter` (3 errors), `test_inherited_homebrew` (1 failure + 5 errors), `test_sysusers` (1 error). If your change touches those suites, show their before/after explicitly.
  - Memory is tight (16 GB, shared with the owner): run at most **one** full-suite run at a time. Before starting, check that no other `unittest discover -s os/tests` runs inside WSL (another package may be testing in parallel).
- **Bound sources:** if you change a file that the package 16 walk binds, add its new checkout hash to `os/manifest/ci/16/pending-rebind.json` exactly, generated with `checkout_sources.records`, as `reviews/15f-lenovo-firmware-entry/REPORT.md` describes. `test_checkout_sources` must pass.

## Out of scope (other packages)

- `os/owner-tools`, the install guide and `docs/INSTALL*.md`: package 22 runs in parallel and owns them.
- The release pin (`os/manifest/release.json`, the digest in `docs/INSTALL.md`) and any publishing: a later release package, with the owner's OK.
- The backlight driver/kernel argument and the power button (no key event reaches logind): 21b, after a read-only check on the real laptop.
- The control layer's `/etc/claude-code` files (board #136/#137): after brief 18d merges.
- Minecraft.

## Rules

- `AGENTS.md` applies. You may push your branch `pkg/21-everyday-account-and-chrome` and open a PR. Never merge, never push to `main`. Never `--no-verify`: the privacy pre-push hook must pass.
- The repo is public: no personal data, serials, GUIDs, emails or tokens.
- Don't run anything as admin on Windows. Don't touch disks or boot settings. Don't touch other worktrees.
- Commits end with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Write `reviews/21-everyday-account-and-chrome/REPORT.md` in the AGENTS.md format, with JUDGMENT-CALLs marked.
