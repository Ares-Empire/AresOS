Verdict: NOT READY

# Brief review 1: brief 18c-b (Chrome's browser side in the image)

Fresh reviewer (Fable 5.2: install and security work), 2026-11-15, on `briefs/18c-b-chrome-image` at `2dcb8250`.
Read against `main` (`62e1abb3`; `main` is now `a2e45730`, one STATE.md line more), `origin/pkg/18c-image` at
`84f45c28`, `origin/briefs/28-chrome-capability`, and today's Chromium and polkit sources (file and line per
finding). Nothing ran in CI. Local, read-only: `build.py` on both trees, the base's tools on the laptop, GitHub's
release API, GitHub CLI's published key file.

One blocker (the lead's answer 6). The design itself holds: Chrome's sources agree with the research on every point
the brief builds on.

## Claims that check out

- **Chrome** (Chromium `main`): a `file:` update address is valid for `ExtensionSettings`
  (`policy_handlers.cc:65-71, 347-354`) and both downloads use a file loader (`extension_downloader.cc:469-482`);
  off-store force-install is restricted on Windows and macOS only (`extension_management.cc`,
  `IsLowTrustEnforcementActive` returns false elsewhere); `override_update_url` is honoured for a policy install
  with a non-store address (`extension_management_internal.cc:112-118`), and without it an extension with no
  manifest `update_url` is checked at the web store (`extension_downloader.cc:168-174`), so the override and case 5
  are needed; policy files are found through links (`FileEnumerator::FILES` uses `stat`,
  `file_enumerator_posix.cc:28`); the package is copied to a temporary file, never taken from its place (`:1294`).
- **`main`:** the templates and README as quoted; `install.mjs`'s `pack` and `idFor`; `build.py`'s inputs
  (`builds.json`, `qualification.json` and a new `control/chrome/record_build.py` are not inputs); the manifest has
  no `key` and no `update_url`; no storage API in the extension; `FIXED_HOSTS`; `Boundary.read` (root-owned,
  nothing group- or world-writable, regular file, no links); `verify` calls `gh` by name and wants 2.102.0, with
  the unit's `PATH=/usr/bin:/bin`; `maintenance` refreshes only with a version from a connected host; the polkit
  action (`no`/`no`/`auth_admin`, owner annotation); `ares` is in `wheel`; the shell's `systemd-run --user --scope
  --slice=app.slice` line; job `native-precedence`; the CI-only polkit rule; `launch.py` accepts a 0755 `host`.
- **18c's branch:** `TREES`/`FILES`/`DERIVED`, root-only, no group; `control.json` and `check-image.sh`'s compare
  of `links`, `directories`, `files`; no template or extension copy in the installed tree; Chrome's RPM step
  (import, check, delete); the job limit 127; `aresos-tools` 250; `build.py` prints `ccd0fd79…ce15` on its
  `control/` (run here).
- **The base** (read on the laptop): `pkcheck` (polkit 127), `rpmkeys`, `rpm2cpio`, `cpio` (rpm 6.0.2), OpenSSL
  3.5.9, `cryptography` 50.0.0; no `node`, no `gh`; KDE's file alone in `native-messaging-hosts/`.
- **`gh`:** the release asset is 15672051 bytes with digest `65d55875…f4d2` (GitHub's API). Key ID
  `5612b36462313325` is the 2026 key `7F38 BBB5 9D06 4DBC B3D8 4D72 5612 B364 6231 3325` in GitHub's own key file
  (`https://cli.github.com/packages/githubcli-archive-keyring.gpg`), so answer 8 can be met.

## Blocker

### B1. Answer 6 (`setup_needed`) rests on a tool that doesn't save this list, and its mark would outlive the list

*Where:* "The lead's answers", 6 (lines 500-505), against "Out of scope" (446-453), C6 (271) and the image check
"giving an empty list" (394-395).

*Evidence:*
- `chrome_sites` has `list`, `readonly`, `revoke` and `allow` (`adapter.py:849-871`). None saves excluded hosts; it
  writes `chrome:readonly:*` and `chrome:allow:*` to the service's store. The excluded list is the root-owned file
  in `/etc` (`exclusions.py:8`), and the service can't write there (`aresos-toold.service:15,22`:
  `ProtectSystem=strict`, writable only `/run` and `/var/lib`). "Saved his list once with `chrome_sites`" can't
  happen, and "where `chrome_sites` writes" is `/var/lib/aresos-tools`.
- `/var` is shared by all deployments, `/etc` belongs to each (18c's agreed change 5 argues from this,
  `briefs/18c-image-test.md:170-173`). With tmpfiles making the file when missing, `previous` into a deployment
  that never had his list gives: mark set, list empty and valid. The tools then run with an empty never-list, the
  one case the guard is for.
- It needs `control/aresos_control/`, `control/generated/` and the setup of every existing Chrome test (all would
  answer `setup_needed`). The brief forbids each and says "stop and report" (446-453). Package 28 rewrites the same
  adapter.
- The checks weren't updated: C6 "as shipped … reads work", the image check's empty list, and C2 to C9 have no way
  to set the mark.
- 28b item 9 and section 6 on PR #48 say "no gate" (`28b:572-581`, `CONTROL.md:492-498` there). Their reason (a
  gate would need his host's name in the repo) doesn't hold for a "saved once" mark, so the guard is right in
  substance; those two texts must change with it.

*Fix* (pick one, then write it into the body):
1. **Recommended, no service change: the file is the mark.** tmpfiles makes a placeholder that today's validator
   refuses, for example `{"format":0,"hosts":[]}` (`exclusions.py:16` wants format 1). Every Chrome read and action
   then answers the existing `chrome_settings_unavailable` ("ask the owner to install it") until root saves a
   format-1 list; an empty one counts. The mark shares the list's fate through update and rollback, and the group
   by name stays as `linux-aresos` answered. Change with it: C6's first line and the image check (as shipped:
   refused; with a valid empty list written by root: `[]`); the test layer writes a valid list before C2; the
   README sentence "The image must install … `{"format":1,"hosts":[]}`"; a unit test in a new file that the shipped
   placeholder is refused; 28b item 9 and section 6 on PR #48.
2. A real `setup_needed` in the service: its own brief on the service's line, the mark in `/etc` written by root,
   never in the store. Not in 18c-b.

## Should-fix

### S1. A rollback brings back an older never-list, silently

*Where:* Goal ("after an update or a rollback … belongs to the booted image again"), the security row "A stale or
foreign identity after update or rollback", "Agree".

*Evidence:* his list is a local file in `/etc`, kept per deployment. A host he adds after an update isn't in the
previous deployment's `/etc`. After `previous` the tools read and act on that site with no refusal and no notice,
and the next update carries the old list forward. That is unsafe, not just broken, and neither the row nor C4 nor
the rehearsal checks look at it.

*Fix:* add the risk row. Add a question for `linux-aresos`: should `previous` carry or compare this file (its
owner tools, next release)? Add a rehearsal check that prints the list's hash before the update and after
`previous` and says when they differ. Until solved: "Not verified" and a known limit for his guide ("after going
back a version, check the never-list"). Moving the list to `/var` would solve it, but is a service change.

### S2. Two sets of answers aren't in the body, and three contradict it

*Where:* "The lead's answers" 7 and 9; lines 37, 429, 439, 451; "Agree" (294 onward).

*Evidence:*
- Answer 7 has the builder edit `docs/design/CONTROL.md` and 18c's Part C in step 1. Line 451 forbids
  `docs/design/` and line 439 asks for proposals only. PR #48 rewrites that same paragraph (its line 375 still says
  `ExtensionInstallForcelist`), so a builder's edit on `main`'s text conflicts with it.
- Answer 9 puts the polkit check in step 4. Line 429 has C7 in step 5 and line 37 expects the Fable switch there.
- `linux-aresos`'s seven answers are on `main` only as one STATE.md line (`a2e45730`): tmpfiles with the group by
  name, the licence under `os/config`, the key as `os/keys/github-cli-rpm.pub`, no polkit review entry. The table
  still says "only if … (question 2)".

*Fix:* fold all of it into the body and say which text wins. The two doc sentences are the lead's: change section
6 on PR #48's branch and 18c's Part C note there, and keep the builder out of `docs/design/`. Step 4 starts with a
small polkit probe (a process started the shell's way as the subject of `pkcheck --allow-user-interaction`; exit
code and journal, no dialog driving yet), so the stop condition is met early; C7's dialog stays in step 5.

### S3. 18c's own image check fails once the link exists

*Where:* line 72 ("Package 21's image check already creates the policy folder"); "Agree", path 4.

*Evidence:* `image-checks.sh:281-284` on `pkg/18c-image` makes `/etc/opt/chrome/policies/managed` and then runs
`rmdir` on it and its parent. With `aresos.json` inside, `rmdir` fails and the image check stops. That costs one of
three `check_build=build` runs, and hard rule 5 leaves the builder unsure whether it may change the check.

*Fix:* say it: this check is replaced by the new ones (the folder exists, 0755 root, holds exactly our link), and
name the replacement in "Agree", path 4.

### S4. Case 4 and C5 can't show what they claim on a profile that already has the extension

*Where:* item 2 case 4 (183-185), C5 (270), security row 1 ("C5 shows a tampered package is not installed").

*Evidence:* for an installed extension Chrome takes a package only when the manifest's version is higher
(`extension_downloader.cc:890-918`); the version stays `1.0.0`. In the guest C5 follows C2 to C4 on the same
profile with the same ID, so a changed or missing `extension.crx` is never read: the extension stays installed and
connected, and "restored, it installs again" has nothing to do.

*Fix:* case 4 and C5 use a fresh profile (or a bundle whose ID the profile never held), and say so. Add the other
half as its own assertion: with the extension installed, a changed or missing package leaves the installed copy
running. Reword the security row: the signature is checked at first install; after that the copy in his profile
is what runs (user-writable, covered by `KNOWN-LIMITS.md` line 21).

### S5. The probe's install route isn't given, and the obvious one breaks ours

*Where:* item 2 "A probe extension" (170-172); C1 ("plus the test layer's, named").

*Evidence:* Chrome takes each policy key from one file: the last in name order wins and nothing is merged
(`config_dir_policy_loader.cc:211-250`). A second file with `ExtensionSettings` either removes ours or is ignored.
The builder would then read the result as "the pinned Chrome doesn't install from this form" and take the fallback
of line 143.

*Fix:* the probe is installed by `ExtensionInstallForcelist` in its own file (a different key; both apply
together, as today's template shows), from a `file:` address of its own. Add one image-side line for his guide: a
later file that sets `ExtensionSettings` and sorts after `aresos.json` removes our extension (fails closed).

### S6. Case 5 and C9 pass when nothing was checked at all

*Where:* item 2 case 5 (186-188), C9.

*Evidence:* "no request names our ID" is also true when no update check ran in the window or the log caught
nothing. Loads from `file:` don't go through the network log, so the log can't show that our check happened.

*Fix:* a positive control in the same run: the probe has no override (or a `localhost` update address), and its ID
must appear in at least two update requests in the same log. That shows two checks ran and that the log would have
shown ours.

### S7. GitHub's key file holds two keys

*Where:* item 3, `gh` (208-216); answer 8; the image check "no … key of GitHub's" (397).

*Evidence:* the published file holds the 2022 key `2C61 0620 … 7571 6059` (expired 2026-09-05) and the 2026 key
`7F38 … 6231 3325` (`gpg --show-keys` today, on the `.gpg` and on the `.asc` that GitHub's own repo file names).
The brief says "the pinned key … then delete the key again". Importing the file as published adds two keys;
deleting one fingerprint leaves the other in the image. A trimmed file no longer has the published file's SHA-256.

*Fix:* commit GitHub's file unchanged with its SHA-256 and source; pin the one accepted fingerprint (`7F38…3325`)
and require the header signature by it; delete every key the import added (compare the key list before and
after); the image check compares the key list with the base's.

### S8. Where the new tests run: one can't be built, two land in suites that can't run them

*Where:* item 1 (124-129), item 4 (232-247), Proof (369-378).

*Evidence:*
- Everything named `test_*.py` or `*.test.mjs` in `control/chrome_tests/` is picked up by three existing runs:
  `python-shard.py` (runner, checkout without history) and `run.sh:32` and `:75` (Chrome's container: `control/`
  only, no `os/`, no repository, no `cryptography`; see its `Dockerfile`). The brief counts three places for
  `pack.py` and misses these. `pack.py`'s tests and the `node` cross-check would fail there, and a `chrome_tests`
  test of `check` finds no `os/manifest/` in the container.
- "`add` for a commit whose `control/` is 18c's head must compute `ccd0fd79…`": no commit on `main` has that tree
  (18e isn't merged; `main`'s `control/` gives `4c1eccb9…`), and none of those runs has the history.
- "unless three newer rows exist" needs an order between a release manifest and rows; the manifests have no
  `shipped_at`. Where `chrome_build` sits in the manifest isn't fixed, but `check` must read it.

*Fix:* `pack.py`'s tests and the `node` cross-check live under `control/chrome/ci/install/` and run in item 2's
workflow only. The `check` test runs on the runner (the path-filter workflow), not in `chrome_tests/`. Drop the
`ccd0…` unit test; the lead runs `add --commit 84f45c28… --expect ccd0…` once into a scratch copy and records it
as **run**. `check`: `os/manifest/release.json` must have a row equal to its `chrome_build`; for `releases/**` a
row for the same commit must be equal if one exists. Fix the key's name and place and add it to "For your next
release".

### S9. Two image checks aren't concrete enough

*Where:* Proof, "What the image check pins" (387-391); item 3's `check-image.sh` line (222-225).

*Evidence:*
- Nothing opens the shipped package: the checkout is compared with `payload`, and `payload` is what `pack.py`
  said it packed. That the package holds exactly those files is a unit test of `pack.py`, not a fact about the
  image.
- There is no DER marker for a private key. The RSA object identifier is in the package's public key too, so the
  scan either never fires or fires on our own file.

*Fix:* the image check reads the zip inside `extension.crx` and requires exactly `payload`'s names and SHA-256s.
The key scan: PEM markers, plus the public modulus (raw, hex, base64) found exactly once in the image's additions
(inside the package) and nowhere in the build's temporary folders or log. Every stored form of the key holds it.

### S10. Steps 1 and 3 are the heavy ones

*Where:* "Steps".

*Evidence:* step 1 has two unrelated tools with their tests, the templates, the pin, the README, and by the
answers a service guard and a design-doc edit. Step 3 has the install map, the bundle, tmpfiles, `gh` with its key
provenance, about eight groups of image checks, `check-image.sh`, `os/tests` and two hosted runs.

*Fix:* step 1 without the guard and the doc edit (B1, S2). Split step 3: 3a Chrome's files with their checks; 3b
`gh` (own stop conditions), then `check_build=build`.

## Notes

- **polkit, likely fine:** for a process outside a session scope polkit falls back to the user's display session
  (`polkitbackendsessionmonitor-systemd.c:397-424`, `sd_uid_get_display`). Keep the check and the stop condition.
- **Question 1's alternative can't work as asked:** `/usr/share/aresos/control/` is compared file by file
  (`image-checks.sh:738`) and walked by `launch.py`. Answered with `/usr/share/aresos/chrome/`; drop the option.
- **README:** the paragraph "Copy all … `chrome/{extension,…,packaging,…}` into the installed service tree"
  contradicts "the installed tree holds no template copy". Add it to item 1's README edits.
- **`pack.py` refuses links and non-regular files** in the extension folder, as `build.sh`'s `TREES` loop does.
- **`briefs/18c-image-start.md`** is on `pkg/18c-image` only until PR #58 merges; line 4 names it as if on `main`.
- **Not asked of `linux-aresos` yet:** does any release step build twice and expect equal bytes? The bundle and
  `control.json` differ per build. The brief states it; make it a question.
- **The native host residuals** stay as accepted. `NativeMessagingUserLevelHosts=false` wouldn't close them (any
  process of his user reaches `chrome.sock` directly) and would break his other extensions' hosts.
