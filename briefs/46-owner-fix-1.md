# 46, owner fix 1: no "Saving world" text in the home screen

The owner answered package 46's JUDGMENT-CALL (board #331, 2026-11-16): **"Hide it"**. In the home screen, Minecraft's "Saving world" text in the bottom-right corner never shows, for any save:
- the supervisor's `save_world`;
- the game's own autosave every five minutes;
- any other save.

A home screen shows no game notices.

**Builder:** a Claude agent on Opus. It's a small change to a finished package. **Review:** part of package 46's review (Codex `gpt-6-astra` `high`, Tuesday 2026-11-17).

## What changes

- **Where it's hidden:** in a game the session started (`HomeScreen.session()`) and in a desktop world (`DesktopWorld`), the HUD doesn't draw the saving indicator. This is the same gate as package 48's Esc menu, whether or not the app helper is connected right now.
  - Do it at the drawing (the HUD's saving-indicator extraction; see `HudTestAccess` and the comment in `SaveNowClientGameTest` for the names in 26.2), not by changing the player's `options.txt` setting. Outside the home screen his own setting stays in charge.
- **Everywhere else** (a normal world, the plain development client, a game the session didn't start), the indicator behaves as in Minecraft.
- **Saving itself is untouched.** Only the corner text goes.

## Tests

- **`SaveNowClientGameTest`:** its observation of the indicator becomes assertions.
  - In the home screen (session flag on, desktop world), the indicator is never drawn, for a requested save while playing, under the Esc menu and while covered, and for a vanilla autosave or a `save-all`.
  - With the session flag off, or in a normal world, it rises during a save as before (one case is enough).
- **Runs:** one full `mod/dev/client-test.sh` and one `mod/dev/build.sh`, both green.

## Docs

- `reviews/46-save-now/REPORT.md`: the JUDGMENT-CALL section records the owner's answer and what was built. Add the run results under Verified.
- `docs/design/HUB.md`, package 40's corrections section: one line that the home screen shows no "Saving world" text.

## Rules

As in `briefs/46-save-now.md`. Worktree `~/AresOS-46-save-now`, branch `pkg/46-save-now` (PR #92). Only `mod/`, `docs/design/HUB.md` and `reviews/46-save-now/` change.

Another builder (package 48) may be running client tests:
- `client-test.sh` waits for the lock;
- on exit 75 (low memory), wait about five minutes and try once more, then stop and say so.

Commit, push, and add a comment to PR #92 saying what changed.
