# 18c image part: progress (Part A, step 1; B2, step 2a)

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
| 6 Enabled, never holds the session | image side done; the failed-service session check is B2 check 6 (step 2) |
| 7 Config in `/usr/share/aresos/control` | done; image check done; booted-guest check `control-claude-code-files` (step 2a) |
| 8 `checks.py` hook | done (step 2a): `actions.d` |
| 9 Fixture servers, negative check | negative check done; fixture servers and CI layer done (step 2a) |
| 10 Owner's yes before merge | open (lead) |
| 11 Folders by tmpfiles | done |
| 12 Rehearsal check actions | done (step 2a): `os/ci/control/release_checks.py` |
| 13 Reserved words test | done |
| 14 Idle footprint | measured (step 2a): ~32 MB, 10 wake-ups/s, 0.35–0.67 % of one CPU |
| 15 `os-image.yml` additive, lead first | done (step 2a): one option, own commit `1ee81d1b` |
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

## Left, in order (step 2b on)

1. Step 2b: B2 checks 6 (ordinary session, service stopped and failed by a CI drop-in under `/run/systemd/system`),
   7 (Mail flows in `control/ci/image/`), 8 (passwords), 9 (the four interactive asks with B1's driver), as actions
   in `os/ci/control/actions.py` and lines in `control_vm.py`'s `CHECKS` (Mail and the asks after check 5, which
   installs Claude Code; check 2's SELinux scan should move or repeat after them). On the runner the password is
   `$RUNNER_TEMP/aresos-control-fixtures/password` (0600; never into evidence); the guest reaches `greenmail:3993`,
   `greenmail:3465` and `dovecot:993` through the system trust store. Seeding and reading arrivals run on the runner
   against `127.0.0.1`. Mind PLAN-GAPs 2 and 3.
2. `check_build=control` green twice on the final head (rerun of the same run).
3. The Chrome follow-up after PR #27: two map entries, their checks, `SOCKET_MODES` from the merged `daemon.py`.
4. The reviews (the lead's job): a package review and a high-stakes security review of the whole package.

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
