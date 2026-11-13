# 27: The first update release (packages 21, 22 and 24)

Empire board brief 266. Release package. Starts once packages 21 and 22 are merged; 24 already is.

**Builder:** a Claude agent (Opus 5.5). If the VM rehearsal resists normal attempts, the integrator moves it to Fable 5.2. **Review:** Codex gpt-6-astra (high), a fresh context; this release reaches the owner's real laptop.

## Why

The laptop runs release 13 (`ghcr.io/ares-empire/aresos@sha256:9b19b794…`, installed 2026-11-08/09). Packages 21 (the everyday account like Windows, Chrome, PATH and terminal fixes), 22 (`at update` and `at previous`) and 24 (apps open from the hub) are on main but reach the laptop only through a new signed release. This package builds that release, rehearses the owner's real update route on it in a VM, publishes it, and pins it. Then the owner runs `at update` on the laptop.

**Owner OK (2026-11-09: "Once its safe and done you can merge and publish"):** the release built from packages 21–24 may be published and pinned without asking again, once its rehearsal passes. Installing it on the laptop stays his own step. Anything outside that, such as a new base image, making something public or spending money, still needs his OK.

## Build

### A. The release image

1. **Build from main** on the same pinned base (`ed93d215…`) with the locked packages, through the reviewed build that package 21's CI used (`check_build`).
   - If a pin has vanished upstream since (package 21's PLAN-GAP: Chrome on `dl.google.com`, Fedora `updates`), renew only that pin, the way 21's JUDGMENT-CALLs 4 and 10 did, and record each one as a JUDGMENT-CALL.
   - A new base image is out of scope.
2. **Image diff** against release 13: packages, files and units, as `releases/13.json`'s `image_diff` did. Every difference must trace to package 21, 24 or a renewed pin. An unexplained difference stops the release.
3. **Publish** privately to `ghcr.io/ares-empire/aresos`, keyless-signed by this repo's workflow.
   - Today the publish job runs only for `pkg/13-keyboard-layout` (`release_13`). Give this package's branch the same reviewed shape. Don't loosen it into "any branch may publish".
   - Record the signature identity the tools will trust (the workflow at this branch's ref).
   - Delete nothing from GHCR, and keep the old release records.
   - Check whether CI can read the org package with the job token. Report it, and keep `GHCR_READ_TOKEN` until the owner removes it.
4. **Records:**
   - add `os/manifest/releases/27.json` with the digest, signature proof, run and image diff;
   - append the release to `os/owner-tools/history.json` with `daily_wheel: true` (package 22's PLAN-GAP);
   - regenerate the payload and the tools fingerprint (`python os/owner-tools/bundle.py --refresh`), and update every pin of it: `docs/INSTALL.md` (copy check and bootstrap line 8), `commands.json` and INSTALL-STATUS.

   **The order is publish, rehearse, then pin.** `os/manifest/release.json` and the guide's digest change only after the rehearsal below passes.

### B. Rehearsal: the owner's update, in a VM

Use the two-disk VM harness from packages 11, 14 and 16 (a stand-in Windows disk that is never written). Start from **the laptop's state**: corrected Bazzite stock, paused and pinned, then switched to release 13 by the release-13 tools, as on 2026-11-08/09. Then walk the guide's new route (package 22, step 8) by typing, exactly as the owner will:

1. Copy the new tools bundle onto the tools stick (`Copy-AresOwnerTools` and the fingerprint check, simulated as the package 16 walk did), then run the bootstrap on AresOS. The installed tools are older than the bundle, so this proves the tools update itself.
2. `at update`, `at title`, `at reboot`. In the boot menu, choose the new entry the way the guide says. Then `at check`. That is the new release booted, the old one as rollback, and stock pinned.
3. **The admin password:** run `sudo passwd ares` as `ares-recovery`. Then prove package 21's rules on the real boot:
   - `ares` is in wheel;
   - `sudo` asks every time and keeps no ticket;
   - no passwordless polkit rule remains;
   - Chrome starts;
   - the AresOS terminals and the hub's terminal have his PATH, and the session keeps the system PATH;
   - `aresos-shell` is present.
4. `at previous`: back to release 13. Then `at check`. Then forward again with the guide's route, so the walk ends on the new release, as the laptop will.
5. **Audits at every stage**, all of package 11's:
   - the stand-in Windows disk and its boot entry are byte-identical;
   - the stock deployment is untouched and still pinned;
   - no deployment is lost beyond what package 22's JUDGMENT-CALL 1 allows.
6. **Bindings:** the walk types `update` and `previous`, so remove them from `unwalked_commands`. It rebinds every file listed in `os/manifest/ci/16/pending-rebind.json`, which ends empty. Update `source-bindings.json` exactly as the walk records it.

After the rehearsal passes: pin the release in `release.json` and the guide (the step 8 route, the digest and the fingerprint), mark the update-route gate in INSTALL-STATUS with the run links, and keep `docs/EMERGENCY.md` consistent.

### C. Verification and budget

- Unit tests for every changed rule. Run `test_checkout_sources`, `test_owner_equality`, `test_owner_step_limits` and `verify_release`.
- WSL suites on your pushed branch, plain and `-B`, one at a time. Check memory first: at least 5 GB free and no other suite running. Use `pkg27-` names for scripts and `/tmp` paths. If Claude Code stops a run for low memory, restart it once memory is free (owner, board #160).
- **Budget:** the repo is public, so standard GitHub runners cost nothing.
  - Plan at most one image build-and-publish, one checks-only suite and three rehearsal runs.
  - Report before dispatching more.
  - Stop if anything would need a paid runner or other spending.

## Out of scope

- Package 23 (Minecraft starts) and 21b (backlight, power button): the next release.
- 22c (rollback, keep-stock and layout trials after an update): before the second update.
- Running anything on the real laptop. The owner runs `at update` himself, guided.

## Rules

- `AGENTS.md` applies. You may push `pkg/27-first-update-release` and open a PR. Never merge, never push to `main`. Never `--no-verify`.
- The repo is public: no personal data, serials, GUIDs, emails or tokens. The image stays private.
- Never make anything public. Don't touch disks or boot settings on the laptop. Don't touch other worktrees.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Write `reviews/27-first-update-release/REPORT.md` in the AGENTS.md format, with JUDGMENT-CALLs marked. The acceptance evidence:
  - digest and signature proof;
  - the image diff;
  - the rehearsal transcripts and audits;
  - the emptied pending list;
  - the fingerprint;
  - the WSL results;
  - the budget table.
