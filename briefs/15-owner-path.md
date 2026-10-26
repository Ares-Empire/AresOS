# 15: The owner path: one linear checklist, and an emergency card that works under stress

**Goal:** on install day the owner follows one linear checklist from a phone. Each step gives a short command or click path, says what the screen should show, says what to record, and says exactly where to go on STOP. When something goes wrong, the emergency card gets the owner to the right action in under 30 seconds.

This closes the install-gate council's remaining findings: **1 and 4 (blocking), and 8–11**, plus its "minimal owner version" list. Package 14 closed 2, 3, 5, 6 and 7 with the owner tools.

**Base:** this branch starts from package 14's pushed head (`5156f5f`). Package 14's commands are final (`os/owner-tools/commands.json`); only its VM qualification is still pending (it reruns on 1 November). **Don't change the owner tools, the bundle, the harness, the workflows or the image.** If a finding seems to need a tool change, stop and report a PLAN-GAP. A tool change would need a new VM qualification.

**Read first:**
- `AGENTS.md`
- `reviews/councils/2026-10-25-install-gate/`: VERDICT, the "minimal owner version" paragraph, and the three member files
- `reviews/14-owner-tools/REPORT.md`: both "For package 15" lists and the stage walk
- `docs/INSTALL.md`, `docs/EMERGENCY.md`, `docs/INSTALL-RECORD.md`, `docs/design/OS-BASE.md` §8 and Appendices C/D
- `os/owner-tools/commands.json` and the guide/command equality tests

## Owner decisions to keep (don't re-argue)

- Two sticks only: WINDOWS RECOVERY (keep), and ARESOS INSTALLER, which becomes the tools stick through Media Writer 5.3.2's restore.
- Offline from the live session until `prepare` has paused updates.
- The tools stick goes in only after Linux is up and signed in, and comes out before every restart. A forgotten stick at power-on: don't pick it in F12; unplug it and carry on.
- The backup stock keeps the installer's German layout. The recovery account stays `ares-recovery`. Automatic updates of the backup stay off during the trial.
- After a failed first switch boot: F12 → Windows → get help.
- AresOS stays publishable: no personal data in the repo.

## In scope

1. **One linear owner checklist** (`docs/INSTALL.md`), following the council's minimal version:
   - backups and recovery-media tests
   - encryption and power preparation
   - fitting stops, including the battery stop rule
   - same-session disk and EFI identification
   - installer plan review
   - corrected-stock preparation
   - account and signature checks
   - §5's unattended Windows proof
   - deployment and title checks
   - recovery login
   - token retirement

   Each step uses package 14's short commands verbatim, with the expected PASS line or screen, what to record, and an explicit **STOP → go to …** destination.
2. **Finding 1: return routes.**
   - Every checkpoint and detour ends with an explicit "Return to step N" link.
   - No link or route may reach authentication or switching before §5 has passed.
   - Add a test that walks every link in the guide (no browser Back), and fails if any route reaches §6's authentication or switching without passing §5's completion marker.
3. **Finding 4: token retirement.**
   - Permanent abandonment (leaving, removing or erasing Crucial, or giving up AresOS) requires revoking the private-pull token on GitHub from Windows or the phone. This applies even if Linux can't boot.
   - Give the click path as GitHub shows it today; verify the labels from current GitHub documentation and record the date.
   - Local deletion is optional cleanup, and only through existing commands or none. Don't add a tool.
   - Add an owner-side check that fresh authentication fails after revocation. If no existing command can show that, list it as a physical gate item; don't fake it.
4. **Finding 8: the emergency card** (`docs/EMERGENCY.md`):
   - Symptom-first: frozen laptop, the failed first switch boot, a stale title, a password not accepted, text over the prompt (press Enter), a forgotten stick at power-on, and a battery warning sign.
   - Immediate actions come first. Preparation, examples and CI history move to references.
   - Add a test: every symptom heading appears before any preparation text, and the first action under each symptom is at most a few lines down.
5. **Finding 9: keyboard labels.** `Ctrl = Strg` wherever a shortcut appears. FnLock on the LOQ: the Fn-modified alternative for F-key shortcuts, the expected login prompt, and how to return to the desktop (F1/F2 as applicable). Take these from Lenovo's documentation for this model, with links.
6. **Finding 10: Media Writer 5.3.2 in German.**
   - The exact German labels for selecting the ISO, choosing the stick, Write, the warning that appears after Write, cancelling, and completion.
   - The restore path ("Wiederherstellen") and its success message.
   - Verify the labels from the 5.3.2 tag's translation sources, not `main`.
7. **Finding 11: one current status table.**
   - Replace scattered status statements in INSTALL, EMERGENCY and OS-BASE with one current gate/status table, linked from everywhere else.
   - Reconcile the binding boot sequence (Linux-first until §5, Windows default after) in OS-BASE.
   - Move qualification chronology, audit counts and historical screenshots into the reports, linked from that table. Keep each result's drive-order, release and physical-test limits.
8. **Separate procedures, outside the initial path:** later layout changes, stock promotion, rollback/keep-stock, and optional removal/erasure. Keep their checks.
9. **Package 14's "For package 15" items:**
   - record navigation
   - STOP/help/photo handling
   - the two-stick round trip and eject reminders
   - recovery menu followability
   - account/session entry and exit
   - the "press Enter if text covers the prompt" note
   - keep the backup-layout exception and the NVIDIA deferred-work distinction
10. **Keep the existing guide/command and bundle equality tests passing unchanged.** Extend them only if the new layout needs it.

## Out of scope

- Any change to the owner tools, bundle, harness, workflows, image, release or audits.
- Any VM run or workflow dispatch.
- Physical installation, which stays **NOT RELEASED**. Physical and novice gates (the unaided-reader trial, both FnLock states, the expendable-media trial, the damaged-battery refusal) stay open in the gate table. No document check closes them.

## Budget

No dispatches. Run the tests locally and with the pinned local gitleaks over the full history before any push.

Make **at most one push**, at the end, and open a draft PR then: each push runs the privacy check, about 3–6 org minutes. Before pushing, check that the org still has at least 150 free minutes (read-only billing). If not, keep the work local and report.

## Acceptance

- The rewritten INSTALL and EMERGENCY, the status table, and the separate procedures.
- The new route and card tests, and the existing equality tests, all passing locally.
- `reviews/15-owner-path/REPORT.md`, with:
  - findings 1, 4 and 8–11 mapped to the changes
  - what each test proves and doesn't prove
  - the open physical gates
  - word counts before and after
- A draft PR. Don't merge.

**If unsure:** keep every check, and prefer an explicit STOP destination over a shortcut.

**Model:** gpt-6.1-sol, xhigh (a fresh Codex session).
