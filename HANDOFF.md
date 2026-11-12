# Handoff

The baton from the last session. Read it after `STATE.md`. Overwrite it when you pick it up. Detailed history lives in each package's `reviews/NN-*/REPORT.md` and its briefs.

## The repo is public now (2026-11-02, from the MacBook session; keep this until both points are done)

- `Ares-Empire/AresOS` is a fresh **public** repo since 2026-11-02 23:59. Every branch came over with the same commit
  hashes, so clones and worktrees need nothing: pull as usual. The old repo is the private archive
  `Ares-Empire/AresOS-archive-2026-11` (read-only): the pull requests #1–#15 and their discussion, the old branch
  `pkg/03-os-image` and the Actions history live there. PR numbers start again at #1 in the new repo.
- Public repos get free Actions minutes on GitHub's standard runners, so the $0 budget no longer limits `os-image.yml`.
- **Two settings did not come along** (GitHub keeps them per repo); Patrik restored both on 2026-11-07:
  1. The repository secret `GHCR_READ_TOKEN` (used by the release-13 and rehearsal runs): a new classic token with only
     `read:packages`, valid 30 days (until about 2026-12-07). Renew it the same way before then if runs still need it.
  2. Write access for the new repo's workflows on the `aresos` package in GHCR (Package settings → Manage Actions
     access → `AresOS`, Write role). Not yet exercised: the next publishing run shows it works.
- Public means: nothing personal in commits (the pre-push privacy check enforces it; never `--no-verify`).

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
- **Then:** a package review of 15. It also checks the council delta's November runtime conditions against qualification 21. Then the merge, then the physical install (SSD return deadline about 2026-11-09).
- **Owner permission (2026-11-02):** "you can merge once its safe to merge, this is permission."
- **15d and 15e:**
  - REVIEW-3 was CHANGES-NEEDED: a second abandon, and an interrupted finish that may have persisted the new map. The mounted-child runtime check is kept OPEN.
  - 15e fixed the documents only. REVIEW-4: **SAFE**.
- **PR #14 MERGED 2026-11-02** as squash `2f4c0d9`.

### Next: the release decision (owner)

- `docs/INSTALL-STATUS.md` keeps the physical install NOT RELEASED until physical and novice gates close "before opening the laptop, writing installation media or installing". Most of those can only close on the laptop.
- **OWNER DECISION (2026-11-02): staged release,** with the owner as first reader and Claude checking each stage's records before the next:
  - **A, released now:** steps 1–2 (Windows prep, recovery stick, record A, installer stick write and test boot).
  - **B, after A's records are checked:** step 3, fitting, by about 2026-11-09, with Claude checking the photos and record B.
  - **C:** steps 4 onward, after A and B, package 16's native mounted-child check, and a table update.
- **Package 16** (`pkg/16-staged-release`, worktree `C:/Users/pab/AresOS-16-staged-release`, Codex thread `01a19de6-f5b9-7b83-bfe8-3c530e9402eb`, log `../AresOS-16.log`):
  - records the staged release in `INSTALL-STATUS.md`/INSTALL.md
  - adds the native mounted-protected-child refusal check
  - wires a probe-only dispatch (cap 120 minutes, 2 probes)
  - one push, a PR, one probe
- **Package 16 MERGED 2026-11-02** as `4e69540`. Review SAFE, no findings. Probe run 41532052332 passed: mounted-child refusal, zero mutations, cleanup. INSTALL-STATUS: stage A RELEASED, B after A is checked, C NOT RELEASED.
- **Stage A help:** Claude copied the verified ISO (776b76f3…, equal to the pin and the fresh official checksum) and FedoraMediaWriter-win64-5.3.2.exe (f53e0c11…, equal to the pin and the GitHub digest) into Downloads. The owner installs the writer and writes the sticks themselves.
- **Stage A DONE and CHECKED 2026-11-05.** PR #1 of the public repo **MERGED** as `e0f737b` (reviews `reviews/status-stage-a-checked/`, REVIEW-4 SAFE). INSTALL-STATUS: A CHECKED, B RELEASED, C NOT RELEASED.
  - Every step 1–2 record passed: cloud backups opened online, recovery stick booted, UEFI/Secure Boot off/decrypted/hibernation off, record A in OneDrive, writer cancel trial, "erfolgreich geschrieben", live desktop boot.
  - Afterwards the Windows disk and its four partitions matched record A (read-only check).
  - Private records stay out of the public repo.
- **Stage B (fitting) DONE and CHECKED 2026-11-07,** guided step by step (recorded in INSTALL-STATUS by PR #13, merged `f5bc2d4d`). Battery, seating and Crucial-label photos PASSED (checked by a Claude session on the Mac; the photos stay private). The F2 screen listed both drives (owner-reported: an "M…" and a long "C…" name; no photo). By owner decision, the maintainer's read of Windows' disk inventory (Micron GPT, Crucial `CT500P310SSD8` 466 GB RAW) stands in for checking that screen. The expendable fitting trial and the damaged-battery photograph trial stay OPEN; they are not Stage C conditions. Record B after-fit PASSED: Windows disk identity, all partition GUIDs/types/boundaries and the original Windows boot target match record A. A broken bottom-cover screw post (front corner, likely the old rattle) was removed, so that one screw stays out. The stage record is `after-fit-20261107-191942-745.json` beside record A in the owner's OneDrive.
- **Stage C RELEASED 2026-11-07** (PR #13 merged `f5bc2d4d`; REVIEW.md CHANGES-NEEDED fixed, REVIEW-2.md SAFE; Linux tests OK). **Next:** step 4 with the owner, each step's record checked before the next. Linux-side steps: the owner sends screens to a Mac session (no serials or GUIDs in any message or repo). Windows-side steps: here.
- **2026-11-08: step 4 DONE, step 5's Windows half PASSED** (see STATE). Linux-side steps run with `mac-aresos-install` (PASS/FAIL reports, no values). Next: step 5's Linux half when the owner reboots into Bazzite, then step 6. Records live in the owner's OneDrive `Dokumente/AresOS-own-ssd-record` (record A, after-fit, three after-bazzite, and `record-C-compare-card.txt` with the printed serials). The elevated record-B runner is the guide's block with its answers filled in; it waits up to 3 minutes for USB sticks to be pulled.
- **2026-11-09: install-night guide fixes merged** (PR #23, `a1052cf0`; see STATE). The owner pages now match what step 4 needed; the ten-minute hung-shutdown rule is owner-approved. Nothing is running; no open PR. Step 5's Linux half waits for the owner.
- **2026-11-10 ~13:00: packages 21, 22 and 24 are MERGED** (`25ef5cd1`, `002dcc09`, `7cf0541b`); see STATE. Two Claude agents (Opus) are building in their own worktrees; each round gets a fresh Codex review:
  - **23 (Minecraft starts)**: `../AresOS-23-minecraft-starts`, agent `af1524c06373de3ac`. It started from `25ef5cd1`, before 22 merged, so it needs a merge of main if it touches a bound file.
  - **27 (the first update release)**: `../AresOS-27-first-update-release`, agent `afc79d03d9f22e06d`. Build, publish (owner OK), VM rehearsal, then pin. After it merges, tell the owner to run `at update` and `sudo passwd ares` (guided).
  - **~15:00 update:** 23 reported. PR #36 is in review: REVIEW-1 (Astra) in `../AresOS-23-minecraft-starts/reviews/23-minecraft-starts/REVIEW-1.md`, log `../AresOS-23-review1.log`. Owner asks #168/#169 are open. 27's first release run failed before publish; the second (last) dispatch is approved. The test-leak fix is PR #37 in `../AresOS-fix-update-test-leak`; REVIEW-1 (Sol) is there, log `../AresOS-fixleak-review1.log`. A WSL proof (`pkg22d-leak.sh` in the scratchpad) is running.
  - **Codex allowance:** reset 2026-11-10 10:54 and must last until 11-17 (mac-capacity). Use gpt-6.1-sol for narrow review rounds and keep gpt-6-astra for first reviews of big packages and for the release.
  - **Memory:** Claude Code stops background wrappers when RAM runs low, but `codex.exe` keeps running and writes its review, so check for `REVIEW-N.md` before restarting anything. Restarting stopped work once memory allows is OK (owner, board #160). Only one full WSL suite at a time, and two agents share the laptop.
  - **~15:00 UTC: Ubuntu's snapshot mirror (`snapshot.ubuntu.com`, pinned 2026-10-21) is down or very slow.** Every CI run that installs tools fails in "Install pinned tools" (502/503/504, or the 20-minute timeout):
    - 23's three `check_build=build` runs: 42827288649, 42829696745, 42834907206;
    - 27's release runs 3 and 4: 42831158090, 42835704653.
    - Nothing was built or published. Both agents wait.
    - A watcher (`mirror-watch.log` in the scratchpad) waits for two healthy checks. Then approve one 23 `check_build=build` and the next 27 release dispatch.
    - If the mirror stays slow, add apt retries and a longer step timeout in `os-image.yml`. It is bound, so do it inside package 27.
  - 23's REVIEW-2 (Astra) runs on `7ec26b84`, log `../AresOS-23-review2.log`. The owner answered #168, #169 and #170, so all of 23's calls are decided.
  - **Claude allowance (mac-capacity, 2026-11-11 07:05):** about 3.5% of the weekly is left for finishing 27 through merge. Work straight through; the 09:00–12:00 pause doesn't apply to 27.
    - Use one blocking wait per CI run, never polling: each wake of a ~1M-token agent is expensive.
    - If run 4 needs another real round, or Patrik's meter shows ~96%, stop at a clean point. The rest continues after the Thu 00:00 reset.
    - Guide Patrik through `at update` today only if 27 merges in time; otherwise after the reset.
    - **After the reset, start fresh agents.** Don't resume `afc79d03d9f22e06d` (about 1M tokens) or `af1524c06373de3ac` (about 0.9M).
  - **Stopped 2026-11-11 ~09:35 local for the Claude allowance (both packages at clean points):**
    - **27:** `pkg/27-first-update-release` at `8f28ca0b` or later, everything pushed. Rehearsal run 4 proved `at update`; the harness's util-linux pin stopped it after the R27 boot. After the reset, start a **fresh** Opus agent in `../AresOS-27-first-update-release` with `briefs/27-rehearsal-fixes-1.md`. Then the Codex review (Astra high), merge, and guide the owner through `at update` and `sudo passwd ares`.
    - **23:** parked at `b32af2e2`. After the reset, start a fresh Fable 5.2 agent in `../AresOS-23-minecraft-starts` with `briefs/23-review-fixes-5.md`.
    - Old agents `afc79d03d9f22e06d` and `af1524c06373de3ac` are stopped; don't resume them.
    - **Thu 11-12 00:08: the fresh 27 agent `acc21f0f24d7065a0` (Opus) started** with `briefs/27-rehearsal-fixes-1.md`.
    - **Thu 11-12 02:25: run 5 (43120759117, head `9ee933d9`) passed the util-linux fix, `at update`, the R27 boot and login,** then failed at `terminal_path` (`os/ci/owner_vm.py:1206`, "No terminal PATH probe"): the harness typed into foot right after Ctrl+Alt+F1, before labwc had resumed input. util-linux 2.41.5→2.41.6: login.c and agetty.c byte-identical upstream; the observer accepts exactly both.
    - **02:30: approved the fix** (probe prepared after the switch, wait for an Active logind session, one guarded retry with Ctrl+U, screenshots, the same check on every step that is new on a VM, update cap 7) and resumed `acc21f0f24d7065a0` for run 6. mac-capacity has the timing: at the earliest 07:00–08:00 if run 6 passes.
    - **04:30: run 6 (43136407300, head `5335f8a4`) stalled in R27's first boot on the VM** before `login:`: the serial log ends right after systemd 259's console size probes (`ESC[6n`), with `clocksource: Watchdog remote CPU 1 read timed out` just before. Run 5 booted the same image past that point. The probes only happen on the VM's serial console (`console=ttyS0`); the laptop has none. Read as a VM stall; **run 7 dispatched unchanged** (cap 8). If it stalls the same way: stop, diagnose (the agent has diagnostics ready, unpushed).
    - **04:40: final code review launched in parallel**: Codex gpt-6-astra high on `5335f8a4`, in a detached worktree `../AresOS-27-review`, output `reviews/27-first-update-release/REVIEW-1.md` there, log `../AresOS-review27-1.log`. After run 7: a short delta check of the cap commit, records and REPORT.md, then merge and Patrik's `at update`.
    - **04:55: REVIEW-1 is CHANGES-NEEDED** (committed on the branch as `cd3f273a` with `briefs/27-review-fixes-1.md`): (1, blocking) `Host.script()` runs update.sh with `timeout=1800`; a timeout SIGKILLs bash, the EXIT trap never re-masks the finalizers and `bootc` keeps staging. (2, should-fix) the util-linux check accepts suffixes like `2.41.6-rc1`. The agent builds the fix while run 7 runs (43148798803, head `dd7da09e`). Run 7 stays evidence for the route. If it passes: push the fix, cap 9, run 8 on the new bundle, step 6 on run 8, then a fresh delta review of the fixes. Earliest merge ~09:30; Patrik's update late morning or evening (mac-capacity told).
  - **Safety bar for AresOS tools (Patrik via mac-capacity, 2026-11-11 ~08:10; the control lead records it for decision 24):**
    - "baseline is basically MCPs or CLIs like any other mcp or cli that already exists", "reasonably safe", not "nothing could ever go wrong". It is a judgment that "cannot be taken too literally".
    - Extra care only where AresOS adds its own risk (Claude Code as system operator). Disks, boot, updates and rollback are already in that group.
    - For later tools (23's next round, 22c, the 25 guardian, desktop shortcuts), brief reviewers with this bar: adversarial edge cases come back as known limits, not blocking rounds, unless they touch those AresOS-specific risks.
  - **Fable week plan (Patrik via mac-capacity, 2026-11-11 ~11:00; the week runs Thu 11-12 00:00 to Wed 11-18 23:59):**
    - **Thursday, in order:**
      1. 27's last round overnight (fresh Opus agent at about 00:05), then guide Patrik through `at update`. Then he switches to AresOS.
      2. First job on AresOS: Lunar Client and a working Minecraft with his own Microsoft login, which he types himself, so he can stay on AresOS in the evenings. He asks for this, so hard rule 3 allows it.
      3. Then everything else.
    - **How to run the work** ("Fable on AresOS early with all work"):
      - a Fable session as orchestrator;
      - Fable agents for work that is new, heavy, important, quality-critical or design;
      - Opus or Sonnet agents where Fable isn't needed.
    - **Fable budget:** use Fable early, to fill the Fable half of the weekly by about Sat/Sun. Patrik then presses the Fable reset, which returns that usage. After the press, be selective with Fable.
    - **Keep the orchestrator lean:** hand reading to agents, and start fresh when the context gets long (each turn re-reads it at about 2× Opus cost).
    - **Home screen (the Minecraft hub):** ask Patrik for his pointers first. Don't design it before.
    - **Reviews:** Codex is out from about Sat until Tue 10:53 and ends for good on 11-21. Meanwhile, reviews run as a fresh Claude agent that isn't the builder, or as Codex from the Mac on Tue–Fri.
      - **Reviewer model (Patrik via mac-capacity, 2026-11-11):** Opus by default, this week too. Fable only for high-stakes reviews: AresOS-specific risks (updates and rollback, disks, software installs, credentials, system settings) and the final review before something reaches his laptop. Fable's cap is for building.
      - Done: CLAUDE.md, docs/REVIEW.md and docs/WORKFLOW.md carry the new rule (owner in the chat, 2026-11-11: "Yes change it"; b19a4cf1).
    - **Safety bar:** normal MCP/CLI level, with extra care for AresOS-specific risks (decision 24 clarification, PR #38).
  - **Fable 5.2 next week (about 2× Opus per token; Patrik plans a Fable-heavy week). Where it helps most:**
    1. **Package 23's hand-off** (`briefs/23-review-fixes-5.md`): five Codex reviews in a row found supervisor/wrapper races. It needs a simpler, conservative design: only certain crashes restart, anything uncertain waits for `retry`. A fresh Fable builder.
    2. **Package 22c** (rollback, then forward again, keep-stock and layout trials after an update; plus the refusal-invariant test gap from PR #37). It is the owner tools' state machine on his real disks, where mistakes are costly.
    3. **Package 25 (guardian) design**: B2's focus, stop and shutdown states and a clean world save at logout. It is design-heavy and touches 23's supervisor.
    4. **The next release's update path**: stop masking the finalize units in the image, review the updater allowlist, and a second-update rehearsal (R27 to the next release). Use Fable only if run 4 shows more surprises; otherwise Opus.
    - The WSL disk image is 14.2 GB with about 3 GB in use; compacting it needs admin.
  - **Disk resolved (2026-11-11 ~04:20 local):** C: has 132 GB free. With the owner's OK in the chat, AresOS-delete-me (115 GB) and 1,694 WSLg Remote Desktop `.etl` traces (11.5 GB, in `%TEMP%/DiagOutputDir/RdClientAutoTrace`) were deleted. The traces grow back slowly, so check them now and then. Board #174 and #175 are done.
  - **Trace logs, 2026-11-12 (board #179 "Yes, do both"):** they had regrown to 19 GB (about 1 GB/h) and were cleared again. `C:/Users/pab/.wslconfig` now has `[wsl2] guiApplications=false` (turns off WSLg, the likely writer); it applies from the next WSL start. Delete that file to undo. Check `%TEMP%/DiagOutputDir` size after a day.
- **Owner to-dos:**

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

- **Hardware:** the SSD is fitted (2026-11-07); the two Kingston sticks are the recovery and installer sticks from Stage A.
- **Package 12** (the companion in the hub): the brief is drafted, waiting for the owner's go (scratchpad draft path in the transcript). Companions live in the private repo `Ares-Empire/companions`.
- **The CI secret `GHCR_READ_TOKEN`** was renewed on 2026-11-07 and is valid until about 2026-12-07.

## Watch out

- **Pushes no longer cost Actions minutes** (2026-11-01): the privacy check runs locally before each push (aresync's pre-push hook) instead of on GitHub. Only `os-image.yml` dispatches use the org's minutes. gitleaks 8.30.1 flags 12 false alarms on `pkg/14-owner-tools` (sha256 checksums next to key/token file names in `os/manifest/ci/14/host-walk/*.json`, plus code in `os/ci/owner_vm.py` and `os/ci/owner_key_counter.py`): a new local commit carrying them (e.g. a local squash merge) is blocked until they're allowlisted in `.gitleaks.toml`.
- **Low memory** stops Claude's background wrappers, but `codex.exe` keeps running. Find its PID and watch its log for `turn.completed`.
- **Never force-push, and never push `pre-rewrite/*`** (the 2026-10-23 history rewrite). The repo-local git identity uses the noreply email.
- **Only one Minecraft client-test run at a time** on the laptop.
- **Check every new check's assumptions against real retained output, not mocks.** Most of package 14's lost rounds came from invented fixtures.
- **Leftover worktrees** for merged branches 03–11 and 13 can be removed with `git worktree remove` once they're no longer needed.
