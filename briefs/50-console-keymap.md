# 50: The console keymap at boot (rides release 28)

Empire board brief 303. Written 2026-11-17 by `linux-aresos` after the owner tools' version 4 install on the laptop.

## Why

On the laptop, `systemd-vconsole-setup` logs at every boot since 2026-11-09 (the first AresOS boot):

> All allocated virtual consoles are busy, will not configure key mapping and font.

Plymouth holds the virtual consoles in graphics mode while the setup runs, so the setup skips the keymap. Sometimes a
later run in the real root loads it and sometimes it doesn't (boot 2026-11-13 13:59: both runs skipped). The console
then keeps the kernel's US map while `/etc/vconsole.conf` and `localectl` say `de`.

What it breaks:
- **Recovery typing.** The recovery console (tty3, `ares-recovery`) types y/z and the symbols wrong, exactly when the
  owner needs it.
- **The tools' `check`.** It reads `dumpkeys -C /dev/tty3` and STOPs with `Loaded console keys differ from system
  layout; get help` (`os/owner-tools/owner.py`, `check`, about line 1990). On 2026-11-17 that STOP came right after
  `PASS install`. With the owner's OK the lead loaded the map for that boot with `loadkeys -C /dev/tty3 -- de`, the
  tools' own trial command (`trial_keyboard`). After it: dumpkeys keycode 21 `+z` (it was `+y`), `PASS check`,
  `PASS title`, and the owner's typing proof matched.
- **Release 28's route.** The update ends with a restart and an `at check` on the new boot, which STOPs whenever the
  race hits.
- **The tools' own assumption.** `trial_keyboard`'s comment says "A reboot therefore always reloads the last finished
  system setting". Today that holds only by luck.

The VM rehearsals never showed it: their consoles are free when the setup runs.

## What to build

1. **A unit that loads the finished console setting once the splash has quit.** Read `vconsole.conf` the way systemd
   does; never hard-code `de`. Preferred: a oneshot service that runs systemd's own setup on one fixed text console,
   `/usr/lib/systemd/systemd-vconsole-setup /dev/tty3`. Opening tty3 allocates it in text mode, so the setup finds a
   console it may configure. The kernel keymap is global, so this sets every console's map.
   - Order it after `plymouth-quit-wait.service` and `systemd-vconsole-setup.service`, wanted by the boot's default
     target the way the image enables its other units. Check how the image ships and enables units: `os/config`,
     `os/build.sh`, presets.
   - It must never delay or break the graphical login. If it fails, it logs and the boot goes on.
   - It must not fight the tools' layout trials. A trial's `loadkeys` is runtime-only, and a reboot must load the
     finished setting, which is exactly what this unit does.
   - Check systemd's `vconsole-setup` source or man page for this argument form. If it doesn't work as described, use
     `loadkeys -C /dev/tty3` with the map from `vconsole.conf`, with the same ordering, and say why.
2. **Image checks** (`os/ci/image-checks.sh` or wherever the image's static checks live): the unit file is present,
   root-owned, has the expected content, and is enabled.
3. **A VM check in the check build** (the VM pass that prints `CHECK_BUILD_VM_PASSED`):
   - after boot the unit has run successfully;
   - `dumpkeys -C /dev/tty3 --keys-only` shows keycodes 21 and 44 matching `vconsole.conf`'s map (the same rule as the
     tools' `check`: `z`/`y` for `de`, `y`/`z` for `us`).
   - If you can, make the VM hit the race once: put a console in graphics mode, or run the unit's command after a forced
     skip, and show the unit repairs it. If you can't, say so.
4. **Unit tests** for any script logic, and the static test that pins the image's file list, if one exists.
5. **Release 28's diff:** say exactly which paths this adds or changes in the image, and whether package 42's
   `os/ci/release_diff.py` rules (on `pkg/42-release-28`) explain them already or need a rule. Don't change package
   42's branch; write it in your notes for the lead.

## Rules

- Branch `pkg/50-console-keymap` from main, worktree `~/AresOS-50-console-keymap`.
- Read the repo's `CLAUDE.md` / `AGENTS.md` first.
- No GitHub dispatch. The lead runs the check build.
- No sudo, nothing on the running system, no rpm-ostree, bootc or ostree command.
- Don't change the owner tools (`os/owner-tools/`).
- If you change a bound file, run `python3 reviews/27-first-update-release/rebind.py pending "<note>"` (never with
  `--help`). Run the affected test modules one at a time with
  `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'`. Never run
  `test_inherited_homebrew`, `test_sysusers` or the whole suite.
- Notes go in `reviews/50-console-keymap/PROGRESS.md`: what you built, the tests and their results, what needs the check
  build, what the code doesn't show, and the release-diff note.
