# 18c image part: progress (Part A, step 1; B2, steps 2a to 2c)

Branch `pkg/18c-image`, draft PR #58. Step 1 builds Part A of `briefs/18c-image-test.md` as amended by the sixteen
changes agreed with `linux-aresos` and by `briefs/18c-image-start.md`. It has no VM test (B2), no `os-image.yml` change
and no `check_build=build` run. Built by a Claude agent on Opus 5.5.

**Open, needs a decision before `gh` goes in (stop rule):** GitHub's release RPM for `gh` requires `git`, and the base
has only `git-core`. See "gh" below.

## Done

- `os/Containerfile`: the aresos stage copies `/source/control` from the existing `source` stage to
  `/tmp/aresos/control` and runs `build.sh control` before `build.sh configure` (agreed change 1).
- `os/build.sh`:
  - `source`: the same single fetch also extracts `AresOS-<commit>/control` (named exactly, so `docs/control/` stays
    out) and requires `control/launch.py`.
  - `control` (image build only, as root): pip installs `control/requirements.lock` into
    `/usr/lib/aresos-control/vendor` (`--require-hashes --only-binary=:all: --no-compile --report`, `env -i`, `-I`),
    then `compileall --invalidation-mode checked-hash` in place. Then the install map (below), then two self-checks:
    `/usr/bin/aresos --help` through the installed launcher, and `generate.generated()` equal to every shipped
    generated file (`CONTROL_GENERATED_MATCH`).
  - `control-tree OS CONTROL DEST`: the same install map into any folder, no pip, no root. `check-image.sh` and the
    tests run it.
  - The install map is data: `TREES` (`aresos_control/`, `generated/`), `FILES` (launch.py, the three commands 0755,
    unit, sysusers, tmpfiles, `/etc/claude-code/{managed-settings.json,CLAUDE.md}`, `user-mcp.json`) and `DERIVED`
    (`service.json`, `proxy.json`, the folders' tmpfiles file). The enable link comes from the unit's own `WantedBy=`.
    **For Chrome, a later commit adds one `FILES` line (`chrome/qualification.json`) and one `DERIVED` entry
    (`chrome/build-id.json` from `control/chrome/build.py`) plus their checks. Nothing else changes.**
  - `service.json` and `proxy.json` are the drafts without `_comment`, with `owner_uid`, `home` and `folders` taken from
    the one `u` line of `os/config/usr/lib/sysusers.d/aresos.conf` (uid ≥ 1000, matching `g` line, home under
    `/var/home/`). They are installed in `/usr/share/aresos/control/` (agreed change 7).
  - `/usr/lib/tmpfiles.d/aresos-control-folders.conf`: `d /var/home/ares/Downloads :0700 :ares :ares -` and the same
    for `Documents` (agreed change 11).
  - `/usr/share/aresos/manifest/control.json` (format 1): `files` (path → mode, SHA-256, source), `directories`,
    `links`, `requirements_lock` (SHA-256 of the lock); image build only: `source_revision`, `wheels` (name, version,
    wheel file, SHA-256 from pip's report, each checked against the lock's hashes, same set as the lock) and `vendor`
    (every vendored path with mode and SHA-256).
- `os/ci/image-checks.sh`: early, no `aresos-tools`/250 entry and no `Downloads`/`Documents` before boot. At the end:
  every path `control.json` records is in the image as recorded (mode, SHA-256), root-owned with root-owned parents,
  no links, and nothing unrecorded under Control's four folders; `/etc/claude-code` has its two files and no
  `managed-mcp.json`; the unit is `enabled`, `Type=simple`, named by no other unit file and linked only from
  `multi-user.target.wants`; the updater audit's `updaters.json` saw it (enabled, not suspicious); sysusers gives
  `aresos-tools:x:250:250:...:/usr/sbin/nologin`, locked, nothing else on 250; tmpfiles gives `/run/aresos-tools` 0711
  and both state folders 0700 for `aresos-tools`, the two folders 0700 `ares`, and an existing folder keeps its own
  mode and owner; the config's `owner_uid` and `home` equal the `ares` account; `aresos --help` as root and as `ares`;
  no `mcp` in Python's own site-packages; no fixture CA or fixture names (agreed change 9, below).
- `os/ci/check-image.sh`: runs `build.sh control-tree os control` and requires the image's `control.json` to equal it
  in `format`, `requirements_lock`, `links`, `directories` and `files`, with `source_revision` = `git rev-parse HEAD`
  and every vendored path under `/usr/lib/aresos-control`. The existing lock heredoc is unchanged.
- `os/ci/check-resolve.sh`: the one `gh` step (agreed change 4): base and Fedora `gh`, a `GH_FEDORA <version>
  <verdict>` line, and `gh` added to the candidate request list (nothing else changes).
- `os/tests/test_control_image.py` (11 tests) and one updated test in `os/tests/test_aresos_desktop.py` (the source
  stage now keeps `mod/` and `control/`; fixture gains `control/` and a `docs/control/` decoy).
- `os/README.md`: one paragraph, "The Control tools (package 18c)".
- `control/launch.py` `CONFIG` and `aresos_control/daemon.py`'s `--config` default → `/usr/share/aresos/control`;
  `control/ci/setup.sh`, `control/README.md` and `control/tests/test_integration.py` (five places) follow, no assertion
  changed.
- `control/packaging/aresos-tools.sysusers`: `u aresos-tools 250 ...` (only the number changed).
- `control/tests/test_service_user.py` (pin of that line), `control/tests/test_reserved_words.py` (agreed change 13:
  no served app, MCP server name or top-level CLI word is one of the sixteen reserved words; the generated help uses
  only `admin`, `log` and app names).

## The sixteen agreed changes

| # | Status |
|---|---|
| 1 Sources through the source stage | done |
| 2 Base with 23 and Chrome | built on `main` with 23, without PR #27 (lead's decision, start note); Chrome follow-up later |
| 3 Lists that pin enabled units | done as far as `main` has them: no list pins enabled units or users except release 27's `ci/release_diff.py` (the next release extends its own diff); image check proves the updater audit saw the unit; polkit unaffected (no rules) |
| 4 `gh` | check-resolve step done, resolve run done; **install open** (stop rule, below) |
| 5 Fixed UID/GID | done (250) |
| 6 Enabled, never holds the session | done: B2 check 6 green with the service stopped and failed (step 2c, run 43577034725) |
| 7 Config in `/usr/share/aresos/control` | done; image check done; booted-guest check `control-claude-code-files` (step 2a) |
| 8 `checks.py` hook | done (step 2a): `actions.d` |
| 9 Fixture servers, negative check | negative check done; fixture servers and CI layer done (step 2a) |
| 10 Owner's yes before merge | open (lead) |
| 11 Folders by tmpfiles | done |
| 12 Rehearsal check actions | done (step 2a): `os/ci/control/release_checks.py` |
| 13 Reserved words test | done |
| 14 Idle footprint | measured (step 2a): ~32 MB, 10 wake-ups/s, 0.35–0.67 % of one CPU |
| 15 `os-image.yml` additive, lead first | done: one option (`1ee81d1b`), the VM pass's own step (`0af04070`), its limits sized (`2d1ad22f`); each its own commit |
| 16 `linux-aresos` reads the `os/` diff | before merge |

## gh (agreed change 4): PLAN-GAP and stop

- **run 43547750786** (`check_build=resolve`, head `c47e3c0e`, success): `GH_FEDORA 2.97.0 too-old (Control needs
  2.102.0 or newer)`. Fedora 44: `gh-2.87.3-1.fc44` (fedora), `gh-2.97.0-2.fc44` (updates); the base has no `gh`. The
  candidate adds only `gh-2.97.0-2.fc44.x86_64`; all 29 existing pins are still served (no `MISSING` line).
- **read** (Fedora's update system, 2026-11-14): the newest F44 gh update is 2.97.0 (stable 2026-08-02), nothing newer
  in testing. Waiting for Fedora is not a plan.
- So the brief's route is GitHub's release RPM. **read** (`cli/cli` v2.103.3, downloaded into a scratch folder only):
  `gh_2.103.3_linux_amd64.rpm`, 15672051 bytes, SHA-256
  `65d55875faa3281959676d91da15a9380583281586ac31bbd3d32b7924a9f4d2` (equal to the release's checksums file and the
  asset digest), NEVRA `gh-2.103.3-1.x86_64`, header signed RSA/SHA512 key ID `5612b36462313325`, no scripts, files
  `/usr/bin/gh`, completions and man pages. **It requires `git`**; the base has `git-core-2.56.0-1.fc44` only, and
  nothing provides `git` (checked on the laptop, which runs release 27 on the same pinned base).
- The install as agreed (beside Chrome's, `dnf5 --disable-repo='*'`) therefore fails, and the stop rule applies
  ("another package"). Not built. Options for `linux-aresos`, through the lead:
  1. **Install the pinned RPM with `rpm -i --nodeps` (or dnf with the dependency skipped).** `/usr/bin/git` is there
     (git-core); the rpm database keeps one unmet requirement, so `dnf check` reports it. Smallest change.
  2. **Take `/usr/bin/gh` out of the pinned RPM (`rpm2cpio`) and record it in `gh.lock.json` and `control.json`.**
     Same bytes, no rpmdb entry, no unmet requirement; `rpm -qf /usr/bin/gh` says unowned.
  3. **Add Fedora's `git` package to `packages.lock.json`.** **assumed, not resolved here:** it pulls `git-core-doc`,
     `perl-Git` and Perl modules and must match `git-core`'s version (possibly an upgrade of `git-core`): several more
     packages, which a resolve run would show.
  4. Wait for Fedora's `gh` ≥ 2.102.0 (no sign of it).
  - Signature: the RPM's install with `localpkg_gpgcheck=True` would also need GitHub CLI's key, which the proposal
    does not list. With options 1 and 2 the SHA-256 pin binds the exact bytes, as Chrome's pin does; the key could
    be pinned like Google's if `linux-aresos` wants it.
  - **Recommendation: option 2** (no extra package, no broken rpmdb dependency, same pinned bytes, no repository).
    Pin 2.103.3 (19 days old, the latest patch of 2.103, also what his own `~/.local/bin/gh` runs) rather than
    2.104.0 (two days old).
- `gh.lock.json`, the install step, its image check (`gh --version` ≥ 2.102.0, as `ares`, no repository, no key) and
  the `CONTROL_GH` lines wait for that answer.

## UID and GID 250 (agreed change 5)

- **read** `/usr/share/doc/setup/uidgid` (Fedora setup, on the laptop = the pinned base): static IDs end at 194
  (`xrootd`), plus 65534; the block is 0 to 200.
- **read** `login.defs`: `SYS_UID_MIN 201`, `SYS_UID_MAX 999` (same for GID). sysusers and `useradd -r` allocate
  from 999 downward.
- **read** the laptop's `/usr/lib/passwd`, `/usr/lib/group`, `/etc/passwd`, `/etc/group` and every `sysusers.d`
  file (release 27, same base digest): IDs in 201–999 in use are exactly 957–999 (dynamic; `greetd` at 957, made
  locally). Nothing uses 250. The image's own `aresos.conf` uses 1001 only.
- **run** `systemd-sysusers --dry-run --root=<temp>` with the line: `Creating group 'aresos-tools' with GID 250.` and
  `... with UID 250 and GID 250.`; with 250 already taken it silently falls back to 999, the hazard change 5 names
  (a test pins the first; the image check fails on the second).
- 250 is far below the dynamic frontier and above the static block. The plain `u aresos-tools 250` form (not
  `250:250`) makes the group by name, so a taken GID would show up as a failed image check, never as another
  group's members.

## JUDGMENT-CALLs

1. **His two folders are made only when missing** (`:0700 :ares :ares`, tmpfiles' create-only prefixes, systemd
   259). A folder he already has keeps its own mode and owner at every boot. Alternative: plain `d ... 0700 ares ares`,
   which would chmod/chown his existing folders at every boot. Changing later: one line each.
2. **Folder order `Downloads`, `Documents`** (the agreed text's order; the drafts had `Documents` first). Check 7's
   "first configured folder" is `Downloads`.
3. **Vendored bytecode:** pip with `--no-compile`, then `compileall --invalidation-mode checked-hash` in place. pip's
   own bytecode embeds its temporary folder and timestamps; deployed files have mtime 0, so timestamp bytecode would be
   ignored and every proxy and service start would compile the SDK. Checked locally (pip 26.0.1, Python 3.14.8, the
   base's own): 712 files, identical over two runs. Control's own code ships without bytecode, as in CI. Changing
   later: one line.
4. **One install map, two callers.** `check-image.sh` recomputes the record by running `build.sh control-tree` on the
   checkout instead of a second copy of the map. The enable link is made from the unit's `WantedBy=` rather than
   `systemctl enable`, so the map runs without systemd; the image check then requires `systemctl is-enabled` =
   `enabled`. Like `aresos-subids`, the link is in `/etc`: a `systemctl disable` he makes himself would survive updates.
5. **Build-time generated check covers what the image ships** (`control/generated/*`, `control/settings/*`), using
   `generate.generated()` itself. `generate.py --check` also wants `docs/control/TOOLS.md`, which the source stage does
   not carry; `control-base` checks that file on every pull request.
6. **Package 23's source-stage test changed** (`test_the_source_stage_fetches_the_named_commit_and_keeps_only_mod` →
   `..._and_control`): its expected listing is now `['control', 'mod']` with a `docs/control/` decoy that must stay out.
   Required by agreed change 1; `linux-aresos` should see it.
7. **The service config is derived from the one `u` line of `aresos.conf`.** A second account declared there stops the
   build until someone says which one owns Control.
8. **gh version 2.103.3** if the RPM route goes on (see above).

## PLAN-GAPs

1. `gh`: GitHub's RPM needs `git` (above). The brief assumed the RPM installs beside Chrome's.
2. Agreed change 3 names "whatever list pins the enabled units": on today's `main` only `ci/release_diff.py`
   (release 27 against 13) lists units and users. The next release's diff must explain Control: the unit and its
   `multi-user.target.wants` link, `aresos-tools` (sysusers at boot), the files and vendored tree via `control.json`,
   the wheels via `requirements.lock`, and `gh` once its route is chosen. Likewise `ci/verify_release.py` binds a
   release to `os/` source trees only (release 27's list); a release carrying Control also comes from `control/` at
   its source commit (recorded in `control.json`'s `source_revision`).
3. The negative fixture check matches `fixture`, `.invalid`, `greenmail`, `dovecot`, `badmail` and `10.0.2.2`. Step 2's
   CI layer must use a CA subject and host names it would catch (as `control/ci/mail/run.sh` does: `mail-fixture.invalid`,
   `greenmail`, `dovecot`), or widen the pattern in the same commit.
4. `generate.py --check` cannot run on the image's source alone (TOOLS.md, JUDGMENT-CALL 5).

## What ran (all on the laptop unless a run ID is given)

- `python3 -m unittest discover -s os/tests -p 'test_control_image.py' -v`: 11 tests, OK.
- `python3 -m unittest discover -s os/tests -p 'test_aresos_desktop.py' -k ImageBuildTest -k ModJarPinTest`: 12 tests,
  OK.
- `PYTHONPATH=control python3 -m unittest test_reserved_words test_service_user test_unit -v` (in `control/tests`):
  5 tests, OK.
- `bash os/build.sh control-tree os control <scratch>`: `CONTROL_INSTALLED 57 files`; config and tmpfiles as above.
- The fixture scan of `image-checks.sh` against the laptop's own root (release 27, same base): `NO_FIXTURE_TRACES`,
  4.5 s; a planted CA and hosts line are found.
- pip trial into a scratch folder: report shape (`download_info.archive_info.hashes.sha256`), 28 wheels, 1733 files,
  checked-hash bytecode reproducible.
- **run 43547750786** `check_build=resolve`: success; `GH_FEDORA 2.97.0 too-old`.
- **run 43548179061** Control base on `1aba53a5`: success, `Ran 309 tests ... OK`, `Control base suite PASS`
  (includes `test_integration` with the moved config path and the two new tests).
- **run 43548178915** Control boundary on `1aba53a5`: success, `CONTROL_INTERACTIVE_ASK_PASS cases=17`.
- On `4a6d4c66` (all of Part A step 1 but this note): **run 43549031133** Control base success, `Ran 309 tests ... OK`,
  `Control base suite PASS`; **run 43549031150** Control boundary success, `CONTROL_INTERACTIVE_ASK_PASS cases=17`;
  **run 43549031127** Control Mail success, `Control Mail suite PASS` in all 8 jobs (the integration and Mail suites
  run the launcher with the config in `/usr/share/aresos/control`). Earlier runs on `1aba53a5`/`8c4105a9` were
  superseded by later pushes.
- Also run locally (they read `build.sh`): `test_everyday_account.py` 34 tests OK, `test_release27.py` 41 tests OK.

## Lead, 2026-11-14: gh moved, the first build

- **`gh` leaves 18c** (`linux-aresos`, 2026-11-14): nothing in 18c calls it; it comes with Chrome's files in brief
  18c-b, as option 2 (only the binary out of the pinned release RPM, its licence, its hash in the lock and in
  `control.json`). The `gh` step is out of `check-resolve.sh` again and its test is gone (`3087c59b`). The section on
  `gh` above is history.
- **run 43550587025** (`check_build=build`, head `53e0b79e`): failure in `image-checks.sh`. The check that no other
  unit names the service also required the unit file to contain its own name, which it doesn't. Fixed by the lead in
  `3087c59b` (only other files naming it fail; proven both ways on a fake tree).
- **run 43551606129** (`check_build=build`, head `3087c59b`, 44 minutes): **success**, `CHECK_BUILD_PASSED` and
  `CHECK_BUILD_VM_PASSED`. Control's lines: every recorded file and vendored path in the image as recorded; the
  managed Claude Code files; the unit enabled by `multi-user.target` only, `Type=simple`, named by no other unit, seen
  by the updater audit; `aresos-tools` UID and GID 250; tmpfiles modes, with his folders created only when missing;
  the config derived from `ares`; `aresos --help` as root and as `ares`, no MCP SDK in Python's own site-packages; no
  fixture CA or names in the image, and planted ones found.

## Step 2a (B2, first half): the Control VM test, checks 1 to 5 and agreed changes 7, 12, 14

Built by a Claude agent on Opus 5.5 (2026-11-14). Commits `d22414a2` (layer and hook), `17163b0c` (`check-build.sh`),
`1ee81d1b` (`os-image.yml`), `71c0c9d6` (fixes after run 1).

### Done

- `os/ci/overlay/checks.py`: the hook (agreed change 8). `layer_actions()` loads every `actions.d/*.py` beside it
  (each defines `ACTIONS = {name: function(request)}`), once; `check()` asks it only after its own fixed actions, so a
  layer adds actions and never replaces one; two files naming the same action fail.
- `os/ci/control/Containerfile`: the Control test layer, `FROM localhost/aresos:vm`. `actions.py` →
  `/usr/libexec/aresos-ci/actions.d/control.py`; `release_checks.py`, `own-mcp.py` → `/usr/libexec/aresos-ci/control/`;
  per run the pinned Claude Code → `/usr/libexec/aresos-ci/control/claude-2.1.319`, the fixture certificate →
  `/etc/pki/ca-trust/source/anchors/aresos-ci-mail-fixture.crt` (+ `update-ca-trust extract`), and
  `10.0.2.2 greenmail dovecot` appended to `/etc/hosts`; `bootc container lint`.
- `os/ci/control/runner.sh` (runner only): `start` makes the CA as `control/ci/mail/run.sh` does
  (`/CN=mail-fixture.invalid`, SAN `greenmail`, `dovecot`, `localhost`), a per-run password (`openssl rand -hex 24`,
  masked) in a copy of `dovecot.conf` (only the `args = password=` line changes), starts GreenMail and Dovecot with the
  image references and digests read from `run.sh`, published on `127.0.0.1` only (3465, 3993, 993; checked with
  `docker port`), and fetches Claude Code's `claude-code-linux-x64` package from the lock's URL, checking the lock's
  sha512 integrity and the version against `control/boundary/package.json` (`CLAUDE_CODE_PINNED` line). `layer` waits
  until the three TLS ports verify against the CA for their names, then builds `localhost/aresos:control` with
  `podman build --no-hosts` (so the hosts line lands in the layer). `stop` saves the servers' logs, removes them,
  fails if the password appears in any evidence file, and deletes the key, keystore, password and layer context. The
  key, keystore and password live in `$RUNNER_TEMP/aresos-control-fixtures` (outside checkout, build context and
  evidence); evidence gets only the password's SHA-256.
- `os/ci/control/actions.py` (guest): `control-files` (check 1), `control-claude-code-files` (change 7),
  `control-release` (change 12), `control-idle` (change 14), `control-fixtures` (the layer for step 2b),
  `control-entry-points` (check 3), `control-precondition` (check 4), `control-user-mcp` (check 5), `control-service`
  (check 2), `control-restart` (the end of the pass).
- `os/ci/control/release_checks.py`: change 12's check actions (below).
- `os/ci/control/own-mcp.py`: "his own" MCP server (stdlib, one tool `note`), for checks 5 and 6.
- `os/ci/control/control_vm.py` (runner): boots the disk like `vm.py` (own QMP and channel sockets, fresh overlay),
  sends the actions in order, writes each evidence file under `evidence/control/`, prints the PASS lines, runs every
  check even after a failure, then the power key: `CONTROL_VM_POWEROFF_CLEAN` (QEMU exit 0, guest SHUTDOWN event).
  Step times go to `evidence/control/vm/timings.json` and the log.
- `os/ci/check-build.sh`: `control|build)` shares the build mode's steps (the existing test reads the case from
  `build)`); control starts the fixtures first (trap stops them), builds the layer after the CI layer, makes the disk
  from `localhost/aresos:control` and runs `control_vm.py` instead of `vm.py`: `CHECK_BUILD_CONTROL_PASSED`.
- `.github/workflows/os-image.yml`: `check_build` options `['', resolve, build, control]`, nothing else; the bound
  file's new bytes recorded with `reviews/27-first-update-release/rebind.py pending` in
  `os/manifest/ci/16/pending-rebind.json` (same commit).
- `os/tests/test_control_vm.py`: 10 tests (hook, layer wiring, README step extraction, fixture inputs, own server,
  release checks on a stand-in root).

### Change 12: where the rehearsal's check actions live

`os/ci/control/release_checks.py`, standard library only, no Claude Code. As root in the booted guest after the update:
`python3 -I release_checks.py [check ...]`, or its text piped to `python3 -I -` (the release image has no CI layer; the
update rehearsal types into the guest's console, `owner_vm.py`'s `capture_json`). It prints one JSON line with every
check's values, then `CONTROL_RELEASE_CHECKS_PASS`, or `CONTROL_RELEASE_CHECKS_FAILED <names>` and exit 1; all checks
run even after a failure. Checks: `service_user` (UID, GID and group 250; nothing else has 250), `unit` (enabled,
active, running, main process UID/GID 250), `claude_code_files` (`/etc/claude-code` holds exactly its two files, equal
to `/usr/etc` and to `control.json`, root, recorded mode, no `managed-mcp.json`), `folders` (the two folders of
`proxy.json` exist as folders of `owner_uid`), `state_folders` (`/var/lib/aresos-tools` and
`/var/lib/aresos-operation-evidence` 0700, `/run/aresos-tools` 0711, all 250:250, and every entry inside the two state
folders too). The VM test runs the same file the same way (`control-release`).

### Decisions the code doesn't show (JUDGMENT-CALLs for the report)

1. **The fixture servers run under docker**, as `control/ci/mail/run.sh` does, with its images and digests read from
   it; podman stays for the image. Only the TLS ports are published (3465 SMTPS, 3993 IMAPS, 993); step 2b adds one if
   its runner-side seeding needs another.
2. **The owner's commands run with the system PATH** in this guest: `~ares/.local/bin` holds the CI layer's broken
   stand-ins for `bash`, `python3`, `env` and 22 more names (package 21, `shadow-path.sh`, exit 97), so his real PATH
   (`~/.local/bin` first) would run them. Claude Code is called by its full path, as the README step does; nothing is
   removed from his folder.
3. **CI-only environment for Claude Code:** `DISABLE_AUTOUPDATER=1`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`.
4. **Check order:** the idle footprint before anything talks to the service; check 2 after checks 3 to 5, so its
   SELinux scan covers what they made the service do (the service is still the boot's only invocation).
5. **"Exactly the tools":** each served tool equals the generated one in every generated key, names in the same
   order; keys the server adds are recorded (`keys_beyond_generated`: none in run 1). "Exactly as in user-mcp.json":
   every shipped field equal; anything Claude Code adds must be empty.
6. **Socket modes from today's `daemon.py`:** `act.sock` 0666, `admin.sock` 0600, `chrome.sock` 0600 (the brief's
   0666 for chrome is `8b7e799c`'s); Chrome's follow-up changes `SOCKET_MODES` in `actions.py`.
7. **The pass ends with the power key and QEMU's clean exit**, without `vm.py`'s offline journal read (where PR #60's
   `lsblk` fix lives); Control needs nothing from it.
8. **The throwaway second user** is a system user `aresos-ci-other` without home (UID 249 in run 1).

### Findings for the lead (not changed: `control/aresos_control/` is out of reach)

- **A start-up gap:** `Type=simple` reports active before the daemon binds its sockets; a call in that gap gets
  `transport_error` "Service connection lost; inspect operation_status with the same id, never repeat with a new id."
  (run 43556905450, `aresos control pending` right after `systemctl restart`). Harmless for a read, but the text sends
  him looking for an operation that never existed. The restart check now waits and records the misses.
- **`aresos admin ...` as `ares`** answers `transport_error` with that same text (the kernel refuses `admin.sock`,
  0600), not a permission message that points at `sudo`.
- **Idle cost:** about 10 wake-ups a second and 0.35 to 0.67 % of one CPU (runs 1 and 2, below). Most likely the service's loop wakes every
  0.1 s for `engine.expire()`; a longer select timeout would cut both. For the owner, who plays on this laptop.

### PLAN-GAPs

1. Brief B2 check 2 names `chrome.sock` 0666 (from `8b7e799c`); today's `daemon.py` makes it 0600 (decision 6).
2. The `check-build` job's build step has `timeout-minutes: 80` for build plus the Control pass; run 1 fitted. A longer
   VM test in step 2b (four interactive cases, Mail) may not, and raising it is not additive (`linux-aresos`).
3. The CI layer's shadowing stand-ins (package 21) sit in the daily user's `~/.local/bin` in every CI guest; step 2b's
   interactive cases run Claude Code and its hooks as `ares`: their PATH must not start with `~/.local/bin` either,
   or a hook's `env`/`python3` lookup would hit a stand-in. The managed hooks call `/usr/bin/...` by full path today.

### Runs (step 2a; budget 4 `check_build=control`)

- **run 43556905450** (`control`, head `1ee81d1b`, 16 min): failure, 3 of 10 checks. Green lines:
  `CLAUDE_CODE_PINNED 2.1.319 sha512-FO4Sd23B…oOQ== dabafec8…8eed`, `CHECK_BUILD_PASSED`, the three `Fixture ready`
  lines (TLSv1.3), `CONTROL_IMAGE_FILES_PASS`, `CONTROL_ETC_CLAUDE_CODE_PASS`, `CONTROL_IDLE_FOOTPRINT_RECORDED`,
  `CONTROL_FIXTURES_REACHABLE`, `CONTROL_ENTRY_POINTS_PASS`, `CONTROL_PRECONDITION_PASS`,
  `CONTROL_SERVICE_SANDBOX_PASS`, `CONTROL_VM_POWEROFF_CLEAN`. Failed: `control-release` (`folders`: read from
  `service.json`, which has none: they are in `proxy.json`; the other four checks passed: 250/250, active,
  `/etc/claude-code` equal, state folders 250:250 with 4 and 3 entries), `control-user-mcp` (the README step returned
  97 with no output: `bash` resolved to the CI stand-in, decision 2), `control-restart` (the start-up gap, above).
  Fixed in `71c0c9d6`.
  - Idle footprint (60 s, nothing using the service, one process, one thread): `memory.current` 31,866,880 B
    (peak 32,219,136), anon 23,166,976 B, file 4,415,488 B, RSS 36,024 KiB, PSS 24,451 KiB, swap 0; 601 context
    switches = **10.0 wake-ups/s**; CPU 208.1 ms = **0.35 %** of one CPU.
  - Check 3: `testapp list` 3 items, `aresos log` 2 items; MCP `mail` 28 tools and `control` 3 tools equal to
    `generated/`, protocol `2025-06-18`; refusals: other user via CLI and raw `act.sock` `permission_denied`, its
    proxy exit 1 "AresOS MCP proxy requires the configured owner user (real and effective UID).", `ares` on
    `admin.sock` `PermissionError` (errno 13), `aresos admin testapp fixture_configure` as `ares` `transport_error`.
  - Check 4: `boundary_not_installed` for group-writable ("must not be group- or world-writable") and for
    `mcp__testapp__send` removed ("missing permissions.ask: mcp__testapp__send"); both restores 0644 and
    `5747bb30…d376` (the shipped hash); baseline: cancelled → `failed`, 1 pending before the notice ack, 0 after.
- **run 43558438408** (`control`, head `71c0c9d6`, 43 min): **success**, every line of step 2a, in this order:
  `CLAUDE_CODE_PINNED 2.1.319 sha512-FO4Sd23B…oOQ== dabafec8…8eed`, `CONTROL_INSTALLED 57 files, 28 wheels, 2024
  vendored paths from 71c0c9d6…`, `CHECK_BUILD_PASSED`, `Fixture ready` ×3 (TLSv1.3), `CONTROL_IMAGE_FILES_PASS`,
  `CONTROL_ETC_CLAUDE_CODE_PASS`, `CONTROL_RELEASE_CHECKS_PASS`, `CONTROL_IDLE_FOOTPRINT_RECORDED {…}`,
  `CONTROL_FIXTURES_REACHABLE`, `CONTROL_ENTRY_POINTS_PASS`, `CONTROL_PRECONDITION_PASS`,
  `CONTROL_USER_MCP_INSTALL_PASS`, `CONTROL_SERVICE_SANDBOX_PASS`, `CONTROL_SERVICE_RESTART_PASS`,
  `CONTROL_VM_POWEROFF_CLEAN`, `CHECK_BUILD_CONTROL_PASSED`. Evidence `check-build-evidence` (5.1 MB): `control/`
  `files.json`, `etc-claude-code.json`, `release-checks.{json,txt}`, `idle-footprint.json`, `fixtures.json`,
  `entry-points.json`, `precondition.json`, `user-mcp-install.json`, `unit.json`, `security.txt`,
  `journal-aresos-toold.txt`, `selinux.txt`, `restart.json`, `fixtures/` (CA subject and fingerprint, image refs,
  ports, readiness, both servers' logs, the password's SHA-256 only), `vm/` (serial, QEMU, QMP, timings).
  - Check 1: 57 files, 2024 vendored paths, 6 folders, the one enable link, from `71c0c9d6`, equal to `build.sh
    control-tree` on the checkout; root-owned, recorded modes and hashes, no links, nothing extra, no
    `managed-mcp.json`.
  - Change 7: `/etc/claude-code` holds `CLAUDE.md` (`86433ed3…9819`) and `managed-settings.json` (`5747bb30…d376`),
    0644 root, each equal to `/usr/etc` and `control.json`. Change 12: all five checks true.
  - Change 14 (60 s idle, one process, one thread): `memory.current` 32,034,816 B (peak 32,788,480), anon 23,162,880 B,
    file 4,595,712 B, RSS 35,948 KiB, PSS 24,481 KiB, swap 0; 619 switches = **10.3 wake-ups/s**; CPU 404.0 ms =
    **0.67 %** of one CPU (run 1: 10.0/s, 0.35 %).
  - Layer: `greenmail` and `dovecot` resolve to 10.0.2.2 only; the system trust store verifies `greenmail:3993`,
    `greenmail:3465`, `dovecot:993` (subject `mail-fixture.invalid`, TLSv1.3, the servers' greetings); one anchor.
  - Checks 3 and 4: as in run 1 (other user UID 249).
  - Check 5: Claude Code `2.1.319 (Claude Code)` at `~/.local/share/claude/versions/2.1.319`, linked from
    `~/.local/bin/claude`; his `notes` entry (`/usr/bin/python3 -I …/own-mcp.py`) unchanged by both runs of the README
    step; `control` and `mail` as shipped, nothing duplicated; then `testapp`; `claude mcp list`: `notes`, `control`,
    `mail`, `testapp` all "✔ Connected".
  - Check 2: `User=aresos-tools`, `NRestarts=0`, every sandbox value as the unit says, one invocation in the boot's
    journal, main process UID/GID 250 ×4, `NoNewPrivs 1`, all five capability sets 0, `/run/aresos-tools` 0711 with
    `act.sock` 0666, `admin.sock` 0600, `chrome.sock` 0600, all 250:250. SELinux `Enforcing`, service context
    `unconfined_service_t`; 12 AVC denials in the boot, all `tuned_t` `chcon` `mac_admin` (the base's tuned), none
    naming the service. `systemd-analyze security`: "Overall exposure level for aresos-toold.service: 5.0 MEDIUM"
    (recorded, not asserted).
  - Restart: active again, 3 `transport_error` calls before the sockets answered (the start-up gap), 0 pending.
  - Times (s): boot to channel 31.3, files 3.0, `/etc/claude-code` 0.2, release 0.1, idle 60.0, fixtures 0.1, entry
    points 2.5, precondition 1.8, user MCP 4.1, service 0.0, restart 2.5; the pass 107.5 from QEMU's start to its
    exit. The whole job 43 min (run 1: 16 min, same steps; the runner's speed varies).

Step 2a is done: checks 1 to 5 and agreed changes 7, 12 and 14 green once (run 43558438408). Two of the four
`check_build=control` runs were used.

## Step 2b (B2, second half): checks 6 to 9, the clean baseline, check 2's SELinux scan again

Built by a Claude agent on Opus 5.5 (2026-11-14). Commits `d5d98d2f` (checks 6 to 9), `0af04070` (the workflow's own
Control step), `a4c9ac11` (check 8's encoded forms); later fixes are listed under "Runs (step 2b)".

### Done

- `os/ci/control/actions.py`: `control-ordinary` (check 6), `control-mail` (check 7), `control-interactive` (check 9),
  `control-passwords` (check 8), `control-selinux` (check 2's AVC scan again, over every PID the unit had in the
  boot), and `control-restart` now also requires the Mail account still ready. Order in `control_vm.py`'s `CHECKS`:
  1, 7 (change), 12, 14, fixtures, 3, 4, 5, 2, **6, 7, 9, 8**, 2 again, restart.
- `os/ci/control/sessions.py`: Claude Code sessions as `ares` with B1's `interactive_driver.py` and
  `interactive_model.py` unchanged (copied into the layer). tmux socket in `/tmp/aresos-ci-tmux` (0700 `ares`), work
  folder `~/ci-work`, `~/.claude.json` seeded as 18d does (onboarding, the synthetic key's last 20 characters, the
  folder trusted) on top of what check 5 wrote; the API address and synthetic key come from the session's
  environment, so the managed files stay as shipped. Each turn: wait for the prompt or the done marker, answer by
  text, resume after a native No (B1's marker), then **settle**: the turn is over when no model request came for 20
  s (the managed Stop hook's 15 s timeout plus 5 s). Per turn it records the model requests, the Stop continuations,
  the prompt shown or not, and every line of the turn's screens that names `AresOS` or a hook.
- `os/ci/control/own-hook.py`: his hooks (`Stop`, `UserPromptSubmit`: log a line; `PermissionRequest`: log and allow).
- `control/ci/image/mail_flows.py` (guest) and `control/ci/image/mail_fixture.py` (runner), as the brief puts new
  flows in `control/ci/image/`. The runner seeds three unread messages into Dovecot's INBOX before check 7 (one with a
  6 KiB binary attachment holding every byte value) and afterwards reads GreenMail's mailboxes and the read message's
  flags on Dovecot itself.
- `os/ci/control/control_vm.py`: per-action arguments built only when sent (the password stays in memory, no request
  is written anywhere), runner-side verification after checks 7 and 8, `CONTROL_PERMISSION_REQUEST_RECORDED {json}`
  printed whenever check 9 returns its record, check 6's numbers printed with its PASS line.
- **Workflow (linux-aresos's answer, 2026-11-14):** `check-build.sh control` ends with the disk
  (`CHECK_BUILD_CONTROL_DISK_READY`); a new step "Control VM pass" runs `check-build.sh control-pass` with its own
  `timeout-minutes`; an `always()` step stops the fixture servers (`runner.sh stop`, which also fails on a password in
  evidence); the job's limit is `${{ inputs.check_build == 'control' && 160 || 120 }}`. The build step keeps 80
  minutes for every mode. Record regenerated with `rebind.py pending` (own commit `0af04070`).
- `os/tests/test_control_vm.py`: 13 tests (3 new: his hooks, the layer's session pieces, the seeded attachment).

### Decisions the code doesn't show (JUDGMENT-CALLs for the report)

9. **Check 6's cases.** One session: turn 1 healthy, then `systemctl stop` (in the middle of the session, MCP proxies
   already connected), turn 2, then `systemctl start`, turn 3 (must be clean). Then the failed service: the drop-in
   `/run/systemd/system/aresos-toold.service.d/aresos-ci-fail.conf` (`ExecStartPre=/usr/bin/false`, the unit's own
   `Restart=on-failure` left as is, so it ends `failed` after its restarts), armed before a **fresh** session: turn 4,
   then the drop-in removed, `reset-failed`, start, turn 5 (must be clean). His tool is `mcp__notes__note`, allowed by
   his own user rule. Alternatives: a separate session per state (more starts, same numbers).
10. **Check 9 before check 8**, so the password scan also covers the asks' transcripts.
11. **The password is typed through a tmux paste buffer**: `tmux load-buffer -` reads it from stdin, `paste-buffer
    -d` types it into the pane where `getpass` reads it, and deletes the buffer. It is never on a command line or in a
    process's arguments. Root runs the onboarding in tmux (root stands in for his `sudo`).
12. **Check 8 searches** `/var/lib/aresos-tools`, `/var/lib/aresos-operation-evidence`, `~ares` (with Claude Code's
    transcripts), `/tmp` (with the services' private tmp folders), `/var/tmp` (the guest's own evidence folders),
    `/var/log`, `/run` and `/root`, every regular file, plus `journalctl -o export` of all boots, for the password and
    the three base64 forms Mail's scrubber knows (password; `\0user\0password`; `user\0user\0password`). The password
    must be in exactly its one file, the encoded forms nowhere. The runner searches the evidence written so far.
13. **Evidence per session is one gzip tar** (`control/ordinary/<case>.tar.gz`, `control/interactive/<case>.tar.gz`,
    `control/mail-claude.tar.gz`): the channel's frames are bounded at 4 MiB and the driver saves every changed
    screen. Model requests after the first keep only digests of the system prompt and tool list. A tar over 1 MB is
    rebuilt without the driver's intermediate `wait-` frames (the screens it acted on stay).
14. **Mail account values:** id `ci`, address `owner@mail.invalid`, login `ci-owner`, Dovecot for IMAP (993), GreenMail
    for SMTP (3465, implicit TLS); one distinct recipient per send (`first@`, `second@`, `third@mail.invalid`), so
    "exactly one arrival" is per send.

### Findings for the lead (step 2b; `control/aresos_control/` is out of reach, nothing changed there)

- **The managed Stop hook fails in every interactive session on Claude Code 2.1.319** (run 43563336637,
  `control/ordinary/stopped-mid-session.tar.gz`, screen `012-settled-1.txt` and `model/requests.json`):
  `Stop hook error: [... launch.py hook Stop]: AresOS hook failed; inspect pending work before continuing: hook: unknown
  fields are refused.` `hooks.main` validates the event against a closed field list (`session_id`, `transcript_path`,
  `cwd`, `permission_mode`, `last_assistant_message`, `prompt`, `hook_event_name`, `stop_hook_active`); 2.1.319 sends
  more. For `UserPromptSubmit` the extra field is **`prompt_id`** (his own hook logged the full input,
  `control/ordinary/own-hooks.jsonl`); the Stop event's extra field is not recorded (see the next point). Effects,
  with the service **healthy and nothing pending**:
  - every turn ends only through Claude Code's own cap: the Stop hook exits 2 nine times, the model gets **8 extra
    requests per turn** (each with one more "Stop hook feedback" block), and the screen shows the error four lines at
    a time, then "A hook blocked the turn from ending 9 consecutive times — overriding and ending turn. ... Set
    CLAUDE_CODE_STOP_HOOK_BLOCK_CAP to raise this limit." (`stop_hook_active` cannot help: validation fails first);
  - the `UserPromptSubmit` hook fails the same way and, by design, stays silent: **no pending reminder ever reaches the
    model** on a prompt;
  - so check 6 cannot pass, and check 9's "the Stop hook's reminder reaches the model" (case 2) cannot either.
  B1's container never ran the real hook (its notification stand-in replaces it) and 18d's print mode passes fewer
  fields, so neither saw it. A fix in `hooks.py` (accept and ignore unknown fields, or add `prompt_id` and the Stop
  event's field) is the lead's.
- **His own Stop hook did not run** in run 43563336637 (0 Stop lines; his `UserPromptSubmit` hook ran every turn;
  the screen says "Ran 1 stop hook"). Most likely Claude Code drops the other Stop hooks once one exits 2 with a
  blocking error; to be confirmed once the managed hook no longer fails.
- **A persistently failing service restarts without end:** with a CI drop-in `ExecStartPre=/usr/bin/false`, the
  unit's `Restart=on-failure` restarted it 41 times in 90 s and it never reached `failed` (the start limit never
  tripped). For a laptop, a broken service loops every ~2 s for good. The check's drop-in now also sets `Restart=no`.

### PLAN-GAPs (step 2b)

4. **B1's model double read a preparation's result only as text blocks.** Claude Code passes a real MCP server's
   result as one string, so against the real service the double failed (500, ten retries, check 9's first case out of
   time, run 43563336637). The container never exercised it (fixed approvals). Fixed in
   `control/boundary/interactive_model.py` (`texts()`) with a regression test in `test_interactive.py`; the container
   cases don't use that path.
5. **The time limits (linux-aresos's answer):** the build step (now ending with the disk) took 44 min in run 1
   (05:54:45 to 06:39:03), within its 80; the Control VM pass's step was 8 min with checks 6 to 9 cut short by the
   failures above. The step's 40 minutes stay provisional until a full pass is measured.

### Runs (step 2b; budget 5 `check_build=control`)

- **run 43563336637** (`control`, head `0af04070`, 58 min): failure. Green: `CLAUDE_CODE_PINNED 2.1.319 …`,
  `CONTROL_INSTALLED …`, `CHECK_BUILD_PASSED`, `CHECK_BUILD_CONTROL_DISK_READY`, `CONTROL_IMAGE_FILES_PASS`,
  `CONTROL_ETC_CLAUDE_CODE_PASS`, `CONTROL_RELEASE_CHECKS_PASS`, `CONTROL_IDLE_FOOTPRINT_RECORDED` (31.8 MB, 600
  switches in 60 s, 0.68 % CPU), `CONTROL_FIXTURES_REACHABLE`, `CONTROL_ENTRY_POINTS_PASS`,
  `CONTROL_PRECONDITION_PASS`, `CONTROL_USER_MCP_INSTALL_PASS`, `CONTROL_SERVICE_SANDBOX_PASS`,
  `CONTROL_SELINUX_AFTER_CHECKS_PASS`, `CONTROL_VM_POWEROFF_CLEAN`. Failed: `control-ordinary` (the Stop hook
  finding: 10 model requests and 8 continuations in every turn, also healthy; and the failed state never reached),
  `control-mail` (runner: `Time2Internaldate(None)`), `control-interactive` (the double's string result; the case's
  reserved operation then spoiled the other three baselines, as designed), `control-passwords` (no account, 0 files),
  `control-restart` (that reserved operation). Fixed in `10ef9df0` except the Stop hook.
- **run 43568250360** (`control`, head `10ef9df0`, **before** the hook fix of PR #61; 46 min: build step 06:53:41 to
  07:32:33 = 39 min, Control VM step 07:32:33 to 07:39:27 = 7 min, the pass 413 s from QEMU's start): failure, two
  checks. Per check:
  - Checks 1, 7 (change), 12, 14, fixtures, 3, 4, 5, 2: `CONTROL_IMAGE_FILES_PASS`, `CONTROL_ETC_CLAUDE_CODE_PASS`,
    `CONTROL_RELEASE_CHECKS_PASS`, `CONTROL_IDLE_FOOTPRINT_RECORDED` (31.9 MB, 10.05 wake-ups/s, 1.62 % CPU this
    time), `CONTROL_FIXTURES_REACHABLE`, `CONTROL_ENTRY_POINTS_PASS`, `CONTROL_PRECONDITION_PASS`,
    `CONTROL_USER_MCP_INSTALL_PASS`, `CONTROL_SERVICE_SANDBOX_PASS`.
  - **Check 6, `CONTROL_CHECK_FAILED control-ordinary`** (123 s): the old hook, as expected on this head. Every one of
    the 5 turns: 10 model requests, 8 Stop continuations, "Stop hook error ... unknown fields are refused" and "A hook
    blocked the turn from ending 9 consecutive times" on screen; healthy, stopped, started again, failed (now really
    `failed`: `Restart=no` worked) and recovered alike. His tool ran in every turn. Evidence
    `control/ordinary/{summary.json,own-hooks.jsonl,stopped-mid-session.tar.gz,failed-fresh-session.tar.gz}`.
  - **Check 7, `CONTROL_MAIL_FLOWS_PASS`** (41.5 s): onboarding with the password typed at the prompt (ready after
    `sent_policy: client`); read (untrusted, flags `[]` before and after, also `[]` on Dovecot itself); send from the
    CLI `done`, its Sent copy in `Posta`; delete into `Cestino` (gone from INBOX on Dovecot); the attachment from
    `~/Downloads` arrived byte for byte (6400 B, `1bd9d5f3…`); the received one saved as
    `~/Downloads/seeded-attachment.bin`, `ares`, 0600, hash equal; `~/outside-ci.bin` refused `file_refused`; the send
    through Claude Code: prompt shown, one answer "Yes", `done`. GreenMail: exactly one arrival for each of
    `first@`, `second@` (one attachment), `third@mail.invalid`, plus onboarding's self-send. Nothing pending after.
    That session also shows the old hook's 8 continuations. Evidence `control/mail-flows.json`, `mail-runner.json`,
    `mail-onboarding-screens.txt`, `mail-claude.tar.gz`.
  - **Check 9, `CONTROL_CHECK_FAILED control-interactive`** (120 s): failed **while packing its evidence**:
    `transcripts: 1057224 bytes even without the intermediate screens` (`tree_out` of `~/.claude/projects`, which by
    then holds the transcripts of checks 6, 7 and 9, over the 1 MB cap). The exception left the action before it
    returned, so the four cases' outcomes and the `CONTROL_PERMISSION_REQUEST_RECORDED` line are **not known** for this
    run; the later restart check found nothing pending, so the baselines were cleaned. Evidence only
    `control/vm/control-interactive-result.json` (the traceback).
  - **Check 8, `CONTROL_PASSWORDS_PRIVATE_PASS`**: `ls` of the state folder and the password folder and `cat` of the
    file refused for `ares` (Permission denied); folder 0700, file 0600, both 250:250; the password in exactly
    `/var/lib/aresos-tools/mail-passwords/ef173e6e…` and nowhere else (871 files in his home, 264 in `/var/tmp`, 477
    in `/run`, 14 in the state folder, journal export of all boots, `operations.jsonl`), no encoded form anywhere;
    the runner: 44 evidence files, none holding it. Hash in `control/passwords.json`.
  - `CONTROL_SELINUX_AFTER_CHECKS_PASS` (Enforcing, no denial naming the service over all its PIDs),
    `CONTROL_SERVICE_RESTART_PASS` (Mail account still ready, nothing pending), `CONTROL_VM_POWEROFF_CLEAN`.
- **Runs used: 2 of 5** `check_build=control` in step 2b.
- A text finding for the lead: the outside-folder refusal says "choose Documents, Downloads, Desktop or an
  owner-configured folder", while the image's `proxy.json` configures only Downloads and Documents.

### What the next step does, in order

1. **Check 9's evidence:** pack only what check 9 made: the transcripts whose files changed after the check began,
   one tar per case (or beside each case's tar), and make every packing failure return the summary, the
   `permission_request` record and `returncode 1` instead of raising past them (build the summary first, pack inside
   a try). Keep the 1 MB cap per tar and the 4 MiB frame in mind (`tree_out` in `actions.py`).
2. **Run 3 on a head with the hook fix** (the branch already merged `origin/main` with PR #61: `71a0e8d4`; `be435031`
   adds `forward` to the reserved words). Expected now: healthy, started-again and recovered turns 2 requests and 0
   continuations, nothing of ours on screen; stopped and failed turns 1 continuation each (the Stop hook's "service
   unavailable" block once, then `stop_hook_active` ends it) and that reason on screen. Record those numbers for the
   owner (agreed change 10, JUDGMENT-CALL). **Note in the evidence whether his own Stop hook now runs beside ours**
   (`own-hooks.jsonl`, `own_stop_lines`; the check requires one Stop line per stop attempt).
3. Check 9's four cases against the container's pin (`normal-permission-user`: `hook_calls 1, send_arrivals 1,
   owner_answers 0`); a difference is the brief's stop-and-report.
4. **Size the Control VM step** from the first full pass: run 2's pass took 413 s with check 6 at 123 s (the old
   hook's 9 blocks per turn); set the step's `timeout-minutes` to about 1.5 times the step's measured time (likely
   15) and the job's control limit to cover tools (≤ 20) + build (80) + that step + about 15, in one commit with
   `rebind.py pending`.
5. `check_build=control` green twice on the final head (the second by rerunning the same run), then PROGRESS.md with
   both runs' lines.

## Step 2c (B2): check 9's evidence, run 3, the time limits, two greens

Built by a Claude agent on Opus 5.5 (2026-11-14). Commits `3096c7f2` (check 9's packing), `20f85155` (fixes after
run 3), `2d1ad22f` (the workflow's limits, own commit, `rebind.py pending`).

### Done

- **Check 9's evidence can't lose its record** (`3096c7f2`). Each case copies only the transcripts its session wrote
  (size and mtime against a snapshot taken before it) into `interactive/<case>-transcripts.tar.gz`, beside
  `interactive/<case>.tar.gz`, and his `PermissionRequest` hook's lines into the case folder. `packed()` makes every
  tar of an action within one channel frame (1 MB a tar, 2.4 MB in all, since the 4 MiB frame carries base64): a tar
  that can't be made or doesn't fit is left out and named in the errors, so the check fails but still returns its
  summary and the `permission_request` record. Checks 6 and 7 pack the same way; each result carries
  `evidence_bytes`. Run 4: one case's transcript is about 600 KB, 146 KB as a tar; all eight tars of check 9 together
  768 KB.
- **Fixes after run 3** (`20f85155`), all in the checks, none in Control:
  - Check 9 compared receiver **rows** with the container's pin. testapp's receiver stores one row per recipient, and
    the fixture message has three (`alpha`, `beta`, `hidden`), so one send was 3 rows against the pin's 1 send (B1
    counts one POST per send). It now counts sends (the most rows any recipient has; a send reaches all three or
    none) and requires `operation_status` to name the same recipients as the receiver.
  - Check 6 read a turn's whole screen, which still shows the earlier turns above its prompt: turn 2's reminder
    counted again in turns 3 and 5. Now only the lines from the turn's own prompt on count; screens saved before the
    prompt shows (the driver saves one before typing it) are skipped.
  - His Stop hook: the check now requires 1 to 1 + continuations runs per turn and records each run's
    `stop_hook_active` (see "His own Stop hook" below).
  - `runner.sh stop`: GreenMail runs with auth disabled and logs `Created user login ci-owner for address ci-owner
    with password <it> because it didn't exist before.`, so the leak check deleted `greenmail.txt` and failed the
    step **in runs 43568250360 and 43572578699** (step 2b's record didn't say). The fixture servers' logs are now
    redacted first (the password read from its file, never from a command line; counts in
    `fixtures/redacted.txt`: run 4 greenmail 1, dovecot 0); the check still guards every other evidence file.
- **Time limits** (`2d1ad22f`): the Control VM pass's step from the provisional 40 to **10 minutes** (about 1.5 times a
  full pass: 6 min 21 s in run 3, 6 min 13 s in run 4, 6 min 54 s in run 43568250360); the job's limit for
  `check_build=control` from 160 to **125 minutes** (tools 20 + build 80 + the pass 10 + 15, linux-aresos's rule);
  every other mode keeps 120. Purely additive for the other modes; `rebind.py pending` recorded the workflow's new
  bytes with a note.
- `os/tests/test_control_vm.py`: 17 tests (4 new: the packing budget twice, a turn's own screen lines, only a case's
  own transcripts).

### Runs (step 2c; budget 5 `check_build=control` in steps 2b and 2c, 3 left at its start)

- **run 43572578699** (`control`, head `3096c7f2`, ~50 min: build step 40 min 4 s, Control VM step 6 min 21 s, the
  pass 380.4 s from QEMU's start): failure, but every check ran to its end. Green: every line of run 43568250360 plus
  check 7 and 8 again and `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1,
  "owner_answers": 0, "prompt_shown": true, "send_arrivals": 3}}` (the record now survives). Failed:
  `control-ordinary` (turns 3 and 5: turn 2's and 4's reminder still on screen above the new prompt, and the Stop
  count per attempt), `control-interactive` (`normal-yes` and `normal-permission-user`: 3 rows for one send), and the
  fixture stop step (GreenMail's log). Fixed in `20f85155`; nothing in Control.
- **run 43577034725** (`control`, head `2d1ad22f`, attempt 1; tools 08:42:50 to 08:44:28, build step 08:44:33 to
  09:23:54 = 39 min 21 s, Control VM step 09:23:54 to 09:30:07 = 6 min 13 s, the pass 372.7 s): **success**, every
  line: `CLAUDE_CODE_PINNED 2.1.319 sha512-FO4Sd23B…oOQ== dabafec8…`, `CONTROL_INSTALLED 57 files, 28 wheels, 2024
  vendored paths from 2d1ad22f…`, `CONTROL_GENERATED_MATCH`, `CONTROL_FILES_RECORDED`, `CHECK_BUILD_PASSED`,
  `CHECK_BUILD_CONTROL_DISK_READY`, `CONTROL_IMAGE_FILES_PASS`, `CONTROL_ETC_CLAUDE_CODE_PASS`,
  `CONTROL_RELEASE_CHECKS_PASS`, `CONTROL_IDLE_FOOTPRINT_RECORDED` (32.3 MB, 616 switches in 60 s = 10.3 wake-ups/s,
  0.75 % of one CPU), `CONTROL_FIXTURES_REACHABLE`, `CONTROL_ENTRY_POINTS_PASS`, `CONTROL_PRECONDITION_PASS`,
  `CONTROL_USER_MCP_INSTALL_PASS`, `CONTROL_SERVICE_SANDBOX_PASS`, `CONTROL_ORDINARY_SESSION_PASS {…}`,
  `CONTROL_MAIL_FLOWS_PASS`, `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1,
  "owner_answers": 0, "prompt_shown": true, "send_arrivals": 1}}`, `CONTROL_INTERACTIVE_ASK_PASS`,
  `CONTROL_PASSWORDS_PRIVATE_PASS` (the password in exactly 1 file, not in the journal; the runner: 54 evidence files,
  none holding it), `CONTROL_SELINUX_AFTER_CHECKS_PASS`, `CONTROL_SERVICE_RESTART_PASS`, `CONTROL_VM_POWEROFF_CLEAN`,
  `CHECK_BUILD_CONTROL_PASSED`; the fixture stop step green. Times (s): boot to channel 39.5, files 3.2, idle 59.4,
  entry points 2.7, precondition 1.8, user MCP 8.0, check 6 110.7, check 7 34.9, check 9 107.0, check 8 0.3,
  restart 1.5.
- **run 43577034725 attempt 2** (`gh run rerun`, head `2d1ad22f`; job 09:33:55 to 10:24:51, build step 09:37:15 to
  10:18:35 = 41 min 20 s, Control VM step 10:18:35 to 10:24:46 = 6 min 11 s, the pass 370.6 s): **success**, the same
  lines as attempt 1 in the same order, with the same `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user":
  {"hook_calls": 1, "owner_answers": 0, "prompt_shown": true, "send_arrivals": 1}}`; check 6 the same numbers (2, 3,
  2, 3, 2 model requests; 0, 1, 0, 1, 0 continuations; his Stop hook once per turn, on the second attempt in turns 2
  and 4; the reminder on screen only in turns 2 and 4); idle 32.0 MB, 749 switches in 60 s = 12.5 wake-ups/s,
  1.46 % of one CPU; GreenMail's log 1 redaction; the fixture stop step green.
- **run 43581194306** (`build`, head `2d1ad22f`; job 10:24:53 to 11:08:06 = 43 min 13 s, build step 10:28:30 to
  11:08:01 = 39 min 31 s, the Control VM step skipped as it should be in this mode): **success**, `CONTROL_INSTALLED 57
  files, 28 wheels, 2024 vendored paths from 2d1ad22f…`, `CHECK_BUILD_PASSED`, `CHECK_BUILD_VM_PASSED`.

Step 2c is done: `check_build=control` green twice on the final head `2d1ad22f` (run 43577034725, attempts 1 and 2)
and `check_build=build` green once on it (run 43581194306). Only this file changed after `2d1ad22f`.
- **Runs used:** 5 of 5 `check_build=control` (2b: 43563336637, 43568250360; 2c: 43572578699, 43577034725 twice). In
  the whole package: 1 resolve, 3 build (43550587025, 43551606129, 43581194306), 7 control (2a 2, 2b 2, 2c 3 with the
  rerun), 11 `check_build` in all: one above the brief's first "at most 10"; the lead set each step's budget.

### Check 6 in numbers (run 43577034725; the same in run 43572578699)

One session (turns 1 to 3), then a fresh session (turns 4 and 5). Each turn his model double calls his own tool
`mcp__notes__note` once and answers. "Seconds" includes the 20 s quiet window the check waits after the last model
request, so the turns themselves took 0.5 to 2 s.

| Turn | Service | Model requests | Extra | Stop continuations | His tool | His `UserPromptSubmit` | His Stop hook ran | Ours on screen |
|---|---|---|---|---|---|---|---|---|
| 1 | healthy | 2 | 0 | 0 | ran | once | once (first attempt) | nothing |
| 2 | stopped (`systemctl stop`, mid-session) | 3 | **1** | 1 | ran | once | once (only the second attempt) | the reminder, 4 lines |
| 3 | started again | 2 | 0 | 0 | ran | once | once | nothing |
| 4 | failed (`ExecStartPre=/usr/bin/false`, `Restart=no`), fresh session | 3 | **1** | 1 | ran | once | once (only the second attempt) | the reminder, 4 lines |
| 5 | recovered | 2 | 0 | 0 | ran | once | once | nothing |

What he sees in turns 2 and 4, under the model's answer (screen `022-settled-2.txt` of run 3, the same in run 4):

```
● Ran 1 stop hook
  ⎿  Stop hook error: AresOS held/unfinished work (untrusted app data; inspect status, do not resubmit unknown
  sends): {"message":"Service connection lost; inspect operation_status with the same id, never repeat with a
  new id.","service_unavailable":true} Resolve, cancel reserved work, or report uncertain outcomes to the owner
  before ending.
```

then one more answer of the model (the continuation), and the turn ends. In healthy turns the only trace is Claude
Code's own spinner text "running UserPromptSubmit hook" / "running Stop hook" for a moment, which his own hooks
cause as well. Nothing was pending after the check.

**His own Stop hook** (`own-hooks.jsonl`): it runs once per turn. In a turn where ours blocks the stop once (turns 2
and 4), Claude Code 2.1.319 does not run his on that blocked attempt; it runs his only on the attempt that ends the
turn (`stop_hook_active: true`). So his notification comes once, when the turn really ends. In run 43563336637 (the
old hook, blocking all nine attempts) his never ran, most likely for the same reason. **run** (`control/ordinary/own-hooks.jsonl`, runs
43572578699 and 43577034725). The Stop event of 2.1.319 carries `background_tasks`, `cwd`, `effort`,
`hook_event_name`, `last_assistant_message`, `permission_mode`, `prompt_id`, `session_crons`, `session_id`,
`stop_hook_active`, `transcript_path`; `UserPromptSubmit` carries `cwd`, `hook_event_name`, `permission_mode`,
`prompt`, `prompt_id`, `session_id`, `transcript_path`. The fixed hook (PR #61) accepts them.

### Check 9 against the container's pins (run 43577034725)

| Case | Mode | Prompt shown | His answers | Sends arrived | Operation | Other |
|---|---|---|---|---|---|---|
| no extra rule, "Yes" | normal | yes, the service's question first ("Send this fixture message?") | 1 | 1 (all three recipients once) | `done` | |
| no extra rule, "No" | skip-permissions | yes | 1 | 0 | `reserved` (then cancelled, notice acknowledged) | resumed after the No; 1 Stop continuation; the reminder in the model's requests 2 and 3 |
| user allow rule for `mcp__testapp__send`, "No" | skip-permissions | yes | 1 | 0 | `reserved` (cleaned) | the same as above |
| user `PermissionRequest` allow hook | normal | flashed, never answered | 0 | 1 | `done` | hook called once |

The fourth case equals the container's pin for `normal-permission-user` (`send_arrivals 1, hook_calls 1,
owner_answers 0`). The managed ask asked in every case without a `PermissionRequest` hook, also in skip-permissions
mode and with his allow rule for the send: no stop rule applies. The managed-level and skip-mode `PermissionRequest`
cases stay in the container (the managed files are not edited in the VM), where B1 pinned all four as approving with
one send.

### Findings for the lead (step 2c; `control/aresos_control/` is out of reach, nothing changed there)

- **The stopped-service reminder's text misleads.** With the service simply stopped or failed and nothing pending,
  the Stop hook's reminder carries the client's "Service connection lost; inspect operation_status with the same id,
  never repeat with a new id." There is no operation to inspect. It is the same text as the start-up gap (step 2a).
  Claude Code labels any blocking reason "Stop hook error", which reads as if something broke.
- The earlier ones stand: active before the sockets exist, `aresos admin` as `ares` without a `sudo` hint, about 10
  wake-ups/s idle (run 43577034725: 10.3/s and 0.75 % of one CPU; its rerun 12.5/s and 1.46 %), endless restart without the CI drop-in's `Restart=no`, the
  outside-folder refusal naming Desktop (run 4 again: "choose Documents, Downloads, Desktop or an owner-configured
  folder").

### For the report: B2 (append to `reviews/18c-image-test/REPORT.md`)

**PermissionRequest, in plain words.** A `PermissionRequest` allow hook of his own, at user level, approves the
managed ask interactively in normal mode: the prompt flashes, nobody answers, the send goes out once. That is the
accepted residual, and it equals the container's pin for that case. **run** 43577034725, `CONTROL_PERMISSION_REQUEST_RECORDED
{"normal-permission-user": {"hook_calls": 1, "owner_answers": 0, "prompt_shown": true, "send_arrivals": 1}}`. The
managed-level and skip-mode variants are proven in the container only (B1's pin: all four approve, one send each);
the VM doesn't edit the managed files. Without such a hook the ask asked every time, also in skip-permissions mode
and with his user allow rule for the send. B1 found the container's result equal to 18d's print-mode approval on
2.1.319 (**read** `REPORT.md`, run 43444623151); the VM case agrees with both. The prompt's flash is timing
dependent (B1); in the VM it showed in runs 43572578699 and 43577034725 and is recorded, not pinned.

**Done.** B2's checks 1 to 9 except the Chrome lines and `gh` (moved to 18c-b), as actions of the Control test layer
(`os/ci/control/`), run by `check_build=control` in its own workflow step after the build; the fixture servers
(GreenMail, Dovecot) on the runner's loopback, Claude Code 2.1.319 from the boundary's lock, B1's driver and model
double unchanged in the guest.

**Verified** (all **run**, head `2d1ad22f`, run 43577034725, attempts 1 and 2; log lines as printed):
`CONTROL_IMAGE_FILES_PASS` (check 1), `CONTROL_ETC_CLAUDE_CODE_PASS` (change 7), `CONTROL_RELEASE_CHECKS_PASS` (change
12), `CONTROL_IDLE_FOOTPRINT_RECORDED` (change 14), `CONTROL_FIXTURES_REACHABLE`, `CONTROL_ENTRY_POINTS_PASS` (check
3), `CONTROL_PRECONDITION_PASS` (check 4), `CONTROL_USER_MCP_INSTALL_PASS` (check 5), `CONTROL_SERVICE_SANDBOX_PASS`
(check 2), `CONTROL_ORDINARY_SESSION_PASS` (check 6), `CONTROL_MAIL_FLOWS_PASS` (check 7),
`CONTROL_PERMISSION_REQUEST_RECORDED {…}` and `CONTROL_INTERACTIVE_ASK_PASS` (check 9),
`CONTROL_PASSWORDS_PRIVATE_PASS` (check 8), `CONTROL_SELINUX_AFTER_CHECKS_PASS` (check 2's scan again),
`CONTROL_SERVICE_RESTART_PASS`, `CONTROL_VM_POWEROFF_CLEAN`, `CHECK_BUILD_CONTROL_PASSED`; `check_build=build` on the
same head: run 43581194306 (`CHECK_BUILD_PASSED`, `CHECK_BUILD_VM_PASSED`). Evidence: the `check-build-evidence`
artifact of each run (3 days).

**Check 6 for the owner (JUDGMENT-CALL, agreed change 10).** With the service healthy, an ordinary Claude Code turn
costs nothing extra and shows nothing of ours. While the service is stopped or has failed, each turn ends with one
extra model reply and a four-line "Stop hook error: AresOS held/unfinished work ... Service connection lost ..." under
the answer; his prompt, his own tool and his own hooks still work, and his own Stop hook runs once per turn, at its
real end. Once the service is back the next turn is clean. Question for the owner: should a session that never used
our tools get that reminder at all? Options: (a) keep it as it is: one extra reply (tokens) and four lines per turn
for as long as the service is down; (b) stay quiet when the service is unavailable unless this session used our tools
(the hook needs to know that, a change in `control/aresos_control/hooks.py`); (c) always stay quiet when the service
is unavailable, which loses the reminder in the one case it exists for: a send in flight when the service died.
The builder's lean: (b), with a reminder text that says "AresOS tools are not running" instead of "connection lost".
Changing later: a hook change and its container tests; the image stays the same.

**Not verified.** Real model cost (the double answers instantly; with a real model the extra reply costs one more
response); the Chrome lines (18c-b); `gh` (18c-b); the update path from release 27 (the next release's rehearsal);
his own Stop hook's behaviour on other Claude Code versions.

**PLAN-GAPs** (B2): the receiver counts per recipient while B1's pin counts sends (fixed in the check); GreenMail
logs the fixture password (fixed in `runner.sh stop`); `chrome.sock` 0600 in today's `daemon.py` (step 2a); the
model double's string results (step 2b).

**Measured times** (run 43577034725 attempt 1): tools 1 min 38 s, build to disk 39 min 21 s, Control VM step 6 min
13 s (boot to channel 39.5 s, the pass 372.7 s from QEMU's start: idle 59.4, check 6 110.7, check 9 107.0, check 7
34.9, the rest under 10 s each); the job 48 min 19 s (attempt 2: 50 min 56 s). Run 3: build 40 min 4 s, VM step 6 min 21 s.

## Left, in order (step 2c on)

1. The lead: append the "For the report: B2" text above to `reviews/18c-image-test/REPORT.md` (a Claude builder
   can't create that file name), with Part A's section and the JUDGMENT-CALLs; take check 6's question to the owner.
2. The Chrome follow-up after PR #27: two map entries (`chrome/qualification.json`, `chrome/build-id.json`), their
   checks, `SOCKET_MODES` from the merged `daemon.py`, and one more `check_build=control` run (a new budget).
3. The reviews (the lead's job): a package review and a high-stakes security review of the whole package.
4. `linux-aresos` reads the `os/` diff (agreed change 16), now including `os/ci/control/` and the workflow's limits.
5. The last step deletes this file.

Lead, 2026-11-14 (after step 2c): the report is assembled once, by the lead, after the Chrome follow-up and before
the reviews (Codex from 2026-11-17: a package review and a high-stakes security review of the whole package). Check
6's question is with the owner (board #254); its answer goes into the service-fix brief (board #233, #235, #237), not
this branch. Before `linux-aresos` reads the section below, bring it up to date: `check-resolve.sh` is back to main's
(`gh` is in 18c-b), and `os-image.yml`, `os/ci/control/`, `os/ci/overlay/checks.py` and `os/ci/check-build.sh` did
change (step 2a on).

## The `os/` diff for `linux-aresos`

- `os/Containerfile`: aresos stage copies `/source/control` from the existing source stage and runs `build.sh control`
  before `configure`; `FROM` lines and the other stages unchanged.
- `os/build.sh`: `source` also extracts `AresOS-<commit>/control`; new `control` mode (pip vendor, install map,
  manifest, self-checks) and `control-tree` (the map alone, for checks and tests). `packages` and `configure`
  unchanged.
- `os/ci/image-checks.sh`: early not-at-build check for `aresos-tools`/250 and the two folders; a Control section at
  the end (files, managed files, unit policy, sysusers, tmpfiles, config, launcher, no fixture traces).
- `os/ci/check-image.sh`: a new block after the existing lock check: `control.json` equals what `build.sh control-tree`
  makes from the checkout, from `HEAD`, wheels from `requirements.lock`.
- `os/ci/check-resolve.sh`: the one `gh` step and `gh` in the candidate request.
- `os/tests/test_control_image.py`: new, 11 tests.
- `os/tests/test_aresos_desktop.py`: the source-stage test expects `control/` beside `mod/` (JUDGMENT-CALL 6).
- `os/README.md`: one paragraph on Control in the image.
- Not changed: base digest, `packages.lock.json`, Chrome pin, accounts, sudo, polkit, masks, session, PATH,
  repositories, `os/config/`, `os/policy/`, `os/release/`, `os/owner-tools/`, `os/manifest/`, `os-image.yml`.
