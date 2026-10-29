# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up. Detailed history lives in each package's `reviews/NN-*/REPORT.md` and its briefs.

## Where things are (2026-10-29)

**Nothing is running in CI.** CI waits for **1 November** (fresh free org minutes). The owner's paid overflow (an Actions budget of up to $10, about $8.30 used) is finished; the owner should set it back to **$0**.

### Package 14: owner tools (PR #13, draft)

- **Where:** branch `pkg/14-owner-tools`, worktree `C:/Users/pab/AresOS-14-owner-tools`.
- **Codex session:** `01a165f9-31fc-79c2-80de-0a8237188116` (gpt-6.1-sol xhigh). Resume it with `codex exec resume …` from the worktree, logging to `../AresOS-14<id>.log`.
- **Briefs:** `briefs/14*.md`. The latest is `14zu`.
- **Full story:** `reviews/14-owner-tools/REPORT.md`, newest section first.
- **Pushed head:** `65edb11`. **Local commits after it aren't pushed** (14zs/14zt reports, the 14zu work).
- **Proven in the VM qualification:**
  - offline install and hardware setup
  - Windows round trips
  - tools stick hot-plug, `install`, `prepare` and its zero-change rerun
  - network invariance
  - records and export, corrected stock
  - real token login (owner-length token proven)
  - `verify`, `switch`, `title`
  - the AresOS boot and login
  - `layout begin us`, the rejected plain-US login, the refused trial reboot, `layout revert`
- **Still to prove:** US International success, back to German, rollback, keep-stock, the final Windows checks.
- **Real owner-tool bugs the runs found (all fixed):**
  - flat `lsblk` JSON
  - `efibootmgr` 18 format; entries are now decided from the decoded `dp:` bytes
  - sudo `use_pty` broke the physical-session check (now logind/cgroup plus a nested sudo chain)
  - `ostree admin finalize-staged --hold` counted as busy
  - `loginctl` comma selectors

  Most other stops were in the test harness's console emulation.
- **Last stop (qualification 15):** the guest's xHCI controller died and took the USB keyboard with it. **14zu** (local, running or done: check `../AresOS-14zu.log`) moves the test keyboard to i8042/PS-2 and adds xHCI health checks.
- **On 1 November, resume Codex with a short brief:**
  - free minutes, org reserve back to **150**, closing reservation **12**
  - package cap and allowances raised to fit the bound; the settings are in `os/ci/rehearsal-packages.json`
  - one push, then probe and qualification on the same head

  If the console-typing harness needs more than about 3 more rounds, switch the remaining stages to serial-run commands. Physical typing is already proven for the earlier stages.
- **After acceptance:** a fresh package review (gpt-6.1-sol high, read-only), then the owner's "merge".

### Package 15: owner path and emergency card (PR #14, draft)

- **Where:** branch `pkg/15-owner-path`, worktree `C:/Users/pab/AresOS-15-owner-path`.
- **Codex session:** `01a17936-3347-7552-b472-a7e664893959`.
- **Status:** reviewed and fixed. The council delta re-check was **DELTA-CLEAN** on `e077bdf` (`reviews/councils/2026-10-25-install-gate/delta/`). Local commits aren't pushed.
- **Before merge:**
  1. Merge package 14's final head into it, with **merge commits only: never rebase or force-push.**
  2. Update the tools fingerprint and the PASS lines, then rerun its doc tests.
  3. Merge after 14.
- **Council check:** the tool changes since `e077bdf` need a short chair re-check, or at least the package review.

### Other

- **Hardware arrived 2026-10-26** (SSD, 2 sticks, screwdrivers). Keep it boxed until the guide is released: record A must come before fitting. The SSD return deadline is about **2026-11-09**.
- **Package 12** (the companion in the hub): the brief is drafted, waiting for the owner's go (scratchpad draft path in the transcript). Companions live in the private repo `Ares-Empire/companions`.
- **The CI secret `GHCR_READ_TOKEN`** expires about 2026-11-22.

## Watch out

- **Every push costs Actions minutes** (privacy check on push and PR). Batch pushes, and run the pinned local gitleaks first.
- **Low memory** stops Claude's background wrappers, but `codex.exe` keeps running. Find its PID and watch its log for `turn.completed`.
- **Never force-push, and never push `pre-rewrite/*`** (the 2026-10-23 history rewrite). The repo-local git identity uses the noreply email.
- **Only one Minecraft client-test run at a time** on the laptop.
- **Check every new check's assumptions against real retained output, not mocks.** Most of package 14's lost rounds came from invented fixtures.
- **Leftover worktrees** for merged branches 03–11 and 13 can be removed with `git worktree remove` once they're no longer needed.
