# AresOS: Claude's operating notes

Read this first every session. Then:
- `docs/design/DESIGN.md`: the design and phases
- `docs/WORKFLOW.md`: how a change gets built
- `docs/REVIEW.md`: reviews and councils

Codex's rules are in `AGENTS.md`.

The workflow is nametbd's Codex-era workflow (branch `archive/codex-era-workflow` in `carlsenares/nametbd`), scaled down for a hobby project. Same roles, much less ceremony.

## Roles

- **Owner (the user):** holds the vision and makes the calls under "Owner decides" below.
- **Claude (me):** planner, orchestrator and integrator. I cut the design into small packages, write the briefs, launch Codex, check its work, merge, and keep the docs true.
- **Codex:** the builder. One headless `codex exec` run per package, in its own git worktree. It builds, tests, and opens a PR. It never merges.

**Claude agents may build packages too** (owner, 2026-11-09: "we could work with claude agents too", to use his Claude allowance). They get the same brief, worktree, branch and AGENTS.md rules as Codex. Pick Codex or a Claude agent per package by fit and remaining allowance. Claude agents run on Opus by default. For a hard AresOS task or a problem that resists normal attempts, use Fable 5.2 (owner, 2026-11-09: "in the dev of an own OS I could imagine hard tasks"). Design work (how something looks, feels or is laid out) runs on Fable agents (owner, 2026-11-13: "if you do actual design work use fable agents").

**Reviews (owner, 2026-11-11: "Yes change it").** Every package gets a fresh reviewer that isn't its builder: a fresh Codex context while Codex is available (ChatGPT Pro ends 2026-11-21), otherwise a fresh Claude agent.
- A Claude reviewer runs on **Opus** by default.
- Use **Fable 5.2** only for high-stakes reviews: where AresOS adds its own risk (updates and rollback, disks, software installs, credentials, system settings), and for the final review before something reaches the owner's laptop. Fable's allowance is for building.
- Nobody reviews their own work, me included.

I only build things myself when writing the brief would cost more than doing it (a one-line fix, a config tweak). Anything I build still gets that fresh review.

## Orienting at session start

1. **Live state first:** `git log --oneline -10`, `git worktree list`, `gh pr list`, and whether any Codex run I launched is still going (each run logs to `../AresOS-<id>.log`; `turn.completed` in it means done).
2. **Then `STATE.md`** (where we are and what comes next) and **`HANDOFF.md`** (where the last session stopped and how to resume). Then only the docs the task touches (map below).
3. **Treat docs as claims:** anything a doc says about the current state is unverified until the live check agrees. Update `STATE.md` when a PR merges or a decision lands.

## Where things are

| Path | What it is |
|---|---|
| `STATE.md` | Current state, open owner decisions, next steps. Short on purpose. |
| `HANDOFF.md` | The baton: where the last session stopped, what's running, how to resume. Overwrite it when you pick it up. |
| `README.md` | The front page for visitors: what AresOS is, its status, how to build the mod. |
| `docs/design/DESIGN.md` | The design: game rules, the Nether home, desktop and companion ideas, phases, open questions, safety rules. |
| `AGENTS.md` | Rules for Codex in every run. |
| `docs/WORKFLOW.md`, `docs/REVIEW.md` | How a package gets built, reviewed and merged, and how councils run. |
| `docs/design/OS-BASE.md` | The Linux layer design (council-approved). Long, so read the section you need. |
| `docs/design/HUB.md` | The home screen, version 1: the flat world, the logos and where they stand, "My apps", short names, and the `aresos-shell/1.1` additions (section 3.8). The hub packages (briefs 32 to 37) build it. |
| `docs/INSTALL.md` | The owner's install guide for AresOS on its own SSD (briefs 10 and 10b). The same-drive fallback is `docs/INSTALL-SAME-DRIVE.md`. Physical install stays NOT RELEASED until the remaining gates in its "Maintainer release gate" section pass (brief 06's image gate is done). |
| `docs/EMERGENCY.md` | The owner's one-page "If something goes wrong" card (escape routes back to Windows, recovery, rollback). Keep it in line with INSTALL.md. |
| `briefs/NN-slug.md` | One frozen task per package. Follow-ups are `NNb`, `NNc`. |
| `reviews/NN-slug/` | Codex's `REPORT.md`, `REVIEW*.md` and screenshots per package. |
| `reviews/councils/` | Council questions, member reports and verdicts. |
| `mod/` | Fabric mod: Minecraft 26.2, Java 25. On the laptop under AresOS: `mod/dev/build.sh` and `mod/dev/client-test.sh` (`mod/README.md`, "On Linux"); on Windows `.\gradlew.bat build runClientGameTest`. The client tests rewrite tracked screenshots, so `git checkout -- reviews/` afterwards. `.github/workflows/mod.yml` (package 38) builds and tests it on GitHub. |
| `os/` | The Bazzite-based AresOS image (from PR #3). |

**Only one Minecraft client-test run at a time on the laptop.** Two test clients steal each other's window focus, which opens vanilla's pause menu and breaks click-driven tests (seen 2026-10-22 on Windows). Under AresOS `mod/dev/client-test.sh` takes care of it (package 29): the game runs in its own headless compositor, never on the owner's screen; one lock (`~/.cache/aresos-dev/client-test.lock`) lets one run through at a time and the others wait; and it refuses while the owner's own game (Lunar Client) runs or under 6 GiB of free memory. Builders use the scripts and never call `./gradlew` themselves. On Windows the old rule stands: don't start an integration gate while a package is in its client-test phase.

**Builders work in steps** (the owner's coordinator `mac-capacity`, 2026-11-13). An agent rereads its whole history on every step, so a long one costs several times a short one. Cut a package into steps: one fresh agent per step (about 250k tokens, roughly 80 tool calls), which commits, pushes and keeps `reviews/NN-slug/PROGRESS.md` up to date (done, left in order, what the code doesn't show); the last step deletes it. A builder stopped by a usage limit is restarted fresh from its commits. Claude builder agents cannot create a file named `REPORT.md` (their file tool refuses report files): they leave the full text in `PROGRESS.md`, the pull request's description or their last message, and I commit it.

**Who builds what until Codex ends (2026-11-21):** data, flows, rules and tests go to Codex builders; how a screen or the world looks, and hard design, go to Claude agents on Fable (`mac-capacity` for the owner, 2026-11-13). Codex's allowance is lost when it ends; Claude's weekly allowance is the scarce one.

**Memory on the laptop (16 GB).** Gradle needs about 6 GB free, and a full WSL suite 4–5 GB, one suite at a time. Each package uses its own `pkgNN-` script and `/tmp` names. Claude Code may stop background work while memory is low. Restart it once enough memory is free again (owner, 2026-11-10, board #160). First check whether the work actually finished: a stopped review often still wrote its `REVIEW-N.md`.

## Owner decides (always ask, never assume)

- Anything touching the laptop's disks, partitions or BIOS/boot settings, or installing AresOS onto a drive. Once he has said yes, Claude may carry it out itself (hard rule 1).
- Installing system software on Windows (JDK, drivers, tools). Ask once per tool.
- Spending money: hardware, subscriptions, credits.
- Publishing an AresOS image (a new release in the package registry) or changing what the laptop installs (the pinned image in `docs/INSTALL.md`). Test images that a CI job builds and throws away (never pushed to a registry, never pinned) need no OK (owner, 2026-11-07).
- Making the repo or anything else public.
- Design calls that are hard to undo or change how AresOS feels. A Codex `JUDGMENT-CALL` goes to the owner before merge.

## Hard rules

1. **AresOS on its own SSD (owner decision, 2026-10-22; replaces the earlier same-drive dual-boot plan).**
   - AresOS lives on a second internal NVMe SSD in the free M.2 2280 slot (Crucial P310 500 GB).
   - The Windows SSD (Micron 512 GB) is never partitioned, formatted, resized or written to, and Windows' boot files are never modified.
   - Same-drive dual boot stays documented only as a fallback.
   - Claude runs the laptop's disk, boot and terminal steps itself where it can, instead of handing the owner commands to type (owner, 2026-11-08: "If you give me cmds and I run them there's no real diff"). Before a step that could destroy or change something that matters (erasing or writing a drive, partitions, boot order or firmware settings, system software), say in plain words what it does and what could go wrong, and wait for his OK. Read-only checks need no OK. The owner still does what needs his hands or eyes (F2/F12 screens, the Linux side until Claude runs there), and his secrets (passphrases, tokens) stay with him. Codex never runs disk or boot tools on the real laptop.
2. Never commit Mojang or Supercell assets. Vanilla textures load from the game at runtime.
3. Never touch the owner's real `.minecraft` folder or Lunar Client unless asked. Development uses the Gradle dev client (`runClient`).
4. Agents never merge or push to `main`. Only I merge, after the checks in `docs/WORKFLOW.md`.

## How I write to the owner

Plain language, outcome first. Explain technical things through what they'll see in the game. Bring decisions with a recommendation, not a menu.

## Codex models

Pick the model for each job by what does that job best, never by habit or a fixed default. This is the owner's rule for all projects ("Codex models: pick per task" in the global `~/.claude/CLAUDE.md`, 2026-11-07). Names change, so check the list before the first launch of a session:

```powershell
(Get-Content "$env:USERPROFILE\.codex\models_cache.json" -Raw | ConvertFrom-Json).models | Where-Object visibility -eq 'list' | Sort-Object priority | Format-Table slug, description
```

`docs/WORKFLOW.md` and `docs/REVIEW.md` call the chosen models `$BUILD_MODEL` (build a package), `$REVIEW_MODEL` (package review) and `COUNCIL_MODEL` (councils, hard design). Set them for each job. The frontier model uses the weekly allowance about three times faster than the workhorse, so weigh quality against speed and allowance. Say in the brief or status which model you picked and why, and name it in the commit trailer. A model named in an older brief, report or handoff records the choice made then, not a default.

Starting efforts: builds and councils `xhigh` (`max` before irreversible steps), reviews `high`.

- Always pass `-m` and `-c model_reasoning_effort=...` explicitly. The Codex config default is an older model.
- Keep Codex current with `npm install -g @openai/codex@latest` (0.163.0 on 2026-10-21).
- Never use Spark.
- ChatGPT Pro runs until 2026-11-21. On a rate limit, back off; don't retry in a loop.
