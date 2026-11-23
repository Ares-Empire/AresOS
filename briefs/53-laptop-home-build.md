# 53: the laptop home, built (lead handoff)

Board brief 306, board #335. This is a handoff from `linux-hub` (2026-11-17) to the session that leads this build. It is not a builder brief: the lead writes one short brief per step from it.

**The design.** It is `docs/design/LAPTOP-HOME.md` (package 44, PR #88).
- **The owner's answers are all in.** Section 10 has them: the street by day on terraces, night kept as a second look in the same page, apps dimmed until used, only the clock, date and battery, pins changed in the world only, and Super opens a search over the world.
- **No answer from board #323 is still open.** The one owner look still to come is the search bar's look (step 5): show him pictures before it merges.
- **Every step brief carries the review findings** in section 9's "For the build brief" list.

## The four steps (section 9 numbering)

| Step | What | Where | Client-test lock |
|---|---|---|---|
| 1 | `aresos-shell/1.2` in the helper: views with the view token, `get_home`, `home_changed`, `apps_running`, and the tests listed in section 9.1 | `os/config/usr/libexec/aresos-shell`, `os/tests/test_aresos_shell_*.py` | no |
| 2 | The mod sends `publish_home` after hello and on every change | `mod/`, against `FakeHelper` | yes, for the client game test |
| 3 | The window program and the page, against a stand-in helper: the town, finder, hotbar, lit houses, the `shots.sh check` checks, the vendor pin and the scheme rules | a new program under `os/` | no (headless compositor; pin Mesa from the first run so it never wakes the NVIDIA card) |
| 5 | Super opens a search over the world. Four parts: the `rc.xml` keybind, the supervisor's `search` command, the helper's `shell_search` event, and the mod's search bar | `os/config/usr/share/aresos/labwc/rc.xml`, `os/config/usr/libexec/aresos-desktop`, the helper, `mod/` | yes, for the mod part |

- **Order:** 1 first. Then 2 and 3 side by side, because only 2 takes the lock. Then 5.
- **What waits for the release:** step 6 (the trial with the monitor) waits for 23c on the laptop.
- **Release cut:** the cut is Thu 2026-11-19 12:00, and what rides is what main has then. 53a (the helper's 1.2) and
  53b (the mod's `publish_home`, jar `d4f6e9a6`) are on main, so they ride R28. They are inactive there: no view token
  and no laptop home, so the owner sees no change (confirmed to `linux-aresos` 2026-11-18). **53c (PR #114) merges
  only after the cut**: it adds an image check for WebKitGTK and changes the helper's focus handling.

## linux-aresos and 23c

- **Step 4 belongs to `linux-aresos`.** That is the supervisor making the view token and starting and stopping the laptop home with 23c's screens. It is package 23c (STATE.md "Package 23c", the release after next).
- **Image work:** ask `linux-aresos` for gtk4-layer-shell, JetBrains Mono and the Mesa vendor pin in the image. Step 3 only checks that they are there.
- **Before step 5:**
  - ask `linux-aresos` whether the supervisor's `search` command goes in with 23c or after it, since both change `aresos-desktop`;
  - give notice before editing `rc.xml`.
- **What `linux-aresos` gets:** the PR number for its read of any `os/` diff, and one line per merged mod PR with the jar hash (from main's Mod run log).

## Worktrees and branches

- **This branch:** `pkg/53-laptop-home`, worktree `~/AresOS-53-laptop-home`. It holds only this handoff.
- **Each step** gets its own branch from origin/main: `git -C ~/AresOS worktree add ~/AresOS-53a-shell-views -b pkg/53a-shell-views origin/main`, then 53b, 53c and 53d. Its PR carries its brief and, on the first one, this handoff.
- **Never write in `~/AresOS` itself.**
- **`mod/` is shared with `linux-hub`.** Before step 2 or step 5's mod part starts, send it the mod files the step touches.

## Models and reviews

**Codex ends Sat 2026-11-21.** Until then the plan below holds. After that, builds and reviews go to Claude agents (Opus by default), as CLAUDE.md says.

- **Lead:** Opus, kept light. Builds and reviews run on Codex.
- **Builders for steps 1, 2 and 5:** Codex `gpt-6.1-sol` `xhigh`, run with `< /dev/null`. These steps are data and rules with tight briefs, so Sol fits.
- **Step 3's builder:** also Sol. The look is already designed: it ports the study's day street from `reviews/44-laptop-home/prototypes/street/` and `prototypes/shared/`, and checks against its pictures and `tools/shots.sh`.
- **The search bar's look (step 5):** new design work, so it goes to a Fable agent per CLAUDE.md. It is small: a few pictures for the owner.
- **A step that keeps failing review:** if it still fails after two fix rounds, change the builder (Fable, or Astra while Claude is tight) and say why.
- **Reviews:** a fresh Codex `gpt-6-astra` `high`, read-only, writing `reviews/53x-*/REVIEW-N.md`. Merge on SAFE with the checks green.
- **Security pass:** the view token, the `LD_PRELOAD` and token removal, and the `aresos-home:` scheme are security-sensitive. Step 1's review and step 3's review each get one focused pass on them.

## Machine rules (from AGENTS.md and the hub's practice)

- **The client-test lock:** one game at a time machine-wide, shared with `linux-hub`'s queue.
  - `mod/dev/client-test.sh` exits 75 under 6 GiB free: wait about five minutes and retry.
  - Only steps 2 and 5's mod part need the lock.
- **Tests:** never run the whole `os/tests` suite on the laptop; name the test modules.
- **No access to the owner's session:**
  - Headless compositors only. Never open a window in, reconfigure or send input to his session (`wayland-0`).
  - Never touch his `.minecraft`, Lunar Client or `~/AresOS-try`.
- **The repo is public:**
  - test apps get generic names ("Test Web 1") and generated pictures;
  - no real app icons and no screenshots of his screen.

## Since the handoff (linux-laptop-home, 2026-11-18)

`linux-aresos` answered the asks above (14:25):
- **Image items ride R29**, in one OS image package after the R28 cut: gtk4-layer-shell, and JetBrains Mono under
  `/usr/share/fonts/aresos/`. It sends the package number.
- **The Mesa vendor pin is not an image change.** Bazzite already ships `/usr/share/glvnd/egl_vendor.d/50_mesa.json` and
  `/usr/share/vulkan/icd.d/intel_icd.x86_64.json`. The pin is the supervisor's launch environment for
  `/usr/libexec/aresos-laptop-home` (`__EGL_VENDOR_LIBRARY_FILENAMES`, `VK_DRIVER_FILES`), so it goes with 23c. The
  image package adds a check that both files exist. 53c sets the same environment in its own tests.
- **The view token's contract** is fixed in 53a's brief (A2), and 53a writes it into section 5 for 23c's brief.
- **The supervisor's `search` command goes into 23c**, as a step of its own, because both change `aresos-desktop`.
  53d keeps the helper's `shell_search`, the mod's bar and the `rc.xml` keybind (with notice to `linux-aresos`).
- **Package 25** (the supervisor's recovery fixes) came over to this session as second work. It rides R29 at the
  earliest and gets a Fable review (or Astra while Codex lasts), because it guards the world through save and
  shutdown. Its notes are in STATE.md ("P2's remaining packages", package 48's leftovers, 23b's late SIGTERM).
- **Known hang in the client suite** (`linux-hub`, 14:25): `NetherHomeClientGameTest.testMountedRejoin` can
  deadlock while closing (render thread in `IntegratedServer.halt`/`executeBlocking`, server at a Fabric test
  barrier). PR #108 (package 54, commit 345ba61d) carries a test-only fix. Until it merges, 53b's and 53d's briefs say
  that a full suite hung in that test is this bug, not theirs.
- **The safety bar for every review and fix round** (decision 24, as clarified 2026-11-11; the owner restated it
  2026-11-18 through `mac-capacity`: "it needs to be reasonable … safe right? Not every edge case safe? We once wasted
  time on that … genuinely legitimate safety things make sense to do"):
  - Real-harm findings get fixed: data loss, credentials (the view token), system changes, anything hard to undo.
  - Low-harm edge cases go under Known limits or into a follow-up, not into another fix round.
  - Every reviewer brief states this bar.
- **Brief reviews** (the owner, 2026-11-18 through `mac-capacity`): one Claude review, then one cross-model review (Codex
  while it lasts), or straight to the Codex one while Claude is tight. Then build. Another round only for a blocking
  design flaw, as a targeted recheck; should-fixes and low-harm edge cases go to the code review or Known limits.
  53a's brief goes straight to one Codex review (Claude at 80% this week).
- **Codex pace** (`mac-capacity`, 2026-11-18 16:50): 88% left at 16:44. The average must stay near 1.6%/h until Fri
  12:00, so 20% is left for the Fri–Sat reviews. Until Thu 00:00: one Codex build at a time (53c run A starts after
  53b's build). ~~From Thu 00:00 builds go to Claude Opus agents~~ **(2026-11-18 22:25, replacing the 21:50 note: Codex is renewed, so its 83% must last until about Wed 25 Nov 14:49,
  about 12% a day across all leads. Builds go to Claude Opus agents from Thu 00:00; a Codex build already running
  finishes and stops; Codex Sol for cross-reviews)**, and Codex does the
  cross-reviews (`gpt-6.2-sol` by default, `gpt-6.2-astra` only where the stakes need it, such as 53c's security
  pass). Codex's second-model review is the part Claude can't replace.
- **The laptop home is native** (owner, board #375, 2026-11-18: "yea sounds good"). 53e measured the WebKit page at 418
  MiB PSS at rest at best (524 unchanged) against 47 MiB for a native GTK 4 and Cairo town. 53c still merges after the
  cut (its program skeleton and helper changes stay); 53f replaces its web view and page with a native drawing of the
  same look and deletes the web engine. The companions later bring their own web view, only while switched on.

## Where the next lead starts (linux-laptop-home, Thu 2026-11-19 07:00)

Everything open is reviewed SAFE with green checks; nothing runs. STATE.md (package 53's entry) has the details.
1. **Wait for `linux-aresos`'s "cut taken" line** (R28, Thu 12:00). It covers #114 and #121; the order is ours.
2. **PR #114 (53c):** check its checks are green on its head, then squash-merge.
3. **PR #120 (53f, draft, based on 53c's branch):** rebase onto main, mark ready, wait for green checks, ask
   `linux-aresos` to read its os/ diff, merge.
4. **PR #121 (53d):** after `linux-hub`'s package 56 (PR #117) merges, rebase per `briefs/53d-rebase-on-56.md`, run the
   client suite twice (`mod/dev/client-test.sh`, the lock), a short Codex Sol recheck of the merge resolution, merge.
5. **After each mod-PR merge:** send `linux-aresos` one line with the jar hash from main's Mod run log.
6. **Package 25** (`pkg/25-guardian`, worktree `~/AresOS-25-guardian`, brief `briefs/25-guardian.md`, handoffs and
   decisions in `reviews/25-guardian/PROGRESS.md`): once `linux-aresos` says R28 is through, start
   `gh workflow run "OS image" --ref pkg/25-guardian -f check_build=build` and watch it from a shell. Then step 8 with
   its run ID: fix what the VM checks show, section 5's docs, the REPORT, the PR. Then a fresh Codex `gpt-6.2-astra`
   `high` review with a data-safety pass, and `linux-aresos`'s os/ read. Once 25 is on main, tell `linux-hub` that
   hub-try and `~/AresOS-try` need a stand-in SYSTEMCTL answering active. The VM step adds 3–4 minutes to its
   20-minute limit.
7. **Then** STATE.md and this handoff, worktrees and branches cleaned up, `board done` on #357, #358, #359, #369, #383,
   #384, #387 as each closes, and "ready to clear" to `mac-capacity`.

**Claude budget (the owner, 2026-11-19 through `mac-capacity`):** about 2% of the week per lead per day; one Claude agent
at a time; fresh agents with short handoffs; Opus by default, Fable only for installs, rollback, credentials and
security, so package 25's step 8 goes to Opus (or Codex Sol, within Codex's 12% a day). No agent waits on CI; shell
watchers do.

## Thu 2026-11-19 afternoon (the new linux-laptop-home, from 12:20)

- **#114 (53c) merged** as `e01cd6a1` (OS run 44511583671 green). Board #359 done.
- **#120 (53f) merged** as `3048b221`: rebased with `git rebase --onto origin/main 88d5afe6` (no conflicts), OS run
  44515384290 green, `linux-aresos` read its os/ diff. Board #384 done. No mod files, so no jar line.
- **#121 (53d) merged** as `c576818b` after OS run 44522704032 went green on attempt 3 (attempts 1 and 2 hit
  Ubuntu mirror 503s before any test). Jar `4f7324f5…` (main's Mod run 44532278666) sent to `linux-aresos` and
  `linux-hub`. Board #383 done. The 53c, 53d, 53e and 53f worktrees and local branches are removed (remote branches
  kept).
- **Package 53 is done on this side:** steps 1, 2, 3 and 5 are on main; step 4 is 23c (`linux-aresos`, after R28 is
  published); step 6 (the laptop trial) waits for 23c. #358 stays open (53a's three low-harm follow-ups).

## Where the next lead starts (Thu 2026-11-19 14:35)

Only **package 25** is open (`pkg/25-guardian` at `e203e527`, worktree `~/AresOS-25-guardian`, brief
`briefs/25-guardian.md`, `reviews/25-guardian/PROGRESS.md`; board #357 and #387).
1. Its check build is **OS run 44533435611** (`check_build=build`, dispatched 14:30; `linux-aresos` said it need not
   wait for R28's last steps on pkg/42). Watch it from a shell (`gh run watch 44533435611 --exit-status --interval
   300`), never from a Claude agent. **It failed (14:41)** in "Throwaway image build and checks", before the VM:
   `os/ci/image-checks.sh`'s old rule "no system unit starts the desktop" (`grep -rlE 'aresos-desktop|prismlauncher'`
   over `/usr/lib/systemd/system` and `/etc/systemd/system`) finds 25's new `aresos-guardian.service`. Every image
   check before it passed. Step 8's first fix: narrow that rule so it still catches a unit that starts the desktop
   but allows the guardian (say why in the REPORT; `linux-aresos` reads it), then dispatch the check build again
   for the VM part.
2. **Step 8** with that run's ID, one fresh Opus agent (the budget rule; or Codex gpt-6.2-sol within its 12% a day):
   fix what the VM checks show, section 5's docs, the REPORT, the PR. PROGRESS.md lists what the check build must
   show. Rebase onto main before the PR (main moved a lot: R28 work, 53c/53d/53f in the helper).
3. A fresh Codex gpt-6.2-astra `high` review with a data-safety pass (it guards the world through save and
   shutdown), state decision 24's bar; then `linux-aresos` reads the os/ diff; merge on SAFE with green checks.
4. Once 25 is on main, tell `linux-hub` that hub-try and `~/AresOS-try` need a stand-in SYSTEMCTL answering active.
5. Then `board done 357 387`, this handoff and STATE.md, and "ready to clear" to `mac-capacity` (board #369).

## Thu 2026-11-19 evening to Fri 00:05: package 25 merged

PR #125 merged as `61a66d78` (details in STATE.md and `reviews/25-guardian/REPORT.md`). Board #357, #383, #384, #387 and
#359 are done. **Nothing of this lead's is open** except #358 (53a's three low-harm follow-ups) and #369 (tell
`mac-capacity` "ready to clear", done with this note). Package 53's step 4 and the laptop trial belong to 23c
(`linux-aresos`). Worktree `~/AresOS-25-guardian` removed; the remote branch is kept.

## Sat 2026-11-21: 53a's follow-ups merged as package 322

Board T358's three follow-ups were built as brief 322 (Codex gpt-6.2-sol high, slot from `mac-capacity`) and merged
with PR134 (`reviews/322-helper-followups/`): review 1 (gpt-6.2-sol) SAFE, `linux-aresos` read the os/ diff, hosted OS
regressions green on the code commit (run 44911039176). Two notes went to the REPORT's Known limits. **Nothing of
this lead's is open.** Package 53's step 4 and the laptop trial belong to 23c (`linux-aresos`).
