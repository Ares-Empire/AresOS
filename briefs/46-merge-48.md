# 46, merging package 48: one home screen with saves and New home

Package 48 (the Esc menu, New home and the first start) is on main since 2026-11-17 (PR #94, `dec90106`). Package 46 merges second, so this branch takes the integration items that 48's reviewer listed at the end of `reviews/48-home-menu/REVIEW-1.md`.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`. Run it after review fix 2 (`briefs/46-review-fix-2.md`) is committed on this branch. **Review:** one fresh Codex `gpt-6-astra` `high` review covers review fix 2 and this merge together.

## What changes

1. **Merge `origin/main`** into `pkg/46-save-now`, and resolve every conflict so both packages keep all their behaviour:
   - both packages' client initialisation;
   - production and test mixin registrations;
   - client-test entries;
   - Gradle properties.

   Keep 48's screenshot numbering as it is on main, append 46's own after it, and update test-order comments that the merge makes stale.
2. **`save_world` while New home runs:**
   - For the whole of `HomeSwitch.busy()`, `save_world` answers `ok:false, reason:"no_world"`. That covers:
     - requests that arrive during the switch;
     - requests queued or joined before it started;
     - a save that would otherwise run against the staging world or the closing old home.
   - No `world_saved ok:true` may come from the staging world.
   - Once he is in the new home (or recovery has reopened a world), requests work as normal.
3. **One home gate.**
   - 46's `HomeScreen.home` and 48's `HomeRules` menu gate use one shared predicate: a session game in a desktop world, independent of whether the app helper is connected.
   - Put it in one place and have both call it. Delete the duplicate.
4. **No "Saving world" text during New home.** 46's HUD suppression and 48's working-screen replacements both stay. During New home and recovery the corner text never shows: not while the old home closes, not in the staging world, not in the new home.
5. **`ShellFocusClient.readyWorld`:** keep 48's busy guard, and use 46's `DesktopWorld.saveName(server)` for the world's name on the wire.
6. **`SaveNowClientGameTest`** (around its lines 126 to 138) still expects a paused `PauseScreen` in a session desktop world. Esc there now opens the AresOS menu, which doesn't pause, so:
   - assert that menu instead;
   - keep a paused-save case through Settings, or through a separate vanilla-menu case;
   - keep the covered-world case.

## Tests

- **`save_world` during New home:**
  - one request during a successful flat switch;
  - one during a failed switch with recovery;
  - one queued just before the switch started.

  Each answers `no_world`, and a request after arrival answers `ok:true`.
- **The saving text:** assert that New home shows no "Saving world" text at any point. Check through the drawing, as 46's suppression test does.
- **The shared gate:** a test that both callers agree in each of the four cases (session on or off × desktop world or normal world), with the helper connected and not.
- **Both packages' existing tests** stay green.
- **Runs:** one full `mod/dev/client-test.sh` and one `mod/dev/build.sh`, both green.

## Docs

- `reviews/46-save-now/REPORT.md`:
  - a "Merge with 48" section: what conflicted and how it was resolved;
  - each of the items above;
  - the run results.
- `docs/design/HUB.md`, package 48's section: one line that `save_world` answers `no_world` while New home runs and that no "Saving world" text shows during it.
- `docs/design/OS-BASE.md`, row B1: the same `no_world`-while-switching sentence.

## Rules

As in `briefs/46-review-fix-1.md`:
- the same worktree and branch (PR #92);
- the lock and exit-75 rule;
- only `mod/`, `reviews/46-save-now/`, `docs/design/HUB.md` and row B1 of `docs/design/OS-BASE.md` change.

The hold on `rpm-ostree`, `bootc` and `ostree` is lifted (linux-aresos, 2026-11-17). This package still needs none of them, so run none. Never run the whole `os/tests` suite.

End each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`. Commit, push, and comment on PR #92. Never merge, never push to main, never `--no-verify`.
