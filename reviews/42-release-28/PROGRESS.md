# 42: Release 28, progress

Builder of step 1: a Claude agent (Opus 5.5), started 2026-11-16 from `main` e33ffc46; phase 2 (the dry run's
differences) a fresh Claude agent (Opus 5.5) the same day; review 1's fixes a fresh Claude agent (Opus 5.5) the same
day (below). Nothing has been published, signed or pushed to GHCR. The owner's OK for publishing release 28 has not
been given, and the ledger now stops a publish dispatch until it is (B1).

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
   step 3 (the rehearsal mode; it adds its kind `release-28` to package 42's ledger and raises its minute cap).
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
