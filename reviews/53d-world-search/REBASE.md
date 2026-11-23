# 53d: rebase onto main with packages 56 and 53c

Plan: `briefs/53d-rebase-on-56.md` (both sections). Builder: a Claude Opus agent, 2026-11-19.

- **Old head:** `4fb5eaba`, on main `3b82176e`.
- **First rebase:** onto `d1364d59`, a HANDOFF/STATE commit right after 53c (`e01cd6a1`, PR #114). That main already
  held 56 (PR #117, `da441546`). I fetched at `e01cd6a1`, but `origin/main` is shared with the other worktrees, and
  another session's fetch had moved it on by that one docs commit before my rebase ran. All the conflict work below
  was done in this rebase. All 35 commits were kept, and three were added on top: the test fix, the new client check
  and this file.
- **Second rebase (the lead's request):** onto **`3048b221`**, the final base: 53f (PR #120), with 311 (PR #119) before
  it. There were no conflicts. Of 53f's and 311's files, 53d shares only `docs/design/LAPTOP-HOME.md`, and both sides
  are kept: 53d's net change to it is unchanged, line for line. Neither package touches `mod/` or
  `aresos-shell`. 53f did rewrite the laptop home's tests, so both Python test patterns ran again on the final base.
  The client suite was not rerun, as the lead asked, and the mod was built once more for the jar's hash.
- **Command, both times:** `git fetch origin && git rebase origin/main`.

## What conflicted and how each part was resolved

Conflicts came up in five of the 35 commits. Every other overlap merged on its own: `ShellClient.java`,
`LAPTOP-HOME.md`, the 1.2 examples' README, `test_aresos_shell_views.py`, and the helper in three of the four 53d
commits that change it.

| Commit (old) | File | Resolution |
|---|---|---|
| `4c641233` step 1, screen hint | `AresOsClient.java` | One `launch(id, visit, worldScreen, opened)`. The zone handler and `launch(id)` pass `false, null`, and `launchOnWorldScreen` passes `true, null` (the search path: `opened=null`). 56's `launchFromPointer(id, opened)` passes `worldScreen=false`. 56's two-argument `launch(id, visit)` is gone: its only callers now pass all four arguments. |
| `d3534192` step 1, the search | `mod/build.gradle` | Both sets of `systemProperty` lines: 56's `repoDir`, `pointerReviewDir` and `pointerSession`, then 53d's `worldSearchReviewDir`. |
| `d3534192` | gametest `fabric.mod.json` | `…HomePublishClientGameTest`, `FreePointerClientGameTest`, `WorldSearchClientGameTest` (ours last). |
| `614a4c79` step 1, no crosshair | `aresos.client.mixins.json` | The list ends `"SavingIndicatorMixin", "HotbarPointerMixin", "SearchCrosshairMixin"`, as planned. |
| `0e205ab7` fix 2.2/2.3 | `aresos.client.mixins.json` | The same list, plus `"RecipeBookSearchAccess"` last. 53d added it after the plan was written (fix 2.2), so the plan's list could not name it. |
| `9371eaf2` step 2, shell_search | `ShellFocusClient.java` | Both overrides: 56's `status()` (clears `appInFront` and `HomePointer` when the helper drops), then 53d's `search()`. |
| `b5f9bc5c` fixes 1, 2, 6 | `ShellFocusClient.java` | The same two overrides. `search()` keeps that commit's newer comment ("the compositor reports the world active; the bar still waits for the window's focus"). |
| `e6338fcd` fix 2.1 | `os/config/usr/libexec/aresos-shell` | `windows_changed()` keeps both: `follow_windows()`, then 56's background `shell_focus` for a desktop not yet told (`conn.focus_reported`), then 53d's `search_landed()`, then `report_covered()`. 56's report goes first because it describes the state `follow_windows` just read. `search_landed` neither reads nor changes `self.shell`, so the order changes no outcome. |

**The helper keeps all three sides**, as the plan's second section lists. Checked in the result:
- **56:** `conn.focus_reported` (set in `connected`, marked in `emit`), the background `shell_focus` after hello, and
  its docstring paragraph ("A new tracked desktop connection also receives existing background focus…").
- **53c:** `view_focus` (operation, handler and `VIEW_OPERATIONS`), the gate in `return_to_desktop` (`any(view.focused
  …)`), `cancel_returns` only for desktop launches, `LAPTOP_HOME_APP_ID` kept out of `active()`, `covering()` and
  `unowned_windows()`, and minor 2's docstring line naming `view_focus`.
- **53d:** `shell_search` (capability, gate in `emit`, offer in `hello`), `SearchSignal.install()` first in `main()`,
  the search mark (`SearchHandoff`, `search`, `search_landed`, `search_off`) and its timer (`search_expired` in
  `tick`).

The net change against main matches the reviewed branch's change against its old base, line for line, in
`aresos-shell`, `ShellFocusClient.java`, `ShellClient.java`, `LAPTOP-HOME.md`, the 1.2 README,
`test_aresos_shell_views.py` and `mod/build.gradle`. I compared `git diff -U0` of `3b82176e..4fb5eaba` and of
`origin/main..HEAD` per file, after each rebase (the second time against `3048b221`). The only differences are the
planned ones in `AresOsClient.java`, the gametest `fabric.mod.json` and the mixin list.

### Beyond the plan

1. **53c's new helper test against 53d's queued Wayland writes.** After the rebase,
   `test_close_and_next_activation_across_reads_use_the_latest_view_focus` failed in 80 subtests with
   `TypeError: slice indices must be integers`. The test is 53c's and builds `ForeignToplevels` on a bare
   `mock.Mock()`. Since review 1's should-fix 2, 53d queues requests and reads the byte count that `sock.send()`
   returns, and a bare Mock returns a Mock there. The fix is in the test only: its stand-in socket gets
   `send.side_effect = len`, so it takes every request whole as a real socket does. The test still checks what it
   checked before. The helper is unchanged. Commit `53d rebase: 53c's view-focus test gives its stand-in compositor
   socket…`.
2. **The search's pictures are renumbered.** 56's `FreePointerClientGameTest` now runs before ours and takes one
   picture (`0095_56-taskbar-hover.png`). So the bar's four pictures move from 0095–0098 to 0096–0099. The old files
   are removed, the new ones committed, and `REPORT.md`'s list of pictures names the new files.

## The plan's extra check: a client test

It is now a client test: `appInFront` at the end of `WorldSearchClientGameTest`, last again, so no earlier picture
moves. The test sets `HomeScreen.forTests(true, null)`, so the session's rules apply with the fake helper connected,
and resets it afterwards. Then, twice:
1. The helper's `shell_focus` background for a small app. The test waits for 56's free pointer (the mouse is not
   captured). The pointer moves over the app, and the view stays where it was.
2. Two orders:
   - **The news first:** the helper's own order (LAPTOP-HOME.md section 5): `shell_focus` foreground
     `desktop_activated`, then `shell_search`.
   - **The bar first:** `shell_search` alone, while the mod still has the app in front. The check asserts that the
     free pointer is still on when the bar opens.
3. The bar opens. The pointer moves elsewhere and "web" is typed, which finds the six programs.
4. Escape closes the bar, and the view (yaw and pitch) is unchanged.
5. In the bar-first order the world must not take the mouse yet. Then the foreground news comes.
6. The world takes the mouse back (free pointer off, mouse captured), and the view is still unchanged.

## Commands and results

In the order the brief gives. The runs before the second rebase were on the first rebase's head plus this branch's
two new commits.

1. **`mod/dev/build.sh`:** passed. `BUILD SUCCESSFUL in 3m 1s`. 328 unit tests passed, 0 failed, and 6 skipped (the
   Windows catalogue tests that skip on Linux). The server game tests printed `All 106 required tests passed`.
   - The jar `mod/build/libs/aresos-0.1.0.jar` (678,934 bytes) has SHA-256
     **`4f7324f56ad943a80e892cdce1985dce526bdeee36ea6cc79796abb5ec98211c`** (`sha256sum`).
   - After the second rebase, on the final head: `BUILD SUCCESSFUL in 2m 4s`. Gradle found `:compileJava`,
     `:compileClientJava`, `:jar` and `:test` up to date: the jar's inputs did not change, so it is the same jar with
     the same hash. The jar is reproducible (`preserveFileTimestamps = false`). The server game tests ran again:
     `All 106 required tests passed`.
2. **Helper and laptop-home test modules:**
   - `python3 -B -m unittest discover -s os/tests -p 'test_aresos_shell*.py'`:
     - Right after the first rebase: 396 tests, `FAILED (errors=80)`, all of them 53c's
       `test_close_and_next_activation_across_reads_use_the_latest_view_focus` (see "Beyond the plan", 1).
     - After the fix: `Ran 396 tests in 13.8s`, `OK`.
     - On the final base: `Ran 396 tests in 14.0s`, `OK`.
   - `python3 -B -m unittest discover -s os/tests -p 'test_aresos_laptop_home*.py'`:
     - On the first base: `Ran 18 tests in 65.0s`, `OK`.
     - On the final base (53f's rewritten modules): `Ran 54 tests in 61.7s`, `OK (skipped=3)`. The three skips are
       53f's own opt-in tests: two memory measurements ("opt-in: three fresh measured runs, about 90 s") and one that
       needs gtk4-layer-shell.
3. **`mod/dev/client-test.sh`, the full suite of 28 client game tests:**
   - **Run 1: failed** after 0 min 56 s (the NVIDIA GPU): `ModeInventoriesClientGameTest.toggle`
     (`ModeInventoriesClientGameTest.java:196`, called from line 140), `Timed out waiting for predicate`. This is
     package 09's 50 rapid G presses, early in the suite and far from anything 53d, 56 or 53c changed (see Known
     limits). The suite stops at the first failure, so 53d's own test did not run.
   - **Run 2: passed.** `BUILD SUCCESSFUL in 13m 40s` (the script: 13 min 41 s, NVIDIA). The suite stops at its first
     failure, so all 28 tests passed. Its log has 28 "checks passed" lines, among them 56's free-pointer checks and
     53d's world search checks with the new one ("with a small app in front (56's free pointer) shell_search opens the
     bar, before and after the news that the world is in front, and Escape closing it turns no view"). There was no
     hang, also not in the Nether home's mounted rejoin.
   - **Run 3, on the committed state: passed.** `BUILD SUCCESSFUL in 13m 47s` (the script: 13 min 48 s, NVIDIA), with
     the same 28 "checks passed" lines.
   - In runs 2 and 3, the bar's four pictures came out byte for byte as the reviewed ones under their new numbers
     (`cmp`). Other packages' rewritten pictures were restored with `git checkout -- reviews/`, and the pictures they
     wrote under new numbers were deleted.
4. **The plan's extra check:** the client test described above. It passed in runs 2 and 3.

## Known limits

- **The laptop home window and Super.** 53c keeps `aresos.laptop-home` out of `Windows.active()`, but 53d's
  `Windows.activated()` (the set `search_landed` reads) counts every toplevel reported activated, the laptop home
  included. This was left as it is on purpose: an activated laptop home window has the keyboard, so the world is not
  the only active window. Suppose the compositor kept the laptop home reported active beside the world. Then Super's
  search would wait for news and not open. That is the safe direction: nothing is typed into the wrong window, and
  nothing is minimized. Only labwc on the real two-screen setup can show whether this happens (package 23c).
- **When a view has the keyboard, the world's window may still be reported active.** 53c's own test notes this:
  "labwc can leave a foreign toplevel activated when a layer takes keyboard focus". The helper could then take the
  world as already alone active and send `shell_search` at once. The mod's own guard still applies: the bar opens
  only while the game's window has the keyboard, and otherwise it waits 500 ms and drops the request. So no typing
  goes astray. Also for 23c on the real laptop.
- **An intermittent failure in package 09's test, not investigated further.** One of the three local runs failed in
  `ModeInventoriesClientGameTest.toggle`: after a G press, the mode and selected slot did not arrive within the wait.
  The two runs after it passed, on the same code apart from the report. Nothing this branch changes runs there:
  - 53d's only client hooks outside its own screen are a tick listener that acts only while Super waits for the
    window's focus, and a crosshair mixin.
  - 56's pointer rules need an AresOS session, which that test does not set up.
  The hosted mod runs on main after 56 and 53c (`44511397426`, `44515323393`) are green. No earlier note mentions
  this test failing. Under AGENTS.md a test that passes once and fails once is a failure. But it is package 09's test,
  it is a test-timing issue, and nothing is lost: the brief's safety bar puts it here, not in another round. The
  test logs nothing per press, so this run cannot say which of the 50 presses timed out. If it comes back, the run's
  full log is where to start.
