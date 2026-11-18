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
- **Release cut:** none of this rides R28 (the cut is Thu 2026-11-19 12:00).

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
