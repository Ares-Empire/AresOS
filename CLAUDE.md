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

1. **Live state first:** `git log --oneline -10`, `git worktree list`, `gh pr list`, and whether any Codex run I launched is still going (each run logs to `../AresOS-<id>.log`; `turn.completed` in it means done).
2. **Then `STATE.md`** (where we are and what comes next) and **`HANDOFF.md`** (where the last session stopped and how to resume). Then only the docs the task touches (map below).
3. **Treat docs as claims:** anything a doc says about the current state is unverified until the live check agrees. Update `STATE.md` when a PR merges or a decision lands.

## Where things are

| Path | What it is |
|---|---|
| `STATE.md` | Current state, open owner decisions, next steps. Short on purpose. |
| `HANDOFF.md` | The baton: where the last session stopped, what's running, how to resume. Overwrite it when you pick it up. |
| `README.md` | What AresOS is: design, game rules, phases, safety rules. |
| `AGENTS.md` | Rules for Codex in every run. |
| `docs/WORKFLOW.md`, `docs/REVIEW.md` | How a package gets built, reviewed and merged, and how councils run. |
| `docs/design/OS-BASE.md` | The Linux layer design (council-approved). Long, so read the section you need. |
| `docs/INSTALL.md` | The owner's install guide for AresOS on its own SSD (briefs 10 and 10b). The same-drive fallback is `docs/INSTALL-SAME-DRIVE.md`. Physical install is NOT RELEASED until brief 06 lands. |
| `briefs/NN-slug.md` | One frozen task per package. Follow-ups are `NNb`, `NNc`. |
| `reviews/NN-slug/` | Codex's `REPORT.md`, `REVIEW*.md` and screenshots per package. |
| `reviews/councils/` | Council questions, member reports and verdicts. |
| `mod/` | Fabric mod: Minecraft 26.2, Java 25. `.\gradlew.bat build runClientGameTest` (rewrites tracked screenshots, so `git checkout -- reviews/` afterwards). |
| `os/` | The Bazzite-based AresOS image (from PR #3). |

**Only one Minecraft client-test run at a time on the laptop.** Two test clients steal each other's window focus, which opens vanilla's pause menu and breaks click-driven tests. Seen 2026-10-22, when brief 10's run collided with my 09 integration gate. Don't start an integration gate while a Codex package is in its client-test phase, and vice versa.

## Owner decides (always ask, never assume)

- Anything touching the laptop's disks, partitions or BIOS/boot settings, or installing AresOS onto a drive.
- Installing system software on Windows (JDK, drivers, tools). Ask once per tool.
- Spending money: hardware, subscriptions, credits.
- Making the repo or anything else public.
- Design calls that are hard to undo or change how AresOS feels. A Codex `JUDGMENT-CALL` goes to the owner before merge.

## Hard rules

1. **AresOS on its own SSD (owner decision, 2026-10-22; replaces the earlier same-drive dual-boot plan).**
   - AresOS lives on a second internal NVMe SSD in the free M.2 2280 slot (Crucial P310 500 GB).
   - The Windows SSD (Micron 512 GB) is never partitioned, formatted, resized or written to, and Windows' boot files are never modified.
   - Same-drive dual boot stays documented only as a fallback.
   - Agents never run disk or boot tools on the real laptop.
2. Never commit Mojang or Supercell assets. Vanilla textures load from the game at runtime.
3. Never touch the owner's real `.minecraft` folder or Lunar Client unless asked. Development uses the Gradle dev client (`runClient`).
4. Agents never merge or push to `main`. Only I merge, after the checks in `docs/WORKFLOW.md`.

## How I write to the owner

Plain language, outcome first. Explain technical things through what they'll see in the game. Bring decisions with a recommendation, not a menu.

## Codex models

Pick models by job, not by name. Names change, so check the list before the first launch of a session:

```powershell
(Get-Content "$env:USERPROFILE\.codex\models_cache.json" -Raw | ConvertFrom-Json).models | Where-Object visibility -eq 'list' | Sort-Object priority | Format-Table slug, description
```

| Job | Which model | Effort | Pick on 2026-10-21 |
|---|---|---|---|
| Build a package (`BUILD_MODEL`) | the newest "workhorse" coding model | `xhigh` | `gpt-6.1-sol` |
| Councils, hard design (`COUNCIL_MODEL`) | the "frontier" model | `xhigh` (`max` before irreversible steps) | `gpt-6-astra` |
| Package review (`REVIEW_MODEL`) | same as the build model | `high` | `gpt-6.1-sol` |

When the list shows a newer model for a job, use it and update the last column.

- Always pass `-m` and `-c model_reasoning_effort=...` explicitly. The Codex config default is an older model.
- Keep Codex current with `npm install -g @openai/codex@latest` (0.163.0 on 2026-10-21).
- Never use Spark.
- ChatGPT Pro runs until 2026-11-21. On a rate limit, back off; don't retry in a loop.
