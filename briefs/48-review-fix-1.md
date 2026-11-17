# 48, review fix 1: New home's recovery, and three smaller fixes

`reviews/48-home-menu/REVIEW-1.md` (Codex `gpt-6-astra` `high`, head `79c9b1a5`) has four findings: one blocking, two should-fix and a nit. It found the main staging order sound: the forward renames, a kill between them, and the undo of a failed second rename. The defects are in what happens after that. Fix all four.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`. **Review:** a fresh Codex `gpt-6-astra` `high` context. It checks only these fixes and what they touch.

## What changes

### 1. Recovery always reopens the old home where it really is (blocking)

`HomeSwitch.java:188`, `HomeSwap.java:103`.

**The failure today:** the new home is promoted, then fails to open, and moving it back to staging also fails. AresHub then still holds the new world, and the old home sits under its dated name. `restoreAndOpen` opens AresHub anyway and says "Your home is as it was". If that reopen fails too, `fail()` drops recovery: the title screen becomes allowed, and the working screen can stay up forever.

**Fix:**
- Track where the old home actually is at every point of the switch, and reopen that folder, whether or not an AresHub folder exists.
- The chat line says what really happened. If the old home is open under its dated name and the new world still sits in AresHub, say so plainly, and don't say "as it was". Log both folder names.
- Keep the recovery state until a world is open.
  - If reopening fails, show a small screen that says the home couldn't be opened, with a **Try again** button. Not the working screen, and not the title screen.
  - The session's normal rule (no title screen in a session) stays in force throughout.

**Tests:** inject failures into each of the two restoration renames and into a failed reopen. Check:
- which world is actually open (its folder and its level name), not only that some world opened;
- the chat line;
- that Try again reaches the old home once the fault is lifted.

### 2. New home from a world that isn't AresHub (should-fix)

`AresOsMenuScreen.java:40`, `HomeSwitch.java:97`.

**The failure today:** the menu allows New home in every desktop world, but the switch assumes the open world is AresHub. It never records which save folder it closes, so:
- from a dated archive (which fix 1's recovery can leave the owner in), New home archives and replaces the unrelated AresHub;
- on failure, it reopens AresHub instead of the world he left.

**Fix:** support it explicitly.
- Before closing anything, record the world he is in and its save folder, and check that it exists.
- New home makes a new AresHub:
  - if an AresHub folder exists, it is kept under a dated name as today, whether or not it is the open world;
  - the world he was in is never renamed unless it is AresHub itself.
- On failure, recovery reopens the world he was in. That's the recorded folder, wherever fix 1's tracking says it is now.

**Tests:**
- New home from a dated archive while an AresHub exists;
- New home from a dated archive while no AresHub exists, which is fix 1's leftover case;
- a failure in each, checking that he returns to the archive he was in.

### 3. Cancel leaves Create disabled (should-fix)

`HomeCreateScreen.java:49`, `AresOsMenuScreen.java:70`. Create disables itself before the confirmation opens, and Cancel returns to the same chooser without running `init()` again.

**Fix:** re-enable Create when the confirmation is cancelled, and keep the choices made (home type, seed).

**Test:** Create, then Cancel, then Create again, without changing the type or reopening the chooser.

### 4. Stale key hint (nit)

`AresOsMenuScreen.java:54`.

- **The hint:** build it each time the menu is shown, including on the return from Settings, so rebinding G or the inventory key shows the new keys.
- **The tooltip:** the Build-mode tooltip on Apps… names the actual mode key, not a fixed "G".

**Test:** rebind, return to the menu, and check the hint shows the new key.

## Runs and docs

- **Runs:** one full `mod/dev/client-test.sh` and one `mod/dev/build.sh`, both green. Also keep the existing tests green.
- **`reviews/48-home-menu/REPORT.md`:**
  - a "Review fix 1" section saying what changed for each finding;
  - the run results under Verified.
- **`docs/design/HUB.md`:** update where it describes New home's failure path, the recovery screen and the "Try again" button.

## Not in this fix

Package 46 (PR #92) is a separate branch, and its merge with this one is a later brief. Don't merge it in or build its integration items here:
- `save_world` while busy;
- one shared home gate;
- the "Saving world" text during New home;
- `SaveNowClientGameTest`'s pause case.

## Rules

As in `briefs/48-home-menu.md`. Worktree `~/AresOS-48-home-menu`, branch `pkg/48-home-menu` (PR #94). Only `mod/`, `docs/design/HUB.md` and `reviews/48-home-menu/` change.

- Other builders share the laptop. `client-test.sh` waits for its lock by itself. On exit 75 (low memory, or the owner's own game), wait about five minutes and try again, at most six times, then stop and say so.
- Until further notice:
  - run no `rpm-ostree`, `bootc` or `ostree` command, not even a read-only one;
  - run no `os/tests` owner modules;
  - mount no disk.
- End each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`.
- Commit, push, and add a comment to PR #94 saying what changed. Never merge, never push to main, never `--no-verify`.
