# Hub handoff

The baton for the next `linux-hub` session: the Minecraft home screen and the mod's hub side. Read it after `STATE.md`, and overwrite it when you pick it up.

Written 2026-11-19 by `linux-hub` (Claude Opus 5.5), after package 56. The session was cleared at `mac-capacity`'s request.

## Where things stand

- **On main today, all with SAFE reviews:**
  - 45: leftovers;
  - 46: `save_world`;
  - 47: the client tests keep the NVIDIA card awake for the run;
  - 48: the AresOS Esc menu and New home;
  - 49 and 49b: memory measurements, with the settings unchanged and the arena cap not qualified;
  - 54: the town arrives in one line;
  - 56: the world ignores the mouse behind apps, the hotbar opens apps, and flying is 1.5×.

  STATE.md has a line for each.
- **R28** (cut Thu 2026-11-19 12:00) is the first release with the home screen at boot (packages 23, 23b and 23d, plus 46, 48, 51, 54 and 53a/b inert). Package 56 rides **R29**, as `linux-aresos` asked.
- **No hub worktree or Codex job is open.** `~/AresOS-try` is `hub-try`'s checkout: leave it alone, because `hub-try --update` moves it.

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
- **49b:** the rig's `bash -n` record checks only the first script (REVIEW-1 nit). The rig itself is repaired for reruns in `reviews/49b-arena-rerun/rig/`.
