# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up.

## Where things are (2026-10-25)

- **PR #11 merged** (`0c5902a`, squash of briefs 11–11n). 11n's Part B passed in the protected-second VM order. The fresh fix re-review of `d7f0ac4..5d69724` said SAFE (`reviews/11-two-disk-rehearsal/REVIEW.md`, second section). Package 11's CI ledger closed at about 722/900 minutes (5 full runs and 1 Part B run). The org quota resets 1 Nov.
- **Package 13 (keyboard layout; draft PR #12, branch `pkg/13-keyboard-layout`, worktree `C:/Users/pab/AresOS-13-keyboard-layout`) stopped 2026-10-25 at its zero-cost gate (PLAN-GAP), no VM run, 0/250 minutes.** Findings: Anaconda 44.30's `ConfigureBootloader._set_kargs()` writes `vconsole.keymap=` from the localization module, and the value differed between runs (11k wrote `de`, 11n `us`), so the cause isn't in the retained evidence. labwc 0.9.6 with no `XKB_DEFAULT_*` falls back to US, so the AresOS session needs an image change, and the frozen-release verifier rejects `os/config` changes. **Waiting on the owner:** OK to build and publish a new private AresOS release (in the org, `ghcr.io/ares-empire/aresos`) for the session fix? Then brief 13b: treat the installer's value as untrusted and make the boot line follow the system setting whatever it wrote (OSTree `deployment_set_kargs` keeps one deployment per checksum; qualify it), the session reads the system's X11 layout, and log the localization values at the boundary as a diagnostic, not a gate.
- **Package 12 (the companion in the hub):** brief drafted, not committed, waiting for the owner's go. Draft: `C:/Users/pab/AppData/Local/Temp/claude/C--Users-pab/c9cf9395-8808-409c-be1f-c393ff13e99c/scratchpad/12-hub-companion.md`. On go: commit it as `briefs/12-hub-companion.md`, create worktree `../AresOS-12-hub-companion`, start a **new** Codex session (gpt-6.1-sol xhigh). The Claude crab look is never in this repo. After Codex defines the pack format, Claude writes the private Clawd pack in `C:/Users/pab/aresos-companions/clawd/` (front view 18x5, see the preview) and checks it in the dev client.
- **Companion preview** (private, not a git repo): `C:/Users/pab/aresos-companions/clawd/`. Round 2 (2026-10-25) split it into modules under `js/` (rig, props, world, travel, acts, main), plus `poses.html` (pose sheet) and `serve.py` (no-cache server on 127.0.0.1:8765). `?debug` shows a 4x magnifier, and `?timer` drives frames with a timer so tests run while the window is covered. The old version is `preview-v1.html`.
- **Later:** new releases from the org publish to `ghcr.io/ares-empire/aresos` with a new Sigstore identity (`publish.sh` and `os-image.yml` still name `carlsenares`). The CI secret `GHCR_READ_TOKEN` expires about 2026-11-22.

## History rewrite (2026-10-23 09:34 UTC)

- An owner-run Claude session rewrote the GitHub history to replace the personal email with the no-reply address. All SHAs changed, so SHAs in older docs name pre-rewrite commits.
- The old local heads are kept as `pre-rewrite/*`. **Never push them, and never force-push.**
- The repo-local git identity is `Patrik Breeck <287037715+carlsenares@users.noreply.github.com>`. The global identity is still personal, so a fresh clone needs the local identity set.

## Waiting on the owner

- **Hardware** (ordered 2026-10-22, €127.05: SSD, 2 USB sticks, PH0 + PH1 screwdrivers), delivery Mon 2026-10-26. The slot check happens when the parts arrive. The SSD return must be requested by about 2026-11-09. Details in `STATE.md`.
- **Go for package 12.**

## Watch out

- **Only one Minecraft client-test run at a time** on the laptop (focus stealing). If the owner is playing, keep Gradle and client tests out of packages.
- **Merging:** delete a branch only after `gh pr view N --json state` = MERGED. Never launch Codex into a worktree with unmerged files.
- **Low memory** stops Claude's background wrappers, but `codex.exe` keeps running. Check its PID and the `turn.completed` line in its log.
- **Codex assumptions:** check every new check's assumptions against the retained real inventories, not just mocks (11i lost a full run to a mocked `pgrep`).
- **Leftover worktrees** for merged branches 03, 04, 06, 07, 08, 09, 10 and now 11. Remove them with `git worktree remove` from the main checkout once nothing in them is needed (11's ignored `.work/` folders hold local scratch only; the evidence is committed).
- **Deferred work:** `briefs/03-followup-activation-audit.md` (activation-graph updater audit).
