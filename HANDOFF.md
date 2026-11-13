# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up. Detailed history lives in each package's `reviews/NN-*/REPORT.md` and its briefs; the handoff before this one (the Windows laptop, up to 2026-11-13) is in this file's git history.

Written 2026-11-13 (last update 19:00) by `linux-aresos`, the OS lead, now running on the laptop itself (AresOS, user `ares`). `STATE.md` is current as of `7d96b30e`.

## Running right now

1. **Package 23 is merged** (PR #36, `3bff81b6`, 2026-11-13 20:57; see `STATE.md`, Done). `linux-hub` (briefs 30 and 31) and `linux-tools` (18c's `os/` part) were told; both cut from this main.
2. **27b is merged** (PR #41, `4d0c4dc5`, 2026-11-13): INSTALL-STATUS records the laptop's update, bound files may wait again in `os/manifest/ci/16/pending-rebind.json`, and the hosted checks-only job is green again (it now fetches full history).
3. **22c, every way back works after an update** (empire brief 278; brief `briefs/22c-ways-back-after-update.md`, on main since `6cca14b6`; worktree `~/AresOS-22c-ways-back-after-update`, branch `pkg/22c-ways-back-after-update`). The council's verdict is `reviews/councils/2026-11-13-22c-ways-back/VERDICT.md` (GAPS-FOUND 11, the direction stands); the brief carries every finding and a fresh Codex check's six edits.
   - **Stage 0 is done** (2026-11-13, head `5998739f`, draft PR #46): the VM probe (run 43470161858) showed that plain `ostree admin set-default` behaves as the brief's rule 3 assumes in all six orders; the captures are in `reviews/22c-ways-back-after-update/runs/reorder-probe-43470161858/`. The job ended red on a check of the probe's own, since corrected; no rerun (the integrator's decision is at the end of the stage 0 section of `reviews/22c-ways-back-after-update/REPORT.md`).
   - **Stage 1a runs in three steps with a fresh builder each** (mac-capacity, 2026-11-13). Each ends with a commit, a push and a section in `reviews/22c-ways-back-after-update/REPORT.md` with "For the next builder".
     - **Step 1, the state machine: done** (a Claude agent on Fable 5.2, head `ee6cf085`). Section A is built: rules 1 to 11 in `os/owner-tools/owner.py`, `os/release/start-next.sh`, tools version 3, `os/tests/test_ways_back.py` (29 tests). Rule 7 (layout) had no test yet. The hosted suite is red on purpose (run 43496675626: 40 failures, 23 errors, 0 skipped): 51 old expectations in `test_owner_update` (B9), 9 older fakes, 4 fingerprint pins (stage 1b). Its JUDGMENT-CALLs 7 to 11 and PLAN-GAPs 5 to 8 are in the report.
     - **Step 2, the layout tests and the model test: first part done** (Codex gpt-6-astra xhigh, head `64f4d34a`): the layout tests (B7), the independent ledger and fake, the capture checks and the first revert proofs. It found and fixed four defects in the state machine (a late removal warning, missing layout recovery guidance, an erased finish proof, a repair blocked by another trial). It stopped on a conflict in the brief: in `[R13*, R27, S]` with a bundle for a release that is not installed, rules A4 and A6 make `update` stage that release, while B2 wanted every installed system reachable by one command. **Decided by the integrator** in `briefs/22c-b2-destination-invariant.md` (on the branch): the rules stand, the invariant gets the exception and a walked two-step path (boot menu, then `update`). Hosted run 43506717597: 1019 tests, 41 failures, 23 errors, 0 skipped (the known set plus that one assertion).
     - **Step 2b, the model closed: running since 2026-11-13 22:20** (Codex gpt-6-astra xhigh; prompt `~/AresOS-22c-step2b.prompt.txt`, log `~/AresOS-22c-step2b.log`, last message `~/AresOS-22c-step2b.last.md`). It was started from the lead's session: if that session closes, check the log and the branch and restart from the prompt file with `< /dev/null`. Codex stood at 80% of its week at 22:15.
     - **Step 3, not started:** the tools-version-2-to-3 compatibility tests (B8) and rewriting the old expectations in `test_owner_update` (B9). gpt-6.1-sol xhigh fits if Codex is below 90%; otherwise a Claude agent. Then stop for stage 1a's report, then stage 1b, then the tools review before stage 2.
   - The brief stops after stages 0, 1a, 1b and 2. Each next stage starts from a fresh builder with the brief and the report. Before stage 2 (the rehearsal): a fresh review of the tools (gpt-6-astra high, or a Fable reviewer: updates and rollback are the high-stakes class).
   - Owner: the repaired tools go on the laptop in their own short session before the next release (board #205, "Yes, tools on their own first"); Claude types the steps, he approves the password prompts. `update` going to the newest installed AresOS from anywhere is the integrator's decision on the council's advice; he sees it as a JUDGMENT-CALL with the "try this" note before the merge.
4. **Lunar Client** is installed in his home and he is signed in (`lunar`; details in `STATE.md`). Done on his "Both" (board #197): the external monitor at 180 Hz (until the next login; `wlr-randr --output HDMI-A-1 --mode 1920x1080@180Hz`) and Discord for his user (`discord`). Open: the check of graphics card, sound and frame rate once a game runs (a background watcher in the lead's session reports it). Read-only checks only; never touch `~/.lunarclient`.

## Waiting on others

- `linux-hub`: brief 30, his installed programs in the hub (`~/AresOS-30-installed-programs/briefs/30-installed-programs.md`). It builds after 23 merges and sends the PR number when its two reviews say SAFE; the OS lead then reads the `os/` diff.
- `linux-tools`: brief 18c, the control tools in the image (`~/AresOS-18c-image-test/briefs/18c-image-test.md`, draft PR #42). Its "os/ change proposal" and 12 questions wait for the OS lead's answers. Already told: 23 lands first, and nothing of 18c goes into a release without the owner's separate OK.
- `mac-aresos-control`: the Chrome PR #27, planned for Monday 11-16; it closes the `pkg/20-chrome*` board items itself.
- **Codex rule for all sessions (mac-capacity, 2026-11-13 21:10; one shared allowance, 73% used at 21:05, refill Tuesday 11-17 10:53):** below 90% use it freely; from 90% only reviews and fix checks, new Codex builds wait for Tuesday; at 100% reviews switch to Opus until Tuesday.
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
