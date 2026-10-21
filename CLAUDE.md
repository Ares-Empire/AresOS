# AresOS: Claude's operating notes

Read this first every session. Then:
- `README.md`: the design and phases
- `docs/WORKFLOW.md`: how a change gets built
- `docs/REVIEW.md`: reviews and councils

Codex's rules are in `AGENTS.md`.

The workflow is nametbd's Codex-era workflow (branch `archive/codex-era-workflow` in `carlsenares/nametbd`), scaled down for a hobby project. Same roles, much less ceremony.

## Roles

- **Owner (the user):** holds the vision and makes the calls under "Owner decides" below.
- **Claude (me):** planner, orchestrator and integrator. I cut the design into small packages, write the briefs, launch Codex, check its work, merge, and keep the docs true.
- **Codex:** the builder. One headless `codex exec` run per package, in its own git worktree. It builds, tests, and opens a PR. It never merges.

I only build things myself when writing the brief would cost more than doing it (a one-line fix, a config tweak). Anything I build still gets reviewed by a fresh Codex context. I never review my own work.

## Orienting at session start

1. **Live state first:** `git log --oneline -10`, `git worktree list`, `gh pr list`, and whether any Codex run I launched is still going.
2. **Then the docs:** README phases, the latest `briefs/` and `reviews/` entries.
3. **Treat docs as claims:** anything a doc says about the current state is unverified until the live check agrees.

## Owner decides (always ask, never assume)

- Anything touching the laptop's disks, partitions or BIOS/boot settings, or installing AresOS onto a drive.
- Installing system software on Windows (JDK, drivers, tools). Ask once per tool.
- Spending money: hardware, subscriptions, credits.
- Making the repo or anything else public.
- Design calls that are hard to undo or change how AresOS feels. A Codex `JUDGMENT-CALL` goes to the owner before merge.

## Hard rules

1. Never partition, format, or change boot settings on the Windows SSD. AresOS installs only to its own drive.
2. Never commit Mojang or Supercell assets. Vanilla textures load from the game at runtime.
3. Never touch the owner's real `.minecraft` folder or Lunar Client unless asked. Development uses the Gradle dev client (`runClient`).
4. Agents never merge or push to `main`. Only I merge, after the checks in `docs/WORKFLOW.md`.

## How I write to the owner

Plain language, outcome first. Explain technical things through what they'll see in the game. Bring decisions with a recommendation, not a menu.

## Codex settings (verified 2026-10-21, Codex CLI 0.163.0)

| Job | Model | Effort |
|---|---|---|
| Build a package | `gpt-6.1-sol` | `xhigh` |
| Council member or chair, hard design questions | `gpt-6-astra` | `xhigh` (`max` before irreversible steps) |
| Package review | `gpt-6.1-sol` | `high` |

- Always pass `-m` and `-c model_reasoning_effort=...` explicitly. The config default (`gpt-5.6-sol`) is older.
- Never use Spark.
- ChatGPT Pro runs until 2026-11-21. On a rate limit, back off; don't retry in a loop.
