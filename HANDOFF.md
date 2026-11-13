# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up. Detailed history lives in each package's `reviews/NN-*/REPORT.md` and its briefs; the handoff before this one (the Windows laptop, up to 2026-11-13) is in this file's git history.

Written 2026-11-13 about 15:30 by `linux-aresos`, the OS lead, now running on the laptop itself (AresOS, user `ares`). `STATE.md` is current as of `7d96b30e`.

## Running right now

1. **Package 23, review fixes 5** (PR #36, branch `pkg/23-minecraft-starts`, worktree `~/AresOS-23-minecraft-starts`, was at `b32af2e2`). A Claude agent on Fable 5.2 builds `briefs/23-review-fixes-5.md` (the brief is on the branch). It was also told to merge `origin/main` into the branch once the fixes pass, to run both full suites natively on the merged head, and to push work in progress.
   - Next: read its report. If the image inputs changed through the merge, start a check build (`gh workflow run "OS image" --ref pkg/23-minecraft-starts -f check_build=build`). Then a fresh Codex review as `REVIEW-6.md` (gpt-6-astra high fits; give it the owner's review bar from the brief). Merge on SAFE with passing checks.
   - On merge, send one line each to `linux-hub` (its brief 30 is cut from a main with 23) and `linux-tools` (18c's `os/` part likewise).
2. **27b is merged** (PR #41, `4d0c4dc5`, 2026-11-13): INSTALL-STATUS records the laptop's update, bound files may wait again in `os/manifest/ci/16/pending-rebind.json`, and the hosted checks-only job is green again (it now fetches full history).
3. **22c, council on the brief.** Folder `reviews/councils/2026-11-13-22c-ways-back/` (untracked in the main checkout until the verdict): `QUESTION.md`, `BRIEF-DRAFT.md` and `planner-material/`. Members: `os-reliability.md` (Codex gpt-6-astra xhigh, log `~/AresOS-council-22c-os-reliability.log`), `safety.md` (Claude, Fable 5.2), `architecture.md` (Claude, Opus).
   - Next: a fresh chair writes `VERDICT.md` (`docs/REVIEW.md`). Bring the verdict to the owner in plain words. Fix the draft, take a number with `board brief aresos`, commit it as `briefs/22c-ways-back-after-update.md` and start a Fable builder for stage 1. It starts after 27b merges (same files).
   - Owner answers so far: board #195 (he wants a short command, `aresos update`, instead of the long path; he did not object to `update` being the way to the newest AresOS from anywhere, so the draft's assumption stands until he says otherwise; confirm it once) and board #196 (the repaired tools come with the next release; Claude runs the steps and he approves the password prompt).
4. **Lunar Client** is installed in his home and he is signed in (`lunar`; details in `STATE.md`). Open: the check of graphics card, sound and frame rate once a game runs, and board ask #197 (the external monitor at 180 Hz, Discord). Read-only checks only; never touch `~/.lunarclient`.

## Waiting on others

- `linux-hub`: brief 30, his installed programs in the hub (`~/AresOS-30-installed-programs/briefs/30-installed-programs.md`). It builds after 23 merges and sends the PR number when its two reviews say SAFE; the OS lead then reads the `os/` diff.
- `linux-tools`: brief 18c, the control tools in the image (`~/AresOS-18c-image-test/briefs/18c-image-test.md`, draft PR #42). Its "os/ change proposal" and 12 questions wait for the OS lead's answers. Already told: 23 lands first, and nothing of 18c goes into a release without the owner's separate OK.
- `mac-aresos-control`: the Chrome PR #27, planned for Monday 11-16; it closes the `pkg/20-chrome*` board items itself.
- `mac-capacity` coordinates the Claude and Codex allowances. Ask it before several Fable agents at once. On 2026-11-13 14:45 Codex stood at 55% of its week (refill Tuesday 11-17 10:53; ChatGPT Pro ends 11-21).

## Then, in `STATE.md`'s order

- **21b** (backlight and power button): the read-only results are in `STATE.md`. Still needed: the owner's key test for brightness, and a watched press of the power button (take a `handle-power-key` inhibitor first, or the press powers the laptop off). Board #149's list sits on the Mac (`ssh aresium cat aresos-checks-21b.md`); delete it there once 21b's brief is written.
- **The next release**: 23, 21b, 22c's tools and the image items in `STATE.md`. It goes beyond the owner's standing OK for packages 21 to 24, so publishing needs his OK. `at update` on the laptop stays his step; Claude may type it for him with his OK.
- **Documents that still describe the Windows laptop**: `CLAUDE.md` (the PowerShell model list, `.\gradlew.bat`), `docs/WORKFLOW.md` and `docs/REVIEW.md` (`/c/Users/pab/...` paths), `AGENTS.md` (the WSL suite). The rows of `docs/INSTALL-STATUS.md` that still describe the time before the update are listed in 27b's report section.
- **Tests on the laptop itself**: the 22c planner read that `test_owner_update`'s real-entry tests use `Required tool missing: rpm-ostree` as their marker, so they cannot pass where `rpm-ostree` exists. Unverified until package 23's native run reports.

## How things work on this machine

- Worktrees are `~/AresOS-NN-slug`. Codex is installed (`codex exec -m … -c model_reasoning_effort=… -s read-only -C <worktree> -o <file>`); its model list is `~/.codex/models_cache.json`, its usage is in `~/.codex/sessions/<date>/*.jsonl` (`rate_limits`).
- `ares` is an administrator behind his own password since R27. Anything with `sudo`, system settings, boot or disks needs the owner's explicit OK in the session; he types his password himself (`sudo -A` opens the desktop's password prompt).
- The owner uses the laptop while agents run: one full suite at a time, no Gradle client tests on his screen (`linux-hub` runs them headless under the lock `~/.cache/aresos-dev/client-test.lock`), and modest local load while he plays.

## Watch out

- Never force-push, and never push `pre-rewrite/*` (the 2026-10-23 history rewrite). The repo-local git identity uses the noreply email. The repo is public: nothing personal in commits; the pre-push privacy check enforces it; never `--no-verify`.
- The repository secret `GHCR_READ_TOKEN` (rehearsal and release runs) is valid until about 2026-12-07; the owner renews it.
- Check every new check's assumptions against real retained output, not mocks.
- From a Claude Bash call, `pgrep -f` matches its own shell: match processes by PID or exact executable path.
