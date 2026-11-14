# 18c image part: progress (Part A, step 1)

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
| 7 Config in `/usr/share/aresos/control` | done; image check of `/etc/claude-code` done; the booted-guest check action is step 2 |
| 8 `checks.py` hook | step 2 |
| 9 Fixture servers, negative check | negative check done; the CI layer is step 2 |
| 10 Owner's yes before merge | open (lead) |
| 11 Folders by tmpfiles | done |
| 12 Rehearsal check actions | step 2 (they need a booted guest) |
| 13 Reserved words test | done |
| 14 Idle footprint | step 2 (measured in the guest) |
| 15 `os-image.yml` additive, lead first | step 2 |
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
   the wheels via `requirements.lock`, and `gh` once its route is chosen.
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
- Control Mail on `1aba53a5` was cancelled by the next push; base, boundary and Mail on `8c4105a9` are listed below
  once they finish.

## Left, in order (step 2)

1. Get the `gh` answer from `linux-aresos` (through the lead); add `os/gh.lock.json`, the install step, its image
   check and the README line in one commit.
2. Tell the lead before the first `os-image.yml` change (agreed change 15); then add the `control` choice in its own
   commit, purely additive.
3. `check_build=build` once on the Part A head. Watch for: pip and `compileall` inside the build, the two self-check
   lines (`CONTROL_INSTALLED ... wheels`, `CONTROL_GENERATED_MATCH`), `bootc container lint`, every new `PASS` line of
   `image-checks.sh`, and `check-image.sh`'s `Control in the image is this checkout`.
4. B2: `os/ci/control/` (layer, `control_vm.py`, its actions file), the `checks.py` hook (change 8), the check actions
   for the rehearsal (change 12) and the booted-guest `/etc/claude-code` check (change 7), the idle footprint
   (change 14), check 6 with the service stopped and failed.
5. The Chrome follow-up after PR #27: two map entries, their checks, the socket modes from the merged `daemon.py`.

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
