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
- **The safety bar for every review and fix round** (decision 24, as clarified 2026-11-11; Patrik restated it
  2026-11-18 through `mac-capacity`: "it needs to be reasonable … safe right? Not every edge case safe? We once wasted
  time on that … genuinely legitimate safety things make sense to do"):
  - Real-harm findings get fixed: data loss, credentials (the view token), system changes, anything hard to undo.
  - Low-harm edge cases go under Known limits or into a follow-up, not into another fix round.
  - Every reviewer brief states this bar.
- **Brief reviews** (Patrik, 2026-11-18 through `mac-capacity`): one Claude review, then one cross-model review (Codex
  while it lasts), or straight to the Codex one while Claude is tight. Then build. Another round only for a blocking
  design flaw, as a targeted recheck; should-fixes and low-harm edge cases go to the code review or Known limits.
  53a's brief goes straight to one Codex review (Claude at 80% this week).
- **Codex pace** (`mac-capacity`, 2026-11-18 16:50): 88% left at 16:44. The average must stay near 1.6%/h until Fri
  12:00, so 20% is left for the Fri–Sat reviews. Until Thu 00:00: one Codex build at a time (53c run A starts after
  53b's build). ~~From Thu 00:00 builds go to Claude Opus agents~~ **(replaced 2026-11-18 21:50: builds stay on Codex Sol until
  Sat, one at a time per lead, at about 2%/h across all leads; Claude for design, UI and what Codex does poorly)**, and Codex does the
  cross-reviews (`gpt-6.2-sol` by default, `gpt-6.2-astra` only where the stakes need it, such as 53c's security
  pass). Codex's second-model review is the part Claude can't replace.
