# 22: Update the laptop to a new AresOS release

Empire board brief 263. Owner-tools and install-guide package.

**Builder:** a Claude agent (Opus 5.5), at the owner's request of 2026-11-09 to use Claude agents. **Review:** Codex gpt-6-astra (high), a fresh context. These tools run as root on the real laptop, so review rounds continue until SAFE.

## Why

AresOS is installed and running (install steps 4–7 passed, 2026-11-08/09; see `STATE.md`). The owner tools (`os/owner-tools`, run as `sudo /var/lib/ares/at …` from the recovery console) can only make the **first** switch, from corrected Bazzite stock to the one pinned release:

- `verify` and `switch` call `before_switch`, which requires the stock state;
- the tools pin exactly one release (`self.release`).

Nothing moves a running AresOS to a newer signed release. Package 21 (image: the everyday account like Windows, Chrome, daily fixes) runs in parallel and will be the first release that needs this route. Every later release needs it too.

## Build

### A. An update command (`at update`, or a better name you justify)

1. **Run from:** the recovery console (tty3 as `ares-recovery` → `sudo`), like the other commands, on a running AresOS that `at check` accepts.
2. **Trust:**
   - The new release's reference (digest) and signature identity reach the laptop only through the **existing trust path**: a reviewed tools bundle whose `SHA256SUMS` fingerprint is pinned in the public guide and checked by the bootstrap. Alternatively, use an equally strong path that you justify in the report.
   - The owner never types a digest by hand.
   - The tools keep the record of the currently running release, so they know both the running release and the target.
3. **Verify** the target exactly as `verify` does: cosign, the signature identity, the digest, the registry login in `/etc/ostree/auth.json`. An expired or missing token is a clear refusal that points to `at login`. It changes nothing.
4. **Stage** the target while keeping:
   - the **current AresOS deployment as rollback**;
   - the **pinned corrected stock** deployment, untouched and still pinned.
   No other deployment may be lost or created. Refuse if a staged deployment or a queued rollback already exists, or if updaters, layout trials or other tool runs are active (reuse `idle`).
5. **Rules that change:** reuse `title` and `reboot`. Windows stays the firmware default; the owner uses F12 → Linux. Make `qualified_state` and the other checks accept the update shape: three deployments (new staged, old booted, stock pinned), then after the reboot new booted, old rollback, stock pinned. Keep them refusing everything else.
6. **After the reboot:** `at check` confirms the new release is booted and the shape is right. Document how to return to the previous AresOS if the new one misbehaves (bootc/ostree rollback to the previous deployment, with the same title discipline), and make that a tool command if it isn't trivially covered by `rollback`.
7. **Daily account rule changes with package 21:**
   - From that release on, `ares` **is** in wheel ("Like Windows", owner decision 2026-11-09).
   - `check` today requires `wheel not in id -nG ares` for the booted release. Make it expect what each release's own record declares: not wheel for the current release, wheel for 21's.
   - Never accept "either" for one release.
8. **Tools updating themselves:** a new tools bundle replaces `/var/lib/ares/at` through the same bootstrap, whose fingerprint check stays. Make sure the update route works when the installed tools are older than the bundle on the stick, and refuses the reverse (a downgrade).

### B. The guide

1. **Step 8:** add "Update AresOS to a new release" to step 8 (`docs/INSTALL.md`). Use phone-readable boxes in the existing style: Windows side first (Copy-AresOwnerTools onto the tools stick, fingerprint check), then AresOS (bootstrap, `at update`, `at title`, `at reboot`, F12 → Linux, `at check`), with PASS/STOP for each and explicit returns. Keep `docs/EMERGENCY.md` consistent: a failed or bad update returns to the previous AresOS or to Windows, never to a guessed GRUB title.
2. **Admin password:** after the first update to a release where `ares` is in wheel, the owner sets `ares`'s password once from the recovery console (`sudo passwd ares`). He types it; it is never recorded. Use the every-install alphabet rule (lowercase a–x and top-row digits, so it types the same in German, US International and US). He keeps it private.
3. **INSTALL-STATUS:**
   - Record install steps 4–7 as they happened, from `STATE.md`, with no private values.
   - Step 7's open items: brightness (no backlight device, board #139) and the power-button gate (a short press never reaches logind, board #140). Both stay OPEN.
   - Keep every other gate accurate. Release nothing.

### C. Verification

- **Unit tests** in `os/tests` for every new rule:
  - the update shape is accepted;
  - wrong shapes, a downgrade, an unsigned or wrong-identity target, an existing staged deployment, a queued rollback, an active updater and a stale title are all refused;
  - the per-release wheel rule holds;
  - tools self-update and downgrade refusal work.
- Extend `test_owner_path` (or the right owner-path test) for the new guide route: links, returns, PASS/STOP.
- **Bound sources:** files the package 16 walk binds (the install pages, many owner-tools files) need exact new hashes in `os/manifest/ci/16/pending-rebind.json`, generated with `checkout_sources.records` (see `reviews/15f-lenovo-firmware-entry/REPORT.md`). Never rebind the walk tables themselves. `test_checkout_sources`, `test_owner_equality` and `test_owner_step_limits` must pass.
- **Fingerprint:** if the tools bundle changes, regenerate it (`python os/owner-tools/bundle.py --refresh`) and update its pinned fingerprint in `docs/INSTALL.md` (copy check and bootstrap line 8) and `os/owner-tools/commands.json`, exactly as PR #22 (15f) did.
- **WSL suites (Linux tests):**
  - Clone your **pushed** branch into `/tmp` inside WSL and run `python3 -m unittest discover -s os/tests`, plain and with `-B`.
  - Write any script file with LF endings.
  - From Git Bash: `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu --exec bash /mnt/c/...`.
  - Known WSL-only failures, also on main: `test_greeter` (3 errors), `test_inherited_homebrew` (1 failure + 5 errors), `test_sysusers` (1 error).
  - Memory is tight (16 GB, shared with the owner): run at most **one** full-suite run at a time. Check first that no other `unittest discover -s os/tests` runs inside WSL (package 21 may be testing in parallel).
- **No real update:** no new release exists yet, so test with fixtures. The first real update is rehearsed and run in the release package after 21 and 22 merge, with the owner's OK.

## Out of scope

- Image content: package 21 owns it (`os/config`, `os/build.sh`, the package lock, Chrome).
- The release pin (`os/manifest/release.json`, the digest in INSTALL.md) and any publishing: the release package, with the owner's OK.
- Brightness and power-button fixes (21b), and Minecraft.

## Rules

- `AGENTS.md` applies. You may push `pkg/22-update-route` and open a PR. Never merge, never push to `main`. Never `--no-verify`: the privacy pre-push hook must pass.
- The repo is public: no personal data, serials, GUIDs, emails or tokens.
- Never run the tools against the real laptop. Never run anything as admin. Don't touch disks or boot settings. Don't touch other worktrees.
- Commits end with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Write `reviews/22-update-route/REPORT.md` in the AGENTS.md format, with JUDGMENT-CALLs marked.
