# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up. Detailed history lives in each package's `reviews/NN-*/REPORT.md` and its briefs.

## Where things are (2026-11-01)

**The November round is running.** The owner's Actions budget is **$0 with "stop usage" on** (checked 2026-11-01), so only free minutes are used.

- **14zv** (free minutes, reserve 150) pushed `becfb22`, then STOPPED before the probe. The cause: on 2026-11-01 the owner moved the privacy check from GitHub to aresync's local pre-push hook (`fabd476`), so there was no PR privacy run and no `PRIVATE_TERMS` secret.
- **14zw** merged `main` and made the local hook the privacy proof; pushes now cost no minutes. On `75a2c63`, probe 27 PASSED.
  - Qualification 16 reached a new stage: US International was installed, its login worked, and `layout proof` and `layout finish` passed. It then stopped on a harness bug: `public_typing` collapsed `us-intl` to `us` and couldn't type `ü`.
  - Package ledger: 1832/2750 minutes.
- **14zx** fixed the profile adapter, and probe 28 PASSED.
  - **Qualification 17 proved** US International success, back to German, rollback, rollback-from-stock refused, and keep-stock.
  - It then stopped at the final stock login, with 65 of 66 key events counted. The cause was the harness's `EVIOCGKEY` on the counting evdev fd, which flushed the Return press.
  - **Still left:** the final stock verification and the final Windows checks.
  - Package ledger: 1967/2750 minutes.
- **14zy** fixed the counter: key-state queries now use their own evdev client, and a real-kernel uinput proof showed 0/1 for the old getter and 1/1 for the fix. On `cbaa985`, probe 29 PASSED.
  - Codex cancelled qualification 18 before its VM stage, for two reasons:
    1. GitHub's job `started_at` for probe 29 came after its `completed_at`, and the guard clamped that to 1 minute; the real charge was 26.
    2. A full-log scan found cosign-installer `RELEASE_COSIGN_PUB_KEY_SHA` lines. These are public checksums, verified against the pinned action source.
  - Package ledger: about 1998/2750 minutes.
- **14zz** made the accounting fail-safe (probe 29 is now charged 26) and approved the cosign class. On `10921f8`, probe 30 PASSED.
- **14zza** fixed the local classifier, which now judges whole source lines rather than gitleaks' redacted Match.
  - Qualification 19 ran on the same head. It proved US-intl, back to German and rollback; the post-rollback login took 10 s, and the sudo counts were 66/66.
  - It then hit the **106-minute VM step limit**. This was not a bug.
  - Package ledger: 2144/2750 minutes.
- **14zzb** set the VM step limit to 180 and the qualification bound to 220.
  - **PROBE 31 AND QUALIFICATION 20 PASSED** on `211df98`: the complete owner path, 600 native tests, VM 117.67/180 minutes. **Acceptance is met.**
  - The closing report `f13ac8e` is pushed. Package ledger: 2301/2750 minutes.
- **The package review** (`reviews/14-owner-tools/REVIEW.md` at `f13ac8e`) returned **CHANGES-NEEDED**.
  - **Blocking:**
    1. The bootstrap runs stick code before verifying it.
    2. An abandoned layout trial can't be recovered, and its layout could be active at the next boot's login.
  - **Should-fix:**
    3. resumable install/prepare
    4. STOP diagnostics left out of the export
    5. stale status lines
- **14zzc** implemented all five fixes and pushed `b15d52f`. The new bootstrap fingerprint is `3e2c78eb…`. A layout trial now changes only the runtime map, and `layout abandon` was added. The qualification gained a mid-trial `system_reset` stage.
  - Probe 32 FAILED in its native suite: test fixtures copied a source tree that contained CI-written `__pycache__`. Production is unaffected (`-I -B`, read-only stick).
  - Package ledger: 2310/2750 minutes.
- **14zzd** built the fixtures from the manifest and pushed `dda72ed`. Probe 33 passed all 627 native tests, then STOPPED with "Host walk is stale".
  - Cause: a CRLF-declared PowerShell test source was bound to its LF blob hash. All 195 blobs match, so it's an end-of-line binding bug only.
  - Package ledger: 2326/2750 minutes.
- **14zze** bound the sources to Git's checkout bytes and pushed `3fd7916`.
  - **PROBE 34 AND QUALIFICATION 21 PASSED,** with 630 native tests each. The qualification included the mid-trial `system_reset`, the German login and `layout abandon`. VM acceptance is met.
  - The closing report `ae90dd3` is pushed. Package ledger: 2474/2750 minutes. All dispatch allowances are used (34/21).
- **The re-checks:**
  - **REVIEW-2:** findings 1, 2, 3 and 5 CLOSED.
  - **14zzf:** a real STOP → export → reboot diagnostics test; no payload change.
  - **REVIEW-3:** finding 4 CLOSED, and the payload is unchanged since `3fd7916`. **SAFE.**
- **MERGED 2026-11-02** (owner's "merge") as squash `79a67d2`. The worktree `C:/Users/pab/AresOS-14-owner-tools` is kept for now: its `.work/` holds private retained evidence.

### Package 15 next step (2026-11-02)

- **15d** is running (log `../AresOS-15d.log`, summary `../AresOS-15d.last.md`):
  - merge `origin/main` with `--no-ff`
  - the new bootstrap block, fingerprint `3e2c78eb…`, `layout abandon`, card entries and the qualification 21 status
  - equality tests, then one push, and mark PR #14 ready
- **Then:** a package review of 15. It also checks the council delta's November runtime conditions against qualification 21. Then the owner's "merge", then the physical install (SSD return deadline about 2026-11-09).

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
- **Last stop (qualification 15):** the guest's xHCI controller died and took the USB keyboard with it. **14zu is done locally** (`8507dd6`, not pushed): the test keyboard is on i8042/PS-2, with AT-device counters and xHCI health STOPs; 103 regressions and the full stand-in walk pass.
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

- **Pushes no longer cost Actions minutes** (2026-11-01): the privacy check runs locally before each push (aresync's pre-push hook) instead of on GitHub. Only `os-image.yml` dispatches use the org's minutes. gitleaks 8.30.1 flags 12 false alarms on `pkg/14-owner-tools` (sha256 checksums next to key/token file names in `os/manifest/ci/14/host-walk/*.json`, plus code in `os/ci/owner_vm.py` and `os/ci/owner_key_counter.py`): a new local commit carrying them (e.g. a local squash merge) is blocked until they're allowlisted in `.gitleaks.toml`.
- **Low memory** stops Claude's background wrappers, but `codex.exe` keeps running. Find its PID and watch its log for `turn.completed`.
- **Never force-push, and never push `pre-rewrite/*`** (the 2026-10-23 history rewrite). The repo-local git identity uses the noreply email.
- **Only one Minecraft client-test run at a time** on the laptop.
- **Check every new check's assumptions against real retained output, not mocks.** Most of package 14's lost rounds came from invented fixtures.
- **Leftover worktrees** for merged branches 03–11 and 13 can be removed with `git worktree remove` once they're no longer needed.
