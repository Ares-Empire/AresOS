# Review 1 of package 42, step 1: release 28's diff rules and its release job

Commit reviewed: `5fb88f46` on `pkg/42-release-28` (merge base with `main`: `e33ffc46`). Anything pushed later is not covered.

Reviewer: a fresh Claude agent on Fable 5.2 that did not build this. Review only: no code, test or guide changed, nothing committed or pushed, nothing dispatched.

**How it was checked.**

- Read `AGENTS.md`, `CLAUDE.md`, `docs/REVIEW.md`, `briefs/42-release-28.md` (all of it), `reviews/42-release-28/PROGRESS.md`, then the whole diff `e33ffc46..5fb88f46`.
- Read the code the diff calls: `os/ci/check-build.sh`, `check-image.sh`, `publish.sh`, `build-mod.sh`, `build_tools.py`, `registry_auth.py`, `rehearsal_guard.py`, `verify_release.py`, `image_diff.py`, `os/build.sh`, `os/Containerfile`.
- Ran, one module at a time, bytecode off: `python3 -m unittest discover -s os/tests -p '<module>.py'` for `test_release28` (35 OK), `test_release27` (41), `test_ci_api_permissions` (4), `test_ci_step_environment` (4), `test_checkout_sources` (8), `test_build_tools` (3), `test_tools_local_wiring` (42), `test_job_accounting` (11), `test_keyboard_release` (5), `test_organization_budget` (19), `test_probe_native` (4), `test_rehearsal_auth` (9), `test_rehearsal_budget` (4), `test_rehearsal_history` (9), `test_rehearsal_retry` (7), `test_release_squash_binding` (7), `test_serial_staging` (19). All OK. No `test_owner_*` module ran. `git status` was the same before and after.
- Evaluated every job's `if:` of `os-image.yml` for 64,512 combinations of branch and inputs (a throwaway script, not committed).
- Weakened 57 conditions of `release_diff.py` one at a time, in memory only, and ran `test_release28` and `test_release27` against each (finding S4).
- Read the runs with `gh run view`: 43828756952 (resolve), 43832912792, 43843690867, 43847257976 (dry runs 1 to 3), and the evidence artifact of 43847257976 (its `result.json`, the classified paths, the guard's ledger).
- Recompiled this laptop's release 27 schemas with package 31's override (output to a scratch folder) and compared with the run.
- Ran `rehearsal_guard.budget` in memory on made-up histories: the publish caps at 0 (B1's fix), a third resolve (S3), both inputs (N1).

## Verdict

**CHANGES-NEEDED**, for one thing: B1. It is a small change.

The main structure holds. The dry run cannot publish, sign or push by its structure. The release job publishes only the image its own run built, checked and diffed, only on this branch, and never on a re-run. The diff rules that dry run 3 used are narrow and each one I traced stops on its near misses. The jar pin is bound three ways. All three dry-run claims are true.

What is missing is a technical stop between "the job exists" and "the owner said yes" (B1). S1 and S2 should be closed before step 4's dry run, because that run produces the diff the owner sees and it is the last dry run the ledger allows. S3 before the next resolve or checks dispatch. S4 and S5 before step 2 edits the same rules.

## BLOCKING

### B1. Nothing but a sentence stops `release_28` from publishing before the owner's OK

- **Where:** `os/ci/rehearsal-packages.json:185` and `:194` (`"publish-28": 1`, `"publish_cap": 1`); `.github/workflows/os-image.yml:497` (the job's `if:`) and `:20-23` (the input's description, "only after the owner's OK"); `os/ci/rehearsal_guard.py:533-538`; `os/ci/publish.sh:5-15`; `briefs/42-release-28.md:17-19` and `:26`.
- **What happens.** One command, `gh workflow run "OS image" --ref pkg/42-release-28 -f release_28=true`, publishes today:
  - the guard passes (publish-28: 0 of 1 used, about 122 of 1200 minutes, no active run);
  - the build, the image checks, the VM pass and the diff pass, as dry run 3 showed on the same sources;
  - `publish.sh` pushes `28-<commit>` to GHCR and signs it, and the signature goes to the public Rekor log.
- **Why it is likely enough to matter.** The publishing job will sit on the branch through steps 2, 3 and 4, with a fresh builder for each step. The brief names only `release_28` ("the `release_28` input and job", "One dry run of the job", "the dry run again"). The name `dry_run_28` appears only in the workflow and in PROGRESS.md. A builder who reads "the dry run again" and passes the one input the brief names has published.
- **Why it matters.** Publishing a release is the owner's decision (`CLAUDE.md`, "Owner decides"; the brief, "Owner OK needed before publishing"). It cannot be taken back: the brief says to delete nothing from GHCR, and a Rekor entry is permanent. It also spends the one publish the ledger allows, on a commit that is not the cut. The laptop itself is not at risk: it installs only what the pins name.
- **Fix.** Use the ledger that already exists.
  1. Set `"publish-28": 0` and `"publish_cap": 0` in entry "42" now. A `release_28` dispatch then stops at its first step (`STOP: publish-28 dispatch allowance exhausted`, `rehearsal_guard.py:399-400`), before any build.
  2. After the owner's OK, the integrator raises both to 1 in a commit that names the OK (date, board number) in the entry's `budget` text, and refreshes the pending list. Then the dispatch.
  3. Adjust `test_release28.py:838-839` and `:872`: caps 0 until the OK; a test that a publish-28 dispatch stops at caps 0.
  4. Say in PROGRESS.md, under "Left", which input is which, with the exact command for the dry run.
  A stopped slip still counts as a publish-28 dispatch, so the OK commit would then set the dispatch cap to 2. That is the right cost.

## SHOULD-FIX

### S1. `GENERATED_28` keeps release 27's broad globs that explain nothing in release 28

- **Where:** `os/ci/release_diff.py:92-109`, `:409`, `:1137-1145`.
- **What is true.** Dry run 3 used the "generated" rule for 11 paths: `usr/share/rpm/rpmdb.sqlite`, six files in `usr/lib/sysimage/libdnf5/`, two `var/lib/dnf/repos/*/countme`, `var/log/dnf5.log` and `var/cache/ldconfig/aux-cache`. Nothing matched `etc/selinux/targeted/*`, `var/lib/selinux/*`, `usr/share/icons/*/icon-theme.cache`, `usr/share/applications/mimeinfo.cache`, `run/*`, `var/cache/libdnf5*`, `usr/lib/sysimage/rpm/*` or `etc/ld.so.cache`. So two full builds give the same SELinux policy store and the same caches.
- **What happens.** At the cut, any change under `/etc/selinux/targeted` or `/var/lib/selinux` passes as "SELinux policy store rebuilt by the transaction", with no content check and no package named. The same for a new desktop entry or icon ("Chrome desktop entry", "Chrome icons": release 27's reasons, wrong for release 28). The owner's summary would show a count under "generated" and nothing else.
- **Why it matters.** The brief (A.3) wants every difference traced to a merged package. These globs trace to none, and the SELinux policy is exactly the kind of change that should be read by a person. The cut's dry run is the last one the ledger allows, so this has to be right before it runs.
- **Fix.** Make `GENERATED_28` the patterns the dry run needed: the rpm database file, `usr/lib/sysimage/libdnf5/*`, `var/lib/dnf/*`, `var/log/dnf5.log*` and `var/cache/ldconfig/aux-cache`. Drop the rest, so a change there stops and gets its own rule with its real cause (step 2 will need one if Control adds a desktop entry). Add a negative test per dropped pattern, as line 366 of the test does for the font caches.

### S2. A commit on this branch counts as "a merged package"

- **Where:** `os/ci/release_diff.py:872-884` (`origin`), `:886-903` (`config_rule`), `:947-959`; PROGRESS.md line 17 ("the commits on main that changed the file").
- **What happens.** `origin()` reads `git log 41b06513..HEAD`, which is this branch, not main. Any commit counts, with whatever its subject says. The config rule then needs only "the image's bytes equal the checkout's", which is true for every file the build copies. So an `os/config` change committed on `pkg/42-release-28` (a fix made on the branch, or a wrong conflict resolution when main is merged in at the cut: merge commits are left out of the log, so the reason would name only the real packages) is explained and shipped. The reason would read "from 23 (#36), 42 step 4" at best.
- **Why it matters.** The brief: "Everything on `main` at the cut commit", "nothing of Control is added on this branch". Nothing in the job holds that. Today the branch is clean: it changes no file under `os/config`, `os/policy`, `mod/`, `os/build.sh` or `os/Containerfile` (checked with `git diff --stat`).
- **Fix.** In `main()` for release 28, one stop: against `git merge-base HEAD origin/main` (the checkout fetches full history and every branch), the image sources must be equal: `os/config`, `os/policy`, `os/build.sh`, `os/Containerfile`, `os/.containerignore`, `os/packages.lock.json`, `os/google-chrome.lock.json`, `os/tests/audit.py`, `os/keys`, `os/manifest/base.json`, `mod`; and `os/minecraft/desktop.lock.json` may differ only in the AresOS jar's `sha256`. Record the merge base in `result.json`. Take `origin()`'s labels from that commit's history. One positive and one negative test.

### S3. The `resolve` and `checks` caps are not read by the runs they limit

- **Where:** `.github/workflows/os-image.yml:181-227` (the `check-build` job has no guard step), `:78-83` (the checks guard step runs only on the package 13 and 27 branches); `os/ci/rehearsal-packages.json:186-187`; `os/ci/rehearsal_guard.py:361-364`, `:399-400`.
- **What is true.** For `dry-run-28` and `publish-28` the caps and the 1200 minutes are checked in the job's first step after checkout, before any build. Infra failures count: run 43843690867 died after 6 minutes in the tool install and dry run 3's guard counted it (`dry-run-28: 3`). A re-run stops every later guard (`run_attempt == 1`). That part is sound.
- **What happens.** A third resolve (say the cut's resolve dies on the same mirror) or a second checks-only run starts and runs to the end: neither job asks the ledger. The count is only read by the next dry run or by the publish dispatch, which then dies at its guard and is itself counted. If that is the publish dispatch, the one publish allowance is gone and a ledger commit must move the head after the owner's OK. The same trap for a dispatch whose title the ledger does not know (`check_build=build`, `switch_from_run`, a rehearsal mode before step 3 adds it, `release_27` with `release_28`): every later guard ends in a bare `ValueError` at line 362.
- **Why it matters.** It fails closed, so it is cost, not safety. But it surfaces at the worst moment, in the publish run.
- **Fix.** For checks: add `github.ref_name == 'pkg/42-release-28'` to the step's `if:` at line 79 (the job already has `actions: read`). For resolve: keep `check-build` without a token, and write into PROGRESS.md that every dispatch on this branch is preceded by the guard's local mode on a clean history, for example `REHEARSAL_PACKAGE=42 python3 os/ci/rehearsal_guard.py resolve 120` (it stops with "no dispatch remains"). Give line 362 a `STOP:` message that names the title.

### S4. Many conditions of the new rules have no negative test

- **Where:** `os/tests/test_release28.py`; PROGRESS.md line 120 covers phase 2's conditions only (those are tested: each of mine there was noticed).
- **What was done.** 57 conditions weakened one at a time; 23 made a test fail, 34 did not (with `test_release27` added: the same 34).
- **Not noticed, in `Classifier28`:**
  - config: a file with no origin commit; a new folder with another owner or mode;
  - manifest: another owner or mode; `packages.lock.json` not equal to the source; `packages.txt` not equal to `rpm -qa`; `prism-files.sha256` or `aresos-mod.json` already in release 27; `updaters.json` new;
  - Minecraft inputs: a path release 27 had, or an extended attribute; any other folder under `usr/share/aresos/minecraft` or another folder mode; a pinned file with another owner or mode; another size;
  - Prism: another owner or an extended attribute, or a path release 27 had; an absolute link that stays inside the bundle;
  - alternatives: a record release 27 had; its owner, mode or attributes;
  - schemas: another owner, mode or attribute of `gschemas.compiled`; the image's override not equal to the source; the key's default changed beside the override's desktop value (`release_diff.py:718`); a changed range or choice (`:720`); no differing key at all;
  - `etc/shadow`: another owner or mode; font caches: another owner, mode or attribute, or an old cache that was not root's 0644; the rpm database's metadata.
- **Not noticed, in `main()` (shared with release 27, untested there too):** the revision label, the set of changed labels, the OCI runtime config, release 28's base ancestry, a unit changed only as "generated", release 27 built on another base, release 27's lock differing from its source, an unreviewed unmasked unit, and `status` in `result.json` when a path is unexplained (`publish.sh:15` reads it).
- **Why it matters.** Each condition is right today. But step 2 adds Control's rules to this class with another builder, and a condition without a test can be lost without anyone seeing it. In this file a lost condition is a rule that explains too much.
- **Fix.** One near-miss row per condition in `test_near_misses_stay_unexplained` and `SchemaTest`; for `main()`, variants of `MainSmokeTest` (it already holds the labels, configs and ancestry as data). The fixture forces owner 0 and no attributes; let a test override them per path, as `self.attributes` already does.

### S5. The largest rule checks nothing but the path

- **Where:** `os/ci/release_diff.py:1123-1127` (`package_rule`).
- **What happens.** 470 of the 1,585 paths (142 files, 209 links, 119 folders) are explained as "file of a package added by package 23" because `rpm -ql` of the four Java packages names the path. Owner, mode, link target and bytes are not looked at. A later build step that changed a Java file, or left one setuid, would be explained. Prism's files, right beside it, are held to root, no setuid, not writable, no attributes, and a hash.
- **What is true today.** In dry run 3 all 470 are new, root's, without setuid, setgid, group or world write, and without extended attributes (read from the run's classified paths).
- **Fix.** Add to the rule now: root's; for files and folders no setuid, setgid, sticky, group or world write; no extended attribute. The dry run's data shows these cannot stop the Java packages at the cut. For the bytes, record `rpm -V` of the added packages from the new image in `result.json` at the next dry run without stopping on it, and make it a stop once one run shows it clean.

## NIT

- **N1. Both inputs together spend the publish allowance.** `os-image.yml:2`: with `release_28` and `dry_run_28` no job runs (checked), but the run is titled "Package 28 image release", so the guard counts it as the one publish-28 dispatch. Decide which allowance that slip should cost: testing `dry_run_28` before `release_28` in `run-name` makes it a dry run. PROGRESS.md line 183 should say it is counted.
- **N2. A tag named like the branch.** `os-image.yml:497`, `:607`, `publish.sh:8-13`, `rehearsal_guard.py:512`, `:528` compare the short ref name, which a tag `pkg/42-release-28` also has. Only someone with write access can make one, so it is no new power, but the signature would then say `refs/tags/…`. Use `github.ref == 'refs/heads/pkg/42-release-28'` in the two new jobs, and let step 6's `verify_release.py` pin the `refs/heads` identity as it does for release 27.
- **N3. The old release jobs do not exclude the new inputs.** `image` (`:229`) and `release-27` (`:386`) run with `release_13` or `release_27` plus `dry_run_28` on their own branches. They need their own release input and their ledgers are spent, so nothing follows; add the two terms for symmetry.
- **N4. Prism's bundle is checked against the image's own list.** `release_diff.py:905-920`. PROGRESS.md says so. `build.sh` writes the list right after it checked the tarball's pin, so it holds as long as `build.sh` does. To bind it to a reviewed value, pin the list's SHA-256 in `desktop.lock.json` (dry run 3: `9df32315…`, 679 files).
- **N5. The diff shows what differs, not what failed to arrive.** A changed `os/config` file that the build did not copy would be equal to release 27 and never listed. Cheap converse in `extra()`: every regular file `os/config` changed since release 27 is in the image with the source's bytes; every removed one is absent.
- **N6. One mirror outage costs the publish.** `publish-28` is capped at 1 and the tool install has failed on `snapshot.ubuntu.com` three times in these jobs (twice for release 27, once here). The retry then needs a ledger commit, so a new head. Word the owner's OK for the image source, not for one commit.
- **N7. PROGRESS.md wording.** Line 167: this job has no second VM pass; after the diff come only the credential cleanup, the publish step and the evidence. Line 17: see S2.

## The two PLAN-GAPs

- **Source trees (line 193): real, rightly deferred.** `verify_release.py:59-61` accepts exactly release 27's ten paths, and `:44` knows only release 27's job name. Since package 23 the image also follows `mod/` (fetched at the commit by `build.sh source`) and `os/minecraft/`. Release 28's record is written in step 5 and `release.json` moves in step 6, so nothing in step 1 depends on it. One thing for step 3: on this branch `verify_release.py:85-88` will refuse release 27 ("runtime payload changed"), because `os/config` moved on; the rehearsal mode needs what 22d got at `:62-84`.
- **`build-mod.sh --twice` (line 197): real but small.** The brief's step 1 itself says "through `check_build=resolve`", and `check-build.sh:16` runs that script. "On the pushed cut commit" is step 4's renewal; the resolve cap has one left for it.

## Gaps against the brief's step 1

- No rule is missing for what rides today. Control's rules are step 2.
- "One dry run": three were dispatched (39 differences, a mirror outage, the pass). The ledger's `budget` text records the lead's two raises. One dry run is left for the cut.
- Brief C: the hosted checks-only run has not run on this branch, and `test_owner_equality` and `test_owner_step_limits` were stopped by the lead. So the full suite has not run on this head anywhere. The 17 modules listed above pass here. The release jobs run no unit tests, so the checks-only run should come before the cut (see S3 for its cap).

## Checked and found sound

- **The dry run cannot publish.** Over all input combinations on this branch, `release-28` runs only for `release_28` alone and `release-28-dry-run` only for `dry_run_28` alone (`full_model` aside). No job with `packages: write` or `id-token: write` can run on this branch when `dry_run_28` is set. The dry-run job has `contents`, `packages` and `actions` read only, no OIDC token, no publish step, no secret but the job token, and `publish.sh` is not reachable from its steps. `rehearsal_guard.py:537` also refuses the `dry-run-28` kind at the publish gate. In run 43847257976 GitHub skipped the publishing job.
- **`check-build` and `switch`** run for neither input. With `checks_only` added only the two checks jobs run; with a rehearsal mode added only the read-only rehearsal job starts, and its guard stops it.
- **Other branches.** The two new jobs need `pkg/42-release-28`; `publish.sh` maps only that branch to release 28 and refuses the rest before its guard; the guard, `build_tools.py` and `registry_auth.py` each check the branch and the kind again.
- **A re-run cannot publish.** The guard is the first step and stops on `run_attempt` 2; so does every later run on the branch.
- **One image, built, checked, diffed, published.** `check-build.sh` builds `localhost/aresos:check` as a release from `git rev-parse HEAD`, runs `check-image.sh` on it, then tags exactly it `localhost/aresos:ci`. Nothing later builds, pulls or tags that name. The diff reads `localhost/aresos:ci` and requires its revision label to be this run's commit. `publish.sh` requires `status` passed, refuses an existing tag, copies `containers-storage:localhost/aresos:ci`, and signs the digest of that copy. The publish step runs only if every step before it passed.
- **The ledger for the two release kinds:** see S3, "What is true".
- **The jar pin.** Resolve run 43828756952 on `74927368`: two clean builds, both `8090554997fd…`. Dry run 3 on `e4a0f861`: `MOD_JAR_BUILT 8090554997fd…`, `MOD_JAR_PINNED`. A release build stops on other bytes (`build.sh`, the kind chosen by the job's name, never by an input); `check-image.sh` compares the image's record and lock with the reviewed lock; the diff requires the jar's SHA-256, the record (pin, this commit, pin) and the image's copy of the lock. The dry run also proves no other pin has vanished: it fetched every pinned input.
- **The three dry-run claims.** 43832912792: stopped in the diff, `STOP: 39 unexplained image differences`. 43843690867: failed in "Install pinned tools" on `snapshot.ubuntu.com` 502/503, before any build. 43847257976 on `e4a0f861`: `IMAGE_CHECKS_PASSED`, `CHECK_BUILD_VM_PASSED`, `IMAGE_DIFF_PASSED: 1585 changed paths, all explained`; the counts add up to 1,585. `5fb88f46` differs from `e4a0f861` in PROGRESS.md only.
- **Dry run 3's classification, read path by path for the small rules:** 65 config paths, all files package 23, 23b, 23d, 30, 30b, 31 or 40 added or changed; 70 font caches (68 rebuilt, 2 new, both formats); no path removed; no path with an extended attribute; no package path that release 27 already had; labels differ in the revision only; theme equal to package 31's pin; the one unit change is 23's three recovery drop-ins.
- **The schema rule against real files.** This laptop's release 27 `gschemas.compiled` has the SHA-256 the run recorded for release 27. Recompiled with package 31's override it has the SHA-256 the run recorded for release 28. `schema_changes` reports the one key on those files and returns nothing when a second, made-up override is named.
- **The rules I traced:** fonts (name, both formats, header, MD5 of the folder, folder kind), the updater audit (same units, only `sources` may grow, only by a new `os/config` drop-in of that unit with the source's bytes), `etc/shadow` (only the date field), alternatives (every target a file of an added package, links only through `/etc/alternatives`), Minecraft inputs (SHA-256 and size from the lock), Java's two man folders. Each stops on the near misses its tests name.
- **Release 27's rules** are unchanged: the edits to shared code are the release table and names (`test_release27` 41 OK).
- **Bound files:** the pending list holds the five changed files with their bytes (`test_checkout_sources` 8 OK). Nothing under `os/owner-tools/`, `os/release/` or `docs/` changed.

CHANGES-NEEDED
