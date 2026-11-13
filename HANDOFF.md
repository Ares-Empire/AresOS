# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up. Detailed history lives in each package's `reviews/NN-*/REPORT.md` and its briefs; the handoff before this one (the Windows laptop, up to 2026-11-13) is in this file's git history.

Written 2026-11-13 about 15:30 by `linux-aresos`, the OS lead, now running on the laptop itself (AresOS, user `ares`). `STATE.md` is current as of `7d96b30e`.

## Running right now

1. **Package 23, review fixes 5 is built** (PR #36, branch `pkg/23-minecraft-starts`, worktree `~/AresOS-23-minecraft-starts`; head `bab298fc`, code at `88ac79fd`, main merged in as `3fd0bc1c` without conflicts). Built by a Claude agent on Fable 5.2: the supervisor decides from Java's exit status alone (a SIGKILL by anyone latches, exit 0 is his quit, no facts latch, any other status is one counted crash), with a durable exit record and a rewritten model test (41,984 orders). Its report is the first section of `reviews/23-minecraft-starts/REPORT.md`.
   - Running since 2026-11-13 16:10: **REVIEW-6** (Codex gpt-6-astra high) in the detached checkout `~/AresOS-23-review`, output `reviews/23-minecraft-starts/REVIEW-6.md` there (log `~/AresOS-23-review-6.log`); copy it onto the branch and commit it. The **check build with VM**: run 43450839739 (the merge changed `build.sh` and `image-checks.sh`, and the VM's `desktop_jvm` check has not seen this round's wrapper). A Claude agent on Opus adds the release diff's reasons for package 23's four Java packages (`os/ci/release_diff.py`, `test_release27`): main's test fails on the merged head without them. After its push: hosted checks (`-f checks_only=true`) and a short delta check of that commit by a fresh reviewer.
   - Merge on SAFE with both runs green. JUDGMENT-CALL 10 is widened (a Java the wrapper had to SIGKILL latches recovery instead of restarting): covered by the owner's board #170 answer; tell him in the merge note. Then remove both worktrees and send one line each to `linux-hub` (briefs 30 and 31 start from that main) and `linux-tools` (18c's `os/` part).
   - From its native runs, for later: on the laptop the full suite has 125 failures or errors that the hosted runner does not have: `test_owner_update` (99; it expects a host without `rpm-ostree`, reaches the real `rpm-ostree status` here and leaves stand-in processes: never run it on the laptop), five owner-tools modules (15; test code against Python 3.14's pathlib, while the hosted runner has 3.12 and the laptop's tools run on 3.14), and the root-only tests. 22c's stage 1a should make the owner-tools tests pass on Python 3.14 too.
2. **27b is merged** (PR #41, `4d0c4dc5`, 2026-11-13): INSTALL-STATUS records the laptop's update, bound files may wait again in `os/manifest/ci/16/pending-rebind.json`, and the hosted checks-only job is green again (it now fetches full history).
3. **22c, every way back works after an update** (empire brief 278; brief `briefs/22c-ways-back-after-update.md`, on main since `6cca14b6`; worktree `~/AresOS-22c-ways-back-after-update`, branch `pkg/22c-ways-back-after-update`). The council's verdict is `reviews/councils/2026-11-13-22c-ways-back/VERDICT.md` (GAPS-FOUND 11, the direction stands); the brief carries every finding and a fresh Codex check's six edits.
   - A Claude agent on Fable 5.2 builds **stage 0 only** (the harness wiring and a VM probe of plain `set-default`), then stops and reports. Started 2026-11-13 about 16:05; Claude's usage window was expected to pause it until 17:40. If it did not survive the pause, start a fresh builder from the branch and the stage 0 section of `reviews/22c-ways-back-after-update/REPORT.md`.
   - The brief stops after stages 0, 1a, 1b and 2. Each next stage starts from a fresh builder with the brief and the report. Before stage 2 (the rehearsal): a fresh review of the tools (gpt-6-astra high, or a Fable reviewer: updates and rollback are the high-stakes class).
   - Owner: the repaired tools go on the laptop in their own short session before the next release (board #205, "Yes, tools on their own first"); Claude types the steps, he approves the password prompts. `update` going to the newest installed AresOS from anywhere is the integrator's decision on the council's advice; he sees it as a JUDGMENT-CALL with the "try this" note before the merge.
4. **Lunar Client** is installed in his home and he is signed in (`lunar`; details in `STATE.md`). Done on his "Both" (board #197): the external monitor at 180 Hz (until the next login; `wlr-randr --output HDMI-A-1 --mode 1920x1080@180Hz`) and Discord for his user (`discord`). Open: the check of graphics card, sound and frame rate once a game runs (a background watcher in the lead's session reports it). Read-only checks only; never touch `~/.lunarclient`.

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
