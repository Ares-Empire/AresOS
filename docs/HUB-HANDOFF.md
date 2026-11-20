# Hub handoff

The baton for the next `linux-hub` session: the Minecraft home screen and the mod's hub side. Read it after `STATE.md`, and overwrite it when you pick it up.

Written 2026-11-19 by `linux-hub` (Claude Opus 5.5), after package 56. The session was cleared at `mac-capacity`'s request. Picked up the same day at 12:20 by a fresh `linux-hub` (Claude Opus 5.5).

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
  - Before `linux-aresos` publishes it (standing OK, board #388), it still needs the jar pin, the last dry run, the VM rehearsal and the final review. Installing it (`at update`) is Patrik's own step.
  - The hub waits for `linux-aresos` to say R28 is on the laptop.
- **B318 merged** (PR126, `4105952a`, Fri 2026-11-20): why 49's frozen games died on thaw, the first item of T364. STATE.md has the line.
  - **Next for T364:** once R28 runs the home on the laptop, read the running game read-only: the log's "OpenAL initialized on device" line, its loaded audio libraries (`/proc/<pid>/maps`) and its realtime threads. That tells which backend the product uses.
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

## Who owns what next door

- **`linux-aresos`** owns `os/` and releases. It gets:
  - one line per merged mod PR, with the jar hash from main's Mod run log;
  - the PR number for its read of any `os/` diff;
  - notice before any `rc.xml` edit;
  - notice before a mod merge on a cut morning.
- **`linux-laptop-home`** owns package 53, the laptop-screen home. Patrik chose a native GTK/Cairo drawing (board #375, about 50 MiB) over the web page. It also owns package 25, the guardian. `mod/` is shared with it: it sends the mod files a step touches before the step starts.
- **`linux-desktop`** (formerly linux-deskflow) owns the normal OS pieces: indicators, window buttons, split screen, app switching. It also writes the Minecraft-look component study after the R28 cut (board #361).
  - **What it compares:** two versions side by side:
    - (A) our own pixel art;
    - (B) Minecraft's real textures and font, loaded at runtime from his installed game into a home-folder cache, never committed.
  - **Who decides:** Patrik chooses once he sees the difference.
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

- **PR127** (branch `docs/owner-name-scrub`, worktree `~/AresOS-owner-name-scrub`): his first name becomes "the owner" in 13 current files on main. `AGENTS.md` rule 6 and `CLAUDE.md` get the rule.
- **Review:** Codex `gpt-6-luna` medium, **SAFE** (`reviews/owner-name-scrub/REVIEW-1.md` on the branch).
- **Held** until `mac-capacity`'s freeze ends (after its 13:43 reading). The PR rewrites six lines of `linux-aresos`'s `HANDOFF.md` during R28. Before merging, check that R28 isn't mid-edit.
- **After the merge:**
  - `board leave` a note for `aresos`, `tools`, `desktop`, `laptop-home` and `aresos-control`: pull before editing, write "the owner" from now on, and scrub their unmerged branches before merging;
  - `board done T433`.
- **An idea for `mac-capacity`:** aresync's privacy check uses one terms list for every repo, so his name can't go on it without blocking private repos. A list for public repos only would guard this one.

## Coming to the shell protocol

- **`world_clicked`, a new 1.x request from the mod** (`linux-desktop`, B312 step 3, 2026-11-20; `docs/design/COMPONENTS.md` 4.3 on `pkg/312-component-study`).
  - **Why:** window layouts that cover the world need it. The shell keeps its own record of which window is where, and a window dragged out by its own bar (Chrome) leaves that record stale. The request corrects it.
  - **When:** it is planned for a later layouts package. Nothing is needed now, but the hub, as the mod's protocol side, reviews it when it comes.
- **B23c's Super-release check** went to `linux-aresos` on the board: does Super held through a drag open the search on release?

## Held

- **The companions (board #253):** held until Patrik decides after his try-out.

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
