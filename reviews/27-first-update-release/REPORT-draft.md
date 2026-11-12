# 27 REPORT: The first update release (packages 21, 22 and 24)

Built by a Claude agent (Opus 5.5). Brief: `briefs/27-first-update-release.md` (empire brief 266).

**Outcome.** Release 27 is published privately and keyless-signed:
`ghcr.io/ares-empire/aresos@sha256:5fad242fceac7244563913eed96cd72dfcd300fec5e458cdb2ba81bce00d944c`
([run 42842793096](https://github.com/Ares-Empire/AresOS/actions/runs/42842793096), source `b216f28f`).
The image diff against release 13 explained all 915 changed paths. REHEARSAL-RESULT

Tools manifest fingerprint: `167f587ccd72f3d13226bf9d60f684cde56c1cb7ee674da0a0b1008b2013db94`.

## Done

### A. The release image (`release_27`, job `release-27` in `os-image.yml`)

- **Build:** main's image through package 21's reviewed check build (`os/ci/check-build.sh build`: `podman build os/Containerfile`, the in-image checks, the CI-only VM layer and its one VM pass), then the release-isolation check of release 13's job (no CI service, both passwords locked). Same pinned base `ed93d215…`, same locks. No pin had vanished (all locked RPMs and the Chrome RPM answered on their pinned URLs on 2026-11-10), so no pin was renewed.
- **Image diff** (`os/ci/release_diff.py`, run privileged through `build_tools.py`). Release 13 is verified with its cosign identity and pulled with the job token. Then base, release 13 and the new image are mounted and compared:
  - **packages:** added NEVRAs must equal the lock change since release 13's source (`775be05b`) plus the Chrome pin. Every removed NEVRA must be replaced by a locked one of the same name and arch, and every changed name has a reviewed reason (package 21; its JUDGMENT-CALL 4 for util-linux; its JUDGMENT-CALL 10 for xdg-desktop-portal-wlr).
  - **files:** the complete inventories (mode, owner, type, xattrs, hash, link target) of both images. Every changed path must match one rule:
    - `config`: bytes equal the changed `os/config` file, mode from build.sh. It never explains a mode or owner change of an existing directory.
    - `policy`.
    - `manifest`: lock, Chrome pin, package list, updater audit.
    - `build`: each package 21 build.sh step is checked on its own. Polkit defaults are recomputed from the base bytes with build.sh's own edit. Chrome under `/usr/lib/opt` is checked against Chrome's RPM file list, and the Chrome links against their exact targets. `/etc/default/google-chrome` must have exact bytes. The empty `/var/opt` and `cron.daily` are removed. The `aresos-subids` enable link is checked. `ares` is added to wheel and nothing else changes in group/gshadow. Shadow changes only in creation dates. There is one subid range. The Flatpak and brew-completion base files are restored, and the three Flatpak helper units are unmasked.
    - `package`: owned by a changed RPM, or a Chrome install-script icon/menu file.
    - exact rules for twelve paths found by release run 2. Each covers one path with one exact before/after; a near miss stays unexplained.
    - `generated`: rpm database, dnf5 history/state/log, ld cache, desktop and icon caches, SELinux store, `/run` leftovers. Listed path by path.
  - **units:** every changed path under a `systemd/` directory is listed with its rule, and none may be only `generated`.
  - **image metadata:** OCI runtime configuration equal, labels changed only in the revision, base ancestry of both images.

  Anything unexplained writes `status: stopped` with the full list and stops the job before publishing.
- **A fix the diff found:** release run 2 stopped because `/etc/sudoers.d` had become mode 0755 (package 21 writes `aresos-everyday` there, and the directory's mode followed the build's umask). `os/build.sh` now restores `root:root 0750` after writing the file, `os/ci/image-checks.sh` checks it in the image, and `test_everyday_account` covers it. In the published image's inventories (run 5), no directory present in both images changed mode or owner.
- **Publish** (`os/ci/publish.sh`): only from `pkg/13-keyboard-layout` or `pkg/27-first-update-release` (a `case`, not "any branch"). Tag `27-<sha>`, private, keyless-signed by this repo's workflow at this branch's ref and verified with that identity. The guard allows the branch's release dispatches (cap 5, see the budget) and **one publish**.
- **Job-token read:** CI read the private org package with `GITHUB_TOKEN` (`job_token_read: passed`, `owner_token_used: false`). `GHCR_READ_TOKEN` stays until the owner removes it.
- **Mirror patience** (release job only): `os/ci/install-tools.sh` takes `ARESOS_APT_RETRIES` (5) and `ARESOS_APT_TIMEOUT` (60 s per request) from the job, and the job's tool step may take 40 minutes. Release runs 3 and 4 failed on the Ubuntu snapshot mirror (HTTP 500, then 504).

### B. Records (commit `933f2d35`, written by `reviews/27-first-update-release/records.py`)

- `os/manifest/releases/27.json` and `os/manifest/release.json`: digest, tag, source, base, signature identity, run, image diff summary, job-token read, `daily_wheel: true` and the source trees as `{tree, path}` rows.
- `os/owner-tools/history.json`: release 27 appended with `daily_wheel: true`.
- Payload regenerated (`bundle.py --refresh`). Fingerprint `167f587c…` pinned in both copy checks and both bootstrap blocks of `docs/INSTALL.md`, in `commands.json` and in INSTALL-STATUS. Step 6's exact release line names release 27.
- INSTALL-STATUS: labels R27 (current) and R13 (previous, on the laptop). The update-route row carries the announcement: `daily_wheel: true`, so the one-time password box applies.
- `verify_release.py` binds release 27 by those Git trees (JUDGMENT-CALL 7) and checks the row shape.

### C. The update rehearsal (`rehearsal=update`, `os/ci/owner_vm.py`)

- **Laptop state:** corrected Bazzite stock, paused and pinned, then switched to release 13 by the release-13-era tools (15f tools `3ef85c4a…` from `17fe261c`), as on 2026-11-08/09.
- **Step 8 by typing:**
  - the new bundle is copied with `Copy-AresOwnerTools` and its fingerprint check, then installed by the guide's bootstrap (the tools update themselves);
  - `at update`, `at title`, `at reboot`, the guide's boot-menu choice, then `at check`;
  - `sudo passwd ares` in the root console;
  - package 21's rules on the booted release:
    - wheel; sudo asks every time and keeps no ticket (`sudo -l -U ares`, `sudo -n true` refused, then a fresh tty4 login as `ares` with `sudo -v`);
    - no passwordless polkit rule: package 21's `guest.sh` checks its sample. Then polkitd answers **every installed action** for his active desktop session (`pkcheck`), and every action he may take without his password must be on package 21's reviewed list (`os/ci/polkit-review.json`). This also covers `/etc` kept from release 13;
    - Chrome starts (headless, as `ares`, renders a page);
    - the PATH his AresOS terminal really exports (typed in foot), the hub terminal's argv, the session's system PATH;
    - `aresos-shell` lists its apps;
  - `at previous`, `at reboot`, `at check`, then `at update` refused (JUDGMENT-CALL 2).
- **Audits** (package 11's) at every stage: the stand-in Windows disk and its boot entry, stock deployment untouched and pinned, and the deployment shape.
- **Hidden input:** `owner_hidden.py` has a `passwd` reader; `owner_login.py` logs in the user it is given (`ares` on tty4 for the sudo proof).
- **Bindings:** the run records its own bound sources (`27-bound-sources.json`); `reviews/27-first-update-release/rebind.py record` writes them to `os/manifest/ci/27/source-bindings.json` and empties `pending-rebind.json`. `checkout_sources.py` prefers package 27's tables when they exist.
- **Host walk** (`os/manifest/ci/27/host-walk.json`, `walk-host.py`): both local walks (qualification and update route, 249 sources) on the rehearsal head; `owner_vm.py` refuses a stale walk.

### D. Tests

`test_release27` (new): package diff, accounts, polkit transform against build.sh, classifier (each rule, each exact rule with its near miss, also under umask 077), guard ledger, apt patience, publish branch, the release-27 verifier, the dispatch matrix. Updated: `test_owner_walk` (update route), `test_owner_equality`, `test_checkout_sources`, `test_owner_step_limits`, `test_owner_path`, `test_owner_update`, `test_owner_tools`, `test_everyday_account`, the retained-machine tests (pinned to release 13) and the workflow pins.

**The update job's gates** (`UpdateJobGatesTest`, after rehearsal run 1 stopped at `owner_capabilities.py`):
- It reads every step of the rehearsal job that runs for an update dispatch on this branch, with the environment that step really gets (workflow, job and step env, GitHub's variables, `env -u`), the shell branches that run and each script's own arguments.
- `GateScan` follows the code each script surely runs from its entry point, into the os/ci modules it imports. It evaluates every `assert` and `observations.check` that depends only on that environment and those arguments. Code under unknown branches, loops and handlers is skipped.
- On `87990bc1` it fails at exactly `owner_capabilities.py:147` (run 1's stop) and `owner_devices.py:359`, which would have been the next stop. Both now allow `update`; `owner_media.require_runner()`, which each calls first, limits it to package 27's branch.
- It now evaluates 17 gates and all of them pass.

**The VM step's package and mode decisions** (after run 2 stopped at the installer):
- `installer_webui.py` names the owner VM harness packages once (`OWNER_VM_PACKAGES = ('14', '16', '27')`, `KEYBOARD_PACKAGES`) for its six branches.
- `OwnerHarnessPackagesTest` requires every `REHEARSAL_PACKAGE` set in `os/ci` that names 14 or 16 to name 27. It also requires the installer's `start()` and `readback()` to drive the guest for 27 exactly as for 14.
- `VmStepDecisionsTest` reads every module the VM step imports (30). It finds each comparison, prefix test or lookup on `REHEARSAL_PACKAGE`, `REHEARSAL_MODE`, `GITHUB_REF_NAME` or the mode argument (40 decisions) and requires each whole condition to decide alike for package 27's update rehearsal and package 14's owner-tools qualification. The exceptions are seven reviewed decisions, each with its reason.
- Shell scripts, the overlay and guest templates read none of these names.
- For the update rehearsal only, the rehearsal job's tool install has the release job's mirror patience (JUDGMENT-CALL 10).

A test-only fix: `test_owner_entry`, `test_owner_diagnostics` and `test_owner_update` called `owner.main()` in-process, which sets umask 077 for the rest of the test process. Under discover's order that made one near miss in the exact-rule test a no-op, so the test failed once and passed on rerun. Replaying discover's order showed `test_owner_entry` as the only module that changed process state (umask 022 to 077). The calls now restore the umask (`common.kept_umask`), and the test sets every mode it relies on. The replay at `53dc5fec` then passed (74 modules before `test_release27`, no state change).

## Verified

VERIFIED-SECTION

## Not verified

- The real laptop: step 8 is the owner's own step, guided. The VM shows the route, not his hardware (NVIDIA, backlight, power button stay package 21b's).
- Chrome's start is proved by its process and window in the VM, not by browsing.
- His own passphrase: the VM types a generated one through the same hidden prompts.

## JUDGMENT-CALL

1. **The pins went in before the rehearsal, not after it** (brief: release.json and the guide's digest only after). Package 22's tools carry `release.json` inside the fingerprinted bundle and refuse a bundle whose newest history record is not `release.json` (`lineage()`); the rehearsal walk types the guide's bootstrap, whose line 8 is the fingerprint. So the bundle the rehearsal installs, and the guide it types, must already hold release 27. I pinned `release.json`, `history.json`, the payload, the fingerprint in every page and step 6's digest in the commit the rehearsal ran on, so the rehearsed bytes are exactly the bytes that get merged. What waited for the pass: the INSTALL-STATUS gate (PENDING → PASSED with the run links), the rebinding, and the report. Nothing reaches the laptop before the merge either way. Alternative rejected: rehearse a separately built bundle and pin a different fingerprint afterwards (the pinned bytes would not be the rehearsed ones). Changing it later: none needed; a later release can follow the same order.
2. **No "forward again" after `at previous`.** Package 22's tools refuse it: `previous` only returns from an update, and `update` stops with "Target release is already deployed; get help" (reviewed, owner-accepted design, its JUDGMENT-CALL 3 and report line "refuses the reverse"). The rehearsal walks previous and its confirmation, then types `at update` once and proves it refuses with nothing changed; the walk ends on release 13 with release 27 beside it. Rejected: adding a forward route to the reviewed tools in a release package (new mutation path, needs its own review; it belongs in 22c), or faking the end state by restoring a disk snapshot. Cost: if the owner ever runs `at previous`, he stays on release 13 until the next release (or 22c). The laptop does not run previous on the normal route.
3. **The image diff for a full rebuild classifies rather than equates.** Release 13 was a two-file overlay; release 27 rebuilds everything, so the diff cannot require equality. Each changed path must match a rule, and every rule except `generated` checks content (see Done). `generated` covers databases the package transaction rewrites in every build (rpm database, dnf5 history and log, ld cache, desktop and icon caches, SELinux store, `/run` leftovers); their content is not compared, every such path is listed in the result, and no systemd unit may be explained by it. Rejected: comparing only package lists (misses build.sh effects) or requiring byte equality for unchanged packages' files only (would not catch build.sh effects on base files). Changing it later: one rule table in `release_diff.py`.
4. **The admin password and his sudo:** `sudo passwd ares` is typed in the root console exactly as the guide says, with both hidden values proved (a new reader kind `passwd` in `owner_hidden.py`, the same reader required at "Retype new password:"). His password is then proved by a **fresh login as `ares` on tty4**, `sudo -v` there, and `sudo -n true` refused, instead of "in foot": the hidden-input proofs observe consoles only. The login observer now takes the username (`ares-recovery` stays the default).
5. **No separate probe for package 27.** Package 14's owner-tools qualification needs a passing probe on the same commit; with three rehearsal runs a failed qualification would leave no room for a new probe plus a qualification. The update rehearsal instead proves its own native step (the full unit suite, the native device and counter checks, the release verifier) in the same run before any VM, through the guard's existing current-run native check.
6. **Package 27 stays outside the organization billing gate.** The repo is public and uses standard runners (free). The local billing read showed every Actions SKU with `netAmount` 0, but now includes a macOS SKU from another org repo and a 1e-8 storage rounding value, which package 14's reviewed SKU list stops on. I did not widen that reviewed list; the CI guard still enforces this package's dispatch caps (release dispatches as the integrator raised them, one checks-only, three update rehearsals, one publish).
7. **`verify_release.py` binds release 27 by its source trees**, not by commit ancestry: `releases/27.json` records the Git tree of each image source path at the release commit as `{tree, path}` rows (object ID first: the privacy check read a path key followed by a tree ID as a secret), and the verifier requires the same trees at HEAD. A squash merge keeps the trees, so later rehearsals on main still verify release 27 without a new squash binding (release 13 needed one).
8. **Release-13-era tests pin release 13.** Tests that replay retained package 13 machines (switch, finalize, retained parsers, walk states, the 15e login evidence) now read `os/manifest/releases/13.json`, and two use a bundle of the current tools whose newest release is 13 (`release13_bundle`). Their assertions are unchanged.
9. **The release job runs one VM pass, not two.** Release run 1 (42807087845) failed in a second fresh VM pass: after `/dev/nbd0` was reconnected, `offline_journal.py` could not read the filesystem types. Package 21's reviewed check build runs one pass, and the brief asks for that build, so the release job keeps its single pass (`os/ci/check-build.sh build`), followed by release 13's isolation check. Rejected: re-probing the device between passes (a change to package 11's VM tooling inside a release package). Cost of changing later: one more pass in the job, after the device handling is fixed (PLAN-GAP).
10. **The release job waits longer for the Ubuntu snapshot mirror.** Release runs 3 and 4 failed while installing the pinned host tools (HTTP 500, then 504 from the snapshot mirror). The release job alone sets `ARESOS_APT_RETRIES=5` and `ARESOS_APT_TIMEOUT=60` (apt `Acquire::Retries` and an http/https timeout per request), and its tool step may take 40 minutes instead of 20. Other jobs keep the old defaults (3 retries, no timeout). The pinned snapshot, package versions and hashes are unchanged. Cost of reversing: remove two env lines and the step timeout.

11. **`at update` unmasks the two staging finalizers (reverses a lockdown choice from the first image; owner board #175).** Every AresOS image masks `ostree-finalize-staged.service` and `bootc-finalize-staged.service` (`os/policy/masked-system-units.txt`, since #3). bootc cannot stage a release while they are masked, so `at update` could never work from a running AresOS (rehearsal run 42940741765; the earlier switch worked only from stock, where both are static).
    - Chosen: `os/release/update.sh` (in the tools bundle, so it fixes R13 to R27 on the laptop) removes exactly those two `/dev/null` links right before `bootc switch`, reloads systemd and requires both static. Before that it requires each to be exactly the image's mask, or already unmasked by an earlier update, and every other system and user updater the image masks to be masked; anything else stops with nothing changed. If anything fails before staging, both masks are restored and the tools say "do not reboot".
    - A failure, a timeout, Ctrl+C, a closed window or a kill is covered too (reviews 1 to 3). The update step runs in its own session, and one stop routine handles each of those ends. Those signals only note themselves until it ends, and an error in one of its parts never skips the next. It stops every process of the step and tries to prove none is left. Only then does it remove a staged deployment, and only one that is exactly this update's. In every case it tries to mask the two again and checks that they are masked. It always STOPs and says whether every check passed. Nothing changes at the next start only when all of them passed; otherwise it says what is left and not to reboot. Before, a timeout SIGKILLed only the shell, so its restore never ran and staging could go on. This fulfils what the owner accepted on board #175; it is not a new call.
    - The removal carries into R27's `/etc` through ostree's merge, so the next update finds them unmasked. R13's own `/etc` keeps the removal too. Both units fetch and apply nothing by themselves: ostree starts the first only to finalize a deployment that was already staged, and the second is bootc's composefs counterpart. All automatic updaters stay masked.
    - Rejected: re-masking after staging (the finalizer must run at shutdown to finish the update); a non-staged deploy (`ostree container image deploy`; changes what `at check` and the title expect); a new image that stops masking them (out of scope for this release; PLAN-GAP).
    - The tools on AresOS never audited unit masks (`at check`, `at title` and the records read none; `paused_state` runs on stock only), so they accept this state. The update route itself now stops on any other unmasked updater. Package 21's `guest.sh` (the rehearsal's policy check) accepts exactly these two only when unmasked by that route.
    - Cost of changing later: the next image can drop the two masks (then `update.sh`'s check finds them static) and add them to the reviewed updater allowlist.

## PLAN-GAP

- **The brief's order (pin after the rehearsal) and package 22's tools disagree.** The bundle carries `release.json` and its history must end with it, and the walk types the guide's fingerprint, so the pins sit in the rehearsed commit (JUDGMENT-CALL 1).
- **"Forward again" after `at previous` has no route** in package 22's tools (JUDGMENT-CALL 2). If wanted, 22c should add it (for example `at update` queueing an already deployed newer release with `bootc rollback`), with its own rehearsal.
- **Package 23 (PR #36) in the next release:** its mod must be built before the image (`os/ci/build-mod.sh` before `podman build`). The release job here runs `os/ci/check-build.sh build` only; the next release package must add that step (and its evidence) to the release job and to the image diff's `config`/`build` rules.
- **The next release's diff:** `release_diff.py` compares with release 13 (`PREVIOUS`, `PREVIOUS_SOURCE`, the package reason table). The next release must compare with release 27 instead and list its own package changes.
- **`offline_journal.py` and a reused `/dev/nbd0`:** a second `vm.py` pass in the same job failed to read filesystem types after reconnecting the device (run 42807087845). One pass per job works; a job that needs two passes should settle or re-probe the device first.
- **The update route's "announcement"** is the maintainer's message. INSTALL-STATUS's update row now carries it for release 27 (`ares` is an administrator there, so the one-time password box applies); the guide itself is unchanged.
- **Package 14's owner-tools qualification would stop at `guest.sh` on release 27.** Package 21's `guest.sh` requires ares's desktop session to be active (`loginctl ... Active = yes`). `common_boot(..., ares=True)` runs it right after `public_typing`, which leaves the root console (tty3) in front, so the next qualification on release 27 would stop there. The update rehearsal is not affected: `terminal_path` leaves his desktop in front before `guest.sh` and the polkit sweep. Fix before the next qualification: bring the desktop to the front in `common_boot` before `guest.sh`, as `terminal_path` does. I did not change it here because the rehearsal's bindings cover `owner_vm.py`, and the qualification is not rehearsed in this package.
- **Organization billing check:** package 14's reviewed SKU list stops on the org's new macOS SKU (another repo) and on a 1e-8 storage rounding value; any package that still uses the local billing read needs that list reviewed.
- **Old evidence that names release 13 as current** (package 15e's login policy, the retained 13f machines) stays release 13's; tests now read `os/manifest/releases/13.json` for it.

- **Stop masking the two staging finalizers in the image (next release).** Remove `ostree-finalize-staged.service` and `bootc-finalize-staged.service` from `os/policy/masked-system-units.txt`, review them in `updater-allowlist.json`, and keep `image-checks.sh` and `guest.sh` in step. Fresh installs then match updated laptops (JUDGMENT-CALL 11).
- **Package 22 had no VM run of `at update` from a running AresOS**; the masked finalizer showed only in this rehearsal.

## Open questions

- None beyond the JUDGMENT-CALLs for the owner (1 and 2 above).

## Budget

The repo is public, so every run used standard GitHub-hosted runners at no cost. Nothing needed a paid runner or other spending. GHCR received one private publish; nothing was deleted.

The brief planned one build-and-publish, one checks-only run and three rehearsals. Each release dispatch after the first was approved by the integrator, who raised the cap to 3, then 4, then 5.

| # | Run | Kind | Head | Result |
|---|---|---|---|---|
| 1 | [42807087845](https://github.com/Ares-Empire/AresOS/actions/runs/42807087845) | release | `1b17080e` | failed: second VM pass could not read filesystem types on a reused `/dev/nbd0` (JUDGMENT-CALL 9) |
| 2 | [42817411051](https://github.com/Ares-Empire/AresOS/actions/runs/42817411051) | release | `8fc6e350` | stopped by the image diff before publish: `/etc/sudoers.d` 0755 (fixed in build.sh) and 12 paths without an exact rule |
| 3 | [42831158090](https://github.com/Ares-Empire/AresOS/actions/runs/42831158090) | release | `e2c14696` | failed: Ubuntu snapshot mirror HTTP 500 while installing host tools |
| 4 | [42835704653](https://github.com/Ares-Empire/AresOS/actions/runs/42835704653) | release | `31da87f9` | failed: snapshot mirror HTTP 504 (JUDGMENT-CALL 10) |
| 5 | [42842793096](https://github.com/Ares-Empire/AresOS/actions/runs/42842793096) | release | `b216f28f` | **passed and published** release 27 (the one publish) |
| 6 | [42924871252](https://github.com/Ares-Empire/AresOS/actions/runs/42924871252) | update rehearsal 1 | `87990bc1` | failed after 11 minutes, before any download or VM: `owner_capabilities.py` still allowed only probe and owner-tools (fixed, with `UpdateJobGatesTest`) |
| 7 | [42933781975](https://github.com/Ares-Empire/AresOS/actions/runs/42933781975) | update rehearsal 2 | `35e58911` | every pre-VM step passed, then it failed 3 minutes into the VM: `installer_webui.py` opened the WebUI transport only for packages 14 and 16 (fixed, with `OwnerHarnessPackagesTest` and `VmStepDecisionsTest`) |
| 8 | [42940741765](https://github.com/Ares-Empire/AresOS/actions/runs/42940741765) | update rehearsal 3 | `fb06ccde` | reached step 8 (install, stock, switch to R13 with the laptop tools, tools update to v2 all passed; every disk audit unchanged), then `at update` failed: the image masks `ostree-finalize-staged.service`, which bootc needs to stage (fixed, JUDGMENT-CALL 11) |
| 9 | [42973044866](https://github.com/Ares-Empire/AresOS/actions/runs/42973044866) | update rehearsal (guard stop) | `194372ec` | stopped in the guard's first step after about 1 minute: the update cap was still 3 (raised to 5 in fd7d9895) |
| 10 | [42974982988](https://github.com/Ares-Empire/AresOS/actions/runs/42974982988) | update rehearsal 4 | `e3a67619` | **`at update` staged R27 from R13, then title and reboot; R27 booted**, with every disk audit unchanged. It then failed at the first R27 console login: the harness login observer (`os/ci/owner_login.py:148`) accepts only util-linux 2.41.5, and R27 has 2.41.6 (package 21 JUDGMENT-CALL 4). Next: compare v2.41.5..v2.41.6 for login.c and agetty.c, let the observer accept both versions, raise the cap to 6, then run 5 |
REHEARSAL-ROWS
| | | | | |
| | **Total** | | | 5 release dispatches (1 publish), REHEARSAL-TOTAL, CHECKS-TOTAL |
