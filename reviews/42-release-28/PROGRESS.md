# 42: Release 28, progress

Builder of step 1: a Claude agent (Opus 5.5), started 2026-11-16 from `main` e33ffc46; phase 2 (the dry run's
differences) a fresh Claude agent (Opus 5.5) the same day. Nothing has been published, signed or pushed to GHCR.
The owner's OK for publishing release 28 has not been given.

## Done

### Step 1, phase 1 (code and tests; the dry run is phase 2)

- **`os/ci/release_diff.py`: release 28's rules** (`Classifier28`, `RELEASES['28']`). `main(tools, release=...)`
  now runs release 27's comparison (unchanged, still against release 13) or release 28's against release 27
  (`os/manifest/releases/27.json`; its source on main is PR #35's squash `41b06513`, whose ten image trees equal
  the `source_trees` release 27 records, checked by a test). Each rule names its package:
  - os/config files changed or new since release 27: bytes equal the source, root-owned, the mode build.sh gives
    (its chmod 0755 line now has the desktop, its Java wrapper and the cover), no new extended attribute; the
    reason lists the commits on main that changed the file (`git log`, e.g. `23 (#36), 31 (#54), 40 (#71)`). New
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
  counts by its title; caps `dry-run-28` 2, `publish-28` 1, `resolve` 2, `checks` 1; 1200 minutes; one publish).
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

## Not verified yet

- A dry run that passes the image diff. Run 43832912792 confirmed the rules for Prism's bundle, the Java
  packages' files and alternatives, the pins, the schemas, the theme and rc.xml; phase 2's rules are proven
  against its evidence except release 28's own 32-bit cache bytes (see phase 2). The steps after the diff
  in the job (second VM pass onwards) have not run on release 28.
- The release 28 jobs on GitHub: only the resolve dispatch has run on the branch (both jobs skipped there). The
  publishing job (release_27's steps for release 28) has never run and must not before the owner's OK.
- `test_owner_equality` and `test_owner_step_limits` (brief 42, C): not run. The lead stopped every
  `os/tests/test_owner_*` module while the owner tools install runs on the laptop; `test_owner_equality` was
  stopped mid-run (its temp folder removed). Run them once the lead says the install is done, or in the hosted
  checks-only run.

## Left, in order

1. The lead decides when the next `dry_run_28` runs: now (to see `IMAGE_DIFF_PASSED` and the steps after the
   diff before step 2), or at the cut (step 4). Package 42's ledger allows 2 dry runs and one is spent
   (43832912792), so a dry run now leaves none for step 4 unless the lead raises the cap in
   `os/ci/rehearsal-packages.json` (a bound file).
2. Step 2 (Control's rules), step 3 (the rehearsal mode; it adds its kind `release-28` to package 42's ledger and
   raises its minute cap), steps 4 to 6 as the brief says.

## What the code doesn't show

- The two inputs are separate booleans, as the lead asked; dispatching both runs neither release job.
- Kind names: the rehearsal of step 3 is `rehearsal=release-28` (the brief), so the image kinds are
  `publish-28` and `dry-run-28`, not `release-28`.
- The ledger caps (dry runs 2, publish 1, resolve 2, checks 1, 1200 minutes) cover steps 1, 4 and 5: the brief's
  budget (C) names one release build, one publish, one checks-only suite; steps 1 and 4 each also dry-run and
  renew the pin. For the lead to confirm or change.
- The 32-bit font caches exist because the base ships fontconfig.i686 (for Steam). If a later base drops it, its
  caches vanish and every 64-bit cache loses its sibling: the diff stops, which is right for a base change.
- Prism's files are checked against the image's own `prism-files.sha256`, which build.sh writes right after
  extracting the tarball whose SHA-256 and size it checked; the diff does not download the tarball again.
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
