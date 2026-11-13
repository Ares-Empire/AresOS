# AGENTS.md: rules for Codex (and any agent building AresOS)

## What this is

AresOS is a personal operating system whose desktop is the real Minecraft Java. It has three parts:
- **The shell mod** (`mod/`): a Fabric mod for Minecraft 26.2 that turns the game into the desktop. Apps are items in the hotbar and inventory, walking into a block logo opens its app, and closing an app returns you to the world.
- **The OS image** (`os/`): a Bazzite derivative, defined as code in this repo and built and tested in CI, for a second SSD next to an untouched Windows drive. It is meant to boot straight into a Minecraft world; today it starts a minimal session with a terminal.
- **The control layer** (`control/`, in progress): his apps (Mail first, then Chrome) as tools for a normal Claude Code session, which ask him before anything is sent or deleted. The base service is built and tested with a made-up app; Mail is in review and Chrome is designed. Design: `docs/design/CONTROL.md`.

What is built and what isn't: the Status section of `README.md`.

Design: `docs/design/DESIGN.md`. Workflow: `docs/WORKFLOW.md`. Reviews: `docs/REVIEW.md`.

## Your job in one run

You get one **brief** (`briefs/NN-slug.md`), your own worktree and your own branch.

1. Read the brief, `docs/design/DESIGN.md` and this file. Read existing code before you change it.
2. Build exactly what the brief asks. Ideas outside its scope go in your report, not into the code.
3. Verify (see below) and fix until green.
4. Commit in small logical commits. Push your branch and open a PR against `main` with `gh pr create`. Never merge, never push to `main`.
5. Write `reviews/NN-slug/REPORT.md` (format below), then commit and push it on your branch.
6. Stop every Gradle daemon you started (`./gradlew --stop`, and `gradle --stop` for any other Gradle version you ran). Then stop. A leftover daemon keeps your `codex exec` process alive after you finish (seen in package 01). **Under AresOS never run `--stop`:** the dev scripts below run Gradle without a daemon, and `--stop` would end other builders' builds on the same laptop.

Nobody can answer questions mid-run. If the brief doesn't settle something, take the safest reversible option and record it in the report.

## Verification

- `./gradlew build` must pass (inside `mod/`). On the laptop under AresOS use `mod/dev/build.sh` and `mod/dev/client-test.sh` instead of calling Gradle (`mod/README.md`, "On Linux"): they find Java, keep the game off the owner's screen, let one client run through at a time, and refuse (exit 75) while his own game runs or memory is short. Never pass `--force`; wait and try again.
- Write automated tests where they make sense. Use Fabric game tests for game logic. Use Fabric client game tests for anything visual, and save their screenshots under `reviews/NN-slug/screenshots/` so they can be inspected.
- Report exactly what you ran and what it printed. A test you didn't run is not evidence. If something can only be checked by a human playing, say so.
- Watch for things that fail silently, where the tests pass but the result in the game is wrong. Those are the ones reviews exist for.
- A server game test never forces or releases chunks it does not own: the framework holds the chunks of each test's plot, and releasing them took four neighbouring tests' chunks away in package 33, so the run never ended. Hold a ticket of your own. Build relative to your test's own plot: the test world can be kept between runs.
- Screenshot names carry a running number over the whole client suite. Add a new client test at the end of the list, or every later package's pictures are renamed.
- **`os/tests` on the laptop:** run only the modules you touch (`python3 -m unittest discover -s os/tests -p 'test_<name>.py'`), one at a time. Never run `discover -s os/tests` without a pattern there, and never the module `test_owner_update`: it starts the owner tools' real entry, which on AresOS reaches the laptop's own `rpm-ostree` and leaves stand-in processes behind. Importing it as a library is fine. The full count comes from the hosted run: `gh workflow run "OS image" --ref <branch> -f checks_only=true` (about 12 minutes, nothing skipped). Natively the full suite also shows about 124 failures that are not yours (root-only tests, test code against Python 3.14, that module).
- Before reporting green, run the full `build runClientGameTest` **twice**. A test that passes once and fails once is a failure: fix its cause, never the assertion. Package 04c passed for Codex and then failed in Claude's rerun with a non-deterministic world-generation search.

## Report format (`reviews/NN-slug/REPORT.md`)

- **Done:** what was built, in a few lines per file or area.
- **Verified:** commands run and their results, plus screenshots.
- **Not verified:** what still needs a human in the game.
- **JUDGMENT-CALL:** any decision that changes how AresOS feels or is hard to undo. Give what you chose, the alternatives you rejected, why, and what changing it later would cost. These go to the owner before merge.
- **PLAN-GAP:** anything the brief or design gets wrong or misses.
- **Open questions.**

## Hard rules

1. Stay inside your worktree. Don't touch other worktrees, the main checkout, or files outside the repo, except the Gradle and Java caches the build needs.
2. Never touch the owner's real Minecraft folder (`%APPDATA%\.minecraft`) or Lunar Client. Test with Gradle's dev client (`runClient`), which uses its own `run/` folder.
3. Never commit Mojang or Supercell assets (textures, sounds, fonts, logos). Vanilla textures load from the game at runtime. App icons are generated or drawn by us.
4. Never install system software, change Windows settings, touch disks, partitions or boot configuration, or run anything as admin. If the brief seems to need that, stop and record it as a blocker.
5. Never weaken, skip or delete a test to get green.
6. Never put secrets in the repo.
7. Keep at most **one** verified copy of each large download (ISO, image layer) in your worktree's `.work/`, and reuse it. Delete extracted images (`squashfs.img`), duplicates and partial downloads as soon as the step that made them ends. Before the closing report, list what is left in `.work/` that is over 500 MB. The laptop's SSD is shared with the owner: package 14's replays once left 115 GB behind (2026-11-02).

## Environment (the owner's laptop)

- Lenovo LOQ 15IRH8: i5-13500H, 16 GB RAM, RTX 4060. Since 2026-11-13 the work runs under **AresOS** itself (Linux, user `ares`, no sudo, nothing installed system-wide; Java 25 in `~/.local/opt/jdk-25`, `gh` in `~/.local/bin`). The real desktop session belongs to the owner: never open a window in it, never send input to it. Several builders share the laptop's memory: one heavy step at a time.
- Before that: Windows 11 with PowerShell 7 and Git Bash; the mod still builds there with `.\gradlew.bat`.
- Minecraft 26.2 needs **Java 25**.
- Versions as of 2026-10-21 (check Modrinth for newer before pinning):
  - Fabric Loader 0.19.5
  - Fabric API 0.161.0+26.2
  - Sodium mc26.2-0.9.2
  - Iris 1.11.4+26.2
- Remote: `github.com/Ares-Empire/AresOS` (public since 2026-11-02). `gh` is logged in.

## Code style

- Java on Fabric. Start from the official Fabric example mod template for 26.2.
- Keep platform-specific code behind one small interface, so the shell mod runs on both Windows and Linux. The main example is how an app gets launched.
- Comments explain why, not what. Keep it simple. This is a hobby project, not enterprise software.
