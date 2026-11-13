# 30 review fixes 2: nothing on the serving loop can wait, and the last window rules

Follow-up on the same branch (`pkg/30-installed-programs`, PR #55). The two fix checks on `ab58d12f`:

- `reviews/30-installed-programs/SECURITY-2.md` (gpt-6-astra): findings 3, 4 and 5 closed; 1 and 2 still open in a new form; four known limits;
- `reviews/30-installed-programs/REVIEW-2.md` (gpt-6-astra): five findings closed; 2 and 4 open in a narrower form; two new should-fix; two nits.

Read both, `briefs/30-review-fixes-1.md`, the section "Review fixes 1" in `reviews/30-installed-programs/REPORT.md`, and the helper's discovery worker, icon pre-check and window code before changing anything.

**Builder:** a Claude agent (Opus 5.5). **Review:** the same two reviews check only these fixes, with this bar: a finding counts if the helper can stop answering, lose or change something of the owner's, or do something a program's entry did not ask for. Timing cases that need a reconnect or a switch inside half a second, and cases that need a hostile program already running as him, are known limits written into the report, not another round.

## Fixes

Security:

1. **No filesystem call on the serving loop** (SECURITY-2, finding 1). Whether a program's executable exists is worked out by the discovery worker and published with the catalogue; `list_apps` serves those values and touches no file. Opening an app checks its executable off the loop too, with a deadline of a few seconds: if the check does not answer, the launch fails as unavailable and the helper keeps serving; at most a small fixed number of such checks may be outstanding. The scan's deadline is also checked while entries are parsed and right before a catalogue is published. A test with a stand-in for a stalled mount (a check that never returns): listing, heartbeats and other launches go on.
2. **The SVG pre-check runs where the memory ceiling is** (SECURITY-2, finding 2). The check that refuses an SVG referring to pictures runs in a short-lived child under the same address-space limit and timeout as the converter (or inside the converter's own sandboxed child, before conversion), never in the helper's process. It also bounds what it will look at: the length of names and namespace addresses, the number of elements and attributes, and nesting. A test with the review's case (a 256 KiB namespace address and 50,000 differently named elements): the helper's own memory does not grow, the icon is refused, the program keeps its fallback look.

Windows:

3. **Going back to a 1.0 client drops what was pending** (REVIEW-2, finding 1): a return waiting for a discovered program is thrown away when a 1.0 client takes over, and nothing a discovered program does can force a return under 1.0. A test: the reconnect inside the waiting time.
4. **The switch he just made wins** (REVIEW-2, finding 2): when window changes are processed, the current activation is taken into account first and cancels a return that is no longer wanted, before an overdue return is carried out. A test with an activation that arrives after the deadline but before the return has run.
5. **A reviewed prefix beats a discovered exact identity** (REVIEW-2, finding 3): order of ownership is registry identities and the desktop's own window, then reviewed hints (exact, then prefix), then discovered candidates. A discovered entry whose identity falls under a hint of another program loses that identity. A test: a discovered entry with `StartupWMClass=steam_app_1086940` beside Steam, with the launcher's and the game's closing.
6. **The protection holds for the three registry apps too, under 1.1** (REVIEW-2, finding 4): when the last window of Chrome, Terminal or Notepad closes while a window nobody owns is open, the hub is not pulled in front of it. Under 1.0 the old immediate return stays exactly as it is. Change the test that asserted the exception.

Report (the nits and the known limits):

7. In `reviews/30-installed-programs/REPORT.md`: say for each new test whether it is a regression test or a control, and stop claiming that every test fails without its fix; add the visible consequences the review names (a game window that appears after the launcher's launch was closed leaves that launch closed; another launcher's `com.mojang.minecraft` window counts as Lunar Client's); add the four known limits of SECURITY-2 with what the owner would see (a style rule split across fragments can pass the pre-check, and the sandbox still contains it; an icon can be missing for a moment while it is replaced; a scan stuck on a dead drive stops new programs from appearing until the helper restarts; window identities are claims).
8. One line from the OS lead for `os/ci/image-checks.sh`: package 31's check leaves `/tmp/pkg31-home` behind; remove that folder right after its `gsettings` call. (Package 31 is on `main` now: merge `origin/main` first; if `image-checks.sh` conflicts, keep both blocks.)

## Verification

- A test for each code fix that fails without it. Only the helper's test modules on the laptop; never the whole `os/tests` suite (AGENTS.md).
- The headless end-to-end check once more (kcalc and btop).
- Push, then both hosted runs (`checks_only=true`, then `check_build=build`), each awaited with one blocking `gh run watch <id> --exit-status`; their URLs and results go into the report section "Review fixes 2".

## Rules

- As before. Worktree `/var/home/ares/AresOS-30-installed-programs`; push; never merge; never `--no-verify`. The example messages under `mod/src/test/resources/shell-1.1/` stay unchanged.
- Never open a window in the owner's session; a headless compositor with programs only while his game is not running and 4 GB are available.
- Commit after each fix. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
