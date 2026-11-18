Verdict: READY

# Brief review 2: brief 18c-b (Chrome's browser side in the image), after its revision

Fresh reviewer (Fable 5.2: install and security work), 2026-11-15, on `briefs/18c-b-chrome-image` at `59814973`.
Read against `main`'s `control/` (as on this branch), `origin/pkg/18c-image` (`84f45c28`),
`origin/briefs/28-chrome-capability` (`6a78b084`) and today's Chromium `main`. Nothing ran in CI. Local, read-only:
the list's parser on sample bytes, and `systemd-tmpfiles` 259 (the base's) on a scratch folder with the agreed
line shape.

No blocker. Every finding of review 1 is closed in the brief's text and holds against the code. Six should-fixes,
all a level below review 1: each is a few lines in the brief, and none changes the design or what `linux-aresos`
agreed. Fold S1, S3 and S6 in before step 1a starts (they shape step 1a's and step 2's files); the others before
step 3a. They need no further review round.

## Review 1's findings: closed

| Finding | Closed by | Checked against |
|---|---|---|
| B1 guard on `chrome_sites` | the `format` 0 placeholder, no service change beyond two lines | `exclusions.py:16` refuses anything but `format` 1; `adapter.py:204-207` answers `chrome_unavailable` first, then reads the list on every call; 28b item 9 and `CONTROL.md` section 6 at `6a78b084` say the same |
| S1 older list after rollback | the list in `/var/lib/aresos-control/` | `SETTING` is a constant (`exclusions.py:8`); the only other writers of the path are `prepare.mjs:32-34` and `test_exclusions.py:13`; no 18c file names it |
| S2 answers not in the body | body, "Agree" and answers 6, 7, 9 agree | no builder edit of `docs/design/`; the probe opens step 4 in four places |
| S3 18c's `rmdir` check | named as replaced in "Facts", "Agree" path 4, "Proof" | `image-checks.sh:281-284` on `pkg/18c-image` |
| S4 broken package on an installed ID | fresh profile, bundle C, the installed-copy half | case 4, C5, first security row |
| S5 the probe's install route | `ExtensionInstallForcelist` in its own file | `config_dir_policy_loader.cc:185-249` (last file in name order wins per key); `extension_management.cc:733-802` (both policies apply together) |
| S6 no positive control | the probe's ID in two update requests | holds for what it controls; see S3 below for what it doesn't |
| S7 two keys in GitHub's file | one committed key, pinned fingerprint, key list equal before and after | rpm 6 prints the full fingerprint per line (`os/build.sh:344-346` on `pkg/18c-image`), so "by that fingerprint" can be checked |
| S8 where tests run | `ci/install/`, `ci/records/`, the records workflow, the recorded run | `build.py:10-17` hashes neither `chrome/ci/` nor `record_build.py`, and skips `__pycache__` |
| S9 image checks not concrete | the zip is opened; the modulus scan | see S4 below for where the scan can run |
| S10 heavy steps | 1a, 1b, 2, 3a, 3b, 4, 5, 6 | see S5 below for 3a |

## What the fixes introduced, and holds

- **The gate on today's code.** Every read and action goes through `mode()` or `allowed_url()` and so through the
  list: `adapter.py:310, 323, 406, 500, 588, 659, 833, 912, 931, 935` and `307`. Nothing caches a decision:
  `_configured_exclusions` (`:208-210`) only remembers what the extension was last sent, and the file is read
  again on every call. With the placeholder `configure` is never sent, and the unconfigured extension refuses
  everything but `ack_steps` and `queued_steps` (`background.js:874-875`, `:319`).
- **Missing, a link, writable by the group:** all three refuse. `Boundary.read` opens every component with
  `O_NOFOLLOW`, requires root as owner and no group or world write bit, and a regular file (`boundary.py:11-15,
  33-45`). An empty file refuses too, so the moment between `tee`'s truncate and its write fails closed.
- **tmpfiles, observed on systemd 259:** the argument is written as it stands, 23 bytes, no newline; a second run
  over a changed file keeps its content and puts mode and owner back; a link in the file's place is left alone
  with an error, which `Boundary.read` then refuses.
- **`echo … | sudo tee`:** the parser accepts `echo`'s trailing newline.
- **The service can't write the list:** root-owned 0755 folder, file 0640 with the group read-only, outside
  `ReadWritePaths` (`aresos-toold.service:15, 22`; 18c adds only start-limit lines).
- **A throwaway image's build is unqualified, and that is fine:** `switches` answers conservative mode with the
  core groups on (`qualification.py:62-63`), so C3 and C8 can read and ask.
- **The manifest's `control` object:** `control.json` already has `source_revision` (`os/build.sh:255` on
  `pkg/18c-image`), and `release.json` has no `control` key today, so the name is free.

## Should-fix

### S1. The gate is pinned at one function and one verb, and packages 28 to 28b rewrite the adapter behind it

*Where:* item 1 (`test_excluded_sites_placeholder.py`), C6's first use, the risk row "Chrome's tools before his
never-list is in" (line 549), Goal ("holds every Chrome tool back").

*Evidence:* the brief's claim is "every Chrome read and action". What it tests is `owner_hosts()` (item 1's test,
the image check) and `aresos chrome tabs` (C6). The only existing test of the refusal is
`test_exclusions.py:25`, with `Boundary.read` mocked. That each verb reaches the list is true today by reading
(the lines above), not by a test. Packages 28, 28a and 28b rewrite `adapter.py` and add `chrome_take`,
`chrome_take_reload` and in-place reads of his tabs; 28b item 9 says "This package changes none of it" and has no
test for it. A new verb that calls the bridge before `mode()` would pass every check in this brief and in 28b.
Also: `chrome_sites` (`list`, `revoke`, `allow`) and `chrome_notices` answer with the placeholder in
(`adapter.py:849-873, 893, 907-909`); they read no page, but "every Chrome tool" overclaims.

*Fix:*
- Item 1's new test file gains a sweep at the adapter: with the list refused (`read_owner_hosts` raising what
  the placeholder raises, `Boundary.read` patched as `test_exclusions.py` does), every Chrome tool of the tool
  list answers `chrome_settings_unavailable`, and the bridge has seen no call. The exceptions are written in the
  test by name (`chrome_sites` without `readonly`, `chrome_notices`), so a new tool fails it until someone
  decides.
- C6's first use tries one read of a page, opening an address and taking a tab, besides `tabs`.
- The lead adds one line to 28b (PR #48): its new tools join that sweep, and its take and in-place read tests
  include the refused list.
- Goal and the risk row: "every Chrome read and action" (not "every Chrome tool").

### S2. Nothing in this package shows that a later boot leaves his written list alone, and the rehearsal's hash check can't fail

*Where:* "The design" ("updates and `previous` keep it"), C1, C6, "For the release rehearsal" (lines 365-371),
the risk row "His never-list across update and rollback".

*Evidence:* C1 looks at the first boot. C6 writes the list and restores it, but the guest never boots again with
a written list. The only proof named is the rehearsal's `CONTROL_CHROME_SITES_SHA256`, equal before the update,
after it and after `previous`. The rehearsal has no test layer and nobody writes a list there, so all three
hashes are the placeholder's: they are equal whether tmpfiles keeps a file or rewrites it at every boot. The
behaviour is right on systemd 259 (observed, above), but it is the property the move to `/var` rests on, and
18c's image check already runs tmpfiles files this way (`image-checks.sh:792-801`).

*Fix:*
- Image check: after "nothing under `/var/lib/aresos-control/`", run `systemd-tmpfiles --create` on the installed
  file. Require the folder `root:root` 0755 and the file `root:aresos-tools` 0640 with exactly the placeholder's
  bytes. Then write a `format` 1 list with a made-up `.invalid` host, change its mode and group, run it again:
  the content is unchanged, mode and group are back. Remove the folder.
- VM: after C6's first use, reboot the guest once (or run `systemd-tmpfiles --create` as root, if a reboot costs
  too much) and require the written list's hash unchanged.
- "For your next release" and the rehearsal lines: root writes a `format` 1 list with a made-up host before the
  update; `release_checks.py` fails when the list equals the placeholder at the two later points. The lead
  relays this with the other changes.

### S3. Case 5 and C9 still can't see the store path: it sends the ID in a request body, not in an address

*Where:* item 2 case 5 (lines 239-243), C9, the risk row "Chrome telling a store about our extension", "Stop and
report" (line 602).

*Evidence:* for an installed extension whose effective update address is empty or the store's, Chrome doesn't use
the downloader at all. It hands the extension to the update service
(`extension_updater.cc:515-518, 776-795`; the effective address comes from the policy override,
`extension_management.cc:331-345`). That service posts a JSON body to Google's update endpoint; the ID is in the
body. The network log at its default capture level records no bodies, and in a guest without network the
request never leaves. So if the override ever stopped working (a Chrome change, a template mistake), the scan
"no request … names our extension's ID" would still pass. The positive control proves the other path: the
probe has a `localhost` address in its manifest, goes through the downloader, and has its ID in the address.

*Fix:*
- Keep the address scan and the probe. Add a second assertion on the same log: no request at all to Google's
  update endpoints (`…/service/update2/…`) in the window. For this run only, allow `--disable-component-update`
  beside the two flags (item 2 and line 337), so such a request can only come from an extension; if the pinned
  Chrome still sends some, compare with a run without our policy instead.
- A negative control, in the container only (item 2): the same package under a test policy without
  `override_update_url` must fail the scan. That shows the check sees the leak it is there for.
- Line 602 becomes "a request naming our extension's ID, or an update-service request caused by it".

### S4. Two of the three key scans are placed where they can't run, and "the image's own additions" isn't defined

*Where:* "Proof", "What the image check pins", the bullet "no private key anywhere" (lines 511-513); the risk row
"The signing key, made in CI".

*Evidence:* `image-checks.sh` runs inside the built image without network (`check-image.sh:11-14` on
`pkg/18c-image`). Neither the build's temporary folders nor its log exist there; the log is
`evidence/build.log` on the runner (`check-build.sh:43`). "The image's own additions" has no definition: a key
left in the image's `/tmp`, `/var/tmp`, `/root` or a cache is in no record. And the PEM-marker scan can't be the
whole image: the base's own `/usr` already holds nine files with a private-key marker (read on the laptop, for
example in Python's `cryptography` package and a Perl example key).

*Fix:*
- The modulus scan runs over the whole image file system in `image-checks.sh` (the modulus is unique, so there
  are no false hits): exactly one hit, in `extension.crx`. That covers anything a build step left in the image.
- The same scan runs on the runner over `evidence/build.log`, in `check-build.sh` after the image check (the
  runner takes the modulus from the image's `extension.crx`): no hit.
- The PEM-marker scan covers the files `control.json` records, `/usr/share/aresos/chrome/` and the image's
  `/tmp`, `/var/tmp` and `/root`.
- Drop "the build's temporary folders" as a target of its own; `pack.py`'s unit test covers its own.

### S5. Step 3a ends without running what it built

*Where:* "Steps" 3a and 3b (lines 562-566); "What runs when" (budget: 3 `check_build=build`).

*Evidence:* 3a ends on `checks_only`, which runs `os/tests` and builds no image. The install map with `pack.py`
on the real base, the tmpfiles file, the links, the polkit action and about eight groups of new
`image-checks.sh` lines run for the first time at the end of 3b, under another agent who didn't write them. The
budget is three builds: one at 3b's end, one on the final head, one spare for all of 3a's and 3b's image work.
The image checks can't run on the laptop.

*Fix:* 3a ends with `check_build=build` green once; 3b with one more. Budget six builds. Step 4 is the largest
step left (the probe, the second pass with its layer and workflow step, seven checks): say in "Steps" that its
builder stops after C2 and C6's first use if `PROGRESS.md` shows the budget half used, and a fresh agent takes
C3, the rest of C6, C10 and C11.

### S6. The refusal's message doesn't cover the likeliest mistake, and the owner's step has no check

*Where:* item 1, the message pinned "exactly" (lines 183-186); "For his guide" (lines 382-389); C6 ("`ares` can
neither read nor write the list").

*Evidence:*
- The list is now JSON he types once. A capital letter, `https://`, a trailing slash or a pasted typographic
  quote all end at `exclusions.py:23` with the same text: "not set up yet, or is missing, unreadable or unsafe".
  None of these words says "what you wrote isn't a valid list", and he has just set it up. The message was
  changed for exactly this reason in the first-use state. It sits in a hashed runtime file, so a later change
  is a new build.
- The guide has no step that shows the list was taken: `tee` succeeds on any bytes.
- "`sudo tee` writes into the existing file, so it keeps its owner, group and mode" is true only while the file
  exists. If it is missing, `tee` makes it `root:root` 0644: valid for the service, readable by everyone until
  tmpfiles puts mode and group back at the next boot.
- C6 pins that `ares` can't read the list, but `echo '…hosts…' | sudo tee` leaves his hosts in `ares`'s shell
  history, where a Claude Code session can read them.

*Fix:*
- The message: "… its owner-only excluded-sites setting is not set up yet, or is missing, not a valid list,
  unreadable or unsafe; ask the owner to set it up." (item 1, its test, C6).
- The guide: after writing, with Chrome open, `aresos chrome tabs` must list his tabs; if it still answers "not
  set up", the line has a mistake; `sudo cat` shows the file. One sentence on the missing-file case (the next
  boot repairs mode and group).
- Decide the history point and say it: either the list isn't a secret from his own user (then C6's "can't read"
  is about the service's group only, and the guide stays), or the guide uses `sudoedit` on the file.

## Notes

- **The probe at step 4** should pass `--detail change <text>` as the service does (`confirm.py:52-53`): details
  from a caller that isn't root are what the action's owner annotation is for, and CI's rule never exercised it.
- **`pack.py` needs the folder to pack as an argument.** The VM layer has no `node`, and the probe and bundles B
  and C are made there. Say it in item 1, so step 4 doesn't reopen a hashed file. This is not a key input.
- **Answer 5 waits on a picture only step 4 makes**, and step 3a waits on answer 5. Either item 2's case 1 saves
  a screenshot of the pinned button and Chrome's "managed" note, or the lead asks in words.
- **`check`** can also require `control.source_revision` equal to the manifest's existing `source_commit`.
- **"The RPM keyring's key list equals the base's"** (image check): say where the base's list comes from, for
  example recorded by the `packages` step before its first import.
- **C6** tests group-writable, missing and the placeholder; add a link in the file's place (it refuses, and
  tmpfiles leaves it with an error).
- **The details page with the placeholder in:** "read-only on" answers "Owner list unavailable; use the admin
  command" (`adapter.py:193-197`, `:861-862`). Harmless before first use; one line for his guide if he may meet it.
