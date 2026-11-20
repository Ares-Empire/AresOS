# 42: Release 28, progress

Builder of step 1: a Claude agent (Opus 5.5), started 2026-11-16 from `main` e33ffc46; phase 2 (the dry run's
differences) a fresh Claude agent (Opus 5.5) the same day; review 1's fixes a fresh Claude agent (Opus 5.5) the same
day (below). Nothing has been published, signed or pushed to GHCR. The owner's OK for publishing release 28 has not
been given, and the ledger now stops a publish dispatch until it is (B1).

## Step 2: Control's Part A rules (2026-11-18)

Built on `pkg/42-release-28` after the lead merged PR #58. No commit, push, dispatch, rebind, publish or VM run
was performed in this step. Nothing in `control/` or `os/owner-tools/` was changed.

### Done

- **Shipping scope checked first:** `bash os/build.sh control-tree os control .work/42-control-tree` exited 0 and
  printed `CONTROL_CHROME_BUILD <derived build ID>` and `CONTROL_INSTALLED 74 files`. Inspected its `control.json`
  and the image build's additional wheel/vendor fields. The 74 files include Mail, the Chrome **adapter** and its
  generated `chrome/build-id.json` and qualification file. No browser-side `/usr/share/aresos/chrome/`, Chrome
  polkit action, excluded-sites tmpfiles line or locked `gh` is installed. No Chrome build hash was copied into
  source, tests or this report; the install map recomputes the adapter's ID from the current `control/` tree.
- **N8:** `release_diff.IMAGE_SOURCES` includes the actual top-level `control/` fetched by the source stage. Its
  source-coverage test maps `/tmp/aresos/control` back to that tree and tests a changed `control/launch.py` too.
- **A.3:** exact Part A rules in `os/ci/release_diff.py`: the recomputed install map, root ownership, type, mode,
  empty xattrs, file bytes, managed Claude Code files, service enable link, both tmpfiles files, and the full
  vendor tree as recorded by `control.json`. The manifest must have exactly the build's fields, its source revision
  must be the build commit, and every wheel must match `control/requirements.lock`. Missing paths and extra rows
  stop the converse check, including unchanged/missing paths that never enter the diff. The existing independent
  wheel-to-vendor check in `check-image.sh` still supplies that part's real-image evidence.
- **Accounts and audit:** only the exact `aresos-tools` passwd/group/shadow/gshadow row and UID/GID 250 may be
  added, with the existing allowance for shadow creation dates. Other rows and metadata must match; neighbouring
  paths, extra rows, changed IDs and a duplicate 250 fail. Part A creates the account at **boot** (the image build
  runs sysusers with only the daily account's declaration), so its presence is required by the boot checker, not
  invented as a build-time requirement. The updater audit accepts exactly Control's enabled service row alongside
  package 50's row, with their actual installed units, and rejects changed or extra audit rows.
- **A.4/A.5:** `verify_release.py` recognises release 28's own job and signature, binds `control/` alongside every
  image source, and checks `control.source_revision`. `publish.sh` runs `release28_record.py` for release 28;
  the latter reads `evidence/image/manifest/control.json`, requires its source to equal the release/build source,
  and writes the top-level `control: {source_revision: ...}` and the source tree rows to `evidence/release.json`.
  This step prepares that job; no real `os/manifest/releases/28.json` is written before publication.
- **B / REVIEW-4 finding 3:** `CONTROL_RIDES = True`, `CHROME_RIDES = False`. The bound checker is sent to
  `/usr/bin/python3 -I -` on stdin, its real supported interface. Raw stdout, stderr and status are saved before
  validation; all five results, UID/GID 250, state owners/modes, foreign state ownership, and the fresh VM's daily
  folders' owners/types/modes are required. The login probe retains and traverses `After`, `Requires`, `Requisite`
  and `BindsTo` from greetd and systemd-user-sessions, rejecting a direct or transitive Control dependency. Missing
  optional ordering units may be leaves; missing login roots or failed queries stop. Control runs on both the first
  R28 boot and the final R28 boot after forward, with both results in the rehearsal result.
- **Host walk:** regenerated with `PYTHONDONTWRITEBYTECODE=1 python3 reviews/42-release-28/walk-host.py`.
  It printed `PASS package 42 host walk (release-28): 269 sources; no VM started`; the receipt explicitly records
  `control_rides: true` and adds the checker to its bound sources. The local model executes the submitted checker
  and probe against controlled account, filesystem and process interfaces. Wrong state/daily-folder metadata,
  ordering/required login dependencies and missing/failed login queries fail the route, including on final R28.
- **N2:** package 42's CI guard and every `publish.sh` invocation require a full `refs/heads/` ref, before budget
  reads or publish commands. Tests reject a same-named tag, a bare name and a missing ref. Earlier release tests'
  simulated GitHub environments now include their actual full branch ref.
- **Pending source accounting:** `test_checkout_sources` initially reported 8 tests with 1 failure: the existing
  pending hashes for `os/ci/rehearsal_guard.py`, `os/ci/verify_release.py` and `os/tests/test_owner_walk.py` were stale.
  Only those three existing rows were refreshed through `checkout_sources.records()`'s checkout replay, with a
  change note in `os/manifest/ci/16/pending-rebind.json`. No historical source-binding table was rewritten and
  `rebind.py` was not run. The files still await the real rehearsal.
- **gh pin:** #58 ships no gh lock or locked gh installation. No pin was renewed on this branch; no new
  `BRANCH_SOURCE_CHANGES` exception is needed. A future locked gh renewal must be made on main before its cut,
  or get a separately reviewed exception then.

### Verified

Every module below uses exactly
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'`, one at a time.

| Module | Tests | Result |
|---|---:|---|
| `test_release28.py` | 92 | `Ran 92 tests ... OK` (exit 0) |
| `test_release28_control.py` | 13 | `Ran 13 tests ... OK` (exit 0) |
| `test_release28_rehearsal.py` | 44 | `Ran 44 tests ... OK` (exit 0) |
| `test_owner_walk.py` | 34 | `Ran 34 tests ... OK` (exit 0) |
| `test_release27.py` | 41 | `Ran 41 tests ... OK` (exit 0) |
| `test_checkout_sources.py` | 8 | `Ran 8 tests ... OK` (exit 0) |
| `test_release_squash_binding.py` | 7 | `Ran 7 tests ... OK` (exit 0) |
| `test_rehearsal_budget.py` | 4 | `Ran 4 tests ... OK` (exit 0) |
| `test_rehearsal_auth.py` | 9 | `Ran 9 tests ... OK` (exit 0) |
| `test_control_image.py` | 15 | `Ran 15 tests ... OK` (exit 0) |
| `test_ci_api_permissions.py` | 4 | `Ran 4 tests ... OK` (exit 0) |
| `test_ci_step_environment.py` | 4 | `Ran 4 tests ... OK` (exit 0) |
| `test_keyboard_release.py` | 5 | `Ran 5 tests ... OK` (exit 0) |

`git diff --check` passed. All 269 host-receipt source hashes match the checkout, with `control_rides: true`.
The prohibited modules and Gradle were not run. None of `sudo`, `rpm-ostree`, `bootc`, `ostree`, a dispatch
or `rebind.py` was executed.

The required initial `test_release28` ran **92 tests, FAILED (failures=1)**: precisely ImageSourcesTest's missing
`control` entry (N8). During implementation, fixture corrections were needed: `test_release28` reported 17
failures, then 1, as the old miniature image lacked existing R27 parent directories and its expected audit output
omitted the new Control row. `test_release28_rehearsal` first reported 39 tests with 1 failure and 2 errors (the
full ref and the controlled checker's pathlib interface were missing); its corrected run passed 44 tests.
No production assertion was weakened to fix those fixtures.

### Changed files

| File:line | Change |
|---|---|
| `os/ci/release_diff.py:452` | Control source binding, exact Part A rules, accounts, vendor and audit |
| `os/ci/verify_release.py:44` | Release 28 job/signature and all source-tree identities, including Control |
| `os/ci/release28_record.py:12` | Image-derived Control provenance and source trees in the release record |
| `os/ci/publish.sh:7` | Full branch ref; release 28 record completion at line 65 |
| `os/ci/rehearsal_guard.py:517` | Package 42 CI requires a branch ref, including its publishing guard |
| `os/ci/release28_walk.py:73` | Part A enabled; bound stdin checker and login graph at line 498; both R28 boots checked |
| `os/tests/test_release28.py:92` | Actual Control install-map fixture, source coverage, full refs and smoke audit |
| `os/tests/test_release28_control.py:23` | Negative Part A rules, account rows, provenance/verifier and tag-ref tests |
| `os/tests/test_release28_rehearsal.py:434` | Enabled Control path, both boot checks and browser-side exclusion |
| `os/tests/test_owner_walk.py:561` | Execute real submitted Control probes with controlled interfaces and fault injections |
| `os/tests/test_release27.py:405` | Complete simulated GitHub branch refs |
| `reviews/42-release-28/walk-host.py:24` | Bind the supported release checker |
| `os/manifest/ci/42/host-walk.json:3` | Regenerated receipt, Control true, 269 sources |
| `os/manifest/ci/16/pending-rebind.json:32` | Three existing pending source hashes refreshed, with the reason |
| `reviews/42-release-28/PROGRESS.md:8` | This step's scope, results, limits and release-after list |

### Left, in order

1. Fresh Astra review of this step; the lead commits the reviewed changes (this sandbox cannot write git metadata).
2. The lead's pending-source/rebind work and the cut's source merge and mod-pin resolve if needed.
3. The remaining real cut dry run: Part A's complete wheel/vendor record, audit row, exact path metadata and any
   generated cache changes must all pass the image diff. Inspect `result.json`, including its `main`, `control`
   and rpm-verification evidence; explain any newly observed path before proceeding.
4. The owner's publish OK and the lead's publish/record step, then the hosted release-28 VM rehearsal. Both R28
   Control results, the login graph, the protected-disk audits and the actual release record must pass there.
5. Only after that rehearsal: the release/tool pins and guides. None was moved here.

### What the code doesn't show

The local walk is synthetic evidence. It does not prove the real first-boot sysusers allocation, pip's real
vendored bytes, systemd's real ordering graph, merged `/etc/claude-code` or a live Control process on the release
image. Those need the cut dry run and VM boots. Daily Downloads/Documents are freshly created 0700 in this VM;
Part A's tmpfiles `:0700` deliberately preserves an owner's existing folder mode. The actual Minecraft world and
Mail with the owner's account still need their separate live checks. No privileged command or owner window was
used here. No files over 500 MB remain in `.work/`.

### Left for the release after

- **18c-b's browser side**, including `/usr/share/aresos/chrome/` and its per-build diff rule.
- The browser-side polkit action, links/units and excluded-sites tmpfiles line; Part A's service link and tmpfiles
  files are covered now.
- Top-level **`chrome_build`** in the release record: Part A's `control.json` has no such field. Its internal
  adapter `chrome/build-id.json` is already covered by the exact Part A install-map rule.
- `control/chrome/record_build.py add` in the release job and its build-registration row.
- B.2's excluded-sites list and the update/previous/forward hash checks. The route keeps the future code gated by
  `CHROME_RIDES = False` and writes no browser-side list in this release.
- A locked gh installation and pin rule, if 18c-b actually supplies one; no such lock rides from #58.

**PLAN-GAP (resolved by this step's instructions):** the frozen brief couples step 2 and A.5/B.2 to 18c-b. The
lead's release scope explicitly carries only #58's Part A with 18e's fixes. The absent browser items above are
therefore deferred individually. There is no unresolved blocker or new product JUDGMENT-CALL in this step.

## Package 50's rules

Added after main's merge at `276eff4a` (2026-11-17): `release_diff.py` accepts only the new graphical-target
wants link to `/usr/lib/systemd/system/aresos-console-keymap.service`, root:root 0777 with no xattrs, and exactly
package 50's offline audit row. Both require the unit's exact source bytes and metadata and its merged origin,
`50 (#101)` (`ff51cac4`). Other audit rows still match, in sorted order, with only the existing reviewed drop-in
source additions allowed. A missing row stops even when the audit file is unchanged. Tests cover the unit's
existing `config_rule`, wrong link targets/paths/metadata, extra or changed audit rows, missing rows and origins.
The smoke fixture now includes the link, audit row, existing wants directory and console-check receipt.

Verified, one module at a time with `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p
'test_<name>.py'`: `test_release28` **92 OK**, `test_release27` **41 OK**, `test_checkout_sources` **8 OK**,
`test_console_keymap` **21 OK**; each printed `Ran <count> tests` and `OK`. `git diff --check` passed.
The first release-28 run reported 20 failures from the smoke fixture's absent old wants directory and the
build-check fixture's missing console receipt; both fixtures were corrected without weakening assertions.

Package 48 changed `mod/` (jar SHA-256 `9d53bb84a5b9e90b51ba1054384f859d39185637b1a3e64b75868ca6ed2ba179`):
the lead must renew the jar pin through **`check_build=resolve` before the cut's dry run**. S2 permits only the
jar's `sha256` to differ from main's image sources. No pin renewal, real image diff, VM run, dispatch, rebind,
owner-tools change or commit was performed here; those remain with the lead. No files over 500 MB remain in `.work/`.

## Reviews of steps 1 and 3 (Codex, 2026-11-17; the lead)

- **REVIEW-3** (gpt-6-astra high, step 1 cross-review at `8792c274`): CHANGES-NEEDED, five should-fix + one nit in
  `release_diff.py` (missing RPM files passed; generated-file globs too broad; alternatives per link; Prism's typed
  inventory; GVDB lookup metadata; the jar pin's git mode). **REVIEW-4** (gpt-6-astra high, step 3 at `841de8d1`):
  CHANGES-NEEDED, one blocking (the real-commit comparison could be skipped) + seven should-fix.
- Fixes round 1 (gpt-6.1-sol xhigh, two runs in parallel; Codex's sandbox could not commit, so the lead committed):
  `699fb9a6` (step 1, FIXES-3.md), `9d41a9e1` (step 3, FIXES-4.md; REVIEW-4's finding 3, Control's checker path, its
  metadata and login-ordering checks, moved to step 2). **REVIEW-5** (step 1 fix check): five fixed, two should-fix
  left in the alternatives. **REVIEW-6** (step 3 fix check): two blocking left (the instance layout; R27 without
  R28's link targets) + one should-fix (saved worlds).
- Fixes round 2 (gpt-6.1-sol xhigh): `6948f39f` (alternatives bound to `os/ci/release28-alternatives.json`, taken
  from the pinned scriptlet; every selected public link checked; FIXES-5.md), `23311f42` (the provisioner's own
  `expected_links()`; R27 compares link text only; synthetic saved worlds compared; FIXES-6.md).
- **REVIEW-7** (step 1) and **REVIEW-8** (step 3): **SAFE**, no new findings. Merged head `c39d48cc`: host walk 268
  sources; 25 pending files; locally OK: test_release28 (85), test_release28_rehearsal (44), test_owner_walk (34),
  test_ways_back_probe (57), test_tools_local_wiring (42), test_release27 (41), test_checkout_sources (8),
  test_rehearsal_budget, test_rehearsal_auth, test_owner_capabilities, test_release_squash_binding,
  test_owner_step_limits.
- Not yet proven: the new step 1 rules against a real image (the cut's dry run is the first). Finding 5's schema
  rebuild runs the image's own `glib-compile-schemas` in the release job; the dry run shows whether it is
  byte-identical there. Nothing of B has run in a VM (step 6).
- Package 45 (main `968727d2`, mod/ and docs only) keeps the jar's sha256 `8090554997fd…`, so the pin holds.

## Step 3, continued: the rehearsal mode `release-28` (2026-11-17)

Builder: a fresh Claude agent (Opus 5.5), from `b3d744a9`; nothing before it rebased or amended (the Codex Astra
review reads `8792c274`). No GitHub dispatch, no VM, no sudo, no `rpm-ostree`/`bootc`/`ostree` command was run.

### Lead's decisions, 2026-11-17

1. **PLAN-GAP 1 → option (a).** R28's tools bundle is version 4's code with **`tools_version` 5** and R28's
   reference, so a new fingerprint; line 1 of `OWNER-TOOLS.md` will say version 5; package 43's tools take the next
   number. Reason: every bundle carries its release's reference, and the tools install only a higher version, so
   each bundle gets the next number, as 22c (3) and 22d (4) did. The tools' code is not changed. Brief B.1's wording
   on the branch now says "version 4's code with `tools_version` 5 and R28's reference" (done, `acbe72d0`).
2. **PLAN-GAP 2.** The bump to 5 and `release.json` naming R28 happen in step 5's real payload commit, not in this
   step; the real `release.json` still moves only after the rehearsal (A.5). The walk's stand-in origin holds
   `634e1237`, then a **stand-in announced commit** with version 5 and `release.json` naming the R28 image under
   test; the walk records that commit's hash and its `os/owner-tools` and `os/manifest/release.json` tree and blob
   hashes; the real announced commit must be byte-identical in those paths, checkable from the walk's receipt
   (22d's pattern). The INSTALL-STATUS gate in `test_checkout_sources` stays as it is: **step 5 precondition:**
   22d's and 22c's rows move to ON THE LAPTOP after the owner's session (the lead does that), before step 5's
   payload commit, or `test_checkout_sources` refuses that commit.
3. **The start route:** the first builder's JUDGMENT-CALL is accepted. The VM reaches version 4 the way the laptop
   does: 27's route to R27 with version 2, then 22d's folder and routine lines at `634e1237` (`dcbc375f…`). The
   start assumes version 4; the lead confirms it after the owner's session.

### Done (step 3)

- **`os/ci/release28_walk.py`** (new): the walk (its docstring lists the stages).
  - `announced(record)`: the files of the announced commit, from release 28's record bytes and `634e1237` alone:
    `history.json` (both copies) with R28's row (`reference`, its signature identity
    `…@refs/heads/pkg/42-release-28`, `daily_wheel: true`) and `tools_version` 5; the payload's `release.json` and
    `os/manifest/release.json` equal to the record; `SHA256.json`/`SHA256SUMS` as `bundle.py --refresh` makes them;
    `commands.json` with version 4's own `bootstrap.py` (read from `634e1237`) for the new fingerprint;
    `docs/OWNER-TOOLS.md` lines 1 and 3 (`Owner tools version 5: <8>`, the full value). It refuses a record with
    another identity, without the daily wheel, not an org digest, not newline-ended, or one version 4 already knows.
  - `standin_origin(destination, record)`: a bare stand-in (git plumbing only: `ls-tree`/`mktree`/`hash-object`)
    whose `main` holds the stand-in for `634e1237` (its `os/owner-tools` tree `73fb5929`, its `release.json` and
    `OWNER-TOOLS.md` blobs, tag `version-4`), then the stand-in announced commit (only `announced()`'s files differ).
    It records `hashes[...]` of `os/owner-tools`, `os/manifest/release.json` and `docs/OWNER-TOOLS.md`.
  - `matches(commit, recorded)` lists the bound paths in which a real commit differs from the receipt;
    `real_commit(head, standin)`: when the checkout's history already names R28 (after step 5's payload commit), the
    walk STOPs unless its `os/owner-tools` tree and `release.json` blob equal the stand-in's; otherwise it records
    that the real commit is still to be cut.
  - `Walk(tools_local.Walk)`: 22d's dialog driver (step 6d's settle and screen checks, the one-shot launcher and its
    retry) over this origin; `compare()` checks, before any password, that line 1 of the stand-in's
    `OWNER-TOOLS.md` names the window label's 8 characters (the owner's look at his phone bookmark).
  - `rehearsal(...)`: 27's route with version 2 and R27 from fixed sources (`facts_27`: version 2's own bundle at
    `41b06513` names R27, and `os/manifest/releases/27.json` agrees; never `release.json`), then boot `release-27`:
    `passwd`, his sudo, 22d's lines at the `634e1237` stand-in (expect `Tools updated from version 2 to 4` and three
    PASS lines), B.1 at the announced stand-in (`Tools updated from version 4 to 5`, three PASS lines, no sudo
    ticket kept, the receipt names version 4 to 5, the folder, uid 1001, no terminal), B.2 if `CONTROL_RIDES`, then
    B.3 on tty3: `update` (`Signed exact release staged <R28>`; list [R28 staged, R27, R13, stock]), `title`,
    `reboot`. Boot `release-28`: list [R28, R27, stock] (R13 removed at the update's shutdown: 22's JUDGMENT-CALL 1),
    `check`/`title` with `Update to <R28> confirmed`, package 21's rules (`owner_vm.release_rules`), the session
    (`SESSION`: the theme in the rc.xml of the running labwc's `--config-dir` is `Ares-Crown` with its themerc, `fc-match` `Space Grotesk` and `:bold` as ares
    give `/usr/share/fonts/aresos/SpaceGrotesk-Variable.ttf`), Control's checks if it rides, the lead's no-foot
    check (end every foot of ares, `at check` must STOP with `Read failed: pgrep -u ares -x foot` and change
    nothing, then the Terminal app's foot is opened again in his session), the home screen's files, `previous`
    (list [R27, R28, stock], rollback queued). Boot `previous-27`: `Return to <R27> confirmed`, the home screen's
    files unchanged, `forward` (`Newest installed AresOS starts next <R28>`). Boot `final-28`: `Forward to <R28>
    confirmed`, apps.json unchanged, then 23d's game scope last (`JVM`: the check-build VM's method from
    `os/ci/overlay/checks.py`, a real JVM through `/usr/libexec/aresos-desktop-java` paused at startup, its cgroup
    `…/aresos.slice/aresos-game-<launch>.scope` with `memory.high` 2684354560, then the scope killed). Every boot
    ends in `owner_vm.finish` (package 11's audits); the Windows markers at the end.
  - **`CONTROL_RIDES = False`**: B.2 (root writes `{"format":1,"hosts":["rehearsal.invalid"]}` with `tee`,
    `/var/lib/aresos-control` root's 0755 first if missing, its SHA-256 recorded) and Control's checks (UID/GID 250,
    the folder's owner, `release_checks.py`; the hash unchanged on `release-28`, `previous-27` and `final-28`). Both
    settings are walked and tested; step 2 turns it on after PR #58 merges.
- **`os/ci/owner_vm.py`:** `laptop_update(..., target=)`: a fixed step 8 release, checked against the bundle's own
  history instead of the checkout's. `main()`: mode `release-28` for package 42 only (and package 42 only that mode),
  its host walk `os/manifest/ci/42/host-walk.json`, `42-bound-sources` (rebinding 22d's tables), and the walk; it
  STOPs without `os/manifest/releases/28.json` ("its rehearsal runs after step 5").
- **Wiring:** `.github/workflows/os-image.yml` (option `release-28`; the rehearsal job runs it on
  `pkg/42-release-28` only and only with no other input; every own-run-VM condition (bounds 345/315, guard,
  native step, registry steps, cosign) names `pkg/42-release-28 && release-28`; the owner VM driver for
  `REHEARSAL_PACKAGE` 42; the GHCR_READ_TOKEN cleanup skipped on the branch), `rehearsal_guard.py` (`own_native`
  and the model gate for 42's `release-28`; `probe-budget-ci` accepts it), `rehearsal-packages.json` (entry 42:
  `release-28` cap **0**, job bound 345, title `Two-disk rehearsal (release-28)`, the budget text says step 6
  raises it with the lead's OK), `registry_auth.py` (`release-28` on the branch; `signature` allows the branch only
  in that mode), `owner_media.require_runner`, `owner_capabilities.py` and `owner_devices.py` (their mode lists),
  `installer_webui.OWNER_VM_PACKAGES` and `two_disk_vm`'s native signature proof (package 42), `verify_release.py`
  (R27's trees at its source commit in this mode, as 22d's step 6c).
- **Tests:** new `os/tests/test_release28_rehearsal.py` (30 tests: ledger and cap 0, dispatch conditions, every
  step script under 42's environment, decisions like 22d's but where reviewed, guard, runner and registry gates,
  verify_release, `announced()` (manifests equal `bundle.manifests`, `owner.lineage` accepts it, lines, guide
  line 1, refusals), the stand-in origin, `matches`/`real_commit`, the local walk with Control off and on).
  `test_owner_walk.walk(route='release-28', control=...)` with `Release28Local` (the window's caller reads its
  lines from the stand-in commit it names; the routine line installs only over a lower version, else the tools'
  STOP) and `Release28Session` (foot, apps.json, the game scope, Control). Updated pins: `test_tools_local_wiring`,
  `test_release27`, `test_ways_back_probe` (owner_vm's host-walk table), `test_release28` (dispatch counts, the job
  token read for `release-28`, a known `release-28` title stops at cap 0), `test_owner_capabilities`,
  `test_owner_guard`, `test_rehearsal_auth`, `test_rehearsal_budget` (condition strings).
- **Host walk:** `reviews/42-release-28/walk-host.py` writes `os/manifest/ci/42/host-walk.json` (route
  `release-28`, 8 boots, 267 sources: 22d's set and `release28_walk.py`, its test, the script, `releases/27.json`).
- **Pending list:** `rebind.py pending` (25 bound files wait; none under `os/owner-tools/`, `os/release/`, `docs/`).

### Verified (step 3, this laptop)

Each module alone, bytecode off, after the owner-tools checks (`pgrep` for `ksshaskpass` and the tools' window)
printed nothing, on the final code: `test_release28_rehearsal` 30 OK, `test_tools_local_wiring` 42 OK,
`test_release28` 59 OK, `test_release27` 41 OK, `test_release_squash_binding` 7 OK, `test_owner_step_limits` 4 OK,
`test_checkout_sources` 8 OK, `test_owner_equality` 11 OK (106 s), `test_owner_walk` 27 OK, `test_owner_capabilities`
6 OK, `test_owner_guard` 12 OK, `test_owner_devices` 6 OK, `test_ways_back_probe` 57 OK, `test_ci_step_environment`
4 OK, `test_ci_api_permissions` 4 OK, `test_installer_webui` 9 OK, `test_rehearsal_budget` 4 OK,
`test_rehearsal_history` 9 OK, `test_rehearsal_auth` 9 OK, `test_aresos_desktop` 188 OK (1 skipped),
`test_ways_back_model` 26 OK with `ARESOS_MODEL_SCOPE=slice` (the full model runs hosted). Not run here:
`test_owner_update` (hosted only), `test_inherited_homebrew` and `test_sysusers` (they call `sudo -n`), and the rest
of the suite. The wiring test found two real gaps on its first run (`owner_capabilities.py` and `owner_devices.py`
refused the mode; `installer_webui` and `two_disk_vm` did not list package 42), fixed in `7ebfdd05` and `acbe72d0`.

The local walk ran in `walk-host.py` (Control off: 8 boots, 176 checks, 817 commands, 541 typed blocks) and in
`test_release28_rehearsal.WalkTest` (off and on; with Control on also the sites list's four hash reads). A scratch run built the stand-in
origin from a stand-in record: the `634e1237` stand-in's three hashes equal the real commit's
(`73fb5929…`, `9b66a3a1…`, `53c075c8…`), the announced commit differs in exactly the 8 generated files.

### Needs a hosted run or a VM run

- **VM (step 6, cap 0 until the lead's OK):** everything in the guest. Never run: version 4 installing a version 5
  bundle through the window (the first builder's scratch run over `test_owner_update`'s fixtures showed version 4
  installs a version 5 bundle from the folder), the update to R28 and its deployment lists (taken from the tools'
  code: `update` keeps the retained rows and names "At shutdown, this update removes older AresOS …"), `previous`
  and `forward` on R27/R28, the session reads on R28 (rc.xml's theme element as read, `fc-match` in the deployed
  image, `aresos-desktop status`'s `jvm_pid` in SETUP), the no-foot STOP and the Terminal app reopened from the
  root shell with his session's environment, apps.json planted under the instance in SETUP.
- **Hosted checks-only run:** the full suite (`test_owner_update` runs hosted only; `test_inherited_homebrew` and
  `test_sysusers` need root), the full ways-back model (model_scope may select it: `owner_vm.py` and the workflow
  changed).

### What the code doesn't show

- **Release 28's record is the walk's parameter.** CI reads `os/manifest/releases/28.json` (step 5 writes it); the
  announced files depend only on its bytes and `634e1237`. **Step 5's real payload commit must reproduce them:**
  `os/manifest/release.json` and `os/owner-tools/payload/release.json` byte-equal to `releases/28.json`;
  `history.json` and its payload copy `json.dumps(indent=2)` + newline with R28's row last and `tools_version` 5;
  `bundle.py --refresh`; `commands.json` regenerated with `bootstrap.command`/`bootstrap.lines` for the new
  fingerprint (same order, `indent=2`); nothing else under `os/owner-tools/` changes. `release28_walk.announced()`
  is the reference: comparing its files with the real commit's is the quickest check, and the walk itself STOPs
  if the checkout carries R28 with other bytes. After the run, `git rev-parse <commit>:os/owner-tools
  <commit>:os/manifest/release.json` must print the result's `announced[1].bound` values (`matches()`).
- **`verify_release.py` knows no release 28** (step 1's PLAN-GAP, still open): the rehearsal job copies
  `os/manifest/release.json` to the evidence and verifies it; once step 5's commit names R28 there, it STOPs until
  release 28's job name (`Package 28 release …`), branch identity and `source_trees` are added (step 5). Likewise
  `registry_auth`'s preflight, pull and native signature read `release.json`: R27 now, R28 after step 5 (then R27's
  signature is checked by version 2's tools in the guest, as before).
- `os/manifest/release.json` and `os/manifest/releases/27.json` are bound by the host walk: step 5's commit makes the
  receipt stale, so step 6 regenerates it (`python3 reviews/42-release-28/walk-host.py`) and refreshes the pending
  list before any dispatch.
- The ledger's minute cap (1200) has no room reserved for the three rehearsal runs (345 each); step 6 raises it with
  `release-28`'s cap.
- The game-scope check latches RECOVERY (as in the check-build VM), so it runs last; the R28 session stays in SETUP
  in the VM (no Minecraft account).
- `test_owner_walk.laptop_rows`/`update_states` take the R27 reference for this route, since `release.json` will
  name R28 after step 5.

### JUDGMENT-CALLs (step 3; technical, for the lead)

1. **One source for the announced bundle.** The stand-in announced commit is generated from `634e1237` and R28's
   record (`announced()`) both in the local walk (a stand-in record) and in the VM run (the real record), instead of
   taking HEAD's trees as 22d did; when HEAD already carries R28, the walk requires equality. This keeps one code path
   whatever order steps 5 and 6 take, and makes the real commit checkable from the receipt.
2. **The 8 characters** are compared host-side with line 1 of the stand-in's `OWNER-TOOLS.md` before the window
   check and the password; the window check then requires the helper's label to be exactly that label.
3. **B.2's write** runs `tee` in root's serial shell (the guide's `sudo tee` from his terminal ends in the same root
   write); the folder is made root's 0755 only if missing.
4. **The Terminal app after the no-foot STOP** is the hub terminal's argv (`owner_vm.HUB_TERMINAL`) started as ares
   with his labwc session's environment from the root shell (SETUP has no hub to click).
5. **apps.json in the VM:** SETUP never creates the hub, so the walk plants a marker `apps.json` (owned by ares)
   under the instance on R28 before `previous`, then requires it byte-equal on R27 and after `forward`; the instance's
   file tree must be unchanged on R27 and is recorded again on R28 (Prism may rewrite its files there).
6. **The game scope** is proved at the end of the last boot (it latches RECOVERY), with the check-build VM's method.

### PLAN-GAPs (step 3)

None new. Open from earlier: `verify_release.py` for release 28 (above; step 5); release 28's record binding `mod/`
and `os/minecraft/` (step 1).

### Left, in order

1. ~~The Codex Astra review of step 3~~ done: REVIEW-4 to REVIEW-8 above, SAFE at `c39d48cc`.
2. Step 2 (Control's rules) after PR #58: set `release28_walk.CONTROL_RIDES = True`, regenerate the host walk,
   `rebind.py pending`.
3. Step 4 (the cut), then step 5 after the owner's OK: **preconditions** (the lead): 22c's and 22d's INSTALL-STATUS
   rows on ON THE LAPTOP; version 4 confirmed on the laptop. Then the publish, `releases/28.json`, `verify_release.py`
   for R28, and the payload commit reproducing `announced()` (above).
4. Step 6: regenerate the host walk and the pending list; the lead raises `release-28` (and the minute cap); the
   VM runs; then the pins and guides (A.5) and the record step (`42-bound-sources` → `os/manifest/ci/42/`).

## Step 3: stopped at B.1's check (PLAN-GAP 1), 2026-11-17

Builder: a Claude agent (Opus 5.5), from `8792c274` (step 1's head, which the Codex Astra review reads; nothing
before it was rebased or amended). The lead's brief for this step: check whether version 4 installs a same-version
bundle with another fingerprint before building B, and stop with a PLAN-GAP if it refuses. It refuses, so **the
rehearsal mode `release-28` is not built**: no walk, no wiring, no ledger kind, no host-walk receipt.

Done:
- **Main merged** (`66bc606e`) as `75a83393`: no conflicts. Nothing under `os/` or `mod/` changed (main brought
  `control/`, `docs/control`, `.github/workflows/control-owner-oracle.yml`, briefs, reviews, STATE and HANDOFF), so
  the image sources stay main's; the merge base with `origin/main` is now `66bc606e`.
- `rebind.py pending "42 step 3: main merged"` (`d9727cc4`): the same 14 bound files wait; only the note is new.
- **B.1's check** (below): version 4 refuses the bundle the brief describes.

**The start state (recorded as the lead asked):** step 3 assumes the laptop has tools version 4 (`634e1237`,
`dcbc375faa4b269bacaf316c5ddc24503b9773b2538bcd017065ce8e312597be`) after the owner's 22d session. That session has
not happened yet; **the lead confirms version 4 once it is done.** The way to reach it in the VM, for the builder who
continues: the laptop's own route, which `os/ci/tools_local.py` already walks (package 27's route to R27 with version
2 from history, then 22d's folder and routine lines at `634e1237` on the stand-in origin, the window answered), not a
setup shortcut. It is the path the laptop takes, its code is reviewed and passed in run 43737933979, and a shortcut
(copying v4 into `/var/lib/ares` as root) would skip the journal, receipt and entry switch that version 4's
`update_tools` then reads. Its cost is one more window stage in the walk.

### PLAN-GAP 1 (blocks B.1 and everything after it)

Brief B.1: the routine line installs "version 4's code with R28's reference, so a new fingerprint" over version 4.

Version 4 refuses it before any write. `update_tools` (`os/owner-tools/owner.py:2651-2652` at `634e1237`; this
head's `os/owner-tools` is the same tree, `73fb5929`):

```python
require(new['tools_version'] > old_version, 'Installed tools are version ' + str(old_version)
    + '; refusing version ' + str(new['tools_version']) + ' (downgrade or same version)')
```

Both routes (folder and stick) reach it; the fingerprint differing is not enough. Every bundle so far took a new
number: 15f's is 1, 27's 2, 22c's 3, 22d's 4 (22c's and 22d's with release 27's history unchanged).

Evidence, run here on this head:
- `test_owner_update`'s `test_downgrade_same_version_foreign_history_and_unknown_legacy_refuse_without_writes` (its
  case "same version, other bytes"): OK.
- A scratch reproduction over that module's fixtures (not committed): version 4 installed in
  `tools-<fingerprint>/` with a two-release history standing in for [R13, R27], and a bundle at version 4 whose
  history adds a third release. From the folder and from the stick: `Installed tools are version 4; refusing version
  4 (downgrade or same version)`, nothing under the fixture's `/var/lib/ares` changed. The same bundle numbered 5,
  from the folder: `Tools updated from version 4 to 5`.
- On the laptop (and in the walk) the routine line would print `STOP: Installed tools are version 4; refusing version
  4 (downgrade or same version)` and then the bootstrap's `STOP bootstrap: verification or install refused`; nothing
  changes.

Options for the lead (neither changes the tools' code):
- **(a) Recommended:** release 28's bundle is version 4's code with `history.json`'s `tools_version` 5 (and R28's
  record). Version 4 installs it from the folder (the scratch run above). Line 1 of `OWNER-TOOLS.md` then says
  version 5, and package 43's tools (D19) take the next number. It is how 22c and 22d numbered bundles whose code
  changed but whose release history did not; here only the history changes, but the rule is the same: newer only.
- (b) The laptop stays on version 2 until release 28 (no 22d session first): then 4 > 2 and B.1 works as written,
  but `dcbc375f` itself never goes on the laptop. The lead's note of 2026-11-16 already assumes the session happens.

B.3 to B.6, the walk's install stage, its expected lines (`Tools updated from version 4 to N`, the receipt's
`tools_version`) and the stand-in origin's commits depend on that choice, so none of it was built.

### PLAN-GAP 2 (A.5's order; for steps 5 and 6, found while checking B.1)

- The payload carries `release.json` (`bundle.PAYLOAD` copies `os/manifest/release.json`), and `owner.lineage`
  refuses a bundle whose `release.json` does not name the history's newest record (`Release target differs from the
  newest history record`). So the commit announced for B.1 must already have `os/manifest/release.json` at R28, while
  A.5 says `release.json` changes only after the rehearsal passes. Package 27's rehearsal ran the same way
  (`owner_vm.laptop_update` asserts the history's last two are R13 and `release.json`). What can wait for the
  rehearsal: the guides' digest, `OWNER-TOOLS.md`, `INSTALL-STATUS.md`.
- While 22c's and 22d's rows in `docs/INSTALL-STATUS.md` say `VM REHEARSAL PASSED; NOT ON THE LAPTOP`,
  `test_checkout_sources` refuses any waiting change under `os/owner-tools/`, `os/release/` or `docs/`
  (`MUST_NOT_WAIT`; 22d's REPORT, open questions). R28's payload (history, `release.json`, the fingerprint) is such
  a change, so those rows move on first (22d's after the owner's session), or the test fails on step 5's commit.

### Verified on the merged head (step 3)

Each module alone, bytecode off, after the owner-tools checks (`pgrep` for `ksshaskpass` and the tools' window)
printed nothing: `test_release28` 59 OK (its real-branch source check against the new merge base `66bc606e`: only
the jar pin differs), `test_checkout_sources` 8 OK, `test_tools_local_wiring` 42 OK, `test_release27` 41 OK,
`test_release_squash_binding` 7 OK (it runs `verify_release.py`), `test_owner_step_limits` 4 OK,
`test_owner_equality` 11 OK (90 s; not run in step 1), and `test_owner_update`'s same-version test alone, OK.

### For the builder who continues (what the code doesn't show)

- `tools_local.rehearsal`'s start (`owner_vm.laptop_update`) reads R27 as `os/manifest/release.json` and asserts the
  history's last two are [R13, `release.json`]. Once the payload targets R28 that no longer holds: the R28 mode needs
  R27's facts from fixed sources (22d's step 6c read release 27's facts from its own source commit `b216f28f`).
- `tools_local.standin_origin` holds version 3's tree, then the head's. For R28 it would hold `634e1237`'s
  `os/owner-tools` (version 4, reached as the laptop does), then the announced commit's.
- The lead's note: version 4's `check` reads `pgrep -u ares -x foot` through `Host.read`
  (`os/owner-tools/owner.py:2016-2017`), so with no `foot` of `ares` it stops with `STOP: Read failed: pgrep -u ares
  -x foot`. In the VM his session sits in SETUP, which shows a `foot`; the walk must end that `foot` first to see it.

## Done

### Step 1, phase 1 (code and tests; the dry run is phase 2)

- **`os/ci/release_diff.py`: release 28's rules** (`Classifier28`, `RELEASES['28']`). `main(tools, release=...)`
  now runs release 27's comparison (unchanged, still against release 13) or release 28's against release 27
  (`os/manifest/releases/27.json`; its source on main is PR #35's squash `41b06513`, whose ten image trees equal
  the `source_trees` release 27 records, checked by a test). Each rule names its package:
  - os/config files changed or new since release 27: bytes equal the source, root-owned, the mode build.sh gives
    (its chmod 0755 line now has the desktop, its Java wrapper and the cover), no new extended attribute; the
    reason lists the commits on main that changed the file (`git log` up to this branch's merge base with main,
    since review 1's S2; e.g. `23 (#36), 31 (#54), 40 (#71)`). New
    folders of new os/config files must be root's 0755.
  - **Package 23's files:** Prism's bundle (`/usr/lib/prismlauncher`): every regular file is in the image's
    `prism-files.sha256` with its SHA-256, and that list holds exactly the regular files there (one extra or
    missing file stops the whole bundle); links stay relative and inside the bundle; nothing setuid, setgid or
    group/world-writable; `/usr/bin/prismlauncher`. `/usr/share/aresos/minecraft`: every library, mod and Prism
    component file equals its pin in `os/minecraft/desktop.lock.json` (hash and size), the AresOS jar equals its
    pin, the lock copy equals the source. `aresos-mod.json` must be the pin, built from this run's commit.
    `/usr/bin/aresos-desktop`. Java 25 and its three dependencies (the package lock), files they own, and the
    alternatives their scriptlets register (`/etc/alternatives-admindir/<name>`, `/etc/alternatives/<name>` and
    the command links): accepted only when every target is a file of an added package.
  - **23b's font cache:** each changed or added `/usr/lib/fontconfig/cache/<md5>-le64.cache-<n>` must be a
    fontconfig cache (magic, version, size) whose folder is under /usr, exists in the image and hashes (MD5) to
    its name. Release 27's blanket "fontconfig cache trigger" pattern no longer applies to release 28. (Phase 1
    also said the 32-bit caches must not change; the dry run showed 23b rewrites them too, see phase 2.)
  - **Package 31's `gschemas.compiled`:** the rule reads both compiled files (a GVDB reader and a GVariant decoder
    in `release_diff.py`, no glib needed) and lists every default that differs. Only the keys
    `zz-aresos.gschema.override` sets may differ, each by exactly the override's value (here one key:
    `org.gnome.desktop.wm.preferences button-layout` gains the AresOS desktop's
    `'appmenu:minimize,maximize,close'`); the image's override must equal os/config's.
  - **Package 31's theme:** the result records the Ares-Crown checksum of the image's theme and the one
    `os/ci/image-checks.sh` pins; a difference is a problem that stops the release. A test holds that the pin is
    package 31's reviewed value (`cf01b9b1…`, REVIEW-2), that the theme files equal 31's commit, and that the
    checksum of os/config's theme is that value.
  - **40's rc.xml rules:** rc.xml is an os/config file (bytes equal the source, from 23, 23b, 31 and 40); the
    result also lists the settings it adds and removes (comments and layout ignored). A test pins today's list:
    removed the old theme and recovery key, added Ares-Crown, the window switcher, the recovery key that also
    ends the cover (23b), the borderless game window (23), the game below apps (40) and the cover (23b).
  - `etc/shadow` and `etc/shadow-`: only the creation dates sysusers writes (the build date) may differ.
  - Regenerated databases as in release 27 (rpm, dnf5, ldconfig, ...), without the font caches.
- **`.github/workflows/os-image.yml`:** inputs `release_28` (publishes) and `dry_run_28` (never publishes), both
  for `pkg/42-release-28` only; run names `Package 28 image release` and `Package 28 image dry run (never
  published)`; `REHEARSAL_PACKAGE` is 42 on the branch. Jobs:
  - `release-28`: release_27's job, step for step (a test compares them), reading release 27 and publishing with
    `publish.sh`; `packages: write` and `id-token: write`. Runs only for `release_28` (and never with
    `dry_run_28`).
  - `release-28-dry-run`: the same steps without the publish step (a test holds the two equal but for that step,
    the kind and the artifact name), permissions `contents: read`, `packages: read`, `actions: read`. It cannot
    publish by structure: no write permission to GHCR, no OIDC token for signing, no publish step, and publish.sh
    is not reachable from its steps (test).
  - check-build and switch do not run for either input.
- **`os/ci/build_tools.py`:** `build_release(tools, release)` for 27 and 28 (one table: branch, kinds, previous
  release); both 28 kinds (`publish-28`, `dry-run-28`) build and diff identically.
- **`os/ci/registry_auth.py`:** package 42's two kinds may read release 27 with the job token on its branch.
- **`os/ci/rehearsal_guard.py` and `rehearsal-packages.json`:** package 42's ledger (every dispatch on the branch
  counts by its title; caps `dry-run-28` 2, `publish-28` 1, `resolve` 2, `checks` 1; 1200 minutes; one publish;
  since review 1: `dry-run-28` 4, `publish-28` 0 and `publish_cap` 0 until the owner's OK).
  `PUBLISH_KINDS` names the kinds whose job may publish; the dry run's kind is refused at `publish-ci`.
- **`os/ci/publish.sh`:** `pkg/42-release-28` publishes as release 28 (tag `28-<commit>`).
- **Tests:** new `os/tests/test_release28.py` (30 tests) and small compiled-schema fixtures
  (`os/tests/fixtures/release28-schemas/`, made with glib-compile-schemas 2.88.4; SOURCE.txt says how).
  `test_release27`'s and `test_owner_staged_release`'s dispatch helpers know the two new inputs;
  `test_aresos_desktop`'s list of check-build.sh callers names the two new jobs.
- **K6 (lead's request, from 18c's security review):** `ReleaseChecksTest` runs the real `check-build.sh build`
  under each release-28 job's name with stand-ins for podman: it builds `localhost/aresos:check` as a release,
  runs `check-image.sh localhost/aresos:check release` (and through it image-checks.sh, Control's checks
  included once they ride), then tags exactly that image `localhost/aresos:ci`. Nothing later in the job builds,
  pulls or tags that name (build_tools and release_diff only pull release 27 and read), and publish.sh copies and
  signs `containers-storage:localhost/aresos:ci`. So the release job publishes the image its check build checked.
- **The mod jar's pin renewed (A.2):** `check_build=resolve` on `74927368`, run
  [43828756952](https://github.com/Ares-Empire/AresOS/actions/runs/43828756952) (passed; it never pushes, signs
  or publishes): two clean builds of the jar both `8090554997fdb907d741a99eda3240ed15a8e55f806b3b99fd5b406d8213fcc0`
  (`MOD_JAR_REPRODUCIBLE`, was package 23's `8b04c511…`), now the pin in `os/minecraft/desktop.lock.json`. The
  same run found no other pin gone: the package resolution equals `os/packages.lock.json` exactly (29 entries,
  none missing), Prism's tarball still has its pinned SHA-256, Chrome's RPM signature checks. So no other pin
  was renewed. The jar is built from `mod/` only, so a later commit that does not change `mod/` keeps this pin;
  step 4 renews it again on the cut commit if main's `mod/` moved. On GitHub's own evaluation of that dispatch,
  both release 28 jobs were skipped and only the throwaway check build ran.
- **Bindings:** five bound files changed (os-image.yml, registry_auth.py, rehearsal_guard.py,
  rehearsal-packages.json, test_owner_staged_release.py); `rebind.py pending` recorded them. Nothing under
  os/owner-tools/, os/release/ or docs/ waits.

### Step 1, phase 2: the dry run's 39 differences

The dry run [43832912792](https://github.com/Ares-Empire/AresOS/actions/runs/43832912792) (`dry_run_28` on
`611067b7`) built release 28, passed the image checks and the first VM pass, and stopped at the image diff:
1,585 changed paths, 39 unexplained, no other problem (theme equal to package 31's pin, schemas only 31's key,
base ancestry verified). Each of the 39 traces to a merged package; none is OPEN.

| Path(s) | Cause | Package, commit on main | Rule |
|---|---|---|---|
| 34 `usr/lib/fontconfig/cache/<md5>-le32d4.cache-9`, one per font folder release 27 has | 23b's `fc-cache --system-only --really-force` (os/build.sh). Fedora's `/usr/bin/fc-cache` is a script that runs `fc-cache-32` (fontconfig.i686, in the base for Steam) and `fc-cache-64`, so the forced run rewrites the 32-bit caches too. They changed, none vanished: release 27 has 68 caches (34 folders, both formats), release 28 has 70: all 68 rewritten, 2 added, none removed. Each kept its size except `/usr/share/fonts`'s (1544 to 1568 bytes; its 64-bit one 1696 to 1728), which gained the `aresos` entry. Release 27's headers record folder times of 2026-10-12/13, so a rewrite changes the bytes although no font changed. | 23b, `ff6edf55` (#70) | `font_cache_rule`, now for both formats |
| `…/50471fd4bd417ff5c0731b6a17aa3708-le32d4.cache-9` (added) | the same run's 32-bit cache of the new `/usr/share/fonts/aresos` | 23b, `ff6edf55` (#70); the folder is 31's, `29e4fbc6` (#54) | the same rule ("a new font folder") |
| `…/f2e43df3287529323e79e7929dc44cc9-le64.cache-9` (its 32-bit sibling is one of the 34) | the cache of `/usr/share/fonts/noto-cjk`, in both releases the base's link to `/usr/share/fonts/google-noto-sans-cjk-fonts` (unchanged); fc-cache caches a linked folder under the link's own name. Phase 1's rule wanted a real folder. | 23b, `ff6edf55` (#70) | the same rule: the folder may be a link release 27 has, unchanged, to a folder under /usr |
| `usr/lib/jvm/java-25-openjdk/man`, `…/man/man1` (new folders) | java-25-openjdk-headless 1:25.0.5.0.8-3.1.fc44 lists its four man pages in `man/man1` as files but not these two folders (rpm -ql in the dry run; the pinned RPM's header read on the laptop; no scriptlet makes them). rpm creates a missing parent folder of a file it installs, root's 0755. | 23, `3bff81b6` (#36): Java 25 in the package lock | `package_rule`: exactly these two folders, new, root's 0755, no extended attribute, holding a file of an added package |
| `usr/share/aresos/manifest/updaters.json` | build.sh's last step writes the updater audit (os/tests/audit.py). Diffed (release 27's file from the laptop, release 28's from the artifact, both equal to the run's hashes): the same 815 units, one change: `user.slice`'s `sources` gained `/usr/lib/systemd/system/user.slice.d/50-aresos-recovery.conf`. No state, command or "suspicious" verdict changed. | 23, `3bff81b6` (#36): the drop-in | `manifest_rule` with `audit_changes`: the same units in the same order, every field but `sources` equal, old sources kept in order, and each added source a drop-in of that unit (or its template) that os/config gained since release 27, absent in release 27, in the image with the source's bytes |

What each rule now accepts, and its negative tests (`test_release28`):
- **Font caches** (`FONT_CACHE_LAYOUTS`): `-le64` and `-le32d4`, each read with its own header layout (64 and 40
  bytes; the folder's name must follow the header), the name the MD5 of the folder, the version the name's, the
  cache in the other format present in the image, the folder under /usr reached through folders only (no link
  above it), and itself a folder or a link release 27 has unchanged to such a folder. Stops: a cache without its
  sibling (either way), a 64-bit cache under the 32-bit name, another folder or version in a 32-bit cache, a link
  that is new or changed, an unchanged link out of /usr or to nothing, a folder reached through a link, a folder
  outside /usr, a name inside the header. Real fontconfig 2.17 caches of `/usr/share/fonts/aresos` in both
  formats are fixtures (`os/tests/fixtures/release28-fontcache/`, SOURCE.txt; made with `fc-cache-NN --sysroot`;
  release 28's are the same sizes, 6752 and 9144 bytes).
- **Java's man folders** (`JAVA_MAN_FOLDERS`): stops for another folder under the JDK (even holding a package
  file), another mode, an extended attribute, a folder release 27 had, or no page of the package in it.
- **Updater audit**: stops for a changed command, state or verdict, a removed source, an added unit, a source
  os/config does not have, package 23's drop-in of another unit (`user-1001.slice`) listed under user.slice, an
  os/config drop-in not changed since release 27, a drop-in whose image bytes differ from the source, one release
  27 had, and malformed JSON. The rows go to `result.json` as `updaters` (`font_caches` rows now carry `format`
  and `folder_kind`).
- Every new condition was weakened once in a scratch copy of the module (16 mutations); a test failed for each.

**Proven against the dry run's evidence** (a replay, run on the laptop, not committed: release 28's classifier
over the run's own `old-files`/`new-files` inventories, so every kind, mode, owner, attribute, link target and
hash is the run's; file bytes from the laptop's release 27 files and the artifact's manifest files, each checked
against the run's hashes; for release 28's caches, whose bytes the artifact does not hold, release 27's cache of
the same name or fontconfig's own output for the aresos folder):
- all 39 are explained, by the rules in the table;
- of the other 1,546 changed paths, 1,516 get the dry run's rule and reason unchanged; the 30 others are rules
  whose bytes the artifact lacks (`etc/shadow`, `etc/shadow-` and package 23's 28 alternatives paths), not
  affected by phase 2;
- release 27's schemas recompiled with package 31's override (as build.sh compiles them) are byte-identical to
  release 28's `gschemas.compiled` (its SHA-256 in the run).

**Only a new build can prove:** that release 28's own 36 32-bit cache files parse as 32-bit caches naming their
folders (the dry run parsed its 64-bit ones; the 32-bit layout is proven on release 27's 34 real caches from the
laptop, fontconfig 2.17's output and the fixtures, and the run's sizes match), and the whole diff passing in one
run (`IMAGE_DIFF_PASSED`) with the remaining steps of the job after it.

### Review 1's fixes (REVIEW-1.md, CHANGES-NEEDED: B1, S1 to S5, N1 to N7)

Each finding was checked against the code first; none is disputed.

- **B1, publishing shut until the owner's OK.** Package 42's ledger (`os/ci/rehearsal-packages.json`) has
  `publish-28` 0 and `publish_cap` 0, with a `publish_gate` note beside them. A `release_28` dispatch now stops at
  its job's guard, the first step after checkout, before any build (`STOP: publish-28 dispatch allowance
  exhausted`), and again at publish.sh's guard. The guard's publish gate (`publish-ci`) also refuses while
  `publish_cap` allows no publish (`STOP: the ledger allows no publish`), so raising only the dispatch cap opens
  nothing. The input's description says the ledger stops it. **Step 5 raises both to 1, only after the owner's OK,
  in a commit that names the OK (date, board number) in the entry's `budget` text**, and refreshes the pending
  list. A slipped `release_28` dispatch still counts as one publish-28 dispatch and stops every later guard on the
  branch (the cut's dry run too) until a ledger commit records it. Tests: with this ledger and today's history
  (one resolve, three dry runs) the cut's dry run, a resolve and the checks run pass their guards; a publish
  dispatch stops in `ci` and `publish-ci` mode; a slip stops the next dry run; the dispatch cap alone opens
  nothing; both caps at 1 let only `publish-28` through.
- **S1, `GENERATED_28` narrowed** to the four patterns dry run 3 needed (checked in run 43847257976's
  `classified-files.json.gz`: 11 generated paths), each with its reason: `usr/lib/sysimage/libdnf5/*` (six dnf5
  history files), `var/lib/dnf/*` (two countme markers), `var/log/dnf5.log*` and `var/cache/ldconfig/aux-cache`;
  the rpm database keeps its own exact rule. Dropped: the SELinux policy store (`etc/selinux/targeted/*`,
  `var/lib/selinux/*`), `usr/share/icons/*/icon-theme.cache`, `usr/share/applications/mimeinfo.cache`, `run/*`,
  `var/cache/libdnf5` and below, `etc/ld.so.cache`, `usr/lib/sysimage/rpm/*` and the folder
  `usr/lib/sysimage/libdnf5`. A test holds that dry run 3's paths each get a generated reason and every reason
  is used, and that a path under each dropped pattern stops.
- **S2, the image's sources must be main's.** `release_diff.main` for release 28 takes `git merge-base HEAD
  origin/main` first (no `origin/main`: `STOP: no merge base with origin/main`; the release jobs' checkout
  fetches every branch, as dry run 3's log shows) and records it in `result.json` (`main.merge_base`). The image
  sources (`IMAGE_SOURCES`: `mod`, `os/.containerignore`, `os/Containerfile`, `os/build.sh`, `os/config`,
  `os/google-chrome.lock.json`, `os/keys`, `os/manifest/base.json`, `os/minecraft`, `os/packages.lock.json`,
  `os/policy`, `os/tests/audit.py`) on the built commit must equal the merge base's, except
  `BRANCH_SOURCE_CHANGES`: one row, `os/minecraft/desktop.lock.json`, which may differ only in the AresOS jar's
  `sha256` (A.2). Anything else is a problem that names each file (`image sources differ from main at the merge
  base <commit>: <files>`). `origin()` now reads main's history up to the merge base, so a change made on this
  branch has no origin and stays unexplained too. At the cut (step 4) main is merged in: the merge base moves
  to main's commit at the cut and the rule holds the same way (a test merges "main" into a branch and checks the
  base moves, the pin passes, a wrong merge resolution is named). Tests: a temporary repository (the pin alone
  passes, harness files pass, each other source change is named, two at once), the real branch against
  `origin/main` (nothing differs but the pin), the source list against every `/tmp/aresos` path of
  `os/build.sh` and `os/Containerfile`, and `main()` stopping with release 27's source as "main".
- **S3, resolve and checks read their caps.** The checks-only run's guard step now also runs on
  `pkg/42-release-28` (before the suite). `check-build` has a guard step on this branch only, right after the
  checkout and before the tools (`REHEARSAL_MODE: resolve`, reserve 120): a third resolve, a second checks run or
  a check build of another kind stops there. For that the job has `actions: read` and `packages: read` (what
  `test_ci_api_permissions` requires of any job that can reach the guard; still no write and no id-token), and
  its checkout keeps no credentials (`persist-credentials: false`), so only the guard step gets the token. A run
  title the ledger does not know now stops with `STOP: run <id> is titled '<title>', which package 42's ledger
  does not know; record it in os/ci/rehearsal-packages.json before any dispatch`, not a bare `ValueError`.
- **S4, near-miss tests.** One near miss per condition: config files and new folders (owner, group, mode, link,
  attribute, a folder release 27 had, no origin on main), the manifest (lock and `packages.txt` equality, owner,
  mode, Prism's list or the mod record already in release 27, Prism's list not the reviewed one, a duplicate
  line, the audit new), the Minecraft inputs (release 27 had it, attribute, owner, mode, size, another folder,
  folder mode), Prism's bundle (owner, group, attribute, release 27, bytes, writable, an absolute link inside),
  the alternatives (record in release 27, its owner, mode, attribute; link and command owners), the commands,
  `etc/shadow`, the font caches (owner, mode, attribute, an old cache not root's 0644 or a link), the rpm
  database's metadata, the schemas (owner, mode, attribute, the image's override, no differing key, a default
  changed beside the override, changed choices, another desktop's value, release 27 compiled the override
  already: three new fixtures compiled with glib-compile-schemas 2.88.4), a package path that is no file,
  folder or link, a removed package without its locked replacement, and
  each stop of `main()` (revision and source labels, another label, the OCI runtime config, both base
  ancestries, a unit only generated, release 27 on another base, release 27's lock, an unreviewed unmasked unit,
  `status` stopped when a path is unexplained). The fixture overrides owner, group or attributes per image and
  path (`Classifier28Test.image`). Measured by weakening one condition of `release_diff.py` at a time in memory
  and running `test_release28` and `test_release27` (a scratch script, not committed):
  84 weakenings of the conditions that were there (the reviewer's method; the reviewer's list of 57 is not
  recorded, so this is a list of my own over the same rules and `main()`): **before, 24 made a test fail and 60
  did not; now 78 do.** The 6 left change nothing the tests can reach: a new folder that holds no file changed
  since release 27 already has no origin on main, so it stops anyway (tested with `etc/greetd`); os/config holds
  no link (and N5's converse stops on one); an updater audit without release 27's copy already fails to parse;
  a drop-in path that `normpath` changes cannot name a unit's folder; os/config has no drop-in that does not end
  in `.conf`; the alternatives records exclude a record release 27 had before the record rule asks. The 26 new
  conditions of these fixes (S1, S2, S5, N4, N5) were weakened the same way: all 26 make a test fail.
  `test_release28` has 59 tests (35 before).
- **S5, files of the added packages.** The rule now needs the path's records in the added packages' rpm
  database (`rpm -q --qf` in the new image, `RPM_FILE_FORMAT`, read by `rpm_files`, which stops on a line it
  cannot read): no `%ghost`, `root`/`root`, the recorded kind and mode, no file capability, for files the
  SHA-256 (digest algorithm 8) and size, for links the target; in the image root's, no extended attribute,
  nothing setuid, setgid, sticky or group- or world-writable. Checked against dry run 3 before the change: the
  four pinned RPMs (fetched from Fedora's mirror into a scratch folder; their SHA-256 equal the package lock)
  record 480 paths; all 470 paths the rule explained in run 43847257976 match their records in every field, and
  the 10 others are `%ghost` (the alternatives' command links, explained by the alternatives rule, and two
  `.rpmmoved` paths absent from the image). The query format was run with this laptop's rpm 6.0.2 (release 27's, on the same pinned base) on
  the RPMs and on an installed package with file capabilities. `rpm -V` of the added packages is recorded in
  `result.json` (`rpm_verify`: exit code and lines), as evidence, not a stop: it is one more podman run in the
  diff, so it fits the job's shape. A removed package's path is explained only when it is gone.
- **Nits.** N1: done (`dry_run_28` comes before `release_28` in the run name, so both together count as a dry
  run). N3: done (`image` and `release-27` exclude both new inputs). N4: done (`PRISM_FILE_LISTS` pins dry run 3's
  `prism-files.sha256`, `9df32315…`, 679 files, per Prism tarball pin; another list stops Prism's whole bundle; a
  renewed Prism pin needs its own row). N5: done (`extra()` stops when an os/config file changed since release 27
  is missing from the image or has other bytes, or a removed one is still there; dry run 3's inventory holds all
  56). N7: done (the wording above). Left: N2 (`github.ref == 'refs/heads/…'` in the two jobs): the shared
  condition helper (`test_owner_staged_release.condition`) evaluates only `github.ref_name`, and that module may
  not run on this laptop now, so the change could not be tested here; step 6's `verify_release.py` should pin the
  `refs/heads` identity. N6 (one mirror outage costs the publish): for step 5, word the owner's OK for the image
  source, not one commit; step 5 may also set the `publish-28` dispatch cap to 2 with `publish_cap` 1, so a
  dispatch that dies before publishing can be retried without another ledger commit, while the guard still
  allows one publish attempt at most.

## Verified

- Phase 2: `test_release28` 35 OK (30 before), `test_release27` 41 OK, `test_ways_back_probe` 57 OK,
  `test_checkout_sources` 8 OK, each run directly; `py_compile os/ci/release_diff.py`. No bound file changed in
  phase 2: `rebind.changed()` (read-only) equals the pending list's files exactly, so `rebind.py pending` was not
  run.
- Each changed test module run directly: `test_release28` 30 OK, `test_release27` 41 OK,
  `test_ci_api_permissions` 4 OK, `test_ci_step_environment` 4 OK, `test_checkout_sources` 8 OK,
  `test_build_tools` 3 OK, `test_ways_back_probe` 57 OK, `test_tools_local_wiring` 42 OK,
  `test_aresos_desktop` 188 OK (1 skipped) after the pin renewal, `test_owner_staged_release` 7 OK (before the lead's stop on owner modules, see below).
  `py_compile` of the changed scripts, `bash -n os/ci/publish.sh`.
- `test_release28.MainSmokeTest` runs `release_diff.main` for release 28 end to end on small stand-in images
  (podman and skopeo emulated): it passes when every difference is explained and stops on an unexplained file
  or another theme.
- **The schema rule against the real release 27:** this laptop runs release 27. Its
  `/usr/share/glib-2.0/schemas` recompiled with `glib-compile-schemas --strict` alone is byte-identical to its
  `gschemas.compiled`; with package 31's override added, exactly one key differs
  (`org.gnome.desktop.wm.preferences/button-layout`, gaining `{'AresOS': <'appmenu:minimize,maximize,close'>}`).
  The decoder agrees with GLib's own on all 1,124 values of that file (27 types; only number and quote
  formatting differ). So release 28's compiled defaults should differ only by 31's key.
- **The font-cache rule against release 27's caches:** every `-le64.cache-9` file on this laptop has the magic,
  version and size the rule reads, names its folder, and is named by that folder's MD5.

- **Review 1's fixes** (head after the two fix commits; each module run alone, bytecode off):
  `test_release28` 59 OK, `test_release27` 41 OK, `test_checkout_sources` 8 OK, `test_ci_api_permissions` 4 OK,
  `test_ci_step_environment` 4 OK, `test_aresos_desktop` 188 OK (1 skipped). Every other `os/tests` module whose
  name does not start with `test_owner_` (69 modules, 1,247 tests): 67 OK, among them `test_ways_back_model`
  26 OK (the full model, 17 minutes) and `test_ways_back_probe` 57 OK. Two fail here only because they need
  root: `test_inherited_homebrew` (1 failure, 7 errors) and `test_sysusers` (2 errors) run `sudo -n`, which this
  laptop refuses without a password ("a password is required"), so nothing ran as root; the first fails the
  same way on the reviewed head 3980c5ef, and neither touches a file these fixes changed. The hosted run (a
  root-capable runner) is where they count. The first fix commit alone (B1, S3) was run too:
  `test_release28` 37 OK, `test_release27` 41, `test_ci_api_permissions` 4, `test_ci_step_environment` 4,
  `test_checkout_sources` 8, the check-build permission test OK. Mutation counts: see S4 above.

## Not verified yet

- A dry run that passes the image diff. Run 43832912792 confirmed the rules for Prism's bundle, the Java
  packages' files and alternatives, the pins, the schemas, the theme and rc.xml; phase 2's rules are proven
  against its evidence except release 28's own 32-bit cache bytes (see phase 2). (Done since: dry run 3 passed.
  After the diff the dry run has only the credential cleanup and the evidence; the publishing job adds its publish
  step. Neither job has a second VM pass.)
- The release 28 jobs on GitHub: only the resolve dispatch has run on the branch (both jobs skipped there). The
  publishing job (release_27's steps for release 28) has never run and must not before the owner's OK.
- `test_owner_equality` and `test_owner_step_limits` (brief 42, C): not run. The lead stopped every
  `os/tests/test_owner_*` module while the owner tools install runs on the laptop; `test_owner_equality` was
  stopped mid-run (its temp folder removed). Run them once the lead says the install is done, or in the hosted
  checks-only run.

- Review 1's fixes on GitHub: nothing was dispatched (the lead dispatches). Not yet run on a real build: the
  source stop and the merge base (S2; `origin/main` is in the job's checkout, as dry run 3's log shows), the rpm
  query and `rpm -V` in the image (S5; the query format and its reading were run on the pinned RPMs with this
  laptop's rpm, and every path dry run 3 explained matches), the pinned Prism list (N4; dry run 3's value), the
  converse (N5; dry run 3's inventory holds), the narrowed generated patterns (S1; dry run 3's paths). The new
  guard steps of `check-build` and the checks run have not run either (unit tests only).

## Left, in order

1. Done: dry run 3 passed (below). One `dry-run-28` dispatch stays for step 4's cut (cap 4, three spent).
2. Review 1's fixes: done (above). Next: a fresh review of them (review 2).
3. The hosted checks-only run on a head with these fixes (brief C; its cap is 1 and its guard now counts it):
   review 1 noted the full suite has not run on any head of this branch.
4. Step 2 (Control's rules; if Control's image part reads more than `IMAGE_SOURCES` names, add it there),
   step 3 (the rehearsal mode; it adds its kind `release-28` to package 42's ledger with cap 0, which step 6
   raises with the lead's OK). Step 3 is built (the lead answered PLAN-GAP 1 on 2026-11-17; see the top section
   and its own "Left, in order").
5. Step 4, the cut: main merged in, the resolve if main's `mod/` moved (the guard now counts it: one resolve
   left), then the last dry run, `gh workflow run "OS image" --ref pkg/42-release-28 -f dry_run_28=true` (never
   `release_28`: it publishes, and until step 5 its guard stops it and the slip blocks the branch). What that dry
   run can stop on that dry run 3 did not check: S1's narrower generated patterns (a regenerated path outside
   them, e.g. if Control's `gh` RPM changes the SELinux store or the desktop caches, needs its own rule); S2's
   source stop (any image source not main's at the merge base but the jar pin; a wrong merge resolution shows
   here); S5's rpm records (Control's `gh` or a renewed package would be held to its records too); N4's pinned
   Prism list (a renewed Prism pin needs its row); N5's converse. Read `result.json`'s `main` and `rpm_verify`:
   if `rpm_verify` is clean (exit 0, no lines), a later step may make it a stop.
6. Step 5, after the owner's OK only: raise `publish-28` and `publish_cap` to 1 (or 2 and 1, see N6) in a commit
   that names the OK, refresh the pending list, then the lead dispatches `release_28`. Step 6 as the brief says.

## What the code doesn't show

- The two inputs are separate booleans, as the lead asked; dispatching both runs neither release job, and the
  run is titled and counted as a dry run (review 1, N1), not as the publish.
- Kind names: the rehearsal of step 3 is `rehearsal=release-28` (the brief), so the image kinds are
  `publish-28` and `dry-run-28`, not `release-28`.
- The ledger caps (dry runs 2, raised to 4 by the lead; publish 1, now 0 until the owner's OK; resolve 2,
  checks 1, 1200 minutes) cover steps 1, 4 and 5: the brief's
  budget (C) names one release build, one publish, one checks-only suite; steps 1 and 4 each also dry-run and
  renew the pin. For the lead to confirm or change.
- Which input is which: `dry_run_28` builds, checks, boots once and diffs against release 27 and can never
  publish; `release_28` is the publishing job (stopped by its ledger until step 5). Both together run nothing and
  count as a dry run.
- The image sources are what the build reads. The Containerfile's `COPY . /tmp/aresos/` also carries the rest of
  `os/` (tests, owner tools, manifests) into the first build layer, where build.sh's last step deletes it; those
  files are not in the image's file tree, so the diff (which compares file trees) cannot see them and the source
  stop does not cover them. They are this public repository's own files.
- `rpm_verify` is evidence only; nothing reads it yet.
- The 32-bit font caches exist because the base ships fontconfig.i686 (for Steam). If a later base drops it, its
  caches vanish and every 64-bit cache loses its sibling: the diff stops, which is right for a base change.
- Prism's files are checked against the image's own `prism-files.sha256`, which build.sh writes right after
  extracting the tarball whose SHA-256 and size it checked; the diff does not download the tarball again. Since
  review 1 (N4) that list must also be the one dry run 3 recorded for this Prism pin.
- **PLAN-GAP:** release 27's record binds ten source trees; since package 23 the image also depends on `mod/`
  (the jar is built from the commit) and `os/minecraft/` (the pins). Release 28's record and
  `verify_release.py` (step 5) should bind those too, and `verify_release.py` must learn release 28's job name
  and branch before release.json points at release 28 (step 6).
- **PLAN-GAP:** brief A.2 says to renew the jar pin with `os/ci/build-mod.sh --twice`; that script is what
  `check_build=resolve` runs (`check-build.sh resolve`), so step 1 uses the dispatch.

## JUDGMENT-CALLs

None so far. (A pin other than the mod jar's renewed by resolve would be one; none was touched.)

## Lead, 2026-11-16: a second dry run before the cut

Phase 2's rules are proven on the evidence but not on a build (the 32-bit caches' own bytes, `IMAGE_DIFF_PASSED`, the job's steps after the diff). The lead raised `dry-run-28` from 2 to 3 in `os/ci/rehearsal-packages.json` (test updated, pending list refreshed) and dispatches the second dry run on this head; step 4's cut keeps one.

Dry run 2 (43843690867, on `f6e0d693`) died at 6 minutes in "Install pinned tools on disposable runner": snapshot.ubuntu.com answered 502/503 (before any build; a dispatch all the same). The server answered again at 10:15Z; the lead raised `dry-run-28` to 4 and dispatches dry run 3; the cut keeps one.

Dry run 3 (43847257976, on `e4a0f861`, 10:15Z to 11:28Z) passed: `IMAGE_DIFF_PASSED: 1585 changed paths, all
explained` (phase 2's rules held on a real build, the 32-bit font caches included), `CHECK_BUILD_VM_PASSED`, and
the UEFI VM checks. The release-28 publish job was skipped, as the dispatch gate says. Step 1 is done; its review
(Codex, from Tue 2026-11-17) reads phases 1 and 2 and this run.

## Lead, 2026-11-16: fix check SAFE, dry run 4

The fix check of review 1 (REVIEW-2.md, Fable) says SAFE: every finding is closed or left with a reason it accepts.
Left for later steps:
- **N2** (nit): commits before `90c9d862` still carry publish caps of 1, so a tag named `pkg/42-release-28` on one
  of them would run that old ledger (a deliberate tag push, no slip). Cheap close for step 2's builder: the guard
  and `publish.sh` require `GITHUB_REF` to start with `refs/heads/`.
- **N8** (step 2): when main is merged in with PR #58, run `test_release28` before any dry run and add `control`
  to `IMAGE_SOURCES` (`ImageSourcesTest` fails on it).
- A pin renewed on this branch now stops the diff (S2). Brief A.2 names `gh`'s lock: renew such a pin on main
  before the cut, or give it a row in `BRANCH_SOURCE_CHANGES`.
- **N6** stays with step 5 (dispatch cap 2 with `publish_cap` 1: one retry, still at most one publish).

Nothing in `3980c5ef..8b427862` had run on a real build, and the cut's dry run would have been the last one allowed.
The lead raised `dry-run-28` to 5 (`bfe92f45`) and dispatched dry run 4 (43897120279) on that head; the cut keeps one.

Dry run 4 (43897120279, on `bfe92f45`, 15:30Z to 16:10Z) passed: the guard counted it as dry run 4 of 5;
`IMAGE_CHECKS_PASSED`, `CHECK_BUILD_PASSED`, the UEFI VM checks, `CHECK_BUILD_VM_PASSED`, and `IMAGE_DIFF_PASSED: 1585
changed paths, all explained`. result.json: `main.merge_base` `e33ffc46`, the only branch change is the jar pin,
`differing` empty (S2); `rpm_verify` of the four added packages exit 0 with no lines (S5; a later step may make it a
stop). Review 1's fixes hold on a real build. One dry run is left, for the cut.

### Step 2 reviewed (2026-11-18)

REVIEW-10 (Codex gpt-6-astra, high) on `b82e8fb3`: **SAFE**, three notes. Its first note (a login-graph timeout in
`release28_walk.py:507` drops the checker's stdout before it is exported) fails closed; it is a diagnostics
improvement for a later step, not a release blocker. `linux-tools` confirmed on 2026-11-18 03:15 that R28 needs
neither the record's `chrome_build` nor a builds.json entry: at runtime Control reads its build only from the
image's `chrome/build-id.json` and qualification only from `chrome/qualification.json`, builds.json is read only by
the CI qualification pipeline, and without the browser side R28's Chrome tools answer that Chrome is unavailable.

## Step 5: the publish and release 28's record (2026-11-19, the lead)

- **Order** (the lead, with the owner's yes): the owner's route in the VM (B) pulls the signed R28 image from the
  registry, and `owner_vm.py` STOPs without `os/manifest/releases/28.json`, so the private publish comes before the
  rehearsal; nothing is pinned for the laptop until the rehearsal passes (as R27 went). The release job publishes only
  after its own build, image checks, first VM pass and the complete diff against R27. The owner's standing rule
  (board #388) and his answer to board T415 (2026-11-19, "Yes, publish now") cover it.
- **Gate:** `publish-28` and `publish_cap` 0 -> 1 (`9393cbcb`); review 12 (Codex gpt-6.2-sol high) SAFE, no findings
  (`REVIEW-12.md`). `release_28` dispatched once on `7d5fbbf2`: run 44590446680.
- **The record:** `python3 -B reviews/42-release-28/payload.py record <evidence/release.json> <run> "<line>"` writes only
  `releases/28.json` (the job's record + `daily_wheel` + `owner_review`). Per the lead's decision 2 of 2026-11-17, the
  rehearsal generates its stand-in announced commit from that record; the real payload commit follows the rehearsal.
- **After the rehearsal passed (the pin step):** `payload.py announce` writes exactly `release28_walk.announced()`'s
  eight files from the committed record and checks `bundle.py --refresh` agrees; then the walk's receipt must match
  (`matches()`). Tried on a stand-in record (scratch, never committed): fingerprint and paths as announced. The same
  stand-in run showed the tests the pin step must bring along (guides, INSTALL-STATUS and pins of R27/version 4):
  `test_release28` (Release27SourceTest reads `release.json` as R27), `test_owner_walk` (update route, 2),
  `test_ways_back_probe` (version 2's bundle, the local walk's order, RehearsalWalkTest setup),
  `test_tools_local_wiring` (WalkTest setup), `test_owner_path` (4: the routine box, INSTALL-STATUS's 22c/22d row,
  windows/tools/update order, historical results), `test_owner_equality` (4: bootstrap block, generated lines quoted,
  typed commands), `test_ways_back_compatibility` (historical payload and unchanged history; version 2 reads; first
  switch over single stock), `test_owner_sources` (older recovery code at cuts, version 2 stick). Each is a pin or a
  guide quote to move, or a real compatibility question to answer before the pin; none was looked into yet.

## Step 6 preparation: announced payload stopped at compatibility (2026-11-20)

Codex gpt-6.2-sol ran `python3 -B reviews/42-release-28/payload.py announce` against the committed R28 record.
It printed `PASS announced files written; tools version 5 fingerprint df89ac336e13db84934505551ba28163cbd60fa5b3b9fb0ec97b9585945896c6`.
A read-only comparison found exactly the eight generated changes relative to `634e1237` across the bound paths.
Every generated file, including all of `docs/OWNER-TOOLS.md`, is byte-equal to `announced()`'s output. The two
earlier release history rows are intact and R28 is last. The payload stays in the worktree for review.

**(b) PLAN-GAP — tools version 5 refuses installation over an already-staged R27.** The contract in
`test_ways_back_compatibility.CompatibilityTest` includes `test_single_stock_prepared_and_first_switch_remain_accepted_and_updatable`
and `test_tools_update_runs_over_every_historical_resting_and_staged_shape`. Both exercise replacing the exact
version 2 tools while an R27 deployment is staged. The first-switch subtest raised `Unexpected staged switch`.
The historical-shapes test failed on both the first switch and the staged update over the R13/stock pair, the
latter with `Unexpected staged update`. The same fixture, replayed with the exact version 4 bundle from `634e1237`,
completed the tool replacement in both states. The exact version 5 bundle refused in both states with the fixture
installation, records and deployment state unchanged. Both bundles installed over the exact version 2 bundle
with R27 already booted beside R13 and stock. The compatibility assertions stand.

**(a) Pin and quote findings from inspection.** `test_release28`'s previous-source test needs the fixed R27
reference from the historical bundle or record. `test_owner_walk`'s update route, `test_ways_back_probe`'s bundle
and walks, and `test_tools_local_wiring`'s walk use R27-era inputs, with some reads still tied to the checkout's
current release, commands or tool bundle. `test_owner_path` and `test_owner_equality` need the current generated
guide quotes and fingerprint. INSTALL-STATUS must retain the laptop's recorded R27/version 4 evidence.
`test_ways_back_compatibility` also has stale literal destination-version and two-row history expectations.
The version 2 read cases and `test_owner_sources`' cut and stick cases contain literal version 4 expectations.
Their underlying read, journal and recovery guarantees still need their own passing runs. No pins, guides or
fixtures were edited after the blocker was reproduced.

**Verified locally.** The module command was `python3 -B -m unittest discover -s os/tests -p '<module>.py'`.
`pgrep -a -u ares -x ksshaskpass` printed nothing before each invocation. `test_release28` ran 94 tests with
one failure, the R27 source comparison against the new current manifest. `test_owner_walk` printed two failure
markers before it was interrupted when the staged-state comparison reproduced the blocker. The two named
`test_ways_back_compatibility` methods selected with `-k` ran in 1.983 s, with 14 subtest failures and one error.
Twelve failures were version-string assertions after successful installs. The remaining two failures and the
error were the staged-state refusals above. The isolated install comparison used the test harness as a library.
The remaining modules, rebind and host walk are pending. No commit, push or dispatch was made. `.work/` has no
file over 500 MB.

**What the code doesn't show.** The executable payload is unchanged, but `update_tools.system_ready()` calls
`qualified_state()` with the incoming bundle's target. That function requires a staged first switch or update to
match the target, so appending R28 changes which staged states pass readiness. B starts from a confirmed R27,
which is why even a successful R28 route would leave this compatibility property untested. The host receipt
still needs regeneration and the VM's `real_commit()` comparison still needs the actual committed payload.
The current `matches()` implementation checks the guide's two fingerprint lines. The worktree comparison above
also checked its full bytes. Run 44625380879 stopped before the VM route could qualify R28.

## Step 6 payload pins and verification (2026-11-20)

**(b) Known limit, per the lead.** Version 5 refuses to install while an older release is staged, leaves the installation, records and deployments unchanged, and can be installed after rebooting into the staged release.

**(a) Pins and quotes.** The local R27 walks use the fixed release record and the tool bundles from their original
commits (version 2 for the update and reorder probe, version 3 for ways back, and version 4 for tools-local).
The R28 walk reads the folder and routine lines from its announced stand-in, and the guide quotes match the
current `commands.json` byte for byte. The install guide names the R28 target, and both the install and emergency
guides carry the version 5 fingerprint. INSTALL-STATUS keeps the R27 and version 4 laptop evidence and marks the
R28 rehearsal and update pending. The older journal, stick, read and recovery tests still exercise their original
historical inputs. The two checkout-history expectations in `test_owner_update` require the R27 row to remain
between R13 and R28. The model's capture replay uses the recorded tools version 3 release target and history
while still exercising the checkout's owner code.

The compatibility tests accept both R28-staged deployment shapes and the prepared/resting shapes. The R27-staged
first switches (including single stock) and staged update require the exact refusal and compare the installation
snapshot (including every record and the entry symlink), both deployment views and the host mutation trace.

### Verified locally

`rebind.py pending '42 step 6: announced R28 and tools version 5 payload'` printed `pending: 37 bound files differ
from the active bindings, 0 removed`. `walk-host.py` printed `PASS package 42 host walk (release-28): 269 sources;
no VM started`. Its receipt records eight starts, 176 checks, 824 commands and 542 typed blocks with Control on.
The eight announced files match both their initial checksums and every byte returned by `announced()`.

Module command was `python3 -B -m unittest discover -s os/tests -p '<module>.py'`, one module at a time.
`pgrep -a -u ares -x ksshaskpass` printed nothing before each module. The model used `ARESOS_MODEL_SCOPE=slice`.

| Module | Result |
| --- | --- |
| `test_release28` | 94 OK in 37.541 s |
| `test_ways_back_compatibility` | 21 OK in 33.000 s |
| `test_owner_sources` | 13 OK in 52.765 s |
| `test_owner_path` | 48 OK in 1.172 s |
| `test_owner_equality` | 11 OK in 106.320 s |
| `test_ways_back_probe` | 57 OK in 155.246 s |
| `test_tools_local_wiring` | 42 OK in 58.020 s |
| `test_release28_rehearsal` | 44 OK in 35.558 s |
| `test_release28_control` | 15 OK in 4.223 s |
| `test_release27` | 41 OK in 6.730 s |
| `test_checkout_sources` | 8 OK in 1.126 s |
| `test_owner_step_limits` | 4 OK in 0.011 s |
| `test_release_squash_binding` | 7 OK in 0.056 s |
| `test_control_image` | 15 OK in 4.567 s |
| `test_owner_devices_native` | 14 OK in 1.790 s |
| `test_ways_back_model` | 26 OK in 175.524 s. Slice processed 120,000 states and discovered 173,130, covering 3,185,862 edges and all eight journal outcomes. |
| `test_owner_walk` | 34 OK in 407.528 s |
| `test_owner_update` | Library fixture only. `PASS owner-update fixture: exact R13/R27/R28 history, receipt, prior records and no deployment mutations`. |

The first host walk exposed a local `subprocess` binding error. The first owner-walk module reported six fixture
errors, and the focused reruns passed 1 update-route test (both subtests) and 4 installer tests after the fixes.
The first probe run reported three failures from a stale version 3 reader expectation and stale binding hashes
after that file was edited during the run. The first model run reported three historical capture failures because
it tried the R28 target in the recorded R27 session. The table gives the passing reruns after fixing those inputs
and refreshing the bindings. No new compatibility PLAN-GAP surfaced.

### What the code doesn't show

The host receipt covers the synthetic walk. The R28 VM rehearsal, the comparison against the actual committed
payload in `real_commit()` and physical qualification remain pending. The caller walk exercises the version 4
export line, and the guide equality check verifies the version 5 line and its updated label. The full
`test_owner_update` module and `test_owner_reset` remain for hosted checks, along with the two excluded modules
`test_inherited_homebrew` and `test_sysusers`. All work is in the worktree. HEAD remains `3ae3716a`, with no push
or dispatch. `.work/` has no file over 500 MB.

## Step 6: the stock rewind (2026-11-20, Claude Fable 5.2)

The pinned live ISO (`bd043223…`) installs Bazzite `49ded650…`; the laptop and the owner tools need
`ed93d215…` (`base.json`). The harness now gives the unmodified installer that image. Nothing is committed,
pushed or dispatched.

### PLAN-GAP 3: the installer's web pages are pinned to the previous ISO (stops rehearsal 4 before it installs)

Read this before dispatching. It is not part of the stock rewind, and the rewind does not fix it.

- `installer_webui.Pages.completion_source()` requires the served `index.js` and `index.js.map` to equal
  `UI_BUNDLE_SHA256` (`9e456995…`) and `UI_SOURCE_MAP_SHA256` (`de301b46…`). Those are the previous ISO's installer
  (the same map hash is in `os/manifest/ci/11n/b-1/installer/webui-source-map.json`, ISO `776b76f3…`).
- The new ISO's map is `9c3f8f28461619452bc89d966fcc944bd8ef9a39d4cc073275faccd6388b8e24` (run 44644689353,
  `installer/webui-source-map.json`). So every two-disk mode stops with "Served installer bundle changed" in the first
  live session, at the latest after the review page and before anything is installed. Rehearsal 3 stopped at minute 3, before it
  got there. The ISO pin commit (`3ae3716a`) says the rehearsal's own inspection and installation requalify the web
  route; for the pinned pages they stop instead.
- What the new sources show (checked against the run's `installer/webui-source/`): `completion_selectors()` returns
  the same four selectors; the ids the driver clicks are built from the same pieces in the same files (destination,
  keyboard dialog, time zone, accounts, encryption, review). 69 of 102 source files changed, 20 are new, 2 are gone.
  `liveinst` is unchanged; `webui-desktop`, `cockpit-coproc-wrapper.sh` and `webui-cockpit-ws.service` changed but
  still serve on `127.0.0.1:80` with the same Firefox profile path.
- What is missing: the served bundle's hash (the evidence never held it; a failing run does not write it either) and
  a run through the new pages. I did not move the pins: that qualifies a new installer, which needs a run and is the
  lead's call. The inspection now records `bundle_sha256` beside `source_map_sha256` (evidence only), so any run
  that gets through the inspection step gives both values, also an inspection-only run (`rehearsal=inspect`, about
  10 minutes, no VM; this branch's job condition admits only `release-28`, so it needs another branch).
- Advice: get the bundle hash from an inspection, move the two pins in a small step, then a `probe` run if the caps
  and branches allow one (live session through the review page, no installation). The probe also runs the whole
  stock rewind up to the proof of the image, and the stock CLI probe on it. Only then rehearsal 4.
- Not checkable from the evidence, same risk: `require_supported_live_kickstart` needs the new anaconda's `--help`
  to still say a live kickstart is unsupported; `keyboard_proof` runs against anaconda's localization code, where
  `installation.py` and `localed.py` changed (the hashes are read from each run's own inspection, so no pin stops it).
- Another way out, if it exists: the owner's installer stick. If it still holds the previous ISO byte for byte
  (`776b76f3…`), a copy kept as a private file would bring the laptop's real installer back, and neither this
  gap nor the stock rewind would be needed. Only the owner can check that.

**Closed by the lead (2026-11-20, Claude Opus 5.5).** The bundle hash comes from the pinned ISO itself, not a run:
the public ISO downloaded to the laptop's `/var/tmp` matched `bd043223…` (9088845824 bytes); `unsquashfs -cat` of
`LiveOS/squashfs.img` gave `usr/share/cockpit/anaconda-webui/index.js.gz`, unpacked as a browser receives it,
`fffb3a05621db05f3419230e7b8b0c3c82c8253f1d35da1a49d3ca66954a0fdb` (895148 bytes), and `index.js.map`
`9c3f8f28…`, the value run 44644689353's inspection recorded, so the method matches CI's. The previous pages were
served unpacked too (913874 bytes in `os/manifest/ci/11g/probe-2/two-disk/completion-selector-source.json`). Both
pins moved in `os/ci/installer_webui.py`; a mismatch now prints the served hash. No `probe` run first: this branch
admits only `release-28`, and a stop at the web pages comes in the first live session, minutes into rehearsal 4,
so the probe would save little. Rehearsal 4 is the run through the new pages; the two unpinned risks above
(`require_supported_live_kickstart`, `keyboard_proof`) stop it there too, just as early. The owner's installer
stick is not pursued: a 9 GB private copy needs hosting, and nothing waits on a fresh install.

### The design: (a), the live session's store holds the base image before the installer starts

The new ISO is a different Bazzite generation: its live root is `45.20261117.1` (Fedora 45, kernel
`7.3.4-300.fc45`), the base image is `44.20261012.1` (Fedora 44). That decides it:

- With **(b)** or **(c)** the installer first installs 45, and everything it writes around the image stays from 45:
  the boot loader on the EFI partition (the walk drives GRUB's menu, and the stock probe pins stock's
  `grub2 2.12-66.fc44`), and `/etc`, merged from 45 down onto 44. (c) adds 45's first boot and its services.
  A rehearsal on that system could pass or fail where the laptop would not.
- With **(a)** the unmodified installer does every step on the base image, as the laptop's installation did, and
  its own `%post` (`bootc switch --mutate-in-place … --transport registry …:stable`) sets the laptop's origin. The
  first boot of the target is stock `ed93d215…`'s first boot.

How it runs (`os/ci/stock_image.py`, called from `two_disk_vm.py`):

1. **Host, before each live boot** (`stock_share`): at least 24 GiB free, then
   `skopeo copy --src-no-creds --preserve-digests --retry-times 3 docker://ghcr.io/ublue-os/bazzite-nvidia-open@sha256:ed93d215… oci:.work/installer/stock-share/image:stock`.
   `verify()` then checks, in Python, that the layout holds exactly that one manifest, that its bytes hash to the
   digest in `base.json`, and that every blob has the size and the SHA-256 the manifest names, with no blob missing or
   extra. No tag is ever used for the fetch. An empty 32 GiB sparse file `store.raw` is put beside it.
2. **QEMU, live boots only:** the directory is a virtio-9p share (`mount_tag=aresos-stock`, PCI slot 8). No
   installed boot gets it (`stock_args`, tested for both Guest classes).
3. **Live session, first thing in `live_inventory`** (`substitute_stock`), each a command with its own evidence:
   - `-stock-embedded`: the ISO's own image, read from its store's `images.json` before any container tool opens the
     store. It must be exactly `ghcr.io/ublue-os/bazzite-nvidia-open:stable` at `49ded650…`, the new `embedded_stock`
     record of the live ISO in `installer-isos.json`. Anything else stops: that is another ISO to qualify. The
     inspection step checks the same record from the squashfs, before any VM.
   - `-stock-share`: mount the share at `/run/aresos-stock`.
   - `-stock-store`: `mkfs.ext4` on `store.raw` and loop-mount it over `/var/lib/containers/storage`.
   - `-stock-copy`: the ISO's own `skopeo --insecure-policy copy oci:/run/aresos-stock/image:stock
     containers-storage:ghcr.io/ublue-os/bazzite-nvidia-open:stable`.
4. **The check that was failing, unchanged:** `podman image inspect …:stable` must print `ed93d215…` (`-payload`).
   The printed digest goes into `stock-rewind.json`; then the host deletes the fetched layout.
5. **The installer runs as before.** After it finishes the store and the share are unmounted (`-stock-release`,
   a lazy unmount is recorded, never a stop), and after the live session is closed the host deletes the share.
6. **First stock boot** (`offline-first-stock`, from the snapshot the route already takes; no new guest command):
   `stock_rewind_booted` requires no transaction, nothing staged, pinned or queued; one or two deployments, all the
   same commit with digest `ed93d215…`; origin exactly
   `ostree-image-signed:docker://ghcr.io/ublue-os/bazzite-nvidia-open:stable`. It completes `stock-rewind.json`.

### Facts it was checked against

- **Memory:** the VM has 6144 MB and the live root is a RAM overlay; the image is 5,634,826,157 bytes in 128 gzip
  layers (`skopeo inspect --raw`, whose bytes hash to `ed93d215…`) and 12.5 GB in 284,000 files unpacked (the
  laptop's own stock deployment, read only). So the store cannot be in the live root; it is a file on the runner.
- **Every command exists on this ISO** (`installer/squashfs-files.txt` of run 44644689353): `mkfs.ext4`, `mount`,
  `losetup`, `lsblk`, `findmnt`, `df`, `skopeo`, `podman`, `python3`; `fs/9p/9p.ko`, `net/9p/9pnet_virtio.ko` and
  `drivers/block/loop.ko` for `7.3.4-300.fc45.x86_64`, the kernel that run's console shows booted.
- **QEMU:** the runner has 8.2.2 (`rehearsal-host-packages.txt`). `-fsdev local` with `virtio-9p-pci` is what
  `two_disk_vm.Guest` has used for the credential share since package 11, with the same mount options.
- **No disk for anyone:** OVMF has no 9p driver, so no firmware boot option appears (the audit only requires that
  options name attached devices). The store is a loop device like `loop0`, the live image, which the installer
  never offered. `disk_names` ignores it (tested on rehearsal 3's `lsblk` plus the loop row), the pages are driven
  by disk id, and the review fails closed on any disk but the target.
- **The origin and the commit:** the ISO's kickstart and `%post` are those of the previous ISO (the kickstart
  differs by one blank line). A real first stock boot after the previous ISO (`os/tests/fixtures/keyboard/stock-two-*.json`)
  has two serials of commit `aa669eff…` with exactly this origin, the laptop has the same, and the switch runs on a
  built disk recorded the same commit (`os/manifest/ci/06e/full-1/switch/result.json`). The new check is tested on
  that capture.
- **The console:** the live shell puts an OSC 3008 sequence directly before a command's first output (rehearsal
  3's `-payload.txt`), so the digest is parsed without line anchors.

### Requirements 6 to 8

- **Other users of the ISO's cached stock:** `stock_recipe_probe` and `stock_probe.py` run only in the `probe` modes
  (`two_disk_vm.py probe`, `owner_vm.py probe`: packages 11c, 13, 14, 16), never in 22c, 22d, 27 or 42. They read
  `/var/lib/containers/storage` after `live_inventory`, so they now see the base image and their pins (the base
  digest, `ostree 2026.4-1.fc44`, `grub2-common 2.12-66.fc44`, `rpm-ostree 2026.3`, `uupd 1.5.0`) stay true as
  written. `stock_probe.py` is unchanged. `keyboard_vm.py` installs through `td.install` and is covered the same way.
- **Time:** fetch 1 to 3 minutes, check under 1, copy into the store an estimated 4 to 10, release under 1: about
  8 to 15 minutes more in the 315-minute step. I left the timeouts alone. No release-28 walk has run through, so its
  length is unknown (22c's whole job took 216 minutes, 22d's 130); the job cap of 360 leaves at most 15 more.
- **Disk:** about 21 GB more for the minutes of the copy (the fetched layout and the store), about 15 GB more
  while the installer runs (the store alone), nothing after the live session. The host stops before the VM with less
  than 24 GiB free (the store beside the first installation of about 10 GB). The inspection now deletes its extracted
  `squashfs.img` (8.7 GB, read by nothing else), so the run's later peak is lower than before. The sparse files
  (target 49 GiB, store 32 GiB) only take what is written. The evidence grows by a few small files (bound 180 MB).
- **The guide:** `docs/INSTALL-REFERENCE.md` no longer lists an ISO to download. One STOP line says the installer
  is no longer published and a fresh install waits for a checked one. `installer-isos.json` keeps the harness's
  record. No test bound the removed row itself: `test_owner_equality` only requires every hash on an owner page to
  be a manifest pin, and the page now has one hash fewer.

### Known limits

1. ~~Rehearsal 4 stops at the web pages until PLAN-GAP 3 is closed.~~ Closed by the lead (pins moved, see PLAN-GAP 3).
2. A loop file on a 9p share is new in this harness and no run has shown it. If it fails, the run stops in
   `-stock-store` or `-stock-copy`, minutes into the first live session, with the command's output in the evidence.
3. The installer is Fedora 45's anaconda installing a Fedora 44 image. Upstream never shipped that pair; the laptop
   was installed by 44's. Any design has this, since the old ISO is gone.
4. The flatpaks and the files the installer itself writes come from the new ISO.
5. The image in the store carries no signature (the ISO's own had one). The installer does not check it
   (`--no-signature-verification`); the digest is the proof.
6. `stock_commit.equal` (the booted commit against `aa669eff…`) is recorded and printed, not required: a newer
   importer may write other metadata around the same files.
7. `stock-rewind.json` is completed in the owner's route only. `part-b` and the keyboard rehearsal get the
   substitution and the payload check, and keep their own first-boot checks.
8. Each live boot fetches again (the two-order probe twice).

### What rehearsal 4 must show

- `installer/embedded-stock.json` and `two-disk/protected-second-install-stock-embedded.json`: `49ded650…`.
- `two-disk/stock-image-host.json`: `digest` `ed93d215…`, 128 layers, `credentials` `none`.
- `…-stock-store.txt`: an ext4 on a loop device at `/var/lib/containers/storage`; `…-stock-copy.txt`: 128 layers
  copied and about 13 GB used; `…-payload.txt`: `sha256:ed93d215…`.
- `boot-2-devices.json`: `stock-image-device` at `pci:00:08.0`; no later boot has it.
- The installation completes, `…-stock-release.json` (`lazy` should be false), and the audits after the live session pass.
- `two-disk/stock-rewind.json`: `status` `passed`, `booted.digest` `ed93d215…`, `booted.origin` the laptop's,
  one or two deployments of one commit, and `stock_commit.equal` true. If it is false, compare before trusting a pass.
- `offline-first-stock-link`: every interface without carrier, as before.

### Verified locally

`rebind.py pending '42 step 6: the stock rewind (the live session installs the base image; the guide stops at
the ISO line)'` printed `pending: 38 bound files differ from the active bindings, 0 removed`. `walk-host.py`
printed `PASS package 42 host walk (release-28): 270 sources; no VM started` (`os/ci/stock_image.py` is the new
source). Modules ran one at a time with `python3 -B -m unittest discover -s os/tests -p '<module>.py'`;
`pgrep -a -u ares -x ksshaskpass` printed nothing before each; the model ran with `ARESOS_MODEL_SCOPE=slice`.

| Module | Result |
| --- | --- |
| `test_stock_image` | 27 OK in 0.099 s |
| `test_two_disk_vm` | 29 OK in 0.190 s |
| `test_keyboard_vm` | 5 OK in 0.007 s |
| `test_keyboard_walk` | 3 OK in 1.364 s |
| `test_rehearsal_auth` | 9 OK in 0.078 s |
| `test_installer_download` | 12 OK in 0.311 s |
| `test_installer_webui` | 9 OK in 0.008 s |
| `test_stock_probe` | 3 OK in 0.001 s |
| `test_checkout_sources` | 8 OK in 1.080 s |
| `test_owner_path` | 48 OK in 1.172 s |
| `test_owner_entry` | 3 OK in 0.365 s |
| `test_release28` | 94 OK in 25.003 s |
| `test_release28_rehearsal` | 44 OK in 34.379 s |
| `test_release28_control` | 15 OK in 4.726 s |
| `test_owner_walk` | 34 OK in 401.459 s |
| `test_ways_back_probe` | 57 OK in 149.359 s |
| `test_tools_local_wiring` | 42 OK in 54.648 s |
| `test_owner_equality` | 11 OK in 100.062 s |
| `test_owner_sources` | 13 OK in 140.376 s |
| `test_control_image` | 15 OK in 4.691 s |
| `test_owner_devices_native` | 14 OK in 1.987 s |
| `test_release27` | 41 OK in 6.459 s |
| `test_release_squash_binding` | 7 OK in 0.055 s |
| `test_ways_back_compatibility` | 21 OK in 67.618 s |
| `test_ways_back_model` | 26 OK in 175.050 s. Slice processed 120,000 states and discovered 173,130, covering 3,185,862 edges and all eight journal outcomes. |
| `test_build_tools` | 3 OK in 0.112 s |
| `test_ci_api_permissions` | 4 OK in 3.076 s |
| `test_grub_bls` | 6 OK in 0.308 s |
| `test_owner_console` | 15 OK in 1.247 s |
| `test_loop_nodes` | 7 OK in 0.255 s |
| `test_owner_hidden` | 11 OK in 6.216 s |
| `test_owner_login` | 18 OK in 1.442 s |
| `test_owner_layout_adapter` | 5 OK in 0.016 s |
| `test_owner_reliable_typing` | 15 OK in 2.199 s |
| `test_keyboard_proof` | 5 OK in 0.028 s |
| `test_owner_read_diagnostics` | 6 OK in 0.161 s |
| `test_owner_guard` | 12 OK in 0.057 s |
| `test_ci_step_environment` | 4 OK in 12.847 s |
| `test_probe_native` | 4 OK in 0.002 s |
| `test_serial_staging` | 19 OK in 32.991 s |
| `test_owner_capabilities` | 6 OK in 0.166 s |
| `test_owner_counter_flush` | 7 OK in 0.046 s |
| `test_owner_diagnostics` | 9 of 10 pass in 0.954 s; 1 error, the same on the committed tree (below) |
| `test_owner_key_counter` | 11 OK in 1.803 s |
| `test_owner_ps2` | 18 OK in 0.498 s |
| `test_owner_staged_release` | 7 OK in 0.045 s |
| `test_aresos_desktop` | 189 OK in 169.154 s (1 skipped) |
| `test_owner_session` | 16 OK in 0.247 s |
| `test_rehearsal_budget` | 4 OK in 0.035 s |
| `test_owner_sudo_idle` | 13 OK in 0.041 s |

`test_owner_diagnostics` has one error, `test_last_install_step_failure_has_no_premature_success_record`
(`owner.Stop: Unsafe private setup directory: uninstalled`). It is not from this step: the same module on an
extracted copy of the committed tree (`git archive` of `f787ab0b`) gives the same single error, and neither the
test nor `owner.py` is changed here. My reading of the cause, not checked on another Python: the laptop's Python
3.14.8 has `Path.lstat` call `os.lstat` directly, so the test's stand-in on `Path.stat` (`private_metadata`) no
longer reaches `owned_directory`. That is the class AGENTS.md names ("test code against Python 3.14"); the hosted
checks-only run decides.

A first batch was stopped during `test_owner_walk` for one more edit (the evidence lines of the live session's
commands now end in `|| true`, so only the checks can stop a run). Its temp folder under `os/tests` was removed.
The table is the full rerun on the final code, after the bindings and the walk above.

### What the code doesn't show

- Nothing here ran in a VM. The live session's commands were checked for syntax and content, and against the ISO's
  file list; the host's fetch ran only as `skopeo inspect --raw` of the manifest.
- `walk-host.py` now binds `os/ci/stock_image.py`. The walk's stand-in for the installation writes the live
  session's record, and its first stock boot (the real two-serial capture) goes through the new check.
- `test_keyboard_vm` patches the host's share away: it is about the keyboard fixture, and the share has its own tests.
- Branches 22c, 22d and 27 get the rewind when they merge this one; none of them can install until then.
- `.work/` has no file over 500 MB.

### Fix 1 (cross-review, Codex gpt-6.2-sol)

1. **Live-session scratch and runner space.** The guest copy creates a private directory on the 9p share and passes it
   to Skopeo as both `--tmpdir` and `TMPDIR`. It removes the directory on success or failure. Using the share gives the
   blocks directly back to the runner. The host also discards an incomplete share if the fetch or guest fails.
   The installer still runs its own kickstart and post-scripts. The live store now backs a bind mount at `/var/tmp` until
   installation ends. The image proxy can write a temporary layer export there even without `TMPDIR`. Ext4 provides the
   permissions and file operations the importer expects. The harness checks the bind and the effective overlay store
   before the copy, and removes the bind before releasing the store.

   The inspector evidence from run 44644689353 lists the rootful vendor `storage.conf` files under
   `usr/share/containers`, with no `etc/containers/storage.conf` override. The ISO's overlay image index is on the graph
   root. The packaged Fedora rootful drop-in has the same byte length as the listed file. Its additional image
   store is a read-only lookup under `/usr/lib/containers/storage`. The overlay run root in `/run` held runtime
   metadata. The new command requires graph root
   `/var/lib/containers/storage`, run root `/run/containers/storage` and driver `overlay`. Layer unpacking and staging use
   the loop-backed graph root. The kickstart uses `ostreecontainer --transport=containers-storage` and its target-side
   post-script sets the signed registry origin in place. The source lists and launcher show small live `/tmp` logs and
   UI state. The upstream Anaconda deploy path puts the OSTree repository and its import staging on the target.
   Containers/image defaults large file scratch to `/var/tmp` and can reconstruct a layer there when reading the store.
   That is also the default `image_copy_tmp_dir` in containers.conf. The bind covers those defaults without relying
   on the installer's launcher to preserve a shell variable.
   [ISO inspection](https://github.com/Ares-Empire/AresOS/actions/runs/44644689353)
   [Anaconda deploy task](https://github.com/rhinstaller/anaconda/blob/main/pyanaconda/modules/payloads/payload/rpm_ostree/installation.py)
   [Containers/image temporary directory](https://github.com/containers/image/blob/main/internal/tmpdir/tmpdir.go)
   [Store source](https://github.com/containers/image/blob/main/storage/storage_src.go)
   [Store destination](https://github.com/containers/image/blob/main/storage/storage_dest.go)
   [Overlay staging](https://github.com/containers/storage/blob/main/drivers/overlay/overlay.go)
   [Packaged rootful drop-in](https://sources.debian.org/src/golang-github-containers-common/0.69.1-1/rpm/00-storage-rootful.conf/)
   [Containers configuration](https://github.com/containers/common/blob/main/docs/containers.conf.5.md)
   [OSTree importer](https://github.com/bootc-dev/bootc/blob/main/crates/ostree-ext/src/container/store.rs)

   At the copy peak, the verified layout and temporary blobs are about 5.25 GiB each, alongside up to 32 GiB in
   `store.raw` including unpacked layers and staging. That is about 42.5 GiB of new allocation. Both blob copies are
   gone before Anaconda starts. At the install peak, the full store and the full 49 GiB target would use 81 GiB
   together. The protected 50 GiB disk had 79,470,592 bytes allocated (0.074 GiB) and the target had zero allocated
   in rehearsal 3's live-boot QMP evidence. If a live boot already has a full target, the copy peak includes that
   49 GiB of existing allocation and reaches 91.5 GiB across the target, store and blob copies.

   The runner logs show 124 GiB free on the root filesystem after cleanup in 44644689353, 43737933979 and
   43597505549. The retained ISO used 9,088,851,968 allocated bytes (8.47 GiB). Inspection removes its extracted
   squashfs before the VM step. The private preflight image layout has also been removed. Allow 4 GiB for further
   host allocations, including tools and browsers, evidence, extracted boot kernel and initrd, firmware and the
   128 MiB tools stick. This puts the
   R28 install peak at about 94 GiB of growth after runner cleanup, or about 104 GiB for a copy beside a full target.
   With the ISO and protected disk counted and that allowance set aside, estimated free space before the first
   stock fetch is about 111 GiB. `FREE_BYTES` is 88 GiB (94,489,280,512 bytes), giving 7 GiB beyond the maximum
   new store-plus-target growth. The guard reads the actual filesystem before fetching and records that reading.
   [R28 rehearsal 3](https://github.com/Ares-Empire/AresOS/actions/runs/44644689353)
   [22d complete walk](https://github.com/Ares-Empire/AresOS/actions/runs/43737933979)
   [22c complete walk](https://github.com/Ares-Empire/AresOS/actions/runs/43597505549)

   **PLAN-GAP 4 — historical disk samples.** The earlier logs have a rounded post-cleanup `df -h` reading.
   They have no host sample at first live boot or the peak. The later free space and peaks above are estimates
   using the logged reading, allocated disk bytes and file size bounds. Rehearsal 4 must show the exact free-byte
   gate and the guest store usage, and prove the live 9p copy, loop store, installer and cleanup.

2. **First stock boot.** The receipt joins the bootc booted and rollback slots to the rpm-ostree rows by checksum,
   serial and stateroot, and checks the reference, digest and pin. A missing or extra rollback slot stops the receipt.
   The retained fixture with just bootc's booted checksum changed now fails. If both views agree on a different
   historical commit, `stock_commit.equal` is still false and recorded. Compare the imported tree before trusting
   that result for the laptop.

3. **Time.** The release-28 pre-step times were 37m00s in 44644689353 and 37m03s in 44625380879. Run 44612480026
   stopped at ISO inspection at 32m50s before reaching the VM step. The complete VM steps took 91m12s for 22d
   (43737933979, with 36m10s before it) and 186m46s for 22c (43597505549, with 28m40s before it).
   The R28 job and both guard reservations stay at the approved ledger bound of 345 minutes, below the hosted
   360-minute maximum. The R28 VM step gets 225 minutes, leaving 110 for setup and preflight and 10 for cleanup
   and upload. The five explicitly timed preflight steps total at most 107 minutes. Other preflight steps took
   at most 154 seconds across these R28 logs. Cleanup and upload in the complete walks took 8 and 13 seconds.
   R28's route makes one live install. Allowing 15 minutes for each of two rewinds, including fetch, verification,
   store copy and release, takes the 91m12s route to about 121 minutes or the longer 186m46s comparison to about
   217 minutes. These are estimates. The VM step limit still allows for the route's extra R28 boots and checks.
   [Hosted job time limit](https://docs.github.com/en/actions/reference/limits)
   [R28 rehearsal 1](https://github.com/Ares-Empire/AresOS/actions/runs/44612480026)
   [R28 rehearsal 2](https://github.com/Ares-Empire/AresOS/actions/runs/44625380879)
   [R28 rehearsal 3](https://github.com/Ares-Empire/AresOS/actions/runs/44644689353)

   **Lead, 2026-11-20: the VM step gets 290, not 225.** 225 leaves about 8 minutes over the 217-minute estimate,
   and a walk cut by its step limit costs the last rehearsal. Preflight measured 37 minutes in both R28 runs
   that reached the VM step; the 107-minute worst case of its own step limits is not what happens. So: 45 for setup
   and preflight, 290 for the VM step, 10 for cleanup and upload, inside the unchanged 345. If a preflight ever runs
   past 45 minutes, the job limit can cut the step's last minutes and the upload: a known limit, cheaper than a
   walk stopped short.

   The same arithmetic exposes the old limits. At its observed pre-step time, 22d's 315-minute step would reach
   about minute 351 against its 345-minute job. 22c would have about 1m20s after its step cap. Their limits stay
   as recorded for their own branches.

4. **Inherited sources.** Package 27's host walk now binds `os/ci/stock_image.py`. Packages 27, 22c and 22d
   regenerate their receipts on their own merge heads.

5. **Fresh-install hold.** The owner's guide stops at the Stage C notice, installer download, reinstall path
   and erase. The emergency card and media reference carry the same hold. The live ISO manifest record has
   `rehearsal_only: true`. Tests check that the owner pages offer none of that record's download identifiers
   and put the hold before writing or erasing. The generic hash check establishes where each printed hash came from.

6. **Probe labels.** The updater inventory and two real pause calls are saved under Fedora 45 live-session
   evidence. The cached CLI probe still records its separate check of the Fedora 44 stock image.

#### Verification

`python3 -B reviews/27-first-update-release/rebind.py pending "42 step 6 fix 1: the cross-review's six findings"`
printed `pending: 39 bound files differ from the active bindings, 0 removed`.
`python3 -B reviews/42-release-28/walk-host.py` printed `PASS package 42 host walk (release-28): 270 sources; no VM started`.
Every hash in the refreshed receipt matched its worktree file. The 22c, 22d and 27 receipts were left for their merge heads.

`python3 -B -m unittest discover -s os/tests -p '<module>.py'` ran one module at a time.
`pgrep -a -u ares -x ksshaskpass` printed nothing before each invocation. The model used `ARESOS_MODEL_SCOPE=slice`.

| Module | Tests | Time | Result |
| --- | ---: | ---: | --- |
| `test_aresos_desktop` | 189 | 166.860 s | OK, 1 skipped |
| `test_build_tools` | 3 | 0.108 s | OK |
| `test_checkout_sources` | 8 | 1.070 s | OK |
| `test_ci_api_permissions` | 4 | 3.000 s | OK |
| `test_ci_step_environment` | 4 | 12.779 s | OK |
| `test_grub_bls` | 6 | 0.308 s | OK |
| `test_installer_webui` | 9 | 0.002 s | OK |
| `test_keyboard_proof` | 5 | 0.033 s | OK |
| `test_keyboard_vm` | 5 | 0.010 s | OK |
| `test_owner_bootstrap` | 13 | 1.271 s | OK |
| `test_owner_capabilities` | 6 | 0.168 s | OK |
| `test_owner_devices_native` | 14 | 1.756 s | OK |
| `test_owner_entry` | 3 | 0.332 s | OK |
| `test_owner_equality` | 12 | 104.514 s | OK |
| `test_owner_guard` | 12 | 0.058 s | OK |
| `test_owner_login` | 18 | 1.414 s | OK |
| `test_owner_path` | 48 | 1.153 s | OK |
| `test_owner_session` | 16 | 0.305 s | OK |
| `test_owner_sources` | 13 | 49.734 s | OK |
| `test_owner_staged_release` | 7 | 0.046 s | OK |
| `test_owner_walk` | 34 | 403.653 s | OK |
| `test_probe_native` | 4 | 0.002 s | OK |
| `test_rehearsal_auth` | 9 | 0.077 s | OK |
| `test_rehearsal_budget` | 4 | 0.034 s | OK |
| `test_release27` | 41 | 6.870 s | OK |
| `test_release28` | 94 | 24.873 s | OK |
| `test_release28_control` | 15 | 4.130 s | OK |
| `test_release28_rehearsal` | 44 | 34.859 s | OK |
| `test_release_squash_binding` | 7 | 0.055 s | OK |
| `test_stock_image` | 29 | 0.121 s | OK |
| `test_stock_prepare` | 7 | 0.032 s | OK |
| `test_system_keyboard` | 7 | 0.011 s | OK |
| `test_tools_local_wiring` | 42 | 57.317 s | OK |
| `test_ways_back_model` | 26 | 171.200 s | OK |
| `test_ways_back_probe` | 57 | 153.401 s | OK |

35 modules ran 815 tests, with 814 passing and 1 skipped. The model slice processed 120,000
states, discovered 173,130, covered 3,185,862 edges and reached all eight journal outcomes.
The first stock-image run reported two failures because the new shell stand-in wrote a marker to a
file without printing it. The corrected stand-in passed on success and failure and checked scratch removal
in both cases. The table records the rerun.

The grep hit in `test_owner_update` is a workflow identity string. The module does not read the workflow file and
the laptop rules exclude running it. The laptop's exclusions for `test_inherited_homebrew` and `test_sysusers`
also applied. `git diff --check` passed. No file over 500 MB was found in `.work/`.

**PLAN-GAP 5 — local commit blocked.** Git returned `Read-only file system` when staging tried to create the
worktree's index lock. The edits and receipt are in the worktree at `e54b4d2f`. No commit, push or dispatch was made.
The live installer and the package 42 route still need hosted rehearsal 4.

### Final review fixes (Codex gpt-6.2-sol)

Rehearsal 4's input is `c1dba9f9d739fdfec3a99a87d47b34a91009e6ca`. These are local
worktree edits. The release 28 image record, payload, tools and VM route were left at their rehearsed bytes.

1. **Finding 2, Terminal after restart.** On release 28 the owner opens the **Terminal** app before going
   to tty3 and keeps it open until the PASS lines of `at check`. The guide and card cover update, forward
   and failed-update checks. The same requirement is in the layout, boot-menu and diagnostic procedures.
   Tools-only checks on release 28 need it too. `previous` returns to release 27's desktop. The Minecraft
   home files are there again when the owner returns to release 28. The tool checks for the desktop
   `foot` process, and the VM's SETUP terminal supplies it.
2. **Finding 3, export without the stick.** The routine and staged update boxes show the exact stick
   and local-copy result lines. The staged box requires both PASS lines and the result for the owner's
   route. It tells him to save the provisional title off the laptop before restarting. The local copy
   in `/run/ares-records` disappears on restart.
3. **Finding 1, save before restart.** The released AresOS Esc menu has no **Save and Quit** and does not
   pause the game. A window that covers the home can trigger Minecraft's save on pause, but the mod
   hides the corner saving text. The visible path is a normal close. The shipped labwc binding maps
   **Alt+F4** to **Close**. Inspection with `javap -c -p` of the local Minecraft 26.2 jars showed
   `Minecraft.runTick` handling `Window.shouldClose` with `stop`. After `run` returns, the client
   calls `exitWorldAndClose`, then waits for the integrated server thread to exit. The server's
   `stopServer` saves players and calls `saveAllChunks` with flush before closing the levels. The
   shipped supervisor waits for a normal JVM exit, then opens recovery with **Minecraft was closed.
   Nothing is wrong.** The guide makes that visible result the prerequisite to rebooting out of the
   release 28 home. It covers the update's reboot, previous, forward, rollback and failed-update
   restarts. The stock rollback and layout procedures link to the same step.
4. **Install hold.** Both Stage C status cells use **STOP for a fresh install or reinstall.** The dates
   and results for the checked installer stay in the history. The signed update on an existing
   installation has its own row. Its release 28 rehearsal and laptop update are still pending in this edit.
5. **Finding 4, rehearsal record.** Package 42 takes precedence once its `source-bindings.json` exists.
   The test exercises the record step with a fixture, verifies the exact tables became active, and checks
   that a subsequent edit becomes pending. The live receipt test reads the qualified host receipt from
   Git even after the current host walk is refreshed. The real record step is still for the lead.
6. **Finding 5, historical tests.** The image source tests compare the fixed main cut `fba94b25` to the
   published source `7d5fbbf2`. They use the published build inputs to check source coverage. The release
   gate still checks the live release branch against its merge base.
7. **Finding 7, checks accounting.** Package 42 charges 60 minutes for an untimed checks job, matching the
   regressions job's limit. The tests tie the limits together and exercise the fallback charge. The
   rehearsal preflight already has 50 minutes at `c1dba9f9`. The four rehearsals and the 345-minute
   rehearsal job limit stay as recorded.
8. **Finding 6, known limit.** Packages 22c, 22d and 27 have no open PRs. Their rehearsal modes run only
   on their own package branches. After this merge, a branch based on the merged code reads release 28
   by default. Before rerunning an older mode, bind its preflight, target, bundles and expected versions
   to its own release history, then refresh its host receipt. Updating the receipt alone cannot fix
   the R13/R27 assertions in `os/ci/owner_vm.py`.

**PLAN-GAP — save acknowledgement in the shipped session.** The manual close is traceable in the
released sources and Minecraft bytecode. The recovery message reports a normal game exit. Rehearsal 4
uses a planted, idle world and does not exercise a live edit followed by **Alt+F4**. I did not exercise
it on the owner's desktop. Release 28's `at reboot` requests a reboot directly and its supervisor
receives the stop signal without asking the game to save. If the normal-close message does not appear,
the restart steps send the owner to Help. A later released image needs a save acknowledged before the
session stops. Main has package 25's guardian work. That code is outside the release 28 image.

#### Lead's record after rehearsal 4 passes

Accept the hosted evidence first. Read the stock rewind, protected-disk and firmware audits, same-head
native/model gates, private pull and auth cleanup, the no-terminal STOP, the home hashes, Control and the
release 28 rehearsal result listed above. The result and binding tables must both name the actual run
head below. Keep the published release record and the existing tools fingerprint.

Run this from the package worktree with the final review fixes present. Set `run` to the accepted
rehearsal's numeric run ID. The archive in `.work/` extracts only the files needed for the record.
The fixed selector runs from the current checkout, and rebind reads the qualified files and waiting
list from the archive.

```bash
set -euo pipefail
run=REPLACE_WITH_PASSING_RUN_ID
qualified=c1dba9f9d739fdfec3a99a87d47b34a91009e6ca
test "$(gh run view "$run" --repo Ares-Empire/AresOS --json status,conclusion,headSha,headBranch \
  --jq '[.status,.conclusion,.headSha,.headBranch] | join(" ")')" = "completed success $qualified pkg/42-release-28"
mkdir -p .work
record_work=$(mktemp -d .work/42-record.XXXXXX)
gh run download "$run" --repo Ares-Empire/AresOS --name two-disk-evidence --dir "$record_work/evidence"
python3 -B - "$record_work" "$qualified" "$run" <<'PY'
import json
from pathlib import Path
import runpy
import subprocess
import sys

scratch, commit, run = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
evidence = scratch / 'evidence/two-disk'
result = json.loads((evidence / 'release-28-rehearsal-result.json').read_bytes())
bindings = evidence / '42-bound-sources.json'
bound = json.loads(bindings.read_bytes())
released = json.loads(subprocess.check_output(['git', 'show', f'{commit}:os/manifest/releases/28.json']))
assert result['status'] == 'passed' and result['qualified'] is True and result['real_commit']['equal'] is True
assert result['commit'] == bound['commit'] == commit and bound['package'] == '42'
assert result['release_28'] == released['reference'] and result['tools_version'] == 5
assert result['tools'] == 'df89ac336e13db84934505551ba28163cbd60fa5b3b9fb0ec97b9585945896c6'

sys.path.insert(0, str(Path('os/ci').resolve()))
import checkout_sources as checkout

prior_path = 'os/manifest/ci/22d/source-bindings.json'
walk_path = 'os/manifest/ci/42/host-walk.json'
pending_path = 'os/manifest/ci/16/pending-rebind.json'
record_path = 'os/manifest/ci/42/source-bindings.json'
prior = json.loads(subprocess.check_output(['git', 'show', f'{commit}:{prior_path}']))
tables = [(table['name'], table['sources']) for table in bound['tables']]
union = checkout.merge(tables)
paths = {row['path'] for row in union}
paths.update(row['path'] for table in prior['tables'] for row in table['sources'])
paths.update((prior_path, walk_path, pending_path))
tree = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', '-z', commit]).decode().split('\0')
paths.update(name for name in tree if name.rsplit('/', 1)[-1] == '.gitattributes')
snapshot = scratch / 'qualified'
snapshot.mkdir()
with subprocess.Popen(['git', 'archive', commit, '--', *sorted(paths.intersection(tree))],
                      stdout=subprocess.PIPE) as archive:
    subprocess.run(['tar', '-xf', '-', '-C', str(snapshot)], stdin=archive.stdout, check=True)
    assert archive.wait() == 0

tool = runpy.run_path('reviews/27-first-update-release/rebind.py')
tool['rebind']('42', bindings, run, root=snapshot)
assert checkout.active_tables(snapshot) == tables
assert checkout.verify(snapshot, union) == len(union)
assert json.loads((snapshot / record_path).read_bytes())['tables'] == bound['tables']
waiting = json.loads((snapshot / pending_path).read_bytes())
assert waiting['walk'] == record_path and not any(waiting[key] for key in ('changes', 'files', 'removed'))
print('PASS package 42 active tables match the qualified bytes and the waiting list is empty')
PY
test ! -e os/manifest/ci/42/source-bindings.json
cp "$record_work/qualified/os/manifest/ci/42/source-bindings.json" os/manifest/ci/42/
cp "$record_work/qualified/os/manifest/ci/16/pending-rebind.json" os/manifest/ci/16/
git diff --exit-code "$qualified" -- os/owner-tools os/manifest/release.json os/manifest/releases/28.json \
  os/manifest/base.json docs/OWNER-TOOLS.md
```

Keep the archive record's exact tables. Update the package 42 signed-update row with the passing run
and its qualified head after accepting the evidence. The live-game close and the laptop update have
their own evidence. Keep the install hold. Preserve main's newer `os/ci/vm.py` and
`os/config/usr/libexec/aresos-desktop` in the merge. Once the guide and merge edits are in place, rerun
the following in the resulting worktree. The differences from the qualified rehearsal, including
those two main files and the bound review edits, belong on the new waiting list. A refreshed host walk
records only the resulting local checkout. The VM evidence stays tied to `c1dba9f9`. Retain the package
branch ref after the squash merge, as for package 27. Full CI checkouts use it to fetch the fixed
published and rehearsal Git objects.

```bash
git diff --name-status "$qualified" -- os/ci/vm.py os/config/usr/libexec/aresos-desktop
python3 -B reviews/27-first-update-release/rebind.py pending "42 final review fixes"
python3 -B reviews/27-first-update-release/rebind.py pending "42 merge retains main's newer VM and desktop supervisor"
python3 -B reviews/42-release-28/walk-host.py
for module in test_checkout_sources test_owner_equality; do
  helper_status=0
  pgrep -a -u ares -x ksshaskpass || helper_status=$?
  test "$helper_status" -eq 1 || exit 1
  python3 -B -m unittest discover -s os/tests -p "$module.py" || exit 1
done
```

Require no output from each password-helper check before its module. Inspect the new waiting paths
before the lead commits them. When the announcement commit is reachable from `origin/main`, verify
its bytes and fingerprint before announcing it. Set `announced` to its full commit hash.

```bash
git merge-base --is-ancestor "$announced" refs/remotes/origin/main
git diff --exit-code "$qualified" "$announced" -- os/owner-tools docs/OWNER-TOOLS.md os/manifest/release.json \
  os/manifest/releases/28.json os/manifest/base.json
git show "$announced:os/owner-tools/payload/SHA256SUMS" | sha256sum
```

The last command must give
`df89ac336e13db84934505551ba28163cbd60fa5b3b9fb0ec97b9585945896c6`. Keep the run's evidence private
and retain only reviewed, non-sensitive records in Git.

#### Local verification

`python3 -B reviews/27-first-update-release/rebind.py pending "42 final review fixes"` printed
`pending: 40 bound files differ from the active bindings, 0 removed`.
`python3 -B reviews/42-release-28/walk-host.py` printed
`PASS package 42 host walk (release-28): 270 sources; no VM started`.

`checkout_sources.verify_git` replayed all 270 rows in the historical host walk from `c1dba9f9`.
The shell blocks in the lead instructions passed `bash -n`, and the embedded Python compiled.
The actual package 42 record waits on the accepted rehearsal.

The modules ran one at a time with `python3 -B -m unittest discover -s os/tests -p <module>.py`.
`pgrep -a -u ares -x ksshaskpass` printed nothing before each module.
`test_ways_back_model` used `ARESOS_MODEL_SCOPE=slice`. It processed 120,000 states,
discovered 173,130, covered 3,185,862 edges and reached all eight journal outcomes.
The first owner-path run found stale wording assertions and a missing German key label. The first
owner-equality run caught a descriptive command name formatted as an invocation. The guide and
assertions were corrected, and both modules were rerun.

| Module | Tests | Seconds | Result |
| --- | ---: | ---: | --- |
| `test_release28` | 94 | 25.657 | OK |
| `test_release28_rehearsal` | 44 | 35.003 | OK |
| `test_release28_control` | 15 | 4.153 | OK |
| `test_checkout_sources` | 9 | 1.150 | OK |
| `test_owner_equality` | 12 | 105.521 | OK |
| `test_owner_path` | 49 | 1.155 | OK |
| `test_owner_sources` | 13 | 48.458 | OK |
| `test_owner_walk` | 34 | 405.598 | OK |
| `test_rehearsal_budget` | 5 | 0.035 | OK |
| `test_owner_guard` | 12 | 0.057 | OK |
| `test_ways_back_model` | 26 | 172.215 | OK |
| `test_release27` | 41 | 6.695 | OK |
| `test_ci_api_permissions` | 4 | 3.051 | OK |
| `test_ci_step_environment` | 4 | 12.899 | OK |
| `test_grub_bls` | 6 | 0.307 | OK |
| `test_installer_webui` | 9 | 0.002 | OK |
| `test_job_accounting` | 11 | 0.005 | OK |
| `test_keyboard_release` | 5 | 0.003 | OK |
| `test_organization_budget` | 19 | 0.013 | OK |
| `test_owner_bootstrap` | 13 | 1.272 | OK |
| `test_owner_entry` | 3 | 0.334 | OK |
| `test_owner_session` | 16 | 0.267 | OK |
| `test_owner_staged_release` | 7 | 0.046 | OK |
| `test_owner_step_limits` | 4 | 0.012 | OK |
| `test_probe_native` | 4 | 0.002 | OK |
| `test_rehearsal_history` | 9 | 0.012 | OK |
| `test_rehearsal_retry` | 7 | 0.035 | OK |
| `test_stock_prepare` | 7 | 0.028 | OK |
| `test_system_keyboard` | 7 | 0.011 | OK |
| `test_tools_local_wiring` | 42 | 57.531 | OK |
| `test_ways_back_probe` | 57 | 154.072 | OK |

All 31 modules passed, for 588 tests and zero skips.
`git diff --check` passed. No file over 500 MB was found in `.work/`.

### Final review fixes, round 2 (Codex gpt-6.2-sol)

The starting worktree was `e5d97383`. The hosted rehearsal uses `c1dba9f9`. The shipped
release and update tools were the source of truth for the guide sweep. The two generated
receipts below describe the local checkout. The R28 gate still awaits accepted hosted evidence.

- **1 · Save before restart.** On R28, use **Alt+F4** on the focused Minecraft home. Wait for
  **Minecraft was closed. Nothing is wrong.** Leave that screen open. The supervisor waits for
  a retry. Both layout restarts use this step, as do update, previous, forward, rollback and
  the emergency restart routes. The shared instruction also covers a restart for Windows.
- **2 · Recovery terminal.** On R28, **Super+Ctrl+Esc** opens the recovery terminal if the Terminal
  app fails. Keep it open before entering tty3 and through the check. The key binding is in
  `os/config/usr/share/aresos/labwc/rc.xml:20`.
- **4 · Record identity.** The active binding selector compares the record's package with its
  directory. The rejection test puts a package 27 record in the package 42 directory.
- **7 · Checks reservation.** Package 42 reserves 60 minutes, the checks job's limit.
  The regression test ties the workflow reservation to that limit. Packages 13 and 27
  still reserve 15 minutes. The 50-minute rehearsal preflight, four-run cap and
  345-minute rehearsal ceiling still apply.
- **8 · Check the action that ran.** Previous requires the older AresOS and the **Return to**
  result after restart. Forward requires the newest AresOS and **Forward to**. An already
  running target is checked on the same boot when no restart is waiting. A no-op writes no
  new confirmation. Failed-update retries use **F12 → Bazzite**, then leave GRUB alone.
  Windows stays the firmware default.
- **9 · Release 27 console keys.** The exact STOP has a one-boot repair on German R27.
  The proof is in `briefs/50-console-keymap.md:13` and
  `reviews/22d-tools-without-stick/REPORT.md:323`: after `loadkeys -C /dev/tty3 -- de`,
  keycode 21 changed from `+y` to `+z`, the checks passed and the owner proved physical
  typing. The guides use that command from the retained root session with the maintainer.
  A pending or half-written layout goes through layout abandon. Save a one-time
  **was not applied** result even if it precedes a STOP. Require **PASS check** on this boot
  before using it. The repair only lasts until restart.
- **10 · Install hold.** The entry points for Fedora Media Writer, its restore control,
  the installer and the GParted path all carry the hold before a write or erase. The GParted
  path repeats the hold at **Apply**. The signed update on the existing installation has its
  own gate.
- **11 · Registry retry.** Enter the username at **GitHub username:** and the token at
  **Read-only token (hidden):**. Wait for **PASS login** before retrying the same update.
- **Guide tests.** `test_owner_guide_output` compares bold and inline-code console results
  after cues such as “require,” “look for,” “shows” and “prints” with strings used by the
  released CLI. It reads the archived v2 strings for the documented older-tools cases.
  It rejects an invented result, using each guide's ellipsis for variable fields.
  Route assertions reject using **Update to** or the update check box in place of the
  return or forward check. `test_owner_path` also exercises the same-boot selection,
  save-before-restart, R27 STOP and direct-entry holds.

**PLAN-GAP — live save on release 28.** A live edit, normal close, restart and reopen
cannot be tested here for the published release. The source and bytecode trace in round 1
covers normal exit and world save. The rehearsal has no live edited world.
The laptop's R28 route still needs the visible normal-close screen before reboot.
R27's German keymap repair was demonstrated on the laptop before this round. It has
no new physical result after an R28 → R27 return.

#### Owner route audit

`at …` in the command column means `sudo /var/lib/ares/at …`. Each message separated
by a slash is a separate output line. Ellipses stand for the release reference, digest,
menu rows or other variable fields. The guide sometimes quotes the fixed part of a line.

**Tools only and registry login**

| Step | Command | Tool output | Guide |
| --- | --- | --- | --- |
| Install from the folder or the stick | `at install` in the generated block | `PASS install` / `Tools updated from version … to …` / `manifest SHA256 …` | `docs/INSTALL.md:290`, `docs/INSTALL.md:331` |
| Same bundle again | `at install` | `PASS install` / `Tools already installed; nothing changed` / `manifest SHA256 …` | `docs/INSTALL.md:290`, `docs/INSTALL.md:331` |
| Verify tools only and save the title | `at check`, `at title` | `PASS check` / `PASS title` / `newer AresOS … runs and starts next` / `Boot menu at the next start: …` | `docs/INSTALL.md:333`, `docs/INSTALL.md:340` |
| Export after a routine STOP with older tools still installed and no stick | routine export line | `PASS export` / `Tools stick absent; full records remain internal` | `docs/INSTALL.md:298` |
| Login retry | `at login` | `GitHub username:` / `Read-only token (hidden):` / `PASS login` / `Private registry login succeeded; token excluded from diagnostics` | `docs/INSTALL.md:361` |
| Stop before reauth or retry | `at update` | `STOP: Registry login missing, expired or unreachable: run sudo /var/lib/ares/at login, then run this command again; nothing was changed` | `docs/INSTALL.md:355` |

**Signed update**

| Step | Command | Tool output | Guide |
| --- | --- | --- | --- |
| Stage | `at update` | `PASS update` / `Signed exact release staged …` / `Running release stays as rollback …` / `pin yes; transaction idle` | `docs/INSTALL.md:348` |
| Stage with two AresOS releases | `at update` | `… is removed when the update finishes at shutdown` / from the older release, `The new release starts with this system's settings (Wi-Fi, passwords, layout), not …'s` | `docs/INSTALL.md:350` |
| Record interrupted staging that did complete | `at update` | `PASS update` / `Interrupted update recorded: …` | `docs/INSTALL.md:348` |
| Already running and first | `at update` | `PASS update` / `… already starts next; nothing changed` / `It runs now` | `docs/INSTALL.md:352` |
| Cannot stage here or already installed elsewhere | `at update` | `STOP: Update installs a new release only from a running AresOS that starts next: run …` or `STOP: The release of these tools is installed already, so update has nothing to install: run …` | `docs/INSTALL.md:353` |
| Stop and resume | `at update` or next command | `STOP: The update … and was stopped safely: …` or `STOP: The update to … was interrupted before its result was recorded; do not reboot; run …` | `docs/INSTALL.md:354` |
| Save the provisional title | `at title` | `PASS title` / `Boot menu after the update finishes at shutdown (expected): …` | `docs/INSTALL.md:370`, `docs/INSTALL.md:375` |
| Export with ARESTOOLS | `at export` | `PASS export` / `SAFE TO REMOVE ARESTOOLS; unplug before every shutdown/restart` | `docs/INSTALL.md:299`, `docs/INSTALL.md:372`, `docs/EMERGENCY.md:69` |
| Export without ARESTOOLS | `at export` | `PASS export` / `Tools stick absent: records copied to /run/ares-records with SHA256 readback` | `docs/INSTALL.md:298`, `docs/INSTALL.md:373`, `docs/EMERGENCY.md:70` |
| Restart after saving the title off-device | `at reboot` | `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` | `docs/INSTALL.md:383` |

**Check and the failed-update card**

| Step | Command | Tool output | Guide |
| --- | --- | --- | --- |
| Read the result with the terminal open on R28 | `at check` | `PASS check` / `System console …; X11 … variant …` / `Loaded y/z map, cmdline and all retained BLS maps passed` | `docs/INSTALL.md:197`, `docs/INSTALL.md:449`, `docs/INSTALL-PROCEDURES.md:83`, `docs/EMERGENCY.md:26` |
| No open change, default boot | `at check` | `PASS check` / `… runs and starts next` / `Boot menu at the next start: …` | `docs/INSTALL.md:340`, `docs/INSTALL.md:395` |
| No waiting change, another row booted | `at check` | `PASS check` / `… runs; … starts next; this start was not the default` | `docs/INSTALL-PROCEDURES.md:120` |
| Update confirmed | `at check` | `PASS check` / `Update to … confirmed after the restart` / `newer AresOS … runs and starts next` | `docs/INSTALL.md:387`, `docs/EMERGENCY.md:29` |
| Same boot, staging present | `at check` | `PASS check` / `Update to … is not finished until the restart` | `docs/INSTALL.md:390`, `docs/EMERGENCY.md:31` |
| Same boot, a selection is queued | `at check` or `at title` | `PASS check` or `PASS title` / `… runs; … starts next, after the restart` / `… is not finished until the restart` | `docs/INSTALL.md:406`, `docs/INSTALL.md:426`, `docs/INSTALL-PROCEDURES.md:135` |
| Applied with target already running | `at check` or `at title` | `PASS check` or `PASS title` / `… runs and now starts next; no restart is waiting` | `docs/INSTALL.md:406`, `docs/INSTALL.md:436`, `docs/INSTALL-PROCEDURES.md:161` |
| A different boot-menu row started after update | `at check` | `PASS check` / `… runs; … starts next; this start was not the default` / `Update to … is in place and has not started yet` | `docs/INSTALL.md:389`, `docs/EMERGENCY.md:28` |
| Update did not apply | `at check` | `Update to … was not applied: the deployments are as before it, and nothing is waiting` (once, even on a STOP) | `docs/INSTALL.md:388`, `docs/EMERGENCY.md:26`, `docs/EMERGENCY.md:30` |
| Restart to the unchanged default after a nondefault boot | `at reboot`, `at check` | `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` / `PASS check` / `… runs and starts next` | `docs/EMERGENCY.md:30` |
| Journal mismatch or unfinished intent | `at check` | `STOP: The … did not finish as recorded (…); do not repeat it; export records and get help: EMERGENCY Failed or bad update` or `STOP: The update to … was interrupted before its result was recorded; do not reboot; run …` | `docs/INSTALL.md:391`, `docs/EMERGENCY.md:32` |
| Keymap mismatch on R27 | `at check` | `STOP: Loaded console keys differ from system layout; get help` | `docs/INSTALL.md:449`, `docs/EMERGENCY.md:26`, `docs/INSTALL-REFERENCE.md:34` |
| Repair this boot and recheck | `loadkeys -C /dev/tty3 -- de`, `at check` | The repair command needs no output on success. Require `PASS check` / `System console de; X11 … variant …` | `docs/INSTALL-REFERENCE.md:36`, `docs/INSTALL-REFERENCE.md:42` |
| Save after a passing check | `at title`, `at records` | `PASS title` / `PASS records` | `docs/INSTALL.md:460`, `docs/INSTALL-REFERENCE.md:68` |

**Previous and forward**

| Step | Command | Tool output | Guide |
| --- | --- | --- | --- |
| Select older AresOS | `at previous`, `at title` | `PASS previous` / `Previous AresOS queued for the next start …` / `PASS title` | `docs/INSTALL.md:424`, `docs/INSTALL.md:426` |
| Older AresOS booted after the queued return | `at check` | `PASS check` / `Return to … confirmed after the restart` / `older AresOS … runs and starts next` | `docs/INSTALL.md:433`, `docs/INSTALL.md:435`, `docs/EMERGENCY.md:28` |
| Running older AresOS made first | `at check` | `PASS check` / `older AresOS … runs and now starts next; no restart is waiting` | `docs/INSTALL.md:436` |
| Select newest AresOS | `at forward`, `at title` | `PASS forward` / `Newest installed AresOS starts next …` / `PASS title` | `docs/INSTALL.md:404`, `docs/INSTALL.md:406` |
| Newest AresOS booted after restart | `at check` | `PASS check` / `Forward to … confirmed after the restart` | `docs/INSTALL.md:406` |
| Running newest AresOS made first | `at check` | `PASS check` / `… runs and now starts next; no restart is waiting` | `docs/INSTALL.md:406` |
| Target already first | `at previous` or `at forward`, then `at check` | `… already starts next; nothing changed` / `It runs now` or `It does not run yet: it starts at the next restart` / after any needed restart, `PASS check` with the selected AresOS running and first | `docs/INSTALL.md:407`, `docs/INSTALL.md:427`, `docs/INSTALL.md:437` |
| If a restart is needed | `at reboot` | `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` | `docs/INSTALL.md:406`, `docs/INSTALL.md:429` |

**Rollback and keep-stock**

| Step | Command | Tool output | Guide |
| --- | --- | --- | --- |
| Select stock on AresOS | `at rollback`, `at title` | `PASS rollback` / `Saved stock rollback queued` / `PASS title` / `… runs; plain Bazzite … starts next, after the restart` | `docs/INSTALL-PROCEDURES.md:135` |
| Stock already first | `at rollback` or `at keep-stock` | `Plain Bazzite … already starts next; nothing changed` / `It does not run yet: it starts at the next restart` for rollback, `It runs now` for keep-stock | `docs/INSTALL-PROCEDURES.md:135`, `docs/INSTALL-PROCEDURES.md:161` |
| Keep booted stock as first | `at keep-stock`, `at title`, `at check` | `PASS keep-stock` / `Saved stock is default` / `PASS title` / `PASS check` / `plain Bazzite … runs and now starts next; no restart is waiting` | `docs/INSTALL-PROCEDURES.md:161` |
| Boot first stock, or prove second boot | `at reboot` | `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` | `docs/INSTALL-PROCEDURES.md:143`, `docs/INSTALL-PROCEDURES.md:167` |
| Check stock after reboot | `at check`, `at title` | `PASS check` / `plain Bazzite … runs and starts next` / confirmation if selected, `Rollback to … confirmed after the restart` or `Change to … confirmed after the restart` / `PASS title` | `docs/INSTALL-PROCEDURES.md:150`, `docs/INSTALL-PROCEDURES.md:167` |
| Export and independently prove Windows | `at export`, `at reboot` | `PASS export` / `SAFE TO REMOVE ARESTOOLS; unplug before every shutdown/restart` / `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` | `docs/INSTALL-PROCEDURES.md:169` |

**Keyboard layout**

| Step | Command | Tool output | Guide |
| --- | --- | --- | --- |
| Begin trial | `at layout begin us-intl`, `de` or `us` | `PASS layout begin …` / `Console-only trial; system/greeter layout stays finished until layout finish` | `docs/INSTALL-PROCEDURES.md:15`, `docs/INSTALL-PROCEDURES.md:33`, `docs/INSTALL-PROCEDURES.md:41` |
| Fresh tty4 proof | `sudo -k; sudo /var/lib/ares/at layout proof` | `Physically type yz-/!ü then Return:` / `PASS layout proof` / `Fresh second-console login and physical typing passed` | `docs/INSTALL-PROCEDURES.md:21`, `docs/INSTALL-PROCEDURES.md:61` |
| Revert a failed trial | `at layout revert` | `PASS layout revert` / `Old console/X11 settings restored; no reboot` | `docs/INSTALL-PROCEDURES.md:51` |
| Finish after proof, including proof after revert | `at layout finish` | `PASS layout finish` / `Layout trial completed; fresh login/typing proof saved` | `docs/INSTALL-PROCEDURES.md:27`, `docs/INSTALL-PROCEDURES.md:67` |
| Restart after each finish | `at title`, `at reboot`, `at check` | `PASS title` / `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` / `PASS check` / `System console …; X11 … variant …` | `docs/INSTALL-PROCEDURES.md:77`, `docs/INSTALL-PROCEDURES.md:83`, `docs/INSTALL-PROCEDURES.md:85` |
| Abandon an interrupted trial | `at layout abandon` | `PASS layout abandon` / `Last finished console layout restored; abandoned trial cleared` / `Last finished persistent layout verified; stock settings preserved` | `docs/INSTALL-PROCEDURES.md:108`, `docs/EMERGENCY.md:64` |
| Repair a noted partial layout on its system | `at layout abandon` | `PASS layout abandon` / `This system's half-written layout is restored to the settings before its trial` | `docs/INSTALL-PROCEDURES.md:108` |
| Already cleared | `at layout abandon` if accidentally repeated | `STOP: No layout trial and no half-written layout to abandon on this system; nothing changed` | `docs/INSTALL-PROCEDURES.md:91`, `docs/EMERGENCY.md:65` |

**Held initial-install route and other checks**

| Step | Command | Tool output | Guide |
| --- | --- | --- | --- |
| Install tools on prepared hardware | `at install` in the trusted bootstrap | `Photographed Crucial serial:` / `Windows baseline Micron serial:` / `PASS install` / `manifest SHA256 …` | `docs/INSTALL.md:109` |
| Prepare corrected stock, then verify it is repeatable | `at prepare` twice | `PASS prepare` / `pin yes; pending none; updaters paused` / on repeat, `Already prepared; no OS mutations` | `docs/INSTALL.md:115` |
| Stock records and safe removal | `at title`, `at records`, `at export` | `PASS title` / `PASS records` / `PASS export` / `SAFE TO REMOVE ARESTOOLS; unplug before every shutdown/restart` | `docs/INSTALL.md:124` |
| Prove default Windows and return to stock | `at reboot`, then `at check`, `at title`, `at records` | `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` / `PASS check` / `PASS title` / `PASS records` | `docs/INSTALL.md:136`, `docs/INSTALL.md:145` |
| Login, verify, switch once the gate allows it | `at login`, `at verify`, `at switch`, `at title` | `PASS login` / `PASS verify` / `PASS switch` / `PASS title` | `docs/INSTALL.md:161`, `docs/INSTALL.md:176` |
| First boot and physical button records | `at check`, `at title`, `at records`, `at logs` | `PASS check` / `PASS title` / `PASS records` / `PASS logs` | `docs/INSTALL.md:197`, `docs/INSTALL.md:205` |
| Diagnose a STOP | `at export` with or without ARESTOOLS | `PASS export` and the appropriate export line above. An older stick adds `The stick holds tools this laptop installed before (SHA256 …), not the installed ones`. | `docs/EMERGENCY.md:69`, `docs/EMERGENCY.md:70`, `docs/INSTALL-REFERENCE.md:9` |

The check also reports a recovered reorder intent with
`The interrupted … had made its change; it is recorded now`. The standing lines and the
route's PASS still decide the next step. If the recorded staged deployment list changes before restart,
the exact STOP includes `changed before the restart; do not reboot; get help`. This falls
through to the STOP path at `docs/INSTALL.md:391` and `docs/EMERGENCY.md:32`.

The Windows and bootstrap prompts, checksum output, firmware labels and Minecraft close
screen come from their own programs. The install hold is in
`docs/INSTALL-STATUS.md:20`, `docs/INSTALL.md:46`, `docs/INSTALL.md:79`,
`docs/INSTALL.md:82`, `docs/INSTALL-REFERENCE.md:100`, `docs/INSTALL-REFERENCE.md:117`
and `docs/INSTALL-PROCEDURES.md:198`.

#### Local verification

`python3 -B reviews/27-first-update-release/rebind.py pending "42 final review fixes, round 2"`
printed `pending: 40 bound files differ from the active bindings, 0 removed`.
`python3 -B reviews/42-release-28/walk-host.py` printed
`PASS package 42 host walk (release-28): 270 sources; no VM started`.
These commands regenerated `os/manifest/ci/16/pending-rebind.json` and
`os/manifest/ci/42/host-walk.json`.

The final receipt's 270 source hashes match the worktree. The waiting list has 40 paths
and no removals. The local walk does not replace the hosted rehearsal.

I ran the modules below one at a time with
`python3 -B -m unittest discover -s os/tests -p <module>.py`.
`pgrep -a -u ares -x ksshaskpass` printed nothing before each module. The model used
`ARESOS_MODEL_SCOPE=slice`. It processed 120,000 states, discovered 173,130, covered
3,185,862 edges and reached all eight journal outcomes.

| Module | Tests | Seconds | Result |
| --- | ---: | ---: | --- |
| `test_aresos_desktop` | 189 | 67.852 | FAILED (errors=42) |
| `test_build_tools` | 3 | 0.128 | OK |
| `test_checkout_sources` | 10 | 1.174 | OK |
| `test_ci_api_permissions` | 4 | 3.049 | OK |
| `test_ci_step_environment` | 4 | 12.886 | OK |
| `test_grub_bls` | 6 | 0.308 | OK |
| `test_installer_webui` | 9 | 0.002 | OK |
| `test_owner_bootstrap` | 13 | 1.246 | OK |
| `test_owner_capabilities` | 6 | 0.168 | OK |
| `test_owner_devices_native` | 14 | 1.962 | OK |
| `test_owner_entry` | 3 | 0.348 | OK |
| `test_owner_equality` | 12 | 105.478 | OK |
| `test_owner_guard` | 12 | 0.057 | OK |
| `test_owner_guide_output` | 2 | 0.175 | OK |
| `test_owner_login` | 18 | 1.443 | OK |
| `test_owner_path` | 51 | 1.234 | OK |
| `test_owner_session` | 16 | 0.268 | OK |
| `test_owner_sources` | 13 | 48.790 | OK |
| `test_owner_staged_release` | 7 | 0.046 | OK |
| `test_owner_step_limits` | 4 | 0.012 | OK |
| `test_probe_native` | 4 | 0.002 | OK |
| `test_rehearsal_auth` | 9 | 0.076 | OK |
| `test_rehearsal_budget` | 6 | 0.067 | OK |
| `test_release27` | 41 | 6.907 | OK |
| `test_release28` | 94 | 25.812 | OK |
| `test_release28_control` | 15 | 4.157 | OK |
| `test_release28_rehearsal` | 44 | 34.945 | OK |
| `test_stock_prepare` | 7 | 0.028 | OK |
| `test_system_keyboard` | 7 | 0.011 | OK |
| `test_tools_local_wiring` | 42 | 57.561 | OK |
| `test_ways_back_model` | 26 | 172.244 | OK |
| `test_ways_back_probe` | 57 | 154.273 | OK |

31 full modules passed, with 559 tests and zero skips.
Earlier guide runs identified stale wording assertions and a synthetic fixture field;
the fixes and the final installer-hold wording passed the reruns above.

The full desktop module ran because it reads the workflow. Its 42 setup errors were
`PermissionError: [Errno 1] Operation not permitted` at Unix socket bind. A direct
bind reproduced it in both the temporary directory and worktree scratch. The exact test
that reads the changed workflow passed on its own.
`python3 -B -m unittest discover -s os/tests -p test_aresos_desktop.py -k test_a_release_is_the_default_and_only_the_job_that_cannot_publish_throws_away`
printed `Ran 1 test in 0.063s`, `OK`.

`git diff --check` passed. No file over 500 MB was found in `.work/`.

### Rehearsals 5 and 6 (2026-11-20, the lead)

- **Rehearsal 5** (44764936797, `8afed5c5`) stopped before its installer. The live session reached its desktop
  (`failure-protected-second-install.png`), but its serial console went silent right after systemd's terminfo
  probe was answered, so `login:` did not come within 360 seconds. The reply counts (terminfo 3, cursor 4) include
  queries that arrived only after the harness typed `systemctl poweroff`; `finish_shutdown` keeps that output only
  when the shutdown succeeds. A guest serial stall: rerun unchanged (`77a08140`, release-28 6, checks 11; Codex Sol
  recheck SAFE, `~/AresOS-42-cap6-recheck.md`; its known limit: `test_release28.py`'s checks fixture writes an
  invalid `T010:00:00Z` time for its eleventh run). If it repeats: wake the line before `login:` (a design change),
  and save the shutdown wait's output on failure.
- **Rehearsal 6** (44781321736, `77a08140`) passed the live session, the install, the stock rewind, the offline
  first stock boot and the route through releases 13 and 27 to 28, then stopped in `terminal_path`: no foot of ares
  in 120 seconds. `no_foot`'s TERMINAL took the environment from labwc's `/proc/<pid>/environ`, which never holds
  `WAYLAND_DISPLAY` (labwc sets it after it starts), so foot started without a display and exited at once
  (`release-28-terminal.json`: `foot` 1, `wayland` false). The fake session had given labwc's environ a display.
- **Fix:** TERMINAL takes the environment from the one `aresos-desktop session` process of ares (exact command line;
  the walk's own `aresos-desktop status` is skipped), which labwc's autostart starts and whose environment the hub's
  programs inherit; `no_foot` STOPs without exactly one supervisor or without a display, and when the foot is gone
  three seconds after it appeared. The fake: labwc's environ has no display, the supervisor's has it, a foot started
  without a display is seen once and then exits; new cases `supervisor_without_display` and
  `test_a_terminal_from_labwcs_own_environment_stops`. Caps: release-28 7, checks 12.
- **Review of `391366a9`** (Codex gpt-6.2-sol high, `~/AresOS-42-terminal-fix-review.md`): NOT SAFE, one must-fix.
  The reopened foot inherited the serial root shell's directory (the recovery account's, which ares cannot enter;
  package 27's report) through `runuser`, and foot exits when its chdir fails. Fixed: TERMINAL starts it in his
  home (`cwd`), as the hub's Terminal does (`apps/terminal.json` `"working_directory": "~"`), requires the
  supervisor's HOME to be `/var/home/ares`, keeps foot's output in `/run/aresos-terminal.log` for the evidence, and
  checks that the same foot PID still runs three seconds later. The fake's foot also exits when started elsewhere;
  `test_a_terminal_outside_his_home_exits_and_stops` covers it (the first case of a foot that appears and dies).
  Checks 13 (checks 12 ran on `391366a9`); rehearsal 7 was not dispatched.
- **Known limits from that review** (no sure VM failure): a supervisor exiting between its cmdline and environ
  reads STOPs falsely (teardown only); on `final-28` the SETUP terminal and Control service start with the boot
  while `at check` and the Control checker query them soon after login (the same moves passed on rehearsal 6's
  first R28 boot); Prism may rewrite unmodelled files during the final home snapshot; `game_scope` does not assert
  the kill's result; the PATH probe relies on labwc giving the reopened foot keyboard focus (one retry).
- **Rehearsal 7** (44812508100, `ecf94d07`; recheck SAFE, `~/AresOS-42-terminal-cwd-recheck.md`) reached release 28
  again and passed the supervisor, display and home checks; the reopened foot then exited with ` err:
  wayland.c:1827: no monitors available`. It was opened while tty3 (the console of the stopped `at check`) was in
  front, so labwc had no active output. **Fix:** `no_foot` returns to tty1 and waits for it and his active session
  (`ACTIVE_DESKTOP`) before the launch, as his guide opens the Terminal app on his desktop before tty3; TERMINAL
  tries a launch whose log says "no monitors available" again, five times at most, and keeps each attempt's log.
  The fake tracks the VT in front from the QMP keys; a foot started without a monitor writes foot's line and exits.
  New cases: `vt_stays_tty3` (STOP with the log) and `test_a_late_monitor_is_tried_again`. Caps: release-28 8,
  checks 14.
