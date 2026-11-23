# Hub handoff

The baton for the next `linux-hub` session: the Minecraft home screen and the mod's hub side. Read it after `STATE.md`, and overwrite it when you pick it up.

Written Fri 2026-11-20 13:50 by `linux-hub` (Claude Opus 5.5), before a clear at `mac-capacity`'s request; updated 14:15 after PR127 merged and Sat 2026-11-21 06:45 after R28 was published.

## Resume here

Updated Mon 2026-11-23 10:45 (by `date`) by `linux-hub`. R29 is cut around 27 Nov from whatever is on main then (`linux-aresos` sends a cut line a day ahead).

1. **On main since R28:**
   - B327 (try-out fixes, `4dd5288b`);
   - B328a (the world keeps the pointer, `92cf365a`);
   - B328 (two look-around prototypes behind `look = classic | click | edge`, `17211fb1`);
   - the design note `docs/design/HOME-OUTSIDE.md` with home styles (this PR).
2. **PR150 (B333, open apps and bring back, `aresos-shell/1.3`):** SAFE after six fix rounds; the launch cap now counts systemd's scopes (`reviews/333-open-apps/`). It conflicted with B328's pointer changes; the lead merged main into it by hand, so a small fresh review of that merge and green CI come before the merge.
3. **Waiting for Codex's reset (Wed ~14:49):**
   - edge mode's up/down arrows (it can look up but not back down; before the owner's trial);
   - the admission listing's timeout cut from 5 s to about 1 s (RECHECK-6, nit 6).
4. **The owner's decisions (2026-11-22):** home styles, with a fresh AresOS starting on a normal picture home (T493); icons dragged freely with an alignment setting (T494); a starter icon column (T498); "switchable" as a guideline, built as a fourth look, "Normal". All of it is in HOME-OUTSIDE.
5. **Next for the hub:** the owner's trial of the look modes (`hub-try --outputs 2`, after the arrows); HOME-OUTSIDE's package 1 with `linux-aresos` and package 6 (search outside); T364's study for the gates; board T486 (Alt+Tab then Esc leaves the world without keys) and T515 (build and run-hub take the client-test lock).
6. **Budgets:** the Claude week ran tight (87% on Mon morning); Codex is empty until Wed ~14:49; the API promo is nearly spent until it refills around 29 Nov. Direct pushes to main are refused, so docs travel in PRs.

## Where things stand

- **On main today, all with SAFE reviews:**
  - 45: leftovers;
  - 46: `save_world`;
  - 47: the client tests keep the NVIDIA card awake for the run;
  - 48: the AresOS Esc menu and New home;
  - 49 and 49b: memory measurements, with the settings unchanged and the arena cap not qualified;
  - 54: the town arrives in one line;
  - 56: the world ignores the mouse behind apps, the hotbar opens apps, and flying is 1.5×.
    Main `da441546` (#117); its jar hash from main's Mod run 44511397426 (both builds match) was `b72f91182faba3ed35750e6954deb23c622c76d1d9ef94fb7e2b857185a0c511`.
- **53d** (`linux-laptop-home`, Super opens a search over the world) merged on top of 56 as `c576818b` (#121). Main's jar is now `4f7324f56ad943a80e892cdce1985dce526bdeee36ea6cc79796abb5ec98211c` (Mod run 44532278666, both builds match).
  - **New in `mod/`:**
    - `WorldSearchScreen`, `SearchCrosshairMixin` and `RecipeBookSearchAccess`;
    - `ShellFocusClient.search()`;
    - the four-argument `AresOsClient.launch(id, visit, worldScreen, opened)`.
  - **Test order:** `WorldSearchClientGameTest` stays last in the gametest list.
  - **Shared mod work:** `linux-laptop-home` has nothing more queued in `mod/` (14:25).

  STATE.md has a line for each.
- **R28** is the first release with the home screen at boot (packages 23, 23b and 23d, plus 46, 48, 51, 54 and 53a/b inert). Package 56 rides **R29**, as `linux-aresos` asked.
  - The cut was taken Thu 12:00: main `fba94b25` into `pkg/42` as `7f896b62`.
  - Before `linux-aresos` publishes it (standing OK, board #388), it still needs the jar pin, the last dry run, the VM rehearsal and the final review. Installing it (`at update`) is the owner's own step.
  - The hub waits for `linux-aresos` to say R28 is on the laptop.
- **B318 merged** (PR126, `4105952a`, Fri 2026-11-20): why 49's frozen games died on thaw, the first item of T364. STATE.md has the line.
  - **T364's audio question, answered on the laptop** (Sat 2026-11-21 18:08, R28 `aa97b2d5`, the first SETUP start, read-only): the product uses **OpenAL Soft's PipeWire backend**.
    - The game log says `OpenAL initialized on device Built-in Audio Analog Stereo`. `/proc/<pid>/maps` holds `libpipewire-0.3` with PipeWire memfds; `libpulse` is loaded too, but nothing of it is in use.
    - **All 80 game threads are SCHED_OTHER** (`PWEventThread`, `ALSoftP0` and `Sound engine` included). The game's `RLIMIT_RTPRIO` is 0 and its `RLIMIT_RTTIME` is 200 ms.
    - So the thaw kill from B318 can't happen in the real session. It needs a realtime mixer thread, which only OpenAL Soft's own-thread backends make (null, which the rigs used, and ALSA, the fallback when neither PipeWire nor PulseAudio answers).
    - The supervisor's demotion stays in the sleeping-world design as a cheap safety net for that fallback, not as a fix the product needs now.
  - **A memory lead from the same start** (`linux-aresos`'s 23d check, 18:09):
    - The game scope's anon is about 1019 MiB (`memory.high` 2560 MiB, no `high` events). Prism's scope holds about **418 MiB of anon while the game runs**.
    - The supervisor writes `CloseAfterLaunch=false` (since package 23), and the game's wrapper runs as Prism's child. Prism's "close after launch" probably only closes windows, so the memory study should check whether Prism can leave, or be replaced for the launch, without losing the wrapper.
  - **First-start findings that belong to others:** the Microsoft sign-in's browser route has no `prismlauncher://` handler, so the owner used the device code after a retry (`linux-aresos`, T474, R29). The windows still wear Ares-Crown, not the Minecraft look (`linux-desktop`, after B320).
  - **Then:** the swap side (`linux-aresos`) and prefetch on wake, in the sleeping-world study. The supervisor's demotion goes into that design.
  - **The rig** stays in `~/AresOS-318-thaw-watchdog` (`.work/pkg318` holds its base world). Before reusing it, fix the two Known limits in `reviews/318-thaw-watchdog/FINDINGS.md`.
- `~/AresOS-try` is `hub-try`'s checkout: leave it alone, because `hub-try --update` moves it.
- **B25** (the guardian, PR125, `61a66d78`, rides R29) doesn't change the jar. Its supervisor refuses to start a game while `aresos-guardian.service` isn't active. `hub-try` needs no stand-in for it, because `run-hub.sh` never starts the supervisor (`aresos-desktop`): it runs only the helper and the dev client, and the helper has no guardian check. A future tool that runs `aresos-desktop` outside the real system would need a stand-in `SYSTEMCTL`, as the guardian loop tests use.

## The owner's direction (2026-11-18)

His guideline: "hub wise the main next step is make it a functional, usable homescreen not just isolated as a homescreen but as part of an OS". The order (board #365):

1. **When R28 is on his laptop** (`linux-aresos` says when), try the real home screen with him.
   - Measure boot to home on a later boot, not the first SETUP start (board #362): power-on to the startup cover, and the cover to the world.
2. **Fix what that try-out shows.**
3. **Then memory: the sleeping world (board #364).** It is a priority since his plan of 2026-11-18 put "optimize memory usage" right after R28 and Deskflow.
   - **His idea:** when the world isn't needed, it becomes a still image and is frozen, or its memory goes to swap. It is woken early from signals, possibly predicted from the pointer.
   - **His worry:** what happens when memory is full at wake time. The proposed answer: the image needs almost nothing, so it always shows; the world wakes more slowly on a full laptop; the home never kills his work.
   - **To solve first:**
     - why 49's frozen games died on thaw;
     - swap on disk, which is `linux-aresos`'s side, plus the SSD wear in numbers;
     - prefetch on wake (`process_madvise` `MADV_WILLNEED`).
   - **Use the new covering rule** (board #373): the world counts as covered only when windows on its output fill that output's usable area, decided per output. `linux-desktop` changes `Windows.covering` with split screen.
   - **Real measurements only.** His numbers so far: the game about 1.2–1.3 GB while visible.

**Waiting on him:**
- the flying speed after he tries 56: one number, `LiveMode.DESKTOP_FLYING_SPEED`, now `0.075f` (1.5×);
- the permanent DNS change, which needs his password.

## The owner's first try-out of R28 (Sat 2026-11-21 ~18:30)

His findings, in his order, with who takes each. Nothing is built yet.

1. **Monitor plugged in after the start:** the home didn't change, and the monitor stayed black. `wlr-randr`: eDP-1 at 0,0 and HDMI-A-1 at 1920,0, both on. The world is only on eDP-1 and nothing draws on HDMI. He can't cross to the monitor without Esc, because the world holds the mouse. "For a homescreen that's bad. It should be seamless." **Needs his decision** (what each screen shows, how the mouse crosses). Hub and `linux-desktop`, with T373's per-output covering.
2. **The Esc menu:** he likes it after all, but doesn't know what **New home** does. Hub: clearer label and an explanation line.
3. **Apps open part-screen, and the world behind is black.** Only a maximized window covers the world (`HomeScreen.covered`). The black is the camera standing against the app's gate plate after walking in (his words: "that's where the character is"). Hub: a good view behind an app (step the camera back from the gate, or open maximized by default). He asked whether part-screen is normal. On Windows and macOS an app opens at its last size, often maximized.
4. **Clicks reach Chrome while the world has the mouse:** after he clicks the world, the cursor is hidden and he moves the character, but a left click lands in Chrome when the hidden pointer sits over it. A real input bug. Hub (mod pointer capture) with `linux-desktop` (labwc pointer focus).
5. **A click on the world beside a part-screen window hides the window** (the world window is raised over it). He reads it as minimizing, "like on any OS". `linux-desktop`: on Windows and macOS the desktop stays below the windows, so decide whether the world should too.
6. **Minecraft's tutorial toasts** ("punch a tree") don't fit. Hub: off (`tutorialStep:none`, and the other vanilla onboarding toasts). His idea: use toasts for AresOS updates and features later.
7. **Taskbar (the hotbar):** an open app that isn't in front isn't shown, and nothing marks which apps are open or active. Hub: open apps in the bar, a mark for open and one for active.
8. **The hotbar Terminal block is brown, the Terminal itself black, and it doesn't need white edges.** Hub: the logo picture.
9. **No brightness or volume pop-ups, and no status icons (Wi-Fi, battery, sound, clock).** He wants design options. `linux-desktop` (with B312's components).
10. **Reopening an app starts a new instance:** Chrome minimized with "-" (one tab open), then `/chrome` or a right-click on its bar icon opened a new Chrome window without the tab. His proposal: **left click opens or brings back the app, right click opens its options** (new window and so on, like Windows). Hub (launch focuses the existing window) with `linux-desktop` (window list and raise).
11. **No Files app and no System Settings app.** Minor while it's a dev project, needed later. `linux-aresos`/`linux-desktop` roadmap.
12. **The hub's own blocks can be broken.** He'd protect them by default, editable only in a build mode. Hub.
13. **Full-screen apps hide the taskbar, which he likes, but moving the cursor down should bring it up, as macOS does** (added after). This needs a bar outside the game, because the world isn't drawn under a maximized app: a layer-shell bar in the Minecraft look, which auto-hides over full-screen windows. Hub (bar content, the same as the hotbar's) with `linux-desktop` (the layer-shell surface, B312's look).

He didn't test memory. Ask him when the memory work needs his apps open.

**His answers (same evening):**
- **With a monitor, the world is on the monitor.** The laptop screen shows a picture behind its apps.
- **No hold-the-right-button to look around:** "we need to find another way". The cursor must still cross screens seamlessly. This is an open design job: prototype two or three ways and let him try them by feel.
- **A click on the world beside a part-screen app must not hide the app** (the world stays below the windows). `linux-desktop`'s item (c), now decided.
- **The look is already decided:** COMPONENTS.md (B312, on main) uses the game's textures by default and A/C as a setting. The brightness and volume indicator (4.1) is `linux-desktop`'s first build. Status icons (Wi-Fi, battery, sound, clock) aren't in it yet; they go to `linux-desktop` as a new component in the same looks.
- **New: a switch to turn the home world off.** The home becomes a picture: a default one, black, or any picture of his. "Especially good when we are building, so Minecraft doesn't draw that much memory" (game about 1 GiB plus Prism about 418 MiB).
- He agreed to the rest: the fix order, protected blocks with a build mode, tutorial toasts off, the clearer New home label, the Terminal block, open/active marks, left click opens and right click gives options, and apps opening full at first and then at their last size.

**What this means for the structure:** the world-off switch, the bar over full-screen apps, and the picture on the second screen all need the home's own parts outside Minecraft: a picture behind the windows, the bar, search and app launching. Today the bar, search and launching live inside the game (the hotbar, `WorldSearchScreen`, `AresOsClient.launch`). One design note should decide where they live, with `linux-desktop`, before any of the three is built. It should also cover the sleeping world (T364), whose still image is the same picture.

## Who owns what next door

- **`linux-aresos`** owns `os/` and releases. It gets:
  - one line per merged mod PR, with the jar hash from main's Mod run log;
  - the PR number for its read of any `os/` diff;
  - notice before any `rc.xml` edit;
  - notice before a mod merge on a cut morning.
- **`linux-laptop-home`** owns package 53, the laptop-screen home. The owner chose a native GTK/Cairo drawing (board #375, about 50 MiB) over the web page. It also owns package 25, the guardian. `mod/` is shared with it: it sends the mod files a step touches before the step starts.
- **`linux-desktop`** (formerly linux-deskflow) owns the normal OS pieces: indicators, window buttons, split screen, app switching. It also writes the Minecraft-look component study after the R28 cut (board #361).
  - **What it compares:** two versions side by side:
    - (A) our own pixel art;
    - (B) Minecraft's real textures and font, loaded at runtime from his installed game into a home-folder cache, never committed.
  - **Who decides:** the owner chooses once he sees the difference.
  - **The hub's job:** review the study against the checklist sent on 2026-11-19:
    - no Mojang files committed;
    - sprites on Minecraft's GUI grid;
    - fits the noon world and the day street;
    - readable at 1920×1080;
    - the password window keeps its label and "Enter SSH Credentials";
    - overlays never take keyboard focus;
    - Super stays free.

## Board

- **#335** (build the laptop home) was dropped: it is package 53, owned by `linux-laptop-home`.
- **#361** (the Minecraft-look study) was dropped: it is `linux-desktop`'s brief 312 (board #374). The hub's part, the review against the checklist above, is **#410**.
- `linux-laptop-home` has 56's jar hash (it confirmed at 13:55).

## Owner name scrub (T433, his answer 2026-11-20: "Scrub to 'the owner'")

- **Merged** as `d4cfe514` (PR127, squash, Fri 14:10): his first name is "the owner" in 13 current files on main, and `AGENTS.md` rule 6 and `CLAUDE.md` carry the rule. `git grep` finds the name nowhere in the tree.
- **Review:** Codex `gpt-6-luna` medium, **SAFE** (`reviews/owner-name-scrub/REVIEW-1.md`). Before merging, it was rebased onto `33bda493`. The only clash was R28's line 69 of `HANDOFF.md`, next to the scrub's lines 70–73; each side's line was kept. The scrub's added and removed lines are byte-identical to the reviewed ones. `linux-aresos` said "go now" (14:07, no unpushed `HANDOFF.md` edits).
- **Done after the merge:** board notes T443–T446 for `tools`, `desktop`, `laptop-home` and `aresos-control`: pull before editing, write "the owner", and scrub unmerged branches. `linux-aresos` got the same note directly and scrubs `pkg/42-release-28` before it merges back. T433 is done.
- **An idea for `mac-capacity`** (sent 14:15): aresync's privacy check uses one terms list for every repo, so his name can't go on it without blocking private repos. A list for public repos only would guard this one.

## Coming to the shell protocol

- **`world_clicked`, a new 1.x request from the mod** (`linux-desktop`, B312 step 3, 2026-11-20; `docs/design/COMPONENTS.md` 4.3 on `pkg/312-component-study`).
  - **Why:** window layouts that cover the world need it. The shell keeps its own record of which window is where, and a window dragged out by its own bar (Chrome) leaves that record stale. The request corrects it.
  - **When:** it is planned for a later layouts package. Nothing is needed now, but the hub, as the mod's protocol side, reviews it when it comes.
- **B23c's Super-release check** went to `linux-aresos` on the board: does Super held through a drag open the search on release?

## Held

- **The companions (board #253):** held until the owner decides after his try-out.

## How the hub works

- **Capacity:**
  - Claude builds with Opus agents.
  - Codex is for cross-reviews only until its reset on Wed 2026-11-25 (fair pace about 0.5% an hour).
- **Reviews:**
  - Every reviewer prompt states the safety bar (decision 24): fix real harm, and put low-harm edge cases under Known limits.
  - A brief or design note gets one Claude review, then one Codex review, then the build.
- **Running Codex:** `codex exec -m <model> -c model_reasoning_effort=<e> -s <sandbox> --json -o <last.md> "<prompt>" > ../AresOS-<id>.log 2>&1 < /dev/null`.
  - Reviews run read-only and write `reviews/NN-*/REVIEW-N.md`.
  - Codex needs stdin closed.
- **Client tests:** one at a time machine-wide (`mod/dev/client-test.sh`, the lock at `~/.cache/aresos-dev/client-test.lock`). Since 47 they keep the NVIDIA card awake only for the run.

## Known limits left open (low harm)

- **56:** the empty-slot, non-app and world clicks are tested through the game's mouse callbacks, not native compositor delivery (REVIEW-1 nit).
- **40:** a stale press in `AppsScreen` (REVIEW-3 nit).
- **09:** `ModeInventoriesClientGameTest.toggle` timed out once (line 196, from 140, 56 s in, on NVIDIA) in one of three local client suites for 53d's rebase. The other two runs passed all 28. It looks like a timing flake in its 50 G presses (`reviews/53d-world-search/REBASE.md`, Known limits). `linux-laptop-home` left it to the hub: if it shows again, judge it here.
- **49b:** the rig's `bash -n` record checks only the first script (REVIEW-1 nit). The rig itself is repaired for reruns in `reviews/49b-arena-rerun/rig/`.
