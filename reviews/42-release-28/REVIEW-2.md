# Fix check of review 1 (package 42, step 1)

Range checked: `3980c5ef..8b427862` on `pkg/42-release-28` (commits `90c9d862`, `1df72e13`, `8b427862`). Anything pushed later is not covered.

Reviewer: the same Claude agent on Fable 5.2 that wrote review 1. It did not build the fixes. Review only: nothing changed but this file, nothing committed, pushed or dispatched.

Scope: review 1's findings and what their fixes touched. Not a fresh hunt.

**How it was checked.**

- Read the whole range, and PROGRESS.md's account of each fix.
- Ran, one module at a time, bytecode off, `python3 -m unittest discover -s os/tests -p '<module>.py'`: `test_release28` (59 OK), `test_release27` (41), `test_ci_api_permissions` (4), `test_ci_step_environment` (4), `test_checkout_sources` (8), `test_build_tools` (3), `test_job_accounting` (11), `test_keyboard_release` (5), `test_probe_native` (4), `test_rehearsal_auth` (9), `test_rehearsal_budget` (4), `test_rehearsal_history` (9), `test_rehearsal_retry` (7), `test_release_squash_binding` (7), `test_organization_budget` (19). Of `test_aresos_desktop` only the changed class (`-k ModJarPinTest`, 7 OK). All OK. No `sudo`, no `test_owner_*` module, no dispatch. (`test_release28` and `ModJarPinTest` put a stand-in script named `sudo` on a private PATH; the real one is never called.) `git status` was the same before and after.
- Evaluated every job's `if:` again for 64,512 combinations of branch and inputs, and listed each job's permissions and the steps that get the job token.
- Weakened conditions of `release_diff.py` in memory again: the 34 that no test noticed in review 1, and 29 of the new code (S4 below).
- Ran `main_merge_base` and `source_changes` on this branch, and the source-list test's own search on Control's open branch (`origin/pkg/18c-image`, PR #58).
- Ran the new rpm query (`RPM_FILE_FORMAT`) as the user on this laptop's rpm 6.0.2 for six installed packages and read the result with `rpm_files`.
- Read dry run 1's evidence (run 43832912792) beside dry run 3's, for N4 and S1.
- Read `action.yml` of the three other pinned actions in `check-build` at their pinned commits.

## Verdict

**SAFE.** B1 is closed, S1 to S5 are closed, five nits are done and two are left with reasons I accept. The fixes brought no new finding above a nit.

Two things for the lead, neither a defect of the fixes:

- **Nothing of this has run on a real build.** Five new stops (S1, S2, S5, N4, N5) and two new guard steps (S3) run for the first time at the cut, in the last dry run the ledger allows. All fail closed. What could be checked without a build is checked (below), so a real difference is the likely cause if one stops. If a harness fault at the cut would hurt, spend one dry run on this head first (cap 4 to 5), as was done for phase 2.
- **A pin renewed on this branch now stops the diff** (S2). The brief's A.2 allows renewing a vanished pin here and names gh's lock as "renewed by the lead each release". Renew it on main before the cut, or give it a row in `BRANCH_SOURCE_CHANGES` with its own check.

## The findings of review 1

### B1. Publishing before the owner's OK: closed

- **The fix.** `os/ci/rehearsal-packages.json:185` and `:195`: `publish-28` 0 and `publish_cap` 0, with a `publish_gate` note. `os/ci/rehearsal_guard.py:542-543`: the publish gate also refuses while `publish_cap` allows none.
- **Is the gate shut?** Yes, twice, and the two do not depend on each other:
  1. A `release_28` dispatch counts itself as one `publish-28` dispatch, and 1 is more than 0: `STOP: publish-28 dispatch allowance exhausted`, in the job's first step after checkout (`os-image.yml:525-529`), before any tool or build. If the run were missing from the history, line 533 stops instead.
  2. `publish.sh:14` runs the guard again before the login, the push and the signature. There `0 < 0` fails: `STOP: the ledger allows no publish`. Raising only the dispatch cap opens nothing (tested).
- **Input combinations.** Push and signing exist only in `publish.sh` (`:41`, `:53`), and only three jobs call it. Over all combinations, `release-28` starts only for `release_28` alone on this branch, and then stops as above. `image` and `release-27` need their own branch and input and now refuse both new inputs (N3). No job with `packages: write` or `id-token: write` runs when `dry_run_28` is set, on any branch.
- **Re-run.** Stops at `run_attempt` before the caps are even read, as before.
- **Other branch.** The job's `if:`, `publish.sh:8-13` and the guard each need this branch's name. The ledger is read from the dispatched commit, so the head's caps apply.
- **A slip** is counted and stops every later guard on the branch until a ledger commit records it (tested: the next dry run stops). With `publish-28` then at 1 and `publish_cap` still 0 the gate stays shut both ways: a second slip is dispatch 2 of 1, and the publish gate still reads 0.
- **Step 5** raises both in a commit that names the OK; `test_release28` pins both at 0, so that commit must change the test too. Good.
- **One way left, deliberate only:** see N2 below.

### S1. Broad "generated" globs: closed

`release_diff.py:417-422`: four patterns and the rpm database's own rule. The test names dry run 3's ten paths, requires every reason to be used, and holds that a path under each dropped pattern stops. Dry run 1 (another build, another commit) regenerated exactly the same 11 paths, so the narrow list is not fitted to one run.

### S2. A branch commit counted as a merged package: closed

- **The fix.** `main()` takes `git merge-base HEAD origin/main` first and stops when any path of `IMAGE_SOURCES` differs from it, except `os/minecraft/desktop.lock.json` when only the AresOS jar's `sha256` differs. `origin()` reads main's history up to that commit. The merge base goes into `result.json`.
- **Does it hold at the cut?** Yes. The stop compares trees, so it does not matter how the difference came about: a commit on the branch and a wrong merge resolution both show. With main merged in, the merge base is main's merged commit, also when main has moved on since. A test builds exactly that in a temporary repository. On this branch today: merge base `e33ffc46`, the jar pin allowed, nothing else differs. `origin/main` is in the job's checkout (dry run 3's log: `fetch … +refs/heads/*:refs/remotes/origin/*`, `[new branch] main -> origin/main`); without it the diff stops with its own line.
- **Is the list complete?** For today's build, yes. I read `build.sh` and the Containerfile for every read under `/tmp/aresos`, also the ones built from a variable (`:82`, `:200-210`): the two package locks, `keys/`, `minecraft/`, `config/`, `policy/`, `tests/audit.py`, `build.sh`; the source stage keeps only `mod/`; plus the Containerfile, `.containerignore` and `base.json`. All twelve are listed.
- **What the list leaves out, and why that is right.** `COPY . /tmp/aresos/` also carries the rest of `os/` (tests, owner tools, manifests) into the first layer, and `build.sh:366` deletes it. Those files are in a layer blob but not in the file tree a deployment gets. PROGRESS.md says so.
- **At the cut the list must grow** when Control rides: see N8.

### S3. Resolve and checks did not read their caps: closed

- **The fix.** The checks guard step now also runs on this branch (`os-image.yml:79`). `check-build` has a guard step on this branch only, right after the checkout (`:202-207`). An unknown run title stops with a line that names it (`rehearsal_guard.py:362-365`).
- **Checked.** With today's history and this ledger the cut's dry run, a resolve and the checks run pass their guards; a third resolve, a second checks run and a `check_build=build` on this branch each stop at their own first step (tested, and traced by hand through `main()`).
- **The new permissions on `check-build`** (`:191-194`): `contents`, `packages` and `actions`, all `read`. No write and no `id-token` in the job or at the top level, so pushing and keyless signing stay impossible. `packages: read` is not used by the resolve guard when it runs; `test_ci_api_permissions` asks it of every job that can reach the guard, because the guard imports `registry_auth`. It lets this job's token read the private image, as the tokens of the dry run, the checks, the switch and the rehearsal jobs already can.
- **Where the token goes.** One `run` step gets it, the guard, and only on this branch. The checkout now runs with `persist-credentials: false`, so it is not left in `.git/config` for the build that follows. The three other pinned actions (`remove-unwanted-software`, `cosign-installer`, `upload-artifact`) name no job token in their `action.yml` at the pinned commits. Tested: no later step has `GH_TOKEN`.

### S4. Conditions without a negative test: closed

- Of the 34 weakenings no test noticed in review 1, 33 now make a test of that rule fail. The one left (`updaters.json` must already be a file in release 27) changes nothing: without release 27's copy the comparison cannot read it and stops anyway. That is the fixer's reason too.
- Of 29 weakenings of the new code (S1, S2, S5, N4, N5), all 29 make a test fail: each condition of `package_file`, the source stop, the jar-pin allowance, `origin()`'s range, two entries of the source list, the pinned Prism list and the converse.
- The fixer's own list (84, of which 6 called equivalent) is not mine, so the two counts check each other. I read the six reasons and agree with each.

### S5. Files of added packages checked by path only: closed

- **The fix.** `package_file` (`release_diff.py:1229-1248`) needs the path's record from the added packages' rpm database, read in the new image with `rpm -q --qf`.
- **Can it pass when a file differs?** Not in what rpm records:
  - a regular file needs digest algorithm 8, the recorded SHA-256 and the recorded size;
  - a link needs the recorded target; every kind needs the recorded type and mode, `root`/`root` in the record and in the image, no `%ghost`, no file capability, no extended attribute;
  - setuid, setgid, sticky, group or world write stop even when the record says the same;
  - a path with two records must match both; a path with none is not explained; a line the reader cannot split stops the whole diff.
- **On real data.** The format runs on rpm 6.0.2 and `rpm_files` reads it (six packages, 20,440 paths, among them 16,360 `%ghost` and 4 with capabilities). Held against the files on disk, 2,358 readable regular files match their record's SHA-256 and size and one does not, in `shadow-utils`: so the comparison does see a changed file.
- **What it trusts.** The image's own rpm database, read by the image's own `rpm`, as `rpm -qa` and `rpm -ql` already did. A build step that changes a file does not change the database, which is the case the rule is for.
- **Not verified by me:** the fixer's comparison of dry run 3's 470 paths with the four pinned RPMs' headers (it needs the RPMs). In dry run 1 and 3 all 470 are root's, with no attribute and no setuid or writable bit, which I did read.
- `rpm -V` is recorded and stops nothing, as said. A removed package's path is now explained only when it is gone.

### Nits

- **N1 (both inputs): done.** Both together run no job (checked) and are titled, so counted, as a dry run.
- **N2 (a tag named like the branch): left, still a nit.** One thing is new: B1's gate lives in the ledger of the dispatched commit, and every commit before `90c9d862` carries caps of 1. A tag `pkg/42-release-28` on one of them would run that old ledger. It takes a deliberate tag push by someone with write access, so it is no slip. A cheap close that needs no workflow change and not the shared `condition` helper: in the guard, for the titled packages, require `GITHUB_REF` (when set) to be `refs/heads/` plus the branch; in `publish.sh`, `test "$GITHUB_REF" = "refs/heads/$GITHUB_REF_NAME"`. Step 6's `verify_release.py` should pin the `refs/heads` identity either way.
- **N3 (old release jobs): done.** No writer job runs with either new input any more.
- **N4 (Prism's list): done.** `9df32315…` is also the list in dry run 1's image, so two builds agree and the pin cannot stop the cut for the same Prism.
- **N5 (the converse): done.** Today 56 `os/config` files changed since release 27, none removed, no link; dry run 3 explained 56.
- **N6 (one mirror outage): left for step 5,** with the right plan: dispatch cap 2 and `publish_cap` 1 allow a retry and still one publish attempt at most (`rehearsal_guard.py:536-537`).
- **N7 (wording): done.**

## New, from the fixes

- **N8 (nit). The source list's completeness is held by a unit test, and one of its two checks reads a comment.** `test_release28.py` `test_the_source_list_covers_what_the_build_reads` asserts `'keep only mod/' in build`. On PR #58's `build.sh` that string is still there although the source stage also keeps `control/`. The other check, the `/tmp/aresos/…` paths, does fail there, on `control` (run against `origin/pkg/18c-image`). So: after main is merged in for step 2 or the cut, run `test_release28` before any dry run, and add `control` (top level, like `mod`) to `IMAGE_SOURCES`; the release jobs run no unit tests and would not notice. Better: assert the `tar … --wildcards` line and the Containerfile's `COPY --from=source` lines, not the comment.

SAFE
