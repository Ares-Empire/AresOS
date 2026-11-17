# 51: The first-start window's text after package 48 (rides release 28)

Empire board brief 304. Written 2026-11-17 by `linux-aresos`.

## Why

Package 48 (PR #94, merged 2026-11-17) changed the first start. A session game that reaches its first title screen
without an AresHub folder now shows "Making your home…", creates the flat home and opens it in Live mode, so the
title screen never shows. Only if creation fails does the title screen with the AresOS button show, as before
(`reviews/48-home-menu/REPORT.md`, "For linux-aresos").

The desktop keeper's window (`os/config/usr/libexec/aresos-desktop`) still says otherwise:
- SETUP, step 3 (`message()`, about line 976): "On the title screen click AresOS, keep or change the seed, and click
  Create."
- `forget_hub()` (about line 1881): "The next start makes a new hub (title screen, AresOS button). Type retry."

The owner meets the SETUP window right after the update to release 28, because release 27 has no Minecraft desktop.
So the text has to be right in release 28.

## What to change

1. SETUP step 3: the home is made by itself. Use linux-hub's suggested wording, "Making your home… (the first start
   takes a moment)", fitted into the numbered steps. Add one short line for the rare case where creation fails and
   the title screen shows: click AresOS, then Create. Keep "Your hub is built and saved in <world>". Keep the plain
   style, short lines and the other steps unchanged. Check `setup_closed`'s lead ("Minecraft closed before your hub
   was created") still fits; it does unless you find otherwise.
2. `forget_hub()`'s message: the next start makes a fresh flat home by itself. Then "Type retry."
3. `world_missing`'s line "To start a new hub instead: aresos-desktop forget-hub then retry" stays.
4. Update every test that pins these texts (`os/tests/test_aresos_desktop.py` and any other). Add a test that the
   SETUP text no longer tells him to click Create as the normal path.
5. Grep the guides (`docs/`) for the old first-start instruction ("click AresOS", "click Create") and list what you
   find. Change a guide sentence only where it describes release 28's first start, and list each change.

## Rules

- Branch `pkg/51-setup-text`, worktree `~/AresOS-51-setup-text`. Read `CLAUDE.md` / `AGENTS.md` first.
- No sudo, no dispatch, no rpm-ostree, bootc or ostree command. Don't change `mod/` or `os/owner-tools/`.
- If a bound file changes, run `python3 reviews/27-first-update-release/rebind.py pending "<note>"` (never with
  `--help`).
- Tests: one module at a time with `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'`.
  Never run `test_inherited_homebrew`, `test_sysusers` or the whole suite.
- Notes go in `reviews/51-setup-text/PROGRESS.md`.
