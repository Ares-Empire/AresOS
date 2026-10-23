# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up.

## Where things are (2026-10-23, about 18:25)

- **Package 11** (draft PR #11, branch `pkg/11-two-disk-rehearsal`, worktree `C:/Users/pab/AresOS-11-two-disk-rehearsal`). Part C (media pins) is done. **11b** (real Anaconda Web UI pages driven from host Chromium) stopped at 05:37 after 168/350 minutes and 0/3 full runs. All pre-install pages and the review work in the first drive order. The protected disk stayed byte-identical with zero writes. It stopped on the strict NVRAM rule: when the ISO and empty target were detached, OVMF pruned its own auto-created entries for them (Boot0002 DVD, Boot0004 target). Both carried exactly the EDK2 auto-create GUID `8108ac4e-9f11-4d59-850e-e21a522c59b2` as OptionalData. The Windows entry stayed identical.
- **Integrator decision (brief 11c):** a firmware-owned option (OptionalData exactly that GUID) may be removed only for a device not attached in that boot, and added only for an attached one. Everything else stays strict.
- **11c running since 18:21** (`briefs/11c-firmware-entries-and-installs.md`): the narrow rule plus regressions, a probe, then the full Part A (both orders) and Part B. Cap 330 minutes and 3 full runs (about 450 account minutes were left in October). It resumes the 11b Codex session `01a165f9-31fc-79c2-80de-0a8237188116`. Codex PID 26584, log `C:/Users/pab/AresOS-11c.log`, final message `../AresOS-11c.last.md`.
- **11c stopped 19:08 after 15/330 minutes** (pushed `ad882d5`, privacy checks green). The firmware-owned rule and its regressions are done and natively qualified. The probe was blocked before any VM: GHCR returned `manifest unknown` for `ghcr.io/carlsenares/aresos@sha256:362af9b7…` to the job token. The repo moved to the **`Ares-Empire` org** that morning. The package most likely still exists under the user (the registry says DENIED for scope, while the org path says NAME_UNKNOWN), but the moved repo lost Actions access. That fix was not possible: a user-owned package only offers personal repos for Actions access, which the integrator checked in Chrome on 2026-10-24. **Owner decision 2026-10-24:** CI reads the release with the Actions secret `GHCR_READ_TOKEN` (classic, read:packages only, expires about 2026-11-22), and only in dispatch rehearsal jobs. **11d running since 2026-10-24 00:35** (`briefs/11d-owner-read-token.md`, the same Codex session, PID 34080, log `C:/Users/pab/AresOS-11d.log`, final message `../AresOS-11d.last.md`). It shares 11c's 330-minute / 3-full-run cap.
- **Later:** new releases from the org publish to a new path (`ghcr.io/ares-empire/aresos`) with a new Sigstore identity. Nothing baked into the image trusts the old one, because updates are digest-pinned manual switches. `publish.sh` and `os-image.yml` still name `carlsenares`.
- **When it finishes:** read the 11c and 11d REPORT sections, then the package review (`docs/REVIEW.md`), the fix loop, and an explicit owner "merge". Bring any JUDGMENT-CALL to the owner in plain language.

## History rewrite (2026-10-23 09:34 UTC)

- An owner-run Claude session rewrote the whole GitHub history to replace the personal email with the no-reply address, and added `privacy-check.yml` and `.gitleaks.toml`. All SHAs changed. SHAs cited in older docs and reports name pre-rewrite commits.
- The local `main` and the package 11 branch now track the rewritten remote. The old local heads are kept as `pre-rewrite/main` and `pre-rewrite/pkg/11-two-disk-rehearsal`. **Never push them, and never force-push.**
- The repo-local git identity is `Patrik Breeck <287037715+carlsenares@users.noreply.github.com>`. The global identity is still the personal email, so commits in a fresh clone need the local identity set.
- The owner turned on GitHub "Keep my email addresses private". Before that, GitHub's PR test-merge commits used the personal email and failed the privacy check. The leftover worktrees 03 to 10 still hold old-history branches.

## Waiting on the owner

- **Hardware ordered 2026-10-22** (€127.05: SSD, 2 USB sticks, PH0 + PH1 screwdrivers), delivery Mon 2026-10-26. The owner couldn't open the laptop without the right screwdriver, so the slot check now happens when the parts arrive. The SSD return must be requested by about 2026-11-09. Details are in `STATE.md`.

## Watch out

- **Only one Minecraft client-test run at a time** on the laptop (focus stealing). If the owner is playing, keep Gradle and client tests out of packages.
- **Merging:** delete a branch only after `gh pr view N --json state` = MERGED. Never launch Codex into a worktree with unmerged files. Claude Code's auto mode blocks `gh pr merge` without an explicit owner "merge" in chat.
- **Low memory** stops Claude's background wrappers, but `codex.exe` keeps running. Check its PID and the `turn.completed` line in its log. The owner can start Claude Code with `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` to prevent this.
- **Codex assumptions:** before a full CI run, check every new check's assumptions against the image's retained package inventory (06d lost both runs assuming SDDM; Bazzite uses Plasma Login Manager).
- **CI minutes:** about 1,550 of 2,000 used in October (estimate; `gh` lacks the billing scope). Other repos share the quota.
- **Leftover worktrees** for merged branches 03, 04, 06, 07, 08, 09 and 10. Remove them with `git worktree remove` from the main checkout. The safety check blocks deleting a folder the session is inside.
- **Deferred work:** `briefs/03-followup-activation-audit.md` (activation-graph updater audit).
