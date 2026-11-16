# 42: Release 28, progress

Builder of step 1: a Claude agent (Opus 5.5), started 2026-11-16 from `main` e33ffc46. Nothing has been published,
signed or pushed to GHCR. The owner's OK for publishing release 28 has not been given.

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
    its name. Release 27's blanket "fontconfig cache trigger" pattern no longer applies to release 28; the
    32-bit caches (`-le32d4`) must not change.
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
- **Bindings:** five bound files changed (os-image.yml, registry_auth.py, rehearsal_guard.py,
  rehearsal-packages.json, test_owner_staged_release.py); `rebind.py pending` recorded them. Nothing under
  os/owner-tools/, os/release/ or docs/ waits.

## Verified

- Each changed test module run directly: `test_release28` 30 OK, `test_release27` 41 OK,
  `test_ci_api_permissions` 4 OK, `test_ci_step_environment` 4 OK, `test_checkout_sources` 8 OK,
  `test_build_tools` 3 OK, `test_ways_back_probe` 57 OK, `test_tools_local_wiring` 42 OK,
  `test_aresos_desktop` ModJarPinTest 7 OK (the whole module 188 earlier, its one failure was the callers list,
  now updated), `test_owner_staged_release` 7 OK (before the lead's stop on owner modules, see below).
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

- The dry run itself (phase 2). The rules for things only a real build shows are written from the sources:
  the alternatives Java's scriptlets register (the `@family@` form of the admin file is read from the
  alternatives binary's strings), Prism's bundle, the Java packages' files.
- `test_owner_equality` and `test_owner_step_limits` (brief 42, C): not run. The lead stopped every
  `os/tests/test_owner_*` module while the owner tools install runs on the laptop; `test_owner_equality` was
  stopped mid-run (its temp folder removed). Run them once the lead says the install is done, or in the hosted
  checks-only run.

## Left, in order

1. Push `pkg/42-release-28`; dispatch `check_build=resolve` on it, renew the mod jar's pin in
   `os/minecraft/desktop.lock.json` from `MOD_JAR_REPRODUCIBLE`, commit and push.
2. Phase 2 (after the lead checks the gating): one `dry_run_28` dispatch; explain every image difference or list
   it as open here.
3. Step 2 (Control's rules), step 3 (the rehearsal mode; it adds its kind `release-28` to package 42's ledger and
   raises its minute cap), steps 4 to 6 as the brief says.

## What the code doesn't show

- The two inputs are separate booleans, as the lead asked; dispatching both runs neither release job.
- Kind names: the rehearsal of step 3 is `rehearsal=release-28` (the brief), so the image kinds are
  `publish-28` and `dry-run-28`, not `release-28`.
- The ledger caps (dry runs 2, publish 1, resolve 2, checks 1, 1200 minutes) cover steps 1, 4 and 5: the brief's
  budget (C) names one release build, one publish, one checks-only suite; steps 1 and 4 each also dry-run and
  renew the pin. For the lead to confirm or change.
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
