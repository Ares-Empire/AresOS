# 39: Logos in their icon's main colours

Empire board brief 290. Mod package, after package 36 (the town builds itself). It changes how an icon becomes 12 x 12 blocks (`docs/design/HUB.md` 3.6, `zone/GatePicture.java`, `zone/GatePalette.java`) and nothing else.

**Builders:** two steps, one fresh builder per step: Claude agents on **Fable 5.2**, because this is design work (how the logos look in the world; the owner, 2026-11-13: "if you do actual design work use fable agents") and the rules below set a goal, not a method. Each step ends with a commit, a push and an updated `reviews/39-logo-colours/PROGRESS.md`. **Review:** a fresh reviewer that isn't a builder. **Before merge** the orchestrator shows the owner the private before-and-after pictures of his three real logos (see "Pictures").

## Why

Package 36's private run with the laptop's real icons (`reviews/36-town/REPORT.md`, "The town with the real three"):
- Chrome is unmistakable, but its red is red mushroom block, whose white spots show from the pad, and its white ring is a mix of grey stone-like blocks, so it reads grey and rough.
- Discord is recognisable, but the cells on the face's edge are light blue, grey and two amethyst blocks: a fringe that makes the face look frayed.
- Lunar Client cannot be made out without its sign: its thin white lines on black average into four or five greys.

Today every cell takes the block nearest to the **average** colour of what falls into it (HUB.md 3.6, point 4). Edges and thin lines then become in-between colours that the icon never had, and the palette picks textured blocks when they are a shade closer.

**Goal:** a logo is built from the icon's few main colours, one block per colour, and reads from the pad as the icon does: clean edges, no fringe, thin lines that stay lines, plain blocks.

## Read first

`docs/design/HUB.md` 2.3 (the palette) and 3.6 (from an icon to blocks), `zone/GatePicture.java` and `zone/GatePalette.java` with their tests, package 33's report (`reviews/33-gate-logo/REPORT.md`, where the rules and the 24 test icons come from), and in package 36 how a logo drawn by older rules is noticed and drawn again (`GatePicture.CONVERTER`, `TownKeeper`), and how pictures are read off the server thread (`zone/PictureReader.java`).

## What to build

1. **Main colours.** From the icon's visible pixels, find its main colours: few (two to four is the expected range; your rule says how many and why), found the same way every time for the same icon. A cell is painted in one of them, never in a mix of them. Deciding which one per cell is the core of the package: a cell with a thin line of a contrasting main colour must be able to show that line, and a cell on an anti-aliased edge must take one side, not an in-between. Say in the report how the rule decides and what it gives up.
2. **One block per main colour,** chosen once for the whole logo, so a ring or a plate is one block. **Plain blocks first:** between blocks of nearly the same colour, a plain one (concrete, wool, terracotta) beats a spotted, bricked or patterned one (mushroom blocks, bricks, ores). Two main colours must not end up as the same block unless they are nearly the same colour. If the palette needs to change for this (drop or add blocks), say why; the 12 group blocks of 2.3 stay.
3. **Icons the old rules handled well stay as good:** a many-coloured icon, a photo-like icon, a gradient, an icon without a plate, a small icon that is enlarged, an icon that is mostly see-through. The plate test, the enlarging, the cut, solid cells (at least half covered), tidy and the door stay as they are unless the pictures show a reason; say it if you change one.
4. **Raise `GatePicture.CONVERTER` to 2,** so the town draws standing logos again by its own rules (package 36: a logo drawn by older rules is renewed). Check what a world with five or forty logos then says in the chat on its first visit with this mod, and that a frozen town draws nothing (package 36's freeze). Hand-built gates are not redrawn; say so.
5. **Cost:** the converter runs on the picture thread (`PictureReader`), never on the server thread. Measure the time for one icon at 128 and at 1024 pixels and keep it small (the town converts forty icons on a first visit); say the numbers.
6. **HUB.md 3.6** describes the new rules exactly, as it does today, with the numbers.

## Tests

Unit tests with icons the tests draw (never real app icons and no copies of real logos; generic shapes):
- thin light lines (an arc, a ring, a few pixels wide at 128) on a dark plate: the logo has two blocks, and the lines are cells of the light block, connected where the drawn line is;
- a pale figure with anti-aliased edges on a coloured plate: only the main colours' blocks appear, no in-between block on the edge;
- a round figure in four colours with a light ring that has a slight gradient: the ring is one block;
- a strong red figure: a plain red block, not a spotted one;
- the old cases above (many colours, photo-like, gradient, no plate, enlarged, mostly see-through) still give a picture, with the number of blocks you expect;
- the same icon twice gives the same blocks; and `CONVERTER` changed renews a town logo (a server test through package 36's keeper).

## Pictures

- **In the repo** (`reviews/39-logo-colours/screenshots/`, from client game tests with the fake helper and drawn icons): a row of logos from the pad, before (the old rules) and after, at the same spot and light. If the test cannot run the old rules any more, take "before" first, in step 1, before changing the rules. Look at each picture; tune only what the pictures show to be wrong, and say what and why.
- **Private, never in the repo:** the same view with the laptop's three real icons (Chrome, Discord, Lunar Client), before and after, as package 36 did. The icons are in `/tmp/claude-1001/-var-home-ares/500f3f9b-4339-4371-a04c-ee0f7b10c35d/scratchpad/pkg36-real/`; write the pictures to `/tmp/claude-1001/-var-home-ares/500f3f9b-4339-4371-a04c-ee0f7b10c35d/scratchpad/pkg39-real/`. The report describes them in words only (as 36's report does). The orchestrator shows them to the owner.

## Steps

1. **Step 1:** the "before" pictures (repo and private) with the old rules; the new rules, the palette choice and `CONVERTER = 2`; the unit tests; the private "after" with the real three; `mod/dev/build.sh` passes; commit, push, `PROGRESS.md` (what the real three look like now, in words, and what you would still tune).
2. **Step 2:** tune from the pictures; the renewal test and the chat check of point 4; the cost numbers; the repo "after" pictures; HUB.md 3.6; `mod/README.md` if it describes the converter; the full report text (in `PROGRESS.md` or the pull request's description if your file tool refuses `REPORT.md`) with a "try this" note; `mod/dev/build.sh` once and `mod/dev/client-test.sh` twice on the final code; merge `origin/main`; push; `gh pr create`.

## Added for step 2 (the orchestrator, 2026-11-14)

- **Main moved on:** package 37 (getting around: `/go`, `/home`, swap and move, its client test `GettingAroundClientGameTest`) is merged into this branch as `ee24b314`. The two conflicts (`fabric.mod.json`, `build.gradle`) were resolved by keeping both client tests, 37's before 39's. Run `mod/dev/build.sh` first and fix whatever the merge broke; 37's tests may build logos through the converter or with blocks that step 1 stopped building.
- **Pictures:** 37's client test now runs before this one, so this package's picture numbers change. Commit this package's pictures under their new numbers, leave 37's pictures as they are unless the converter changes what they show (then commit them anew, look at them, and say so), and remove stray renumbered copies.
- **A wording fix from package 37's last review** (`reviews/37-getting-around/REVIEW-3.md`, NIT): the comment at `TownKeeper.again()` and HUB.md's correction for 2.5 say the next ordinary pass follows "in the next tick" / "a tick later". It can run at the end of the same tick, after the command, or later while a picture is being read. Write "the town's next ordinary pass, after the command" in both places. Wording only.
- **`README.md`'s status, the mod's paragraph only:** it says the mod works "in Minecraft's development client on Windows" and that the tests "run on Windows, not in CI". Today they also run on AresOS (`mod/dev/build.sh`, `mod/dev/client-test.sh`) and on GitHub (the `Mod` workflow, package 38). Correct those two statements and nothing else in that section.
- **Review:** a fresh Claude reviewer on Opus 5.5 (Codex's week is used up).

## Out of scope

The logo's size, depth, door, niche and sign (packages 33 and 36, and the owner's "12"); where logos stand; the OS helper and how it writes icons (package 30); hand-built gates' rules beyond sharing the converter; no change under `os/`.

## If unsure

Choose what reads better from the pad in the pictures, and say why. When a rule cannot reach the goal for one kind of icon, keep the old result for that kind and name it.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-39-logo-colours`, branch `pkg/39-logo-colours`; push with `git push origin pkg/39-logo-colours`. Never merge, never push to `main`, never `--no-verify`.
- Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh` (`mod/README.md`, "On Linux"). Never pass `--force`, never run `./gradlew` directly, never open a window in the owner's session. Another package's builder may be using Gradle at the same time: before `build.sh`, check `free -g` shows at least 6 GiB available, otherwise wait a few minutes (one sleep at a time).
- Game tests build relative to their own plot and never force or release chunks they don't own; new client tests go last.
- The repo is public: no personal data, no Mojang assets, no real app icons or pictures made from them, never the names of programs installed on this laptop beyond the three the design already names.
- Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft` or `~/.lunarclient`. No sudo. Use `gh` only for `gh pr create` at the end.
- Commits end with a `Co-Authored-By:` line naming the builder's own model.
