# 18c image part: progress (Part A, step 1; B2, steps 2a to 2c; the Chrome follow-up; 18e in the VM pass; fix round 1, parts 1 and 2; the lead's merge of main; fix round X1; fix round X2; fix round X3; fix round X4)

## Fix round X4 (Codex astra's recheck X3) (2026-11-17–18, Codex gpt-6-astra)

From `RECHECK-X3.md` and the longer scratch review/probes in `.work/recheck-x3/`, on `6c172793` (code head
`537790a2`). Code and regressions: `16bcc784`; this file's later commit uses `[skip ci]`. Only
`os/ci/control/tree_scan.py`, `os/tests/test_control_vm.py` and this file changed. X3's records, held descriptors,
owner handover protocol and final password assertion remain. `actions.py` needed no change: its existing `cover`
handover now receives the records previously lost by the scanner. No image, `control/` or workflow change.
`git fetch origin` completed; `origin/main` is `58d2ae1b`, not merged, as instructed.

### What changed, per finding and per sibling, and the tests

1. **Finding 1: observed names before a record exists.** `listing()` calls the observer for every entry as it
   arrives. The observer registers the name before asking for its inode, retains its first inode, and adds new
   names to the same work list during verification listings. A refused partial listing hands its already-observed,
   unread names to the owner along with the folder; each remains a refusal until covered, or becomes an error.
   Tests in `os/tests/test_control_vm.py`:
   - `:971`, `test_partial_listing_refusal_discards_yielded_names`: a real entry is yielded, then readdir is
     denied; the real file disappears before the real owner scanner subprocess runs. Its path and inode are in
     `cover`, and the missing file remains an error. The recovery case also passes when the owner can search it.
     **X3 baseline:** `AssertionError: False is not true`, `errors: []`; only the folder was refused.
   - `:945`, `test_second_listing_learns_a_new_name_then_discards_it`: a real password file appears after the
     initial listing and is observed during FUSE verification. It is searched: five learned paths = three searched
     files + two listed folders. **X3 baseline:** the `[late.log, 0]` hit is absent; only the stored password is found.
2. **Finding 2: an ordinary mismatch authorized by a second observation of a changing name.** Mountinfo now
   establishes the exceptions: the name is a mount point, or its parent folder's deepest mount is FUSE and every
   entry has the portal constant `4294967295`. Ordinary mismatches are errors immediately. FUSE verification still
   checks that constant and learns all its names; it never infers a numbering scheme from matching repeated stats.
   - `:909`, `test_double_rename_fools_numbering_detection`: the reviewer's real A/B renames, with distinct real
     inodes. The mismatch fails before any second listing; B is never credited for A. **X3 baseline:** `[]` instead
     of the required identity error; both extra renames execute and B is credited as searched.
   - `:891`, `test_non_fuse_non_mount_point_numbering_mismatches_are_errors`: a non-FUSE folder, a non-FUSE mount
     nested inside FUSE, shifted FUSE numbers, and mixed constant/ordinary FUSE numbers all reject the mismatching
     files. **X3 baseline:** `AssertionError: 0 != 2` on the ordinary folder.
   - `:877`, `test_mount_points_and_portal_numbering_are_established_from_mountinfo`: both supported exceptions
     still search the expected files. This replaces X3's test of the removed heuristic with the specified mount
     facts; its positive cases pass on both versions. `:1046`, `test_benign_atomic_rewrite_fails_closed`, also passes
     on both: a harmless atomic rewrite still fails coverage, as requested.
3. **Sibling audit, limited to lost observed names and unproven identity acceptance:**
   - **Repeated names could overwrite their first identity in the dictionary.** The same record is reused, and a
     different inode is a named error. Test `:1003`, `test_repeated_name_cannot_overwrite_its_first_observed_identity`,
     yields real directory entries for a real file before and after replacement. **X3 baseline:** `errors: []`,
     three files credited, only the stored-password hit; the first file remains unread.
   - **`DirEntry.inode()` can fail after the name was observed, including on a repeated observation.** The name is
     already registered; failure to establish that observation's identity is a hard error, which an owner's later
     listing cannot clear. Tests `:1025`, `test_a_name_whose_inode_is_refused_cannot_be_cleared_by_the_owner`, and
     `:1055`, `test_a_repeated_name_whose_inode_is_refused_stays_an_error`. **X3 baseline:** both fail with
     `AssertionError: False is not true`, `errors: []`; the first observation is lost, or the repeated observation
     becomes a recoverable refusal instead of an identity error.
   - Read the remaining name-learning and identity paths in `tree_scan.py`, `search_for()` and `passwords()` once
     under those two rules. No further sibling found. Existing missing-owner-coverage, mount-disappearance,
     changed-file, descriptor, symlink and vanished-content tests still pass. Errors are sorted by path, preserving
     deterministic diagnostics now that registration happens in readdir order.

### Checks run (laptop)

Scratch and temporary test files are under `.work/x4/`; none is committed. The baseline is `git archive 537790a2
os/ci control/boundary control/ci control/README.md` extracted to `.work/x4/baseline/`, with the current test module
copied in. `cmp` confirmed its scanner equals `git show 537790a2:os/ci/control/tree_scan.py`.

- `TMPDIR="$PWD/.work/x4" PYTHONDONTWRITEBYTECODE=1 python3 .work/x4/baseline/os/tests/test_control_vm.py
  PasswordScanTest -v`: **21 tests, FAILED (failures=7)**, 0.956 s; all seven are behavioral assertions, no missing
  interfaces or import errors. The three requested escape probes and the sibling cases fail as described above.
- One module at a time from the worktree root, with the same `TMPDIR` and `PYTHONDONTWRITEBYTECODE`:
  `python3 -m unittest discover -s os/tests -p 'test_control_vm.py' -v`: **62 tests, OK**, 1.176 s;
  `-p 'test_control_image.py'`: **15 tests, OK**, 4.467 s;
  `-p 'test_checkout_sources.py'`: **8 tests, OK**, 0.841 s. No skips.
- In-memory `compile(..., 'exec')` on the two changed Python files: **Syntax: 2 changed Python files, OK**.
  `git diff --check`: clean.
- Read `rebind.py` and compared the changed paths with `checkout.active_tables()`: **Changed bound files: []**.
  No `pending` write was needed; `pending-rebind.json` is unchanged.
- No owner module, local image/VM, mount, system change or Gradle process. No file over 500 MB remains in `.work/`
  (final inventory: `[]`).

### Runs

Every watch uses `gh run watch <id> --exit-status --interval 60`. Logs are saved from `gh run view <id> --log`,
with line numbers counted from 1 over that complete output. Dispatches are sequential, all through `os-image.yml`.

| Run | Head | Mode | Result |
|---|---|---|---|
| 44175714681 | `6ea1d437` (code `537790a2`; only PROGRESS differs) | existing `checks_only` run | **success**: 1,764 tests in 1399.757 s at line 3730; `OK (skipped=4)` at 3732; regression job 24 min 2 s |
| 44180217274 | `16bcc784` | X4 `checks_only` | **success**: 1,772 tests in 1267.634 s at line 3527; `OK (skipped=4)` at 3529 |
| 44184266040 | `16bcc784` | first `check_build=control` | **success**: password PASS 4307; final Control PASS 4317 |
| 44195810105 | `16bcc784` | second `check_build=control` | **success**: password PASS 4262; final Control PASS 4272 |
| 44199832455 | `16bcc784` | `check_build=build` | **success**: `CONSOLE_KEYMAP_PASSED` 4202, then `CHECK_BUILD_VM_PASSED` 4225 |

**Control log lines** (complete logs: 4,373 / 4,328 lines):

| Marker | 44184266040 | 44195810105 |
|---|---|---|
| `CLAUDE_CODE_PINNED` | 1327 | 1279 |
| `CONTROL_CHROME_BUILD` | 1707 | 1664 |
| `CONTROL_INSTALLED` | 1708 | 1665 |
| `CONTROL_CHROME_STARTUP_FILES` | 1709 | 1666 |
| `CONTROL_GENERATED_MATCH` | 1710 | 1667 |
| `CONTROL_FILES_RECORDED` | 3471 | 3428 |
| `CONTROL_WHEELS_FETCHED` | 3581 | 3538 |
| `CONTROL_VENDOR_FROM_WHEELS` | 3582 | 3539 |
| `CHECK_BUILD_PASSED` | 3583 | 3540 |
| `CHECK_BUILD_CONTROL_DISK_READY` | 4274 | 4229 |
| `CONTROL_IMAGE_FILES_PASS` | 4282 | 4237 |
| `CONTROL_ETC_CLAUDE_CODE_PASS` | 4284 | 4239 |
| `CONTROL_RELEASE_CHECKS_PASS` | 4286 | 4241 |
| `CONTROL_IDLE_FOOTPRINT_RECORDED` | 4288 | 4243 |
| `CONTROL_FIXTURES_REACHABLE` | 4290 | 4245 |
| `CONTROL_ENTRY_POINTS_PASS` | 4292 | 4247 |
| `CONTROL_PRECONDITION_PASS` | 4294 | 4249 |
| `CONTROL_USER_MCP_INSTALL_PASS` | 4296 | 4251 |
| `CONTROL_SERVICE_SANDBOX_PASS` | 4298 | 4253 |
| `CONTROL_ORDINARY_SESSION_PASS` | 4300 | 4255 |
| `CONTROL_MAIL_FLOWS_PASS` | 4302 | 4257 |
| `CONTROL_PERMISSION_REQUEST_RECORDED` | 4304 | 4259 |
| `CONTROL_INTERACTIVE_ASK_PASS` | 4305 | 4260 |
| `CONTROL_PASSWORDS_PRIVATE_PASS` | 4307 | 4262 |
| `CONTROL_SELINUX_AFTER_CHECKS_PASS` | 4309 | 4264 |
| `CONTROL_STORAGE_TESTS_PASS` | 4311 | 4266 |
| `CONTROL_SERVICE_RESTART_PASS` | 4313 | 4268 |
| `CONTROL_VM_POWEROFF_CLEAN` | 4315 | 4270 |
| `CHECK_BUILD_CONTROL_PASSED` | 4317 | 4272 |

The image records identify `16bcc784`; both have 74 installed files, 28 wheels and 2,024 vendored paths.
The vendor check derives 1,021 files, 712 bytecode files and 291 folders. Production Chrome build hash
`7854f4a2…cfbbfb` is unchanged. The permission result remains one hook call, zero owner answers, no prompt
and one fixture arrival in `normal-permission-user` (lines 4304 / 4259).

**Check 8** (log summaries at 4308 / 4263, checked against each artifact's `control/passwords.json`):

| Count / outcome | 44184266040 | 44195810105 |
|---|---|---|
| Files searched by root | 1877 | 1851 |
| Learned paths (root) | 2896 | 2867 |
| Searched | 1877 | 1851 |
| Listed folders | 721 | 718 |
| Not a file | 297 | 297 |
| Refused by root | 1 | 1 |
| Errors after owner coverage | 0 | 0 |
| Vanished | 0 | 0 |
| FUSE mounts | 1 | 1 |
| Root refusals in those mounts | 1 | 1 |
| Files searched by the owner | 0 | 0 |

Both sums were checked: **2,896 = 1,877 + 721 + 297 + 1** and
**2,867 = 1,851 + 718 + 297 + 1**. The single FUSE mount is `/run/user/1001/doc` (`fuse.portal`);
the owner covers root's mount-point refusal by listing it. Both journals exit 0 with no password hit;
the only file holding the password is its stored file. `MAY_VANISH` remains empty.

The final evidence scans search 192 files and 439 / 415 archive members: no hits, no unreadable archives,
no files removed; the fixture log is redacted once. Check 8's runner scan searches 56 evidence files and
the same 439 / 415 members, with nothing holding the password and nothing unreadable. These are read from
`control/fixtures/password-scan.json` and `control/passwords-runner.json` in the artifacts.

Control job times: **67 min 45 s / 26 min 2 s**; image/disk build step **48 min 57 s / 11 min 8 s**;
VM pass **9 min 11 s / 8 min 12 s**, both within its 16-minute limit. The slow first run still completed
successfully. Neither Control run was retried.

**Build run 44199832455** (complete log: 4,274 lines). Job **47 min 40 s**; build/check step **41 min 44 s**.
The Control-only steps were skipped by this mode; its general VM checks ran.

| Marker | Log line |
|---|---|
| `CONTROL_CHROME_BUILD` | 1656 |
| `CONTROL_INSTALLED` (74 files, 28 wheels, 2,024 vendored paths, from `16bcc784`) | 1657 |
| `CONTROL_CHROME_STARTUP_FILES` | 1658 |
| `CONTROL_GENERATED_MATCH` | 1659 |
| `CROWN_FILES_PASSED` | 3408 |
| `CONTROL_FILES_RECORDED` | 3420 |
| `IMAGE_CHECKS_PASSED` | 3509 |
| `ROOTLESS_MAPPING_PASSED` | 3520 |
| `POLKIT_CHECK_PASSED` | 3523 |
| `CONTROL_WHEELS_FETCHED` | 3530 |
| `CONTROL_VENDOR_FROM_WHEELS` | 3531 |
| `CHECK_BUILD_PASSED` | 3532 |
| `ARESOS_ACTIVE_SESSION_POLKIT_PASSED` | 4198 |
| `ARESOS_GUEST_CHECKS_PASSED` | 4199 |
| **`CONSOLE_KEYMAP_PASSED`** | **4202** |
| `ARESOS_POWER_EVENTS_PASSED` | 4206 |
| **`CHECK_BUILD_VM_PASSED`** | **4225** |

The keymap marker records the boot setting and repair after a forced busy-VT skip, and precedes the final VM marker.
**No infrastructure failure, rerun or second CI fix round was needed.** All four X4 dispatches ran sequentially on
`16bcc784`; the existing X3 run finished successfully before the first X4 dispatch.

### Known limits

- A reused inode can hide replacement between listing and open. Normal tmpfs/btrfs allocation is not a global
  uniqueness guarantee across wraparound or remounts. Changing bytes in an open file, names never observed,
  equivalent unmount/remount and recursion depth retain X3's limits. This is not a filesystem snapshot.
- The FUSE exception is now limited to mountinfo's FUSE type and the portal's constant on every observed name.
  That constant still cannot distinguish replacements; the held descriptor ensures the opened file is the one read.
  Arbitrary shifted numbering, mixed numbering and other unproven mismatches fail closed, even if benign.
- A mount point's covered-folder inode cannot identify the mounted root. Mountinfo independently establishes the
  exception, but is not a lock against mount changes during the walk. No new claim of snapshot or remount detection.
- Failure to read an observed entry's inode is a hard error, even if the owner could later list its name: that later
  observation cannot establish the missing identity. A benign atomic rewrite remains an error; no exemption added.

### Done

Both RECHECK-X3 findings and the two related sibling cases are closed, with checked-in real-file regressions and
seven behavioral baseline failures on `537790a2`. The local modules, syntax and whitespace checks pass. The existing
merged-code X3 checks-only run passed; X4 checks-only passed 1,772 tests; two separate Control runs and the build
run passed on `16bcc784`, with the required keymap marker before the final build VM marker. All requested evidence
and counts are above. Only this progress record changes after that code head.

No new owner JUDGMENT-CALL. This is a CI-only correction implementing the requested exceptions and fail-closed
policy, with X3's record structure preserved. The technical limits above remain explicit.

### Left, in order

1. A fresh `gpt-6-astra` recheck of X4, `6c172793..16bcc784`, including the baseline regressions.
2. `linux-aresos` reads the `os/` diff for this round (the section below is updated).
3. The lead (`linux-tools`) assembles `reviews/18c-image-test/REPORT.md`, including these results and the prior
   production/security limits.
4. The merge, by the lead. PR #58 remains unmerged; this session did not mark it ready.

### Observations for the lead

- Summing records only proves coverage after names are registered. Registration now precedes inode lookup and
  survives partial/repeated/verification listings; the tests specifically exercise those boundaries.
- Ordinary filesystems have no second-listing identity heuristic. Both supported exceptions rely on mount facts;
  the portal's weaker identity guarantee remains visible rather than being generalized to other mismatches.
- The old X3 observation requesting a merged-head checks-only run is superseded by run 44175714681 above.
- Evidence and baseline logs remain under `.work/x4/`; only code, tests and this progress record are pushed.


## Fix round X3 (Codex astra's recheck X2) (2026-11-17, Claude agent on Fable 5.2)

From `RECHECK-X2.md` (Codex `gpt-6-astra`'s recheck of fix round X2 on `fda41017`: CHANGES-NEEDED, two should-fixes,
both in check 8's tree scan; the merge correct; security unchanged, SAFE), on head `23bff734`. Fable, because this is
the third round on the same check and each round so far closed its findings while the next found edge cases one level
deeper: the job was to make the check right by construction, not to patch the two cases. Commits: `8b2e60fa` (#1 and
the scan's new structure), `7dbaea7b` (#2), `537790a2` (the merge of `main` at `3a5eea14`: packages 52, 46 and 79),
and this file's commit (`[skip ci]`). **Final head: `537790a2`.** Everything this round changed is CI-only
(`os/ci/control/tree_scan.py`, `os/ci/control/actions.py`, `os/tests/test_control_vm.py`) or this folder; nothing in the
image, `control/` or the workflow. None of the three is a bound file (`test_checkout_sources` passes with the pending
list untouched).

### What check 8 guarantees now, and how

Every path the scan learns is either searched, that very file, or named as an error that fails the check.
`tree_scan.py` (`scan()`, `:245`) keeps **one record per learned path**: a root it is given, or a name a folder's
listing returns. `Scan.read()` (`:171`) is the one place a record gets its outcome: `searched` (a regular file, read
to its end), `listed` (a folder: its listing read to its end, every name in it a record before the first is read),
`not a file` (a link, socket, pipe or device: nothing to search, never opened, a link never followed), or an error.
`Scan.answer()` (`:213`) builds the whole answer from the records, so there is no second list a path could be missing
from: whatever is not one of the three good outcomes is in `errors` (or, in root's walk of a FUSE mount, in `refused`,
which `search_for()` turns into an error unless the mount's owner searched that path). The one exemption is X2's: a
vanished path that `MAY_VANISH` names, and it still names none. `passwords.json` gains `paths`
(how many paths were learned and how many ended in each outcome); `scanned`, `fuse_mounts`, `owner_walks`, `vanished`
and `errors` keep their names and shapes, and no PASS line changed. Nothing in `os/ci/control/` or
`reviews/18c-image-test/verify-evidence.py` reads those fields (checked: `control_vm.py` prints the action's summary
and writes `passwords-runner.json` from the evidence scan; `verify-evidence.py` reads the boundary artifact only).

### What changed, per finding and per sibling, and the test that pins it

Each regression fails on `fda41017`'s code and passes now. The baseline: `git archive fda41017 os/ci control/boundary
control/ci control/README.md` unpacked under `.work/x3/baseline/` (never committed), this round's
`os/tests/test_control_vm.py` copied in, `PasswordScanTest` run there. The new tests make their races on the real file
system, at a point both scanners pass (`listed()`, `:639`: once a folder's listing has been read; `stated()`, `:680`:
once the scanner has stat'ed a file), so the baseline failures are X2's own behaviour, not a missing helper.

1. **#1, replacement bytes standing in for unread content.** The choice was between failing an observed
   disappearance even if the name reappears, and proving the retry read the same file. **Both, and one step more,
   because either alone leaves a deeper case:**
   - **The scanner holds the file.** A name is opened once, as a handle on the file itself (`O_PATH`, relative to
     its folder's handle, links not followed; `Scan.search()`, `:188`). Its type is read from that handle and its
     content through it (`reopened()`, `:114`: `/proc/self/fd`). There is no stat by name followed by an open by
     name any more, so the reviewer's window (stat'ed, removed, replaced, read) is gone: the file the scanner stat'ed
     is the one it reads, removed or not.
   - **No second try.** A name that is gone when it is opened is an error ("gone before it was read", and named
     under `vanished` in the runtime folders), also when it is back a moment later. **This removes X2's "a replaced
     file is read again".** X2 kept it so that a file a process rewrites would not fail the check; but what it read
     was whatever was under the name then, and the listed content stayed unsearched with no error, which is the
     finding. X1's and X2's four control runs had `vanished: []` and `errors: []`, so failing costs nothing seen.
   - **The listing says which file was listed.** Comparing `lstat`'s `st_dev`/`st_ino` with `fstat` of the opened
     descriptor (the reviewer's example) would have left two holes: ext4 and XFS give a new file the number of one
     just removed, so the replacement can carry the same pair; and the `lstat` itself comes after the listing, so a
     swap between the two is never seen. So the number comes from the listing itself (`listing()`, `:120`: each
     name with the inode number its folder's listing gives it), and the handle, which keeps its number from going to
     another file, is compared with it. Another number: "not the file its folder listed (inode A there, B opened):
     replaced before it was read, so its content is unsearched", an error; what was put there is not searched in
     its place.
   - **Listings that number otherwise** (`numbered_otherwise()`, `:135`). A mount point is listed under the number
     of the folder it covers, and the document portal's FUSE server gives every name 4294967295 (read on the laptop's
     own portal mount; its folders' own numbers are 2, 3, 4). So a differing number alone would fail every mount
     point under `/run`. The listing is asked a second time: a listing whose numbers are the files' own now gives
     the name the opened file's number, which is not the first one; only a listing that numbers otherwise repeats
     the first. The name must still be the opened file afterwards.
   - Tests (`os/tests/test_control_vm.py`, `PasswordScanTest`):
     - `:762` `test_a_file_removed_and_replaced_once_the_scanner_has_stated_it_is_the_one_searched`: the reviewer's
       sequence on the real file system (stat'ed; removed; a clean file under the name when the scanner looks
       again). Now: the hit is in the file the scanner stat'ed, `errors: []`, `vanished: []`.
       **Baseline:** "AssertionError: False is not true : the file the scanner stat'ed was removed and replaced; its
       content was neither searched nor named as an error: {'files': {'…/scanned': 3}, 'hits': [['…/state/password',
       0]], 'vanished': [], 'errors': [], 'refused': {}}": the reviewer's result.
     - `:780` `test_what_is_put_under_a_listed_name_before_it_is_opened_is_never_searched_in_its_place`: the same
       swap one step earlier, between the folder's listing and the scanner's first look, in four forms: a file
       renamed over the listed one, a folder with another folder in its place, a folder with a link in its place
       (not followed), a file with a folder in its place. Each is the "not the file its folder listed" error, no
       hit from what was put there, the rest searched.
       **Baseline:** "AssertionError: Tuples differ: ([], [['…/scanned/state/pass[43 chars]: 3}) !=
       (['…/scanned/state/debug.log[216 chars]: 2})"; the diff under it has `([],` where this round has "…/state/
       debug.log: not the file its folder listed (inode 20115792 there, 20115793 opened): replaced before it was
       read, so its content is unsearched", and 3 files searched where this round has 2: X2 read the replacement, no
       error.
     - `:844` `test_a_listing_that_numbers_otherwise_is_asked_a_second_time`: a listing that gives every name
       4294967295 passes with everything searched; a listing whose numbers are not the files' own but differ per
       file still shows a replaced file; the first number again because the listed file was moved away and back,
       with another file opened meanwhile, is still an error. (New functions; no baseline.)
     - `:706` `test_runtime_content_that_vanishes_unread_fails_and_is_named` (X2's test): its assertions on vanished
       files, the folder, `MAY_VANISH` and `search_for()` are unchanged, but the files are now removed at the moment
       the folder's listing has been read (X2 removed them inside a stand-in for `holds()` and raised the failed open
       itself; the scanner no longer calls `holds()` by path).
       **Its last block is changed, because it encoded what this finding removes:** it asserted that a file gone
       and back is read again with `errors: []`. It now asserts the opposite: gone when opened and back the moment
       the scanner has seen that, it is `vanished` and an error, and the new file is not read in its place.
2. **#2, the owner fallback discarding a known unread FUSE path.** `os/ci/control/actions.py`, `search_for()`
   (`:1515`), and `Scan.answer()`:
   - Root's refusals at or under a FUSE mount stay structured: `[path, the number root's listing gave it, the
     refusal]` per mount.
   - The owner still walks the whole mount, and is now told those paths (`cover`, `:1537`). Its answer names each
     of them its walk met under that number and searched, listed or found not to be a file (`covered`).
   - **Root's refusal stands as an error unless that very path is named** (`:1552`): "…: PermissionError: Permission
     denied, and <owner>'s walk did not search it either". So a path that is gone by then, that the owner's view
     leaves out, that is another file by then, or that is refused to the owner too, fails the check. The owner's
     own errors are added as before, never in place of root's.
   - Test `:1026` `test_what_root_is_refused_inside_a_fuse_mount_its_owner_must_search_path_by_path`, with the real
     `tree_scan.py` started as the owner's process (`owner()`, `:970`): root lists the mount and is refused on
     `private.log` in it. Recovered (the owner reads it: the hit is found, `errors: []`); gone or left out of the
     owner's view (the error above); another file under the name by then ("not the file root was refused", and
     root's refusal stands); refused to the owner too (both errors); a folder root can't list (its owner lists it
     and finds what it holds); the mount gone before the owner's walk; an owner's answer without `covered` (X2's
     scanner) raises.
     **Baseline:** at the omission, "AssertionError: Tuples differ: ([], [['…/scanned/state/password', 0]]) !=
     (["…/scanned/user/1001/doc/p[136 chars] 0]])"; the diff under it has `([],` where this round has "…/user/1001/doc/
     private.log: PermissionError: Permission denied, and ares's walk did not search it either": X2 returned
     `errors: []`. (The recovery passes on the baseline too, as the reviewer said.)
3. **Siblings: other places where something known to be unread could leave the count.** Looked for in `tree_scan.py`,
   the FUSE handover and `passwords()`; each fixed under the same rule:
   - **A folder replaced after it was listed in its parent.** X2's `os.walk` walked whatever folder was under the
     name by then, and skipped it without a word if it was a link by then (`islink` at the descent). Now a folder
     is a record like a file: opened as a handle, compared with its listing's number. Test `:780` (its second and
     third forms).
   - **A file that is a folder by the time it is read** (or the reverse): X2 skipped it as "not a regular file". The
     type now comes from the handle that is compared with the listing. Test `:780` (its fourth form).
   - **A parent folder swapped for a link during the walk.** X2 opened every file by its full path, so a path could
     lead through a link put there meanwhile into another tree, read under the old names. Every open is now
     relative to the folder's handle, and no listed name is opened through a link (`O_NOFOLLOW`). Pinned by `:901`
     and `:780` (they fail if links are followed).
   - **A folder removed between its open and its listing.** New with handles: a removed folder lists as empty
     (glibc reads the kernel's ENOENT as the end of the folder), so it would have counted as listed with nothing in
     it. `listing()` checks the handle's link count after reading: 0 is "gone before it was read". Test `:706`
     (X2's folder case, in both orders: removed as its listing starts, and removed before it is opened).
   - **A needle across short reads.** `holds()` and the journal loop kept only the last read's tail, so a needle
     spread over three reads, the middle one shorter than the needle, was missed. Not reachable through Python's
     buffered reads of a file or pipe today (they are full until the end), but nothing said so. One function now,
     `found_in()` (`:64`), keeps the tail across reads, and `search_for()` reads the journal's export with it
     (`actions.py:1561`) instead of its own copy of the loop. Test `:935` (also: a journal export holding the
     needle is reported).
   - **The handover, by number.** A file put under the refused name before the owner's walk is not the file root
     was refused: the owner's listing must give the name the number root's did (a FUSE server that gives every name
     one number passes this without proof, as below). Test `:1026` ("another file").
   - **The mount gone before its owner walks it.** The owner would walk the empty folder under the mount point and
     answer "listed". `search_for()` requires the mount to be in `/proc/self/mountinfo` still when the walk has
     ended (`:1555`). Test `:1026`.
   - **Refusals with nowhere to go.** `search_for()` asserts that every refusal is filed under a mount its loop
     meets, and that the owner's own answer hands nothing on (`:1526`, `:1546`): neither can happen as the code
     stands, and neither can now happen silently.
   - **Looked at and left:** `passwords()` asserts on `errors`, on the journal and on the hits being exactly the
     stored file, which is also the scan's proof that it finds the password where it is; `operations_jsonl_holds_it`
     is informational (that file is under a scanned root, so a hit there fails the check through `hits`); an owner
     walk that exits non-zero keeps root's refusals and adds its failure; an exception anywhere in the action is a
     failed check (`checks.py:596`), and `control_vm.py` prints a PASS line only for `returncode == 0`.

### Known limits (stated at the top of `tree_scan.py`)

- **A reused inode number.** A file system that gives a new file the number of one just removed (ext4 and XFS do;
  tmpfs and btrfs count upwards) hides a file that is removed and made again between its folder's listing and its
  open. The guest's scanned folders are on tmpfs (`/run`, `/tmp`) and btrfs (`/var`: `check-build.sh` builds the disk
  with `--rootfs btrfs`), so it does not apply there. Nothing the kernel reports about a listed name outlasts the
  file but that number; the folder's change time would show it, but it also changes with every unrelated file made
  or removed in a busy folder.
- **A FUSE server that gives every name one number** (the document portal) gives its listings nothing to hold a
  file to. There the handle still makes the file opened the file searched, and no more. The same holds for the
  number handed from root to the owner.
- **The scan is a walk, not a snapshot.** A file removed before its folder is listed, or moved from a folder not
  yet listed into one already listed, is never learned. Each file is searched as it was while it was read.
- **A FUSE mount unmounted and mounted again** at the same point, of the same type and owner, between root's
  refusal and the end of its owner's walk is taken for the same mount.
- **Depth.** The walk recurses, two Python frames per folder level: a tree more than about 490 folders deep raises
  `RecursionError`, which fails the check (X2's `os.walk` had no such limit; the guest's trees are a few levels deep).

### The merge (`537790a2`, `main` at `3a5eea14`)

After the regressions-only run was green on `7dbaea7b`. `main` moved from `04aef030` (X2's merge) to `3a5eea14`:
**package 52** (`1dc4d188`: Prism's metadata pinned by commit, so image builds work again), package 46 (the mod saves
the world on request: `mod/`, and nine lines of `os/tests/test_aresos_desktop.py`) and package 79 (Chrome's
qualification record is checked once per record: `control/aresos_control/chrome/`, `control/aresos_control/engine.py`,
`control/chrome/ci/`, `control/chrome_tests/`), with their briefs, reviews, `STATE.md` and `HANDOFF.md`. A normal merge
commit, no rebase, **no conflicts**. Under `os/` it brings exactly two files, both `main`'s:
`os/minecraft/desktop.lock.json` (the two metadata URLs now `raw.githubusercontent.com/PrismLauncher/meta-launcher/
<commit>/…`, the SHA-256s unchanged) and `os/tests/test_aresos_desktop.py`; nothing under `.github/`.

`os/manifest/ci/16/pending-rebind.json`: `main` did not change it since `04aef030`, so there was nothing to take a
side on. Checked with the tool all the same (`rebind.py pending` with a note for this merge): "10 bound files differ
from the active bindings, 0 removed", the same ten rows, only the note added; neither of `main`'s two `os/` files is
a bound file. The note was reverted, as X1 and X2 did when no bound file changed, so the list is byte for byte X2's.

### Checks run (laptop)

- Before the merge (`7dbaea7b`), one module at a time: `test_control_vm` 54 OK (48 + 6 new tests; 1.0 s),
  `test_control_image` 15 OK, `test_checkout_sources` 8 OK.
- After the merge (`537790a2`): `test_control_vm` 54 OK (0.9 s), `test_control_image` 15 OK (4.3 s),
  `test_checkout_sources` 8 OK (0.8 s), and `test_aresos_desktop` 189 OK (skipped=1; 168 s), which `main` changed.
  Nothing left running. No owner module (`test_owner_*`), no `rpm-ostree`, `bootc` or `ostree` command, nothing
  mounted, no sudo.
- `bash -n os/ci/check-build.sh os/ci/check-image.sh os/ci/control/runner.sh` (no shell file changed this round);
  `git diff --check` clean over this round's commits.
- The baselines above, against `fda41017`'s `os/ci/control/` in `.work/x3/baseline/`: 4 failures and 3 errors of 13
  (`:762`, `:780`, `:1026` and X2's changed `:706` fail; `:844`, `:901` and `:935` use functions and a field X2's
  scanner doesn't have).
- **Each rule is pinned:** eighteen one-line weakenings of this round's code (no listing number; every listing or
  none taken to number otherwise; the second listing or the name after it not compared; a removed folder read as
  empty; links followed; the last read's tail only; a vanished path not an error; errors not taken from the records;
  the handover ignoring the number, the outcome or whether the path was met; root's refusal dropped after the
  owner's walk or when the owner fails; `cover` not sent; the mount not checked after the walk; the file read by
  its path again), each tried alone in a scratch copy: every one fails at least one `PasswordScanTest` test.
- The scanner over this checkout's `os/` and `control/` as a plain user: 14,313 files searched and 1,041 folders
  listed in 1.3 s, the numbers `find -type f` and `find -type d` give, no error.
- Read on the laptop's own document portal mount (as its owner, listing only): every name's listing number is
  4294967295, the folders' own numbers 2, 3 and 4, link counts 2. On tmpfs and btrfs here a listing's number is the
  file's own; a file removed after it is opened is still read through its handle; a removed folder lists as empty.

### Runs

| Run | Head | Mode | Result |
|---|---|---|---|
| 44140465984 | `7dbaea7b` | regressions only (`checks_only`) | **success**: "Ran 1764 tests in 1881.560s" (log line 3752), "OK (skipped=4)" (3754): X2's 1758 and this round's 6; the job 17:49:10 to 18:21:16 UTC = 32 min 6 s, the ways-back model job green in 16 s |
| 44147238097 | `537790a2` | `check_build=control` | **success** (below) |
| 44152536778 | `537790a2` | `check_build=control` | **success** (below; a new dispatch, after the first had ended) |
| 44166220023 | `537790a2` | `check_build=build` | **success** (below): the image's packages stage passes again with package 52's pin (`PINNED 9c23199a…2b46 …/net.minecraft.json`, log line 3339) |
| PR #58's workflows on `537790a2` | | Repo privacy, Control base, Control boundary, Control Mail, Control Chrome, Control Chrome qualification | all **success** |

No run was rerun: no infrastructure failure this round.

**Log lines** (`gh run view <id> --log`, line numbers from 1; the two control logs have 4326 and 4394 lines, so
their numbers differ):

| Line | 44147238097 | 44152536778 |
|---|---|---|
| `CLAUDE_CODE_PINNED 2.1.319 sha512-FO4Sd23B…oOQ== dabafec8…8eed` | 1277 | 1348 |
| `CONTROL_CHROME_BUILD 7854f4a2…cfbbfb` | 1662 | 1728 |
| `CONTROL_INSTALLED 74 files, 28 wheels, 2024 vendored paths from 537790a2…` | 1663 | 1729 |
| `CONTROL_CHROME_STARTUP_FILES build 7854f4a2…cfbbfb, 8 qualification entries` | 1664 | 1730 |
| `CONTROL_GENERATED_MATCH 15 files` | 1665 | 1731 |
| `CONTROL_FILES_RECORDED 74 files, 2024 vendored paths, 28 wheels from 537790a2…` | 3426 | 3492 |
| `CONTROL_WHEELS_FETCHED 28 wheels, 9732253 bytes from PyPI` (2.0 s / 2.1 s) | 3536 | 3602 |
| `CONTROL_VENDOR_FROM_WHEELS 2024 vendored paths: 1021 files from 28 wheels and pip, 712 bytecode, 291 folders` | 3537 | 3603 |
| `CHECK_BUILD_PASSED` | 3538 | 3604 |
| `CHECK_BUILD_CONTROL_DISK_READY` | 4227 | 4295 |
| `CONTROL_IMAGE_FILES_PASS` | 4235 | 4303 |
| `CONTROL_ETC_CLAUDE_CODE_PASS` | 4237 | 4305 |
| `CONTROL_RELEASE_CHECKS_PASS` | 4239 | 4307 |
| `CONTROL_IDLE_FOOTPRINT_RECORDED {…}` | 4241 | 4309 |
| `CONTROL_FIXTURES_REACHABLE` | 4243 | 4311 |
| `CONTROL_ENTRY_POINTS_PASS` | 4245 | 4313 |
| `CONTROL_PRECONDITION_PASS` | 4247 | 4315 |
| `CONTROL_USER_MCP_INSTALL_PASS` | 4249 | 4317 |
| `CONTROL_SERVICE_SANDBOX_PASS` | 4251 | 4319 |
| `CONTROL_ORDINARY_SESSION_PASS {…}` | 4253 | 4321 |
| `CONTROL_MAIL_FLOWS_PASS` | 4255 | 4323 |
| `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1, "owner_answers": 0, "prompt_shown": false, "send_arrivals": 1}}` | 4257 | 4325 |
| `CONTROL_INTERACTIVE_ASK_PASS` | 4258 | 4326 |
| `CONTROL_PASSWORDS_PRIVATE_PASS` | 4260 | 4328 |
| `CONTROL_SELINUX_AFTER_CHECKS_PASS` | 4262 | 4330 |
| `CONTROL_STORAGE_TESTS_PASS {…}` | 4264 | 4332 |
| `CONTROL_SERVICE_RESTART_PASS` | 4266 | 4334 |
| `CONTROL_VM_POWEROFF_CLEAN` | 4268 | 4336 |
| `CHECK_BUILD_CONTROL_PASSED` | 4270 | 4338 |

Every PASS line of X2's runs is there, in X2's order. Check 8's own summary is the line after its PASS line (4261,
4329).

**Run 44147238097**:
- Times: job 18:26:49 to 18:51:33 UTC = 24 min 44 s (against 131); tools 2 min 42 s; build step 18:32:01 to
  18:43:14 = 11 min 13 s; **Control VM step 18:43:14 to 18:51:27 = 8 min 13 s** against 16. A fast runner: every
  phase was quicker than in any earlier run (the disk alone 6 min against X2's 31), with the same lines in the same
  order and the image built from `537790a2` (`CONTROL_INSTALLED … from 537790a2…`).
- The fixture stop step was green.
- Step times (s): boot to channel 28.6, files 2.6, idle 59.7, entry points 3.4, precondition 1.4, user MCP 4.6,
  **check 6 222.4**, check 7 32.3, check 9 104.9, check 8 0.4, storage tests 28.1, restart 0.7; the pass 491.9.

**Run 44152536778**:
- Times: job 19:05:52 to 20:08:16 UTC = 62 min 24 s (queued 13 min before that); tools 1 min 51 s; build step
  19:08:52 to 19:58:28 = 49 min 36 s; **Control VM step 19:58:28 to 20:08:11 = 9 min 43 s** against 16.
- The fixture stop step was green.
- Step times (s): boot to channel 54.5, files 5.2, idle 59.4, entry points 5.4, precondition 2.5, user MCP 13.1,
  **check 6 235.3**, check 7 39.2, check 9 119.2, check 8 0.6, storage tests 43.2, restart 1.2; the pass 582.5.

**Run 44166220023** (`check_build=build`; its log has 4268 lines):
- Times: job 20:13:04 to 20:59:35 UTC = 46 min 31 s (against 120); tools 5 min 34 s; build step 20:19:58 to
  20:59:29 = 39 min 31 s. The two Control steps were skipped, as they are in this mode.
- PASS lines: `CONTROL_CHROME_BUILD 7854f4a2…cfbbfb` (1650), `CONTROL_INSTALLED 74 files, 28 wheels, 2024 vendored
  paths from 537790a2…` (1651), `CONTROL_CHROME_STARTUP_FILES build 7854f4a2…cfbbfb, 8 qualification entries` (1652),
  `CONTROL_GENERATED_MATCH 15 files` (1653), `CROWN_FILES_PASSED: …` (3402), `CONTROL_FILES_RECORDED 74 files, 2024
  vendored paths, 28 wheels from 537790a2…` (3414), `IMAGE_CHECKS_PASSED` (3503), `ROOTLESS_MAPPING_PASSED` (3515),
  `POLKIT_CHECK_PASSED` (3517), `CONTROL_WHEELS_FETCHED 28 wheels, 9732253 bytes from PyPI, 1.6 s` (3524),
  `CONTROL_VENDOR_FROM_WHEELS 2024 vendored paths: 1021 files from 28 wheels and pip, 712 bytecode, 291 folders; 2.1 s`
  (3525), `CHECK_BUILD_PASSED` (3526), `ARESOS_ACTIVE_SESSION_POLKIT_PASSED` (4192), `ARESOS_GUEST_CHECKS_PASSED`
  (4193), **`CONSOLE_KEYMAP_PASSED: boot setting and repair after a forced busy-VT skip` (4196)**,
  `ARESOS_POWER_EVENTS_PASSED: lid and sleep keys observed/ignored; direct sleep requests rejected` (4200),
  **`CHECK_BUILD_VM_PASSED` (4219)**. The console keymap line comes before `CHECK_BUILD_VM_PASSED`, as package 50
  requires and as X2's merge placed its check: the merged build-only keymap path, which X2's failed build run left
  unverified (`RECHECK-X2.md`), has now run on a head that carries it.

### This round's evidence (run 44147238097 / run 44152536778)

- **Check 8 in the guest** (`passwords.json`): **1851 / 1891 files searched by root, `errors: []`, `vanished: []`**
  (so nothing needed `MAY_VANISH`, and no file was replaced between its listing and its open), the journal export
  exit 0 with nothing on stderr; per folder `/var/home/ares` 931 / 931, `/run` 481 / 484, `/var/tmp` 402 / 439,
  `/var/lib/aresos-tools` 14, `/var/log` 12, `/root` 5, `/tmp` 3, `/var/lib/aresos-operation-evidence` 3; the one file
  holding the password is the stored one. (X2's runs: 1866 / 1874; the difference is `/var/tmp` and `/run`.)
- **Every path accounted for** (`paths`, new): **2867 / 2910 paths learned by root = 1851 / 1891 searched + 718 / 721
  folders listed + 297 / 297 not files + 1 / 1 refused**, no error, nothing gone. The sums are exact.
- **The FUSE mount and the handover:** `fuse_mounts: [{mount: /run/user/1001/doc, type: fuse.portal, owner: ares,
  root_refused: 1}]` both times: root's one refusal is the document portal's mount point. It went to `ares`'s walk
  as the one path to cover; that walk listed it (0 files, no error), which took root's refusal back, and the mount
  was still mounted afterwards. (On the laptop the portal lists its own `by-app` folder under 4294967295; the
  guest's walk of the same file system raised no error.)
- **Check 8's time:** 0.4 s and 0.6 s (X2: 0.4 s): handles and listing numbers cost nothing that shows.
- **The vendor check**: `CONTROL_VENDOR_FROM_WHEELS 2024 vendored paths: 1021 files from 28 wheels and pip, 712
  bytecode, 291 folders` both times: X2's counts.
- **The evidence scan** (`runner.sh stop`, `fixtures/password-scan.json`): **192 files, 415 / 452 archive members**,
  `"unreadable": []`, `"holding": []`, GreenMail redacted once, nothing removed. Check 8's own scan on the runner
  (`passwords-runner.json`): 56 evidence files, 415 / 452 members, nothing unreadable. Each artifact has 195 files.
- **Check 9's transcripts:** one per case in both runs (`normal-yes`, `skip-no`, `skip-user-allow-send`,
  `normal-permission-user`).
- **Unchanged from X2**, both runs: `desktop_with_service_failed` (the service `failed`, `NRestarts=5`,
  `Result=exit-code`; logged out in 11.2 s / 11.4 s, the desktop up again in 12.5 s / 13.8 s, `SETUP`, not latched,
  greetd session `1` then `3`, `marks_after_logout: false`); `held_work` 4 model requests, 1 extra, 1 continuation,
  both reminders `true`; **`held_elsewhere` 2 model requests, 0 extra, 0 Stop continuations, `requests_carrying_it:
  []`**; check 6's CLI while stopped `service_unavailable` after 3.18 s / 3.31 s; idle 1 context switch in 60 s,
  1.1 ms / 1.7 ms of CPU, `memory.current` 32,948,224 B / 33,062,912 B, RSS 37,124 / 36,916 KiB, PSS 25,281 /
  25,310 KiB, 1 process, 1 thread.

### Done

The two should-fixes of `RECHECK-X2.md`, each with its regression test and its baseline failure on `fda41017`, and
the siblings found under the same rule, by restructuring the scan rather than by patching the two cases: one record
per learned path, one outcome each, the answer made from the records. `main` merged at `3a5eea14` (package 52 in, no
conflict). Regressions only green (1764 tests, on `7dbaea7b`), `check_build=control` green twice on the final head
(44147238097, 44152536778), **`check_build=build` green once on the final head (44166220023), with
`CONSOLE_KEYMAP_PASSED` before `CHECK_BUILD_VM_PASSED`**: the run X2 could not get. PR #58's six workflows green.
Only this file changed after `537790a2`.

No JUDGMENT-CALL for the owner: the round is CI-only. The technical choices are in "What changed" (hold the file
and fail closed and compare with the listing's number; a replaced file is an error with no exemption; a listing that
numbers otherwise is asked again instead of exempting FUSE or mount points by type).

### Left, in order

This replaces X2's list below (its item 1, the pinned Minecraft metadata, is package 52, merged here; its build run
is 44166220023).

1. A fresh `gpt-6-astra` recheck of this round's fixes and what they touched (`docs/REVIEW.md`, "Tools for Claude",
   step 3): `23bff734..537790a2`, the merge included.
2. `linux-aresos` reads this round's `os/` diff (agreed change 16): the section at the end is up to date with this
   round. X2's was read (`main`'s `616ab0cd`).
3. The lead assembles `reviews/18c-image-test/REPORT.md` as listed in the merge section below, with X1's known limits
   word for word, X2's known limit (a V7 tar with a damaged first header), this round's known limits (above) and
   this round's runs and log lines.
4. Merge (the lead's).
5. The last step deletes this file.

### Observations for the lead

- **Check 8 is stricter in one more way: a file replaced between its folder's listing and its open fails the check**
  ("not the file its folder listed"), with no exemption table. Both runs had none. A program that rewrites a file
  by writing a new one and renaming it over the old does exactly this, so a later run can fail if a file is
  rewritten just as the scan reaches it; the path is then named. If one turns out to be harmless and regular, the
  honest fix is to search what is there as well and exempt that path with its reason, like `MAY_VANISH`; nothing
  needs it today.
- **The regressions-only run was on `7dbaea7b`, before the merge,** as this round's order of work had it. The merged
  head `537790a2` has the laptop's four modules, PR #58's six workflows, two control runs and the build run, but no
  hosted run of all of `os/tests`; `main`'s own runs cover what the merge brought. One `checks_only` dispatch would
  close that, if the lead wants it.
- **`passwords.json` has one new field, `paths`,** and check 8's line in the log now carries `paths` and
  `fuse_mounts` too, so the counts can be read from the log without the artifact. The owner's walk has no such
  count in the evidence (`owner_walks` keeps X2's shape); if the recheck wants it, it is one field.
- **`CONTROL_CHROME_BUILD` moved** to `7854f4a2…cfbbfb` with `main`'s package 79 (8 qualification entries, as
  before): for `control/chrome/builds.json`, if the lead keeps that record.
- **Runner speed varies a lot:** the first control run took 24 min 44 s, the second 62 min 24 s, on the same head
  with the same lines: the first runner was fast in every phase.
- `main` moved once more while this round ran (package 79, `3a5eea14`, after the lead's message about package 52):
  it is in the merge, and the control and build runs cover it.
- No infrastructure failure and no rerun this round.

## Fix round X2 (Codex astra's recheck) (2026-11-17, Claude agent on Opus 5.5)

From `RECHECK-X1.md` (Codex `gpt-6-astra`'s recheck of fix round X1 on `48570285`: CHANGES-NEEDED, three should-fixes,
all in CI checks; security unchanged, SAFE), on head `8cbdfd02`. Opus, because the fixes were decided by the lead.
Commits: `8d9954b6` (#1), `a2bd7ddb` (#2), `dc9ca2aa` (#3), `dcbb70dd` (the merge of `main`, the lead's addition),
`fda41017` (a test the merge needed), and this file's commit (`[skip ci]`). **Final head: `fda41017`.** Everything this
round changed is CI-only (`os/ci/control/`, `os/tests/`) or this folder; nothing in the image, `control/` or the
workflow. `check-image.sh` is unchanged. `rebind.py pending` recorded no bound file for the three fixes (only its note,
reverted, as in X1); the merge's run of it is below.

### What changed, per finding, and the test that pins it

Each regression fails on `48570285`'s code and passes now (run against the old file on the laptop, as X1 did: the file
swapped for `git show 48570285:<path>`, the test run, the file put back).

1. **#1, siblings of `vendor/`.** `os/ci/control/vendor_check.py`, `check()` (`:206`):
   - **What `build.sh` puts in `/usr/lib/aresos-control`:** only `vendor/`. `build.sh control` requires the folder
     absent (`test ! -e /usr/lib/aresos-control`), then `pip install --target …/vendor` and the compile fill
     `vendor/`; `bin/` (console scripts) is inside it. **No other check binds a file there to the checkout:**
     `check-image.sh` holds the record's `files`, `directories` and `links` to `build.sh control-tree`, and none of
     them is under that folder; the record's `vendor` map is the whole folder (`walk(DEPENDENCIES)`).
   - So the whole tree is derived independently: `check()` now removes all of `/usr/lib/aresos-control` (`:216`,
     was only `vendor/`) and writes the tree the wheels install at `vendor/`. A sibling of `vendor/`, recorded in the
     manifest or not, is "recorded, not derived". The docstring says why.
   - Test (`os/tests/test_control_image.py`, `test_the_record_must_be_what_the_locked_wheels_install`, `:403`, the
     block at `:448`): a sibling source file (`extra.py`), a sibling `.pyc` (compiled, its source removed) and a
     sibling folder, each made in the image and recorded in its manifest, fail with "recorded, not derived".
   - **Baseline:** with `48570285`'s `vendor_check.py` the test fails at its first sibling ("Mismatch not raised : a
     sibling source file"); a probe of each case alone: all three accepted by the old check, all three refused now.
2. **#2, runtime content that vanished unread.** `os/ci/control/tree_scan.py`, `os/ci/control/actions.py`:
   - A file or folder under `/run/`, `/tmp/` or `/var/tmp/` that is gone when read and still gone when looked up
     again is named in `vanished`, **and is now an error** ("gone before it was read, so its content is unsearched"):
     check 8 asserts no error, so it fails. A vanished folder is the same (its whole content unread). A replaced
     file (gone, then back) is still read again.
   - **The exemption table `MAY_VANISH` (`tree_scan.py:29`) is empty:** X1's two control runs had `vanished: []`. A
     path goes there only with the reason its content can't hold the password, in a comment there and here.
   - **FUSE (the reviewer's note):** root now walks every FUSE mount itself (no prune). Only a mount where root was
     refused, a `PermissionError` at or under its mount point, is walked again as its owner (`search_for()`,
     `actions.py:1515`); root's refusals there give way to that walk, and if the owner's walk fails, they and the
     failure are errors. A mount root can read (`allow_other`) stays root's, with no owner walk. A refusal outside a
     FUSE mount stays an error. `passwords.json` now lists every FUSE mount (`fuse_mounts`: mount, type, owner,
     `root_refused`), and each owner walk carries `root_refused`.
   - Tests (`os/tests/test_control_vm.py`, `PasswordScanTest`):
     - `:639` (the existing runtime-disappearance test, changed: it permitted the pass): a runtime file that vanishes
       is an error and named, and `search_for()` passes the error to check 8; outside the runtime folders it is the
       plain ENOENT error as before; a vanished folder is an error and named; a path in `MAY_VANISH` is named without
       an error; `MAY_VANISH` is empty; a replaced file is read again.
     - `:718` a FUSE mount root can read is root's alone (no owner walk; `root_refused: 0`).
     - `:730` a FUSE mount that refuses root (mode 0 for this user) is walked as its owner, its hit found,
       `root_refused: 1`; the owner's walk failing leaves root's refusal and the failure as errors.
   - **Baseline:** with `48570285`'s `tree_scan.py` and `actions.py`, `:639` fails ("Lists differ: [] != ['…/clean.txt:
     gone before it was read…']": the old scan passed it), `:718` fails ("no owner walk": the old code pruned the
     mount from root's walk and always walked it as the owner), and `:730` fails only on the new `root_refused` field.
3. **#3, tar recognition.** `os/ci/control/evidence_scan.py`:
   - A tar is now any data whose first block tarfile reads as a header (`tar_header()`, `:67`: `TarInfo.frombuf`, the
     check `tarfile.open` makes of the first block, the checksum and numbers where numbers go), **or** that carries
     POSIX's `ustar\0` at byte 257 whatever its two version bytes, or GNU's `ustar  \0` (`TAR_MAGICS`, `:44`;
     `kind()`, `:76`). Both magics hold a NUL, so no text line has one.
   - So a V7 tar (no magic) and a ustar header with version `01` are read and searched; a recognisable but damaged
     one (either magic, bad checksum) is `Unreadable`. X1's depth limit and its trailing-blocks check (a later
     header tarfile can't read) are unchanged.
   - One more silent path of the same kind: a member of a type tarfile doesn't know (say `Z`) was skipped by
     `isfile()`, though `extractfile()` hands it out as a regular file (as GNU tar extracts it). It is searched now
     (`:92`).
   - Test (`EvidenceScanTest`, `test_every_tar_tarfile_reads_is_searched_whatever_its_magic`, `:870`): a V7 tar, a
     version-`01` tar (checksum recomputed) and an unknown-type member, each holding `secret.gz` with the synthetic
     password gzipped, each read by tarfile, give the hit `…!secret.gz!gunzip`; version `01` and GNU, each with a bad
     checksum, are unreadable. `:914` also keeps a text log with `ustar  00` at byte 257 ordinary, beside X1's `ustar
     is a tar format` log and the PNG.
   - **Baseline:** with `48570285`'s `evidence_scan.py` the test fails (no hits: "Lists differ: [] != ['control/
     unknown-type.tar!secret.gz!gunzip', …]"); per case, the old scanner gives 0 members and no hit for all three
     archives, the new one 2 members and the hit.
   - **The real evidence still scans:** run 43927257316's artifact (194 files) and X1's run 44076179152's (195 files),
     with the old and the new scanner: **417 and 429 archive members both times, nothing unreadable, no hit** (a
     random stand-in password), 13 gzip streams at the top each; equal to X1's own counts.
   - **Known limit (not fixable by recognition):** a V7 tar whose first header is damaged has neither a magic nor a
     valid checksum, so nothing tells it from other data; it is searched as plain bytes. A ustar or GNU tar damaged
     the same way stays unreadable.

### The merge (`dcbb70dd`, `main` at `04aef030`)

The lead's addition to this round, so the runs cover the final head. `main` moved from `91487807` (the last merge) to
`04aef030`: packages 48 (Esc menu and first start), 50 (console keymap) and 51 (first-start window), and work under
`control/` and `mod/`. A normal merge commit, no rebase. Two conflicts:

- `os/ci/check-build.sh`: **18c's `control|build` structure kept**; package 50's new line `grep -q CONSOLE_KEYMAP_PASSED
  evidence/vm-pass-1/console-keymap-result.json` goes in the `build` branch, after the polkit grep and before `echo
  CHECK_BUILD_VM_PASSED`. `control` mode makes its disk without a VM pass of `vm.py`, as before.
- `os/manifest/ci/16/pending-rebind.json`: **not hand-merged** (`linux-aresos`'s correction). The branch's side taken,
  then `reviews/27-first-update-release/rebind.py pending` run three times: with `main`'s two new notes, word for word
  ("22d and 22c on the laptop (2026-11-17)", "50: boot-only console keymap …"), and with this merge's note. So both
  sides' notes stay, and the rows are the tool's: `main`'s rows (its new bytes for `os/ci/vm.py` and
  `os/tests/test_owner_path.py`) plus 18c's `.github/workflows/os-image.yml`. "10 bound files differ from the active
  bindings, 0 removed".

What the merge changed under `os/` (all `main`'s, auto-merged): `os/build.sh` (+1: `systemctl enable
aresos-console-keymap.service`), `os/config/usr/lib/systemd/system/aresos-console-keymap.service` (new),
`os/config/usr/libexec/aresos-desktop`, `os/ci/image-checks.sh` (+38: package 50's unit checks, at the top; 18c's
Control section untouched), `os/ci/overlay/Containerfile` (+1: copies `console_keymap.py`), `os/ci/overlay/checks.py`
(+3: imports `console_keymap`, the `console-keymap` action), `os/ci/overlay/console_keymap.py` (new), `os/ci/vm.py`
(+1: `request('console-keymap')`), `os/tests/test_aresos_desktop.py`, `os/tests/test_console_keymap.py` (new),
`os/tests/test_owner_path.py`; outside `os/`: `.github/workflows/control-owner-oracle.yml`, `control/` (Chrome
qualification, the owner-state oracle, `control/tests/test_integration.py`) and `mod/`. Checked together:
- `os/ci/overlay/Containerfile` still copies `console_keymap.py` beside `checks.py`, and `os/ci/vm.py`'s
  `console-keymap` step survives; the Control layer is `FROM localhost/aresos:vm`, so its `checks.py` finds the module.
- **One 18c test needed the module too** (`fda41017`): `LayerHookTest` (`os/tests/test_control_vm.py:40`) builds a
  stand-in layer from `checks.py` and `channel.py` alone, so after the merge its three tests failed with
  "ModuleNotFoundError: No module named 'console_keymap'". It now copies `overlay/console_keymap.py` too, as the
  overlay's Containerfile does. Test-only, in 18c's own file; nothing of `main`'s changed.

### Checks run (laptop)

- Before the merge, one module at a time: `test_control_image` 15 OK, `test_control_vm` 48 OK (46 − 2 replaced + 4),
  `test_checkout_sources` 8 OK.
- After the merge (`fda41017`): `test_control_image` 15 OK (4.6 s), `test_control_vm` 48 OK (0.7 s; 3 errors on
  `dcbb70dd` before `fda41017`, above), `test_checkout_sources` 8 OK, `test_aresos_desktop` 189 OK (skipped=1; 173 s),
  `test_owner_path` 48 OK (1.2 s), `test_owner_equality` 11 OK (83.8 s), one at a time, nothing left running. Never
  `test_owner_update`; no `rpm-ostree`, `bootc` or `ostree` command, nothing mounted, no sudo.
- `bash -n os/ci/check-build.sh os/ci/check-image.sh`; `git diff --check` clean over this round's commits and over
  `os/`, `control/` and `.github/` against `main` (the X1 review files' Markdown line breaks are Codex's, unchanged).
- The baselines above, against `48570285`'s files.

### Runs on the final head `fda41017`

| Run | Mode | Result |
|---|---|---|
| 44097419307 | regressions only (`checks_only`) | **success**: "Ran 1758 tests in 1764.828s", "OK (skipped=4)" (X1's 1734, this round's net 2, and `main`'s new tests; the 4 skips are main's 23b cover tests, as before); the job 14:00:01 to 14:30:08 UTC = 30 min 7 s, the ways-back model job green in 17 s |
| 44103926487 attempt 1 | `check_build=control` | failure, **not this branch**: in the image's packages stage, `curl: (56) Recv failure: Connection reset by peer` fetching `asm-util-9.10.1.jar` from `maven.fabricmc.net` (14:39:48 UTC), before any Control step; rerun once |
| 44103926487 attempt 2 | `check_build=control` | **success** (below) |
| 44117467369 | `check_build=control` | **success** (below; a new dispatch, so both runs keep their evidence artifact) |
| 44129709609 | `check_build=build` | failure, **not this branch, and not passing on a rerun**: in the image's packages stage, `AssertionError: net.minecraft.json differs from its pin` (17:00:02 UTC; log line 1551), before any Control step and before `check-image.sh`. Prism's metadata service regenerated `https://meta.prismlauncher.org/v1/net.minecraft/26.2.json` at 16:04 UTC (its repo's commit `e5a979dd`, "Update 2026-11-17"): only Mojang's asset index entry changed (`sha1`, `totalSize`, `url`), same size 24493, SHA-256 now `48b0d18b…1338f`; the pin in `os/minecraft/desktop.lock.json`, `9c23199a…2b46`, is exactly upstream's 2026-11-10 version. Not rerun: the URL now serves the new bytes, so every image build fails there, `main`'s too, until the lock is re-pinned (below) |
| PR #58's workflows on `fda41017` | Repo privacy, Control base, Control boundary, Control Mail, Control Chrome, Control Chrome qualification | all **success** |

**Log lines** (`gh run view <id> --log`, line numbers from 1; 44103926487's is attempt 2, the run's latest; both runs'
logs have 4375 lines and the same numbers):

| Line | 44103926487 attempt 2 and 44117467369 |
|---|---|
| 3584 | `CONTROL_VENDOR_FROM_WHEELS 2024 vendored paths: 1021 files from 28 wheels and pip, 712 bytecode, 291 folders; 1.7 s` (both) |
| 3585 | `CHECK_BUILD_PASSED` |
| 4306 | `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1, "owner_answers": 0, "prompt_shown": false, "send_arrivals": 1}}` (both) |
| 4307 | `CONTROL_INTERACTIVE_ASK_PASS` |
| 4309 | `CONTROL_PASSWORDS_PRIVATE_PASS` |
| 4319 | `CHECK_BUILD_CONTROL_PASSED` |

**Run 44103926487 attempt 2**:
- Times: job 14:42:45 to 15:42:11 UTC = 59 min 26 s (against 131); tools 2 min 26 s; build step 14:46:48 to 15:32:59 =
  46 min 11 s; **Control VM step 15:32:59 to 15:42:04 = 9 min 5 s** against 16.
- PASS lines, every one in X1's order: `CLAUDE_CODE_PINNED 2.1.319 sha512-FO4Sd23B…oOQ== dabafec8…8eed` (1329),
  **`CONTROL_CHROME_BUILD 239de9b9…44b0fb`** (1709; `main`'s Chrome changes, was `8f7036e8…d385c`), `CONTROL_INSTALLED
  74 files, 28 wheels, 2024 vendored paths from fda41017…` (1710), `CONTROL_CHROME_STARTUP_FILES build 239de9b9…44b0fb,
  8 qualification entries` (1711), `CONTROL_GENERATED_MATCH 15 files` (1712), `CONTROL_FILES_RECORDED 74 files, 2024
  vendored paths, 28 wheels from fda41017…` (3473), `CONTROL_WHEELS_FETCHED 28 wheels, 9732253 bytes from PyPI, 1.5 s`
  (3583), `CONTROL_VENDOR_FROM_WHEELS …` (3584), `CHECK_BUILD_PASSED` (3585), `CHECK_BUILD_CONTROL_DISK_READY` (4276),
  `CONTROL_IMAGE_FILES_PASS`, `CONTROL_ETC_CLAUDE_CODE_PASS`, `CONTROL_RELEASE_CHECKS_PASS`,
  `CONTROL_IDLE_FOOTPRINT_RECORDED {…}`, `CONTROL_FIXTURES_REACHABLE`, `CONTROL_ENTRY_POINTS_PASS`,
  `CONTROL_PRECONDITION_PASS`, `CONTROL_USER_MCP_INSTALL_PASS`, `CONTROL_SERVICE_SANDBOX_PASS`,
  `CONTROL_ORDINARY_SESSION_PASS {…}` (4302), `CONTROL_MAIL_FLOWS_PASS`, `CONTROL_PERMISSION_REQUEST_RECORDED …` (4306),
  `CONTROL_INTERACTIVE_ASK_PASS` (4307), `CONTROL_PASSWORDS_PRIVATE_PASS` (4309), `CONTROL_SELINUX_AFTER_CHECKS_PASS`,
  `CONTROL_STORAGE_TESTS_PASS {…}`, `CONTROL_SERVICE_RESTART_PASS`, `CONTROL_VM_POWEROFF_CLEAN` (4317),
  `CHECK_BUILD_CONTROL_PASSED` (4319).
- The fixture stop step was green.
- Step times (s): boot to channel 45.9, files 3.4, idle 59.5, entry points 4.2, precondition 1.9, user MCP 10.8,
  **check 6 229.2**, check 7 36.2, check 9 111.1, check 8 0.4, storage tests 36.9, restart 1.0; the pass 544.1.

**Run 44117467369**:
- Times: job 15:42:52 to 16:46:45 UTC = 63 min 53 s; tools 3 min 43 s; build step 15:49:14 to 16:37:22 = 48 min 8 s;
  **Control VM step 16:37:23 to 16:46:39 = 9 min 16 s** against 16.
- PASS lines: the same lines in the same order on the same log lines, with `CONTROL_WHEELS_FETCHED 28 wheels, 9732253
  bytes from PyPI, 1.6 s` and the same `CONTROL_PERMISSION_REQUEST_RECORDED` (`prompt_shown: false` again).
- The fixture stop step was green.
- Step times (s): boot to channel 49.3, files 5.2, idle 59.1, entry points 4.5, precondition 2.2, user MCP 10.8,
  **check 6 231.3**, check 7 36.9, check 9 112.7, check 8 0.4, storage tests 38.9, restart 0.9; the pass 556.0.

### This round's evidence (run 44103926487 attempt 2 / run 44117467369)

- **Check 8 in the guest** (`passwords.json`): **1866 / 1874 files searched by root, `errors: []`, `vanished: []`**
  (so nothing needed `MAY_VANISH`), the journal export exit 0 with nothing on stderr; per folder `/var/home/ares` 931 /
  931, `/run` 483 / 483, `/var/tmp` 415 / 423, `/var/lib/aresos-tools` 14, `/var/log` 12, `/root` 5, `/tmp` 3,
  `/var/lib/aresos-operation-evidence` 3; the one file holding the password is the stored one.
- **The FUSE mount, root first:** `fuse_mounts: [{mount: /run/user/1001/doc, type: fuse.portal, owner: ares,
  root_refused: 1}]` both times: **root's walk was refused at the document portal's mount point**, so it was walked
  as `ares`: 0 files, no error. X1 assumed the refusal; these runs show it (one refusal, at the mount point itself).
- **The vendor check**: `CONTROL_VENDOR_FROM_WHEELS 2024 vendored paths: 1021 files from 28 wheels and pip, 712
  bytecode, 291 folders` both times: the same counts as X1. The derived tree now includes `/usr/lib/aresos-control`
  itself; the record had nothing else beside `vendor/`.
- **The evidence scan** (`runner.sh stop`, `fixtures/password-scan.json`, the new scanner): **192 files, 428 / 436
  archive members**, `"unreadable": []`, `"holding": []`, GreenMail redacted once, nothing removed. Check 8's own scan
  on the runner (`passwords-runner.json`): 56 evidence files, 428 / 436 members, nothing unreadable. On the laptop,
  the downloaded artifacts (195 files each) with the new scanner: 428 / 436 members, nothing unreadable, 13 gzip
  streams at the top; with `48570285`'s scanner the same counts.
- **Check 9's transcripts:** one per case in both runs (`normal-yes`, `skip-no`, `skip-user-allow-send`,
  `normal-permission-user`).
- **Unchanged from X1**, both runs: `desktop_with_service_failed` (the service `failed`, `NRestarts=5`,
  `Result=exit-code`; logged out in 11.3 s, the desktop up again in 13.7 s, `SETUP`, not latched, greetd session `1`
  then `3`, `marks_after_logout: false`); `held_work` 4 model requests, 1 extra, 1 continuation, both reminders `true`;
  **`held_elsewhere` 2 model requests, 0 extra, 0 Stop continuations, `requests_carrying_it: []`**; check 6's CLI
  while stopped `service_unavailable` after 3.25 s; idle 1 context switch in 60 s, 1.4 ms / 0.9 ms of CPU,
  `memory.current` 32,755,712 B / 33,042,432 B, RSS 37,064 / 37,192 KiB, PSS 25,286 / 25,262 KiB, 1 process, 1 thread.

### Done

The three should-fixes of `RECHECK-X1.md`, each with its regression test and its baseline failure on `48570285`;
`main` merged at `04aef030` (two conflicts, resolved as the lead set out), and the one 18c test the merge needed.
Regressions only green (1758 tests), `check_build=control` green twice (44103926487 attempt 2, 44117467369),
PR #58's six workflows green. **`check_build=build` is not green:** run 44129709609 stopped at the image's pinned
Minecraft metadata, which Prism's service changed upstream at 16:04 UTC (Runs, above); the two control runs built
their images before that. Only this file changed after `fda41017`.

### Left, in order

This replaces X1's list below (its item 1 is `RECHECK-X1.md`, whose findings this round closes).

1. **The pinned Minecraft metadata** (the lead's call; `linux-aresos`'s or `main`'s file, outside this round's
   scope): re-pin `net.minecraft.json` in `os/minecraft/desktop.lock.json` to upstream's new bytes (or pin a URL that
   can't change), on `main` and then merged here; then `check_build=build` once on the final head, recording its
   `CONSOLE_KEYMAP_PASSED: boot setting and repair after a forced busy-VT skip` line (printed by `vm.py` before
   `CHECK_BUILD_VM_PASSED`) and its log line numbers. A new head also needs the control runs again.
2. A fresh recheck of this round's fixes and what they touched (`docs/REVIEW.md`, "Tools for Claude", step 3).
3. `linux-aresos` reads this round's `os/` diff (agreed change 16), the merge's resolution included: the section at the
   end is up to date with this round.
4. The lead assembles `reviews/18c-image-test/REPORT.md` as listed in the merge section below, with X1's known limits
   word for word, this round's known limit (a V7 tar with a damaged first header), and this round's runs and log lines.
5. Merge (the lead's).
6. The last step deletes this file.

### Observations for the lead

- **Check 8 is now strict about vanishing runtime files.** Both runs had `vanished: []`, as X1's. If a later run
  fails check 8 on "gone before it was read", the path is named; it may go in `MAY_VANISH` only with the reason its
  content can't hold the password.
- **The merge needed one change beyond the two conflicts**, in 18c's own test (`fda41017`, `LayerHookTest`): `main`'s
  `checks.py` imports `console_keymap`. Nothing of `main`'s code changed.
- **`CONTROL_CHROME_BUILD` moved** to `239de9b9…44b0fb` with `main`'s Chrome changes (8 qualification entries, as
  before): for `control/chrome/builds.json`, if the lead keeps that record.
- **Every image build fails today at `net.minecraft.json`** (44129709609, above), `main`'s included: Prism's
  metadata service regenerates `v1/net.minecraft/<version>.json` weekly (its repo shows updates on 2026-11-03, -10
  and -17), and an asset index change upstream changes the file's bytes. The lock pins a URL whose content moves, so
  this is likely to recur each week unless the pin points at fixed content.
- One infrastructure failure, rerun once: `maven.fabricmc.net` reset a connection in the packages stage (44103926487
  attempt 1). X1's was Maven Central's 429.

## Fix round X1 (Codex astra's review) (2026-11-17, Claude agent on Opus 5.5)

From `REVIEW-X1.md` (the package review: CHANGES-NEEDED, four should-fixes) and `SECURITY-REVIEW-X1.md` (the security
review: SAFE), both Codex `gpt-6-astra` reviews of `6234b916`, on head `896f45e6`. Opus, because the list was decided:
four findings, each with its fix and its regression named by the lead. Commits: `bf5cba71` (the lead's request: the two
X1 reviews linked absolute paths under the laptop's home folder; only the six link targets changed, now
`../../<path>#L<line>`), `9674dbcf` (#1), `6e1964ff` (#3), `4cb8e152` (#2), `48570285` (#4), and this file's commit
(`[skip ci]`). **Final head: `48570285`.** Everything changed is CI-only (`os/ci/check-image.sh`, `os/ci/control/`,
`os/tests/`) or this folder; nothing in the image, `control/` or the workflow. `rebind.py pending` recorded no bound
file (only its note), so the note was reverted.

### What changed, per finding, and the test that pins it

Each regression test fails on `896f45e6` and passes now (run against the old files on the laptop: the vendor test
errors without `vendor_check.py`; the three new scan tests fail with the old `evidence_scan.py`; with the old
`actions.py` the six check 8 tests and the missing-folder test error, and the check 9 test fails).

1. **#1, the installed vendor bytes against the locked wheels.** New `os/ci/control/vendor_check.py`, called by
   `os/ci/check-image.sh:127-142` after the record is held to the checkout and its lock (so the release job's
   `check-build.sh build` runs it too):
   - **`fetch`**, on the runner: each wheel the record names, from PyPI's JSON for its name and version, by its file
     name; the recorded SHA-256 must be the index's and the downloaded bytes'. The record's wheels were held to the
     checkout's `requirements.lock` just before, so the chain is lock → record → bytes.
   - **`check`**, in a throwaway container of the built image (`--network=none`; it refuses to run outside a
     container): the installed tree must equal the record; then the tree is replaced by the one derived from the
     wheels, compiled with the build's own command at the build's path, and the record must equal it: paths,
     contents and modes. Prints `CONTROL_VENDOR_FROM_WHEELS <paths> vendored paths: <files> files from <n> wheels and
     pip, <bytecode> bytecode, <folders> folders; <s> s`.
   - **The rules for what pip writes** (pip 26.0.1, the image's `python3-pip`; the module's docstring has them):
     `INSTALLER` is `pip\n`; `REQUESTED` empty for every wheel (all are in the lock); `direct_url.json` never (index
     installs), so one present fails; `bin/<name>` per `console_scripts` entry point, pip 26's template behind
     `#!/usr/bin/python3`, mode 0755 (the extras of `mcp = mcp.cli:app [cli]` are dropped as pip does); `RECORD` is the
     wheel's own rows, a hashed row per generated file, a hashless row for a file the wheel's RECORD omits, sorted, CSV
     with CRLF, compared byte for byte. A member is executable when its zip mode is a regular file with an execute bit
     (pip's rule); modes then as `build.sh` sets them (0755 / 0644). Anything without a rule stops the check: a `.data`
     folder, `gui_scripts`, pip's own entry points, a link, a member leaving its folder, a wheel holding a file pip
     generates, two wheels writing one path.
   - **Bytecode** is generated at build time (`pip --no-compile`, then `compileall --invalidation-mode checked-hash`
     in place) and bound by recompiling the derived sources with the image's own Python and that exact command
     (`COMPILE`, pinned to `build.sh`'s line by a test) at `/usr/lib/aresos-control/vendor`, and comparing bytes. A
     `.pyc` whose checked-hash header names the right source but whose code differs fails.
   - Checked on the laptop against run 43927257316's real record (the laptop has the image's `python3-3.14.8-1.fc44`
     and `python3-pip-26.0.1-3.fc44`): the derivation equals all 1203 recorded non-bytecode paths; recompiling gives
     all 712 recorded `.pyc` byte for byte, with a random hash seed and with seeds 0 and 12345; a laptop pip install of
     the 28 wheels plus the build's compile passes `check()` (2024 paths) in 1.6 s; `fetch` took 3.7 s for 9,732,253
     bytes.
   - Tests (`os/tests/test_control_image.py`, `VendorTreeTest`, `:373`): `:402` the regression: a changed source, a
     `.pyc` with other code behind its valid header, an added file, `direct_url.json`, a mode, the generated script,
     `INSTALLER`, a dropped `RECORD` row and a removed file, each made in the tree and recorded with the wheel list
     still valid, fail; an image differing from its record and a wheel with another SHA-256 fail. `:462` wheels without
     a rule stop it; `:486` the rules equal what this Python's pip writes (no console script there: the runner's pip
     may be older than the image's, whose template the image build compares); `:512` the compile step is `build.sh`'s
     and the order in `check-image.sh`; `:532` the fetch (another hash on the index, another host, no such file, other
     bytes, a bad file name); `:458` it refuses outside a container.
2. **#2, the password scan.** New `os/ci/control/tree_scan.py` (the test layer copies it beside `release_checks.py`);
   `actions.py:1515` `search_for()`, used by `passwords()` (`:1552`):
   - the walk passes `onerror`: a folder that can't be listed, a file that can't be read and a scanned root that
     isn't there are errors; the journal export (`JOURNAL`, `:1505`) must exit 0 (its stderr tail is recorded);
     check 8 asserts no error beside no hit.
   - **The one retry** (`tree_scan.py:21`, `VANISHING`: `/run/`, `/tmp/`, `/var/tmp/`): a file or folder there that
     is gone when read (ENOENT) is looked up again; back again (replaced), it is read once more; still gone, it is
     skipped and named in `vanished`, which the summary and `passwords.json` carry and the run prints. ENOENT anywhere
     else, or twice, is an error.
   - **FUSE mounts** under the folders are walked as their owner: FUSE refuses root, and his session mounts the
     document portal at `/run/user/1001/doc` (the laptop's own AresOS session has it, `fuse.portal`, `user_id=1001`).
     Root's walk leaves the mount out and the same module walks it under `runuser`, the needles on stdin, never on a
     command line; `owner_walks` records each. Before this round root's `os.walk` dropped such a folder silently.
   - Tests (`os/tests/test_control_vm.py`, `PasswordScanTest`, `:569`): `:612` one unreadable file fails; `:630` the
     journal export exiting 1 fails; `:620` a folder that can't be listed and a missing root fail; `:637` a runtime
     file may vanish and is named, outside the runtime folders it fails, a replaced one is read again; `:673` a FUSE
     mount is walked as its owner; `:601` a clean search, and `passwords()` asserts on the errors.
3. **#3, the archive scan.** `os/ci/control/evidence_scan.py`:
   - below `DEPTH` (3) a gzip stream or tar archive is `Unreadable` (`contents()`, `:88`), never searched raw only;
   - a tar is recognised by tarfile's POSIX or GNU magic at byte 257 (`:37`), which a damaged header keeps, and must
     parse to its end: tarfile ends an archive quietly at a later header it can't read, so the bytes after the last
     member must be zero blocks (`untar()`, `:69`); a bad checksum or truncation is `Unreadable`;
   - data in a format the scan doesn't unpack (xz, bzip2, zstd, lz4, zip, 7z, by their magic at the start: `:39`) is
     `Unreadable`; a truncated gzip was already.
   - Unreadable evidence counts as holding the password, as fix round 1 made it: `runner.sh stop` removes it and fails
     the step, `control_vm.py` fails check 8.
   - Tests (`EvidenceScanTest`): `:756` four nested gzip streams around the password are unreadable, three are read and
     the hit found, a `.tar.gz` inside a `.tar.gz` is unreadable; `:775` a tar holding a gzipped password with its
     first or its second header's checksum broken is unreadable, the same tar undamaged gives the hit; `:801` xz, zip
     and a truncated gzip are unreadable, a log naming the formats (with `ustar ` at byte 257) and a PNG are not.
   - **Today's real evidence still scans:** run 43927257316 attempt 2's artifact (194 files: the 191 the runner scanned
     and 3 written after) with the new scanner: 194 files, **417 archive members** (as the old scanner, and the run's
     own `password-scan.json`), nothing unreadable; 13 gzip streams and 13 tars, all the checks' `.tar.gz`.
4. **#4, check 9's transcripts.** `actions.py`:
   - `packed()` (`:743`) treats every folder it is given as required evidence: a missing one is named in the errors
     (checks 6, 7 and 9; all their folders existed in every green run);
   - check 9: a transcript copy that raises is added to the errors (`:1446`), and a case whose session ran must have
     copied at least one transcript (`:1451`).
   - Tests (`EvidencePackingTest`): `:218` a missing transcript folder fails and is named; `:229` check 9 with stand-ins
     for the guest passes with transcripts and fails when a case copies none or the copy raises. The test that kept a
     missing folder out without an error (`test_a_tar_that_does_not_fit_...`) now leaves that case to `:218`.

### Known limits for the report (not fixed here; word for word as the reviews state them)

From `SECURITY-REVIEW-X1.md`:

1. **Known limit — internal hook errors can still deliberately block one Stop.**
   Where: [hooks.py:146](../../control/aresos_control/hooks.py#L146).

   Concrete case: a session previously used Control; its Stop input contains a lone Unicode surrogate in an otherwise
   unused field and `stop_hook_active:false`. Strict parsing fails, and the hook emits a JSON diagnostic block. The
   continuation with `stop_hook_active:true` is quiet. An unused session is quiet before parsing.

   I reproduced this in memory. It is bounded diagnostic feedback, inherited from #91, rather than the former
   exit-code loop. No merge fix required, but the behavior must not be described as “every internal failure is
   silent.”

2. **Known limit — the fixed service ID still depends on deployment checks.**
   Where: [aresos-tools.sysusers:2](../../control/packaging/aresos-tools.sysusers#L2),
   [release_checks.py:44](../../os/ci/control/release_checks.py#L44).

   If a previous deployment assigns UID/GID 250 elsewhere, sysusers can choose another number; persistent `/var` state
   then no longer has the intended identity relationship. The fresh-image checks cannot establish the state of every
   previous deployment.

   The supplied rehearsal checks detect the wrong IDs and state ownership. This satisfies the agreed scope of this PR;
   the next release must run them against the actual update path. This review does not certify that migration.

3. **K1 remains a known test gap that I had not separately recorded:** auto mode is not exercised. Explicit ask rules
   remain documented exceptions to automatic approval, but that is not equivalent to testing the pinned binary. Add
   the proposed auto-mode cases.

So the report must never say "every internal failure is silent": hook errors can still deliberately block one Stop
with a JSON diagnostic. UID/GID 250 rests on the release rehearsal's deployment checks.

### Checks run (laptop)

- `python3 -m unittest discover -s os/tests -p <module>`, one module at a time: `test_control_image` 15 OK (9 + 6
  new), `test_control_vm` 46 OK (35 + 11 new), `test_checkout_sources` 8 OK.
- `bash -n os/ci/check-image.sh`; the static test compiles every `os/ci/control/*.py`, the two new modules included.
- Run against the old files: the regressions above fail on `896f45e6`.
- After the lead lifted `linux-aresos`'s install hold (owner tools v4 installed): `test_owner_path` 48 OK (1.2 s) and
  `test_owner_equality` 11 OK (89.6 s), one at a time, nothing left running. Never `test_owner_update`; no
  `rpm-ostree`, `bootc` or `ostree` command, nothing mounted, no sudo. The hosted `checks_only` run below ran the
  whole `os/tests` suite.
- Main's Repo privacy pattern: nothing new holds a home path (the PR's own Repo privacy run below).

### Runs on the final head `48570285`

| Run | Mode | Result |
|---|---|---|
| 44065772401 | regressions only (`checks_only`) | **success**: "Ran 1734 tests in 1274.232s", "OK (skipped=4)" (1717 + this round's 17; the 4 skips are main's 23b cover tests, as before); `test_the_rules_are_what_pip_writes` ran (the runner's pip) and passed; the job 10:32:55 to 10:55:19 UTC = 22 min 24 s, the ways-back model job green in 25 s |
| 44069456146 attempt 1 | `check_build=control` | failure, **not this branch**: the mod stage's Gradle got "Received status code 429 from server: Too Many Requests" from Maven Central (`repo.maven.apache.org`, 11:09 UTC), before any Control step; rerun once |
| 44069456146 attempt 2 | `check_build=control` | **success** (below) |
| 44076179152 | `check_build=control` | **success** (below; a new dispatch rather than a rerun, so both runs keep their evidence artifact) |
| 44085918977 | `check_build=build` | **success**: job 12:44:12 to 13:26:01 UTC = 41 min 49 s, tools 2 min 7 s, build step 12:47:46 to 13:25:57 = 38 min 11 s, the Control VM step skipped as it should be; `CONTROL_CHROME_BUILD 8f7036e8…d385c`, `CONTROL_INSTALLED 74 files, 28 wheels, 2024 vendored paths from 48570285…`, `CONTROL_CHROME_STARTUP_FILES build 8f7036e8…d385c, 8 qualification entries`, `CONTROL_GENERATED_MATCH 15 files`, `CONTROL_FILES_RECORDED 74 files, 2024 vendored paths, 28 wheels from 48570285…`, `CONTROL_WHEELS_FETCHED 28 wheels, 9732253 bytes from PyPI, 2.7 s`, `CONTROL_VENDOR_FROM_WHEELS 2024 vendored paths: 1021 files from 28 wheels and pip, 712 bytecode, 291 folders; 1.7 s`, `CHECK_BUILD_PASSED`, `CHECK_BUILD_VM_PASSED` |
| PR #58's workflows on `48570285` | Repo privacy, Control base, Control boundary, Control Mail, Control Chrome, Control Chrome qualification | all **success** |

**Run 44069456146 attempt 2**:
- Times: job 11:10:42 to 11:38:53 UTC = 28 min 11 s (a fast runner: the packages stage took 48 s); tools 7 min 21 s;
  build step 11:19:53 to 11:30:40 = 10 min 47 s; **Control VM step 11:30:40 to 11:38:50 = 8 min 10 s** against 16.
- PASS lines, every one in the earlier order, with the two new ones after `CONTROL_FILES_RECORDED`:
  `CLAUDE_CODE_PINNED 2.1.319 sha512-FO4Sd23B…oOQ== dabafec8…8eed`, `CONTROL_CHROME_BUILD 8f7036e8…d385c`,
  `CONTROL_INSTALLED 74 files, 28 wheels, 2024 vendored paths from 48570285…`, `CONTROL_CHROME_STARTUP_FILES build
  8f7036e8…d385c, 8 qualification entries`, `CONTROL_GENERATED_MATCH 15 files`, `CONTROL_FILES_RECORDED`,
  **`CONTROL_WHEELS_FETCHED 28 wheels, 9732253 bytes from PyPI, 0.6 s`**, **`CONTROL_VENDOR_FROM_WHEELS 2024 vendored
  paths: 1021 files from 28 wheels and pip, 712 bytecode, 291 folders; 1.4 s`**, `CHECK_BUILD_PASSED`,
  `CHECK_BUILD_CONTROL_DISK_READY`, `CONTROL_IMAGE_FILES_PASS`, `CONTROL_ETC_CLAUDE_CODE_PASS`,
  `CONTROL_RELEASE_CHECKS_PASS`, `CONTROL_IDLE_FOOTPRINT_RECORDED {…}`, `CONTROL_FIXTURES_REACHABLE`,
  `CONTROL_ENTRY_POINTS_PASS`, `CONTROL_PRECONDITION_PASS`, `CONTROL_USER_MCP_INSTALL_PASS`,
  `CONTROL_SERVICE_SANDBOX_PASS`, `CONTROL_ORDINARY_SESSION_PASS {…}`, `CONTROL_MAIL_FLOWS_PASS`,
  `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1, "owner_answers": 0,
  "prompt_shown": false, "send_arrivals": 1}}`, `CONTROL_INTERACTIVE_ASK_PASS`, `CONTROL_PASSWORDS_PRIVATE_PASS`,
  `CONTROL_SELINUX_AFTER_CHECKS_PASS`, `CONTROL_STORAGE_TESTS_PASS {…}`, `CONTROL_SERVICE_RESTART_PASS`,
  `CONTROL_VM_POWEROFF_CLEAN`, `CHECK_BUILD_CONTROL_PASSED`.
- The fixture stop step was green.
- Step times (s): boot to channel 25.9, files 2.0, idle 60.0, entry points 3.4, precondition 1.4, user MCP 5.1,
  **check 6 223.0**, check 7 32.4, check 9 104.8, check 8 0.5, storage tests 27.4, restart 0.7; the pass 489.4.

**Run 44076179152**:
- Times: job 11:40:53 to 12:43:39 UTC = 62 min 46 s; tools 3 min 47 s; build step 11:47:04 to 12:34:18 = 47 min 14 s;
  **Control VM step 12:34:18 to 12:43:34 = 9 min 16 s** against 16.
- PASS lines: the same lines in the same order, with `CONTROL_WHEELS_FETCHED 28 wheels, 9732253 bytes from PyPI, 2.7
  s`, `CONTROL_VENDOR_FROM_WHEELS 2024 vendored paths: 1021 files from 28 wheels and pip, 712 bytecode, 291 folders;
  1.6 s` and `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1, "owner_answers": 0,
  "prompt_shown": true, "send_arrivals": 1}}`, ending in `CONTROL_VM_POWEROFF_CLEAN`, `CHECK_BUILD_CONTROL_PASSED`.
- The fixture stop step was green.
- Step times (s): boot to channel 45.8, files 4.1, idle 60.1, entry points 4.1, precondition 2.0, user MCP 11.4,
  **check 6 230.6**, check 7 37.8, check 9 112.7, check 8 0.5, storage tests 42.1, restart 1.3; the pass 556.4.

### This round's evidence (run 44069456146 attempt 2 / run 44076179152)

- **The vendor check's added time** (from the line before it, "Control in the image is this checkout", to
  `CHECK_BUILD_PASSED`, in the job's own timestamps): **2.4 s / 4.8 s** (the fetch 0.6 s / 2.7 s, the container's
  check 1.4 s / 1.6 s, the rest `podman run` and `tar`), against the build step's 80 minutes. In the build run: 5.0 s (2.7 s, 1.7 s).
- **The evidence scan** (`runner.sh stop`, `fixtures/password-scan.json`, the new scanner): **192 files, 418 / 429
  archive members**, `"unreadable": []`, `"holding": []`, GreenMail redacted once, nothing removed. Check 8's own scan
  on the runner (`passwords-runner.json`): 56 evidence files, 418 / 429 members, nothing unreadable. The member count
  moves with the screens kept in each `.tar.gz` (464, 423, 454 and 417 in earlier runs).
- **Check 8 in the guest** (`passwords.json`): **1854 / 1867 files searched by root, `errors: []`, `vanished: []`**,
  the journal export exit 0 with nothing on stderr; per folder `/var/home/ares` 931 / 931, `/run` 481 / 483,
  `/var/tmp` 405 / 416, `/var/lib/aresos-tools` 14, `/var/log` 12, `/root` 5, `/tmp` 3,
  `/var/lib/aresos-operation-evidence` 3. **The document portal's FUSE mount `/run/user/1001/doc` (`fuse.portal`) is
  in the guest's session**, walked as `ares`: 0 files both times. FUSE refuses root there; before this round root's
  `os.walk` had no `onerror`, so that refusal dropped the folder without a word.
- **Check 9's transcripts:** one per case in both runs (`normal-yes`, `skip-no`, `skip-user-allow-send`,
  `normal-permission-user`), and the eight tars in `interactive/`.
- **Unchanged from `a1e7aad9`**, both runs: `desktop_with_service_failed` (the service `failed`, `NRestarts=5`,
  `Result=exit-code`; logged out in 11.2 s / 11.4 s, the desktop up again in 12.5 s / 13.8 s, `SETUP`, not latched,
  greetd session `1` then `3`, `marks_after_logout: false`); `held_work` 4 model requests, 1 extra, 1 continuation,
  both reminders `true`; **`held_elsewhere` 2 model requests, 0 extra, 0 Stop continuations, `requests_carrying_it:
  []`**; `network_listeners: 0` (`nrestarts 0`, `Enforcing`, `aresos-tools`); check 6's CLI while stopped
  `service_unavailable` after 3.18 s / 3.26 s, the managed hooks while stopped 0.128 / 0.126 s and 0.195 / 0.202 s,
  the first calls after each start 0.38 to 0.39 s / 0.46 to 0.51 s, his Stop hook 13 lines for 13 turns, nothing
  pending after; idle 1 context switch in 60 s (0.017 wake-ups a second), 0.6 ms / 1.8 ms of CPU, `memory.current`
  32,964,608 B / 33,087,488 B, RSS 37,004 / 37,204 KiB, PSS 25,299 / 25,415 KiB, 1 process, 1 thread; check 9's four
  outcomes as before, `normal-permission-user` `hook_calls 1, owner_answers 0, send_arrivals 1` (the prompt flashed
  only in the second run).

### Done

The four should-fixes of `REVIEW-X1.md`, each with its regression test; the X1 reviews' links repo-relative.
Regressions only green (1734 tests), `check_build=control` green twice (44069456146 attempt 2, 44076179152),
`check_build=build` green once (44085918977); PR #58's six workflows green. Only this file changed after `48570285`.

### Left, in order

This replaces the list in the merge section below: its item 1 was fixed in `6234b916` (PR #58's Control base and
Control Mail are green on `48570285`), its item 2 is `REVIEW-X1.md` and `SECURITY-REVIEW-X1.md`.

1. A fresh reviewer checks this round's fixes and what they touched (`docs/REVIEW.md`, "Tools for Claude", step 3).
2. `linux-aresos` reads the `os/` diff (agreed change 16): the section at the end is up to date with this round
   (`check-image.sh`'s vendor block, the two new modules under `os/ci/control/`, the test layer's one new file).
3. The lead assembles `reviews/18c-image-test/REPORT.md` as listed in the merge section below, now with the known limits
   above, word for word, and this round's runs.
4. The last step deletes this file.

### Observations for the lead

- Older review files in this folder still link absolute paths under the laptop's home folder (`BRIEF-REVIEW-1.md` to
  `-3.md`, `REVIEW-B1.md`, `REVIEW-B1-2.md`, `REVIEW-B1-3.md`, `SECURITY-REVIEW-B1.md`); only the two X1 files were in
  this round's scope, so they are unchanged. The Repo privacy check looks only for macOS and Windows home paths and
  passes them.
- A `.data` folder, `gui_scripts` or a new pip version in the base image will stop `vendor_check.py` until its rules
  are extended; that is deliberate (a new rule, then the wheel), and the message names the wheel and the file.

## The lead's merge of main (2026-11-16): head `a1e7aad9`

The lead merged `main`; a Claude agent on Opus 5.5 recorded the runs from their logs (docs only). Commits after part
2's `7480a027`: `69943d65` (the lead's: the control job's limit), `a1e7aad9` (the merge) and this file's commit
(`[skip ci]`). **Final head: `a1e7aad9`.**

### The merge (`a1e7aad9`, `main` at `91487807`)

`main` brought the Stop hook fix #91, #89 (20-ci-noise and 18e follow-ups), #83 (Chrome qualification) and #87 (the
qualification record from fixtures). One conflict, `control/boundary/test_interactive.py`: two unrelated new test
classes in the same place (this branch's `RealToolResultTest`, main's `HeldStops`), both kept. No `os/` or `.github/`
file changed (`main` changed none there since `5bb1500e`). `rebind.py pending` found no bound file changed, so
`pending-rebind.json` is unchanged.

What the merge changes in the image's Control files, from the build's own lines: Chrome's build hash `91cdfeb6…69ae5`
→ **`8f7036e8…d385c`**; Chrome's startup files now carry **8 qualification entries** (was 0: #83's
`qualification.json`); check 9's `managed_settings_sha256` `75c63d14…` → `96d7fdcd…` (#91's shell guard around the
managed Stop command). Still 74 files, 28 wheels, 2024 vendored paths, 15 generated files matching.

Before the merge, `69943d65` (the lead's): the job's `timeout-minutes` for `check_build=control` 127 → **131** with its
comment, so the job can't cut a slow pass before the step's own 16 minutes (`linux-aresos`, agreed change 15);
`rebind.py pending` recorded the workflow's new bytes. That closes part 2's first finding for the lead. Regressions-only
run 43886300738 on it: "Ran 1717 tests in 1442.063s", "OK (skipped=4)".

### Runs on the final head `a1e7aad9`

| Run | Mode | Result |
|---|---|---|
| 43927257316 attempt 1 | `check_build=control` | **success** (below) |
| 43927257316 attempt 2 | `check_build=control` | **success** (below) |
| 43927263485 | `check_build=build` | **success**: job 19:56:35 to 20:52:15 UTC = 55 min 40 s, tools 13 min 37 s, build step 20:12:09 to 20:52:09 = 40 min 0 s, the Control VM step skipped as it should be; `CONTROL_CHROME_BUILD 8f7036e8…d385c`, `CONTROL_INSTALLED 74 files, 28 wheels, 2024 vendored paths from a1e7aad9…`, `CONTROL_CHROME_STARTUP_FILES build 8f7036e8…d385c, 8 qualification entries`, `CONTROL_GENERATED_MATCH 15 files`, `CONTROL_FILES_RECORDED 74 files, 2024 vendored paths, 28 wheels from a1e7aad9…`, `CHECK_BUILD_PASSED`, `CHECK_BUILD_VM_PASSED` |
| 43965960756 | regressions only (`checks_only`) | **success**: "Ran 1717 tests in 1273.677s", "OK (skipped=4)"; the 4 skips are main's 23b cover tests again (a headless labwc, grim and GTK 4: not the hosted runner); the job 22:03:40 to 22:25:45 UTC = 22 min 5 s, and the ways-back model job green in 20 s |
| 43927268960 | regressions only | cancelled before any job ran (below) |
| 43927507924 | `check_build=build`, a duplicate | cancelled before any job ran (below) |
| PR #58's workflows | Control boundary, Chrome, Chrome qualification, Repo privacy | **success** |
| PR #58's workflows | Control base, Control Mail | **failure**: one test the merge left on the old config path (below) |

**Run 43927257316 attempt 1**:
- Times: job 18:40:31 to 19:51:45 UTC = 71 min 14 s (against 131); tools 12 min 37 s; build step 18:54:13 to 19:41:48
  = 47 min 35 s; **Control VM step 19:41:48 to 19:51:40 = 9 min 52 s** against 16.
- PASS lines, every one in `dada7a9b`'s order: `CLAUDE_CODE_PINNED 2.1.319 sha512-FO4Sd23B…oOQ== dabafec8…8eed`,
  `CONTROL_CHROME_BUILD 8f7036e8…d385c`, `CONTROL_INSTALLED 74 files, 28 wheels, 2024 vendored paths from a1e7aad9…`,
  `CONTROL_CHROME_STARTUP_FILES build 8f7036e8…d385c, 8 qualification entries`, `CONTROL_GENERATED_MATCH 15 files`,
  `CONTROL_FILES_RECORDED`, `CHECK_BUILD_PASSED`, `CHECK_BUILD_CONTROL_DISK_READY`, `CONTROL_IMAGE_FILES_PASS`,
  `CONTROL_ETC_CLAUDE_CODE_PASS`, `CONTROL_RELEASE_CHECKS_PASS`, `CONTROL_IDLE_FOOTPRINT_RECORDED {…}`,
  `CONTROL_FIXTURES_REACHABLE`, `CONTROL_ENTRY_POINTS_PASS`, `CONTROL_PRECONDITION_PASS`,
  `CONTROL_USER_MCP_INSTALL_PASS`, `CONTROL_SERVICE_SANDBOX_PASS`, `CONTROL_ORDINARY_SESSION_PASS {…}`,
  `CONTROL_MAIL_FLOWS_PASS`, `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1,
  "owner_answers": 0, "prompt_shown": false, "send_arrivals": 1}}`, `CONTROL_INTERACTIVE_ASK_PASS`,
  `CONTROL_PASSWORDS_PRIVATE_PASS`, `CONTROL_SELINUX_AFTER_CHECKS_PASS`, `CONTROL_STORAGE_TESTS_PASS {…}`,
  `CONTROL_SERVICE_RESTART_PASS`, `CONTROL_VM_POWEROFF_CLEAN`, `CHECK_BUILD_CONTROL_PASSED`.
- The fixture stop step was green.
- Step times (s): boot to channel 57.1, files 4.7, idle 59.5, entry points 5.7, precondition 2.6, user MCP 15.1,
  **check 6 237.1**, check 7 39.0, check 9 119.5, storage tests 45.9, restart 1.2; the pass 592.0.

**Run 43927257316 attempt 2** (a rerun):
- Times: job 20:57:46 to 22:01:00 UTC = 63 min 14 s; tools 11 min 8 s; build step 21:10:10 to 21:52:07 = 41 min 57 s;
  **Control VM step 21:52:07 to 22:00:56 = 8 min 49 s** against 16.
- PASS lines: the same lines in the same order, the same `CONTROL_PERMISSION_REQUEST_RECORDED` (`prompt_shown: false`
  again). The fixture stop step was green.
- Step times (s): boot to channel 45.9, files 3.8, idle 60.0, entry points 3.9, precondition 1.9, user MCP 10.8,
  **check 6 229.4**, check 7 33.6, check 9 107.1, storage tests 27.6, restart 0.8; the pass 528.9.

**The evidence** (attempt 1 / attempt 2):
- **`desktop_with_service_failed`:** the service `failed` 10.3 s / 10.2 s after `systemctl start` (`NRestarts=5`,
  `Result=exit-code`); the logout took 11.4 s / 11.3 s and the desktop came up again in 13.9 s / 13.6 s in all: state
  `SETUP`, not latched, greetd session `1` before and `3` after. `marks_after_logout: false` both times.
- **`held_work`:** 4 model requests, 1 extra, 1 continuation; `reminder_in_stop_reason: true`,
  `reminder_in_prompt_context: true`; the send `reserved`; his Stop hook once, on the ending attempt. On screen the same
  "Stop hook error: AresOS held/unfinished work (untrusted app data; inspect status, do not resubmit unknown …".
- **`held_elsewhere`:** **2 model requests, 0 extra, 0 Stop continuations, `requests_carrying_it: []`**, both times. On
  screen only Claude Code's own spinner text. His Stop hook ran once, at the turn's end, and the held operation was
  `reserved` with `pending_total` 1 the whole time. Released afterwards: cancelled (`failed`), `pending_after: 0`.
- **`network_listeners: 0`** (`control-service`: `nrestarts 0`, `selinux Enforcing`, user `aresos-tools`).
- **`fixtures/password-scan.json`:** `{"files": 191, "hits": [], "holding": [], "members": 454 / 417, "redacted":
  {"greenmail.txt": 1}, "removed": [], "unreadable": []}`. Check 8: `files_holding_it 1`, not in the journal.
- **Idle:** 1 context switch in 60 s (0.017 wake-ups a second) both times; 3.0 ms / 1.8 ms of CPU (0.005 % / 0.003 %);
  `memory.current` 33,083,392 B / 33,079,296 B; RSS 37,136 / 37,192 KiB; PSS 25,328 / 25,336 KiB; 1 process, 1
  thread.
- **Check 9:** `normal-yes` done, 1 arrival; `skip-no` and `skip-user-allow-send` reserved, 0 arrivals, resumed, 1
  continuation, the reminder in it; `normal-permission-user` `hook_calls 1, owner_answers 0, send_arrivals 1`, equal to
  the container's pin. The prompt didn't flash either time (`prompt_shown: false`; timing dependent, recorded, not
  pinned).

### Check 6 after #91

#91 wraps the managed Stop command in a shell guard (Python's output only on success, stderr dropped, always exit 0),
so only JSON decisions block; the hook decides usage first, and a session that never used the tools is quiet whatever
fails.

**Check 6's numbers on `a1e7aad9` are the same as on `dada7a9b`.** In both attempts every count of the 13 turns equals
`dada7a9b`'s attempts 2 and 3: model requests, extra replies (1 in turns 4, 8 and 12, else 0), Stop continuations, the
notices (turns 4 and 8), his Stop hook (13 lines for 13 turns, on the ending attempt in turns 4, 8 and 12). So do
`held_work`, `held_elsewhere`, the failed state, the logout and `marks_after_logout`. The lines on screen are word for
word the same: "Stop hook error: AresOS tools are not running. If you prepared or sent something with them in this
session, …" under turns 4 and 8, "Stop hook error: AresOS held/unfinished work …" under turn 12. Only times moved,
within the spread between runs:

| | `dada7a9b` attempt 2 | `dada7a9b` attempt 3 | `a1e7aad9` attempt 1 | `a1e7aad9` attempt 2 |
|---|---|---|---|---|
| The CLI while stopped (`service_unavailable`) | 3.28 s | 3.23 s | 3.33 s | 3.23 s |
| The managed hooks while stopped (Stop / UserPromptSubmit; exit 0, no output) | 0.198 / 0.204 s | 0.179 / 0.181 s | 0.254 / 0.255 s | 0.176 / 0.180 s |
| The first calls after each start (`ok`) | 0.47 to 0.53 s | 0.43 to 0.45 s | 0.57 to 0.63 s | 0.43 to 0.47 s |
| Check 6's step | 234.5 s | 228.9 s | 237.1 s | 229.4 s |

Attempt 1's slower times go with a slower runner throughout (boot to channel 57.1 s, the build 47 min 35 s); attempt 2
is back at `dada7a9b`'s. What it shows: check 6 drives the hook's working paths, and #91's reordering and guard leave
their outcomes unchanged; the guard passes the JSON block decisions through, since both outage notices and the
held-work reminder still reached the model as Stop continuations and the screen. #91's failure cases (a broken
installation, malformed input, unreadable marks) are not exercised in the VM; main's tests cover them, and one of those
fails on this branch (next).

### PR #58's Control base and Control Mail on `a1e7aad9`: one test on the old config path

Both fail on a test #91 added, `test_integration.Integration.test_stop_hook_installation_failures_are_quiet`:

```
  File "/workspace/control/tests/test_integration.py", line 602, in test_stop_hook_installation_failures_are_quiet
    original = config.read_bytes()
FileNotFoundError: [Errno 2] No such file or directory: '/etc/aresos-control/proxy.json'
```

Line 601 is `config = Path("/etc/aresos-control/proxy.json")`, main's path. This branch moved the config to
`/usr/share/aresos/control` (agreed change 7): `setUp` writes `/usr/share/aresos/control/proxy.json` (line 65) and the
test after it already reads that path (line 633). The merge took #91's new test as main wrote it, with no conflict to
show it. It is the only such config path left in `control/` (the Chrome CI `Dockerfile` still makes the empty
`/etc/aresos-control` folder, as before the merge). The likely fix is that one line, then both workflows again;
`control/tests/` is not among the inputs of Chrome's build hash (`control/chrome/build.py`). Nothing changed here (docs
only); the lead decides.

- **Control base** 43927243265, job `containers` ("Test inside Fedora 45 container"): "Ran 384 tests in 306.519s",
  "FAILED (failures=1, errors=1)": the error above and one failure:
  ```
  FAIL: test_next_deadline_is_none_idle_and_the_earliest_open_reservation_otherwise (test_service_fixes.IdleLoop.test_next_deadline_is_none_idle_and_the_earliest_open_reservation_otherwise)
    File "/workspace/control/tests/test_service_fixes.py", line 355, in test_next_deadline_is_none_idle_and_the_earliest_open_reservation_otherwise
      self.assertEqual(self.engine.next_deadline(), self.expires(later))
  AssertionError: None != 1794853599.8330402
  ```
  That test is 18e's (fix round 2) and the merge didn't change it. It is timing bound: `later` gets 0.6 s, `first` 0.4
  s, then a 0.45 s sleep, so `later` has already expired when the steps between its reservation and the sleep take
  over 0.15 s on a slow runner. The same 384 tests passed it in Control Mail's four container jobs on the same head. A
  flake, recorded for the lead.
- **Control Mail** 43927243311, jobs `containers (0)` to `(3)` ("Real isolated mail servers and shared base"): each
  "Ran 384 tests", "FAILED (errors=1)", the same error; the eight `sweep` jobs green.

### The cancelled runs

The OS image workflow's concurrency (`os-image-${{ github.ref }}`, `cancel-in-progress: false`) lets one run go and one
wait per branch; a newer waiting run displaces the older one. The lead's parallel dispatches (18:17 to 18:19 UTC)
displaced each other:
- 43927268960 (regressions only, dispatched 18:17:30) was cancelled at 18:18:53, two seconds after 43927507924 was
  dispatched;
- 43927507924 (a duplicate `check_build=build`, dispatched 18:18:51) was cancelled at 19:22:45 (the API doesn't say
  what cancelled it then; no run of the workflow was dispatched at that time).

Neither started a job, so neither is a failure. The regressions run was dispatched again as 43965960756 after the
control rerun.

### Done

`check_build=control` green twice on the final head `a1e7aad9` (run 43927257316, attempts 1 and 2) and
`check_build=build` green once (run 43927263485); regressions only green (run 43965960756: 1717 tests, "OK
(skipped=4)"). **Not green on `a1e7aad9`:** Control base and
Control Mail (the test above). Only this file changed after `a1e7aad9`.

### Left, in order

1. The Control base and Control Mail failure above (found while recording; the lead decides the fix, likely one line in
   `control/tests/test_integration.py`), then both workflows again on the new head.
2. The astra reviews (Codex `gpt-6-astra`; Tue 2026-11-17, from 10:56) on head `a1e7aad9` or later.
3. `linux-aresos` reads the `os/` diff (agreed change 16; asked 2026-11-16). The section at the end is up to date:
   `69943d65`'s limit is in, and the merge changed nothing under `os/` or `.github/`.
4. The lead assembles `reviews/18c-image-test/REPORT.md` (Part A, "For the report: B2", "Chrome follow-up", "18e in the
   VM pass", JUDGMENT-CALLs 1 to 28 and the findings; B2's block names `dada7a9b`'s runs, and this section gives the
   same lines on `a1e7aad9`) and merges. The owner gets the JUDGMENT-CALLs and the release question (agreed change 10)
   with check 6's numbers. Chrome's new build hash for `control/chrome/builds.json` and brief 18c-b:
   `8f7036e891737457fcd14cfc680b9c5cb8f42d5a593ba7a0ff64e880668d385c`.
5. The last step deletes this file.

## Fix round 1, part 2 (2026-11-16, Claude agent on Opus 5.5)

Part 1's "Left for part 2", now that PR #69 (18e with its fix rounds, merged as `9324224a`) and PR #86 (`7e712148`)
are on `main`. Opus, because the list was decided. Commits: `e00bf60f` (the merge), `284eb1bb` (the VM step's limit),
`dada7a9b` (check 6 in 18e's merged wording), and this file's commit (`[skip ci]`). **Final head: `dada7a9b`.**

### The merge (`e00bf60f`, `origin/main` at `5bb1500e`)

`main` brought 206 commits: #69, #86, packages 22d, 23b (the startup cover), 23d, 40, the username scrub and briefs
28/28a/28b. Two conflicts:

- `os/manifest/ci/16/pending-rebind.json`: **main's list taken** (22d's rehearsal, run 43737933979, rebound the sources
  and emptied 18c's notes), then `rebind.py pending` recorded the merged workflow again with a note: 18c's
  `check-build` changes wait for the next rehearsal. Its only new row is `.github/workflows/os-image.yml`; main's nine
  rows are unchanged.
- `control/boundary/test_interactive.py`: **both kept.** This branch's `RealToolResultTest` (step 2b) stands before
  main's `ProcessChains` (18e item 6), and main's `if __name__ == '__main__'` closes the file. Main had moved that
  block to the end, because a `ProcessChains` placed after it never ran as a script.

Checked against both parents:
- `control/aresos_control/` equals main's side but for `daemon.py`'s `--config` default. That default and
  `control/launch.py`'s `CONFIG` still name `/usr/share/aresos/control` (agreed change 7). Main's bind-rename is in
  (`listen()`, `.<kind>.sock.new`).
- `control/README.md` and `control/tests/test_integration.py` differ from main only by the config path (2 and 10
  lines).
- `os/build.sh`, `os/ci/image-checks.sh`, `os/ci/overlay/checks.py` and `os/tests/test_aresos_desktop.py` hold main's
  23b and 23d changes plus this branch's own.
- `os-image.yml` differs from main only by 18c's `check-build` lines.

Main's Repo privacy pattern (`.github/workflows/repo-privacy.yml`, run locally over the merged index): 0 file names,
`git grep` exit 1 (nothing found). The hosted Repo privacy run on `dada7a9b` was green as well.

### The Control VM step's limit (`284eb1bb`; the lead's decision, `linux-aresos` told and agreed)

`timeout-minutes` 12 → **16**, with the step's comment on the new basis:
- the last passes took 7 min 50 s and 7 min 9 s;
- fix round 1 adds about 2 to 3 minutes (the full logout and greetd's auto-login, check 6's two new sessions);
- 16 is about 1.5 times the slower pass with that added.

Only that step's lines changed; the job's limit and every other mode stay. `rebind.py pending` recorded the new bytes.
The first green pass took **10 min 31 s** (16 is 1.52 times that).

### Check 6 against 18e's merged behaviour (`dada7a9b`)

- **`held-work` is marked:** its `prepare_send` result names the operation, so its proxy marks the session. It is
  told, and in the merged wording: its Stop reason (the continuation's newest user text) and its resume prompt's
  context (the first of its model requests that carries held work) must both end with `hooks.py`'s `REMINDER` right
  after the held work's JSON.
  - New row fields `reminder_in_stop_reason` and `reminder_in_prompt_context`.
  - The PASS summary gains `held_work` beside `held_elsewhere`.
  - `HELD_REMINDER` in `actions.py` is pinned to `hooks.REMINDER` by `test_control_vm.py`
    `test_check_6s_held_work_texts_are_the_merged_hooks`. That test also builds both hook outputs from the checkout,
    reads them as check 6 does, and shows that the wording before fix round 2 fails the reader.
- **`fresh-beside-held` never used a tool:** it must get nothing and cost nothing. Unchanged from part 1, now required
  with #69 merged.
- **Every VM session that expects a held-work or outage notice used a tool first:**
  - check 6's `used-later`: turn 3 prepares and sends before the outage turns 4 and 8;
  - check 6's `held-work`: it prepares;
  - check 9's four cases: each prepares before its send.
  - Sessions that expect nothing: `failed-fresh-session` only lists (a read never marks), `fresh-beside-held` only
    calls his tool, and check 7's Mail send expects no notice.
- `ServiceModesTest` reads 18e's bind-rename: `__init__`'s loop calls `listen(directory, kind)`, which chmods to the
  module's `SOCKET_MODES[kind]`. Before this change, the test looked for `os.chmod` in the loop and failed on the
  merge.

### Regenerated and checked (laptop)

- `bash os/build.sh control-tree os control <scratch>`: `CONTROL_CHROME_BUILD
  91cdfeb6291380ffd8cf271a77e5baef8a6abd5aaa2c4ea504b69ff866969ae5` (was `ccd0fd79…ce15`), `CONTROL_INSTALLED 74
  files` (8 directories, 1 link). The image build printed the same hash and count.
- No committed manifest binds these generated files. `control.json` is made at build time and compared with
  `control-tree` from the checkout, and `control/chrome/builds.json` is still empty (the lead's, per build). So
  nothing was re-recorded.
- `os/tests` (one module at a time): `test_control_image` 9 OK, `test_control_vm` 35 OK (34 + the new one),
  `test_checkout_sources` 8 OK (main added 2).
- `control/`:
  - `tests.test_reserved_words tests.test_service_user`: 4 OK;
  - `PYTHONPATH=.:tests python3 -m unittest tests.test_slim_policy`: 9 run, 1 failure, the expected
    `boundary_not_installed` (no `/etc/claude-code` on the laptop), as in 18e's record.
- **Not run (the hold):** `test_owner_path` and `test_owner_equality`. The lead's hold for `linux-aresos`'s owner-tools
  install was still on, and no "owner tools done" came during this part. Both ran in the hosted `checks_only` run
  below (the whole `os/tests` suite, OK). No `rpm-ostree`, `bootc` or `ostree` command ran on the laptop.

### Runs on the final head `dada7a9b`

| Run | Mode | Result |
|---|---|---|
| 43860663005 attempt 1 | `check_build=control` | failure, **not this branch**: "Install pinned tools on disposable runner" got 500/502/503 from the Ubuntu snapshot mirror (11:55 to 11:57 UTC). Rerun once after the mirror answered again (three files 200, about 10 s each) |
| 43860697438 | `checks_only` | **success**: "Ran 1717 tests in 1858.481s", "OK (skipped=4)". The 4 skips are main's 23b cover tests (a headless labwc, grim and GTK 4: not the hosted runner); the job took 31 min 37 s |
| 43860663005 attempt 2 | `check_build=control` | **success** (below) |
| 43870759807 | `check_build=build` | **success**: job 14:00:13 to 14:24:44 UTC = 24 min 31 s, build step 14:12:16 to 14:24:38 = 12 min 22 s, the Control VM step skipped as it should be; `CONTROL_CHROME_BUILD 91cdfeb6…69ae5`, `CONTROL_INSTALLED 74 files, 28 wheels, 2024 vendored paths from dada7a9b…`, `CONTROL_CHROME_STARTUP_FILES build 91cdfeb6…69ae5, 0 qualification entries`, `CONTROL_GENERATED_MATCH 15 files`, `CONTROL_FILES_RECORDED 74 files, 2024 vendored paths, 28 wheels from dada7a9b…`, `CHECK_BUILD_PASSED`, `CHECK_BUILD_VM_PASSED` |
| 43860663005 attempt 3 | `check_build=control` | **success** (below; started after the build run, at 14:25 UTC) |
| PR #58's workflows | Control base, boundary, Mail, Chrome, Chrome qualification, Repo privacy | all **success** |

**Run 43860663005 attempt 2**:
- Times: job 12:54:16 to 13:56:20 UTC; tools 16 min 31 s (the mirror was slow); build step 13:12:30 to 13:45:46 =
  33 min 16 s; **Control VM step 13:45:46 to 13:56:17 = 10 min 31 s** against 16.
- PASS lines, every one in this order: `CLAUDE_CODE_PINNED 2.1.319 sha512-FO4Sd23B…oOQ== dabafec8…8eed`,
  `CONTROL_CHROME_BUILD 91cdfeb6…69ae5`, `CONTROL_INSTALLED 74 files, 28 wheels, 2024 vendored paths from
  dada7a9b…`, `CONTROL_CHROME_STARTUP_FILES build 91cdfeb6…69ae5, 0 qualification entries`,
  `CONTROL_GENERATED_MATCH 15 files`, `CONTROL_FILES_RECORDED`, `CHECK_BUILD_PASSED`,
  `CHECK_BUILD_CONTROL_DISK_READY`, `CONTROL_IMAGE_FILES_PASS`, `CONTROL_ETC_CLAUDE_CODE_PASS`,
  `CONTROL_RELEASE_CHECKS_PASS`, `CONTROL_IDLE_FOOTPRINT_RECORDED {…}`, `CONTROL_FIXTURES_REACHABLE`,
  `CONTROL_ENTRY_POINTS_PASS`, `CONTROL_PRECONDITION_PASS`, `CONTROL_USER_MCP_INSTALL_PASS`,
  `CONTROL_SERVICE_SANDBOX_PASS`, `CONTROL_ORDINARY_SESSION_PASS {…}`, `CONTROL_MAIL_FLOWS_PASS`,
  `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1, "owner_answers": 0,
  "prompt_shown": true, "send_arrivals": 1}}`, `CONTROL_INTERACTIVE_ASK_PASS`, `CONTROL_PASSWORDS_PRIVATE_PASS`,
  `CONTROL_SELINUX_AFTER_CHECKS_PASS`, `CONTROL_STORAGE_TESTS_PASS {…}`, `CONTROL_SERVICE_RESTART_PASS`,
  `CONTROL_VM_POWEROFF_CLEAN`, `CHECK_BUILD_CONTROL_PASSED`.
- The fixture stop step was green.
- Step times (s): boot to channel 53.7, files 5.2, idle 59.2, entry points 5.1, precondition 2.4, user MCP 13.5,
  **check 6 234.5** (was 163.1 to 165.6), check 7 44.8, check 9 128.9, storage tests 76.8, restart 1.8; the pass
  630.9.

**Run 43860663005 attempt 3** (recorded after the handback, from the run's log):
- Times: job 14:25:14 to 15:23:27 UTC = 58 min 13 s; tools 7 min 15 s; build step 14:33:37 to 15:14:32 = 40 min 55 s;
  **Control VM step 15:14:32 to 15:23:23 = 8 min 51 s** against 16.
- PASS lines: the same lines in the same order as attempt 2, with the same `CLAUDE_CODE_PINNED 2.1.319
  sha512-FO4Sd23B…oOQ== dabafec8…8eed`, `CONTROL_CHROME_BUILD 91cdfeb6…69ae5`, `CONTROL_INSTALLED 74 files, 28 wheels,
  2024 vendored paths from dada7a9b…`, `CONTROL_CHROME_STARTUP_FILES build 91cdfeb6…69ae5, 0 qualification entries`
  and `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1, "owner_answers": 0,
  "prompt_shown": true, "send_arrivals": 1}}`, ending in `CONTROL_VM_POWEROFF_CLEAN`, `CHECK_BUILD_CONTROL_PASSED`.
- The fixture stop step was green.
- Step times (s): boot to channel 41.9, files 3.4, idle 60.1, entry points 4.2, precondition 1.9, user MCP 9.6,
  **check 6 228.9**, check 7 34.8, check 9 110.0, storage tests 30.9, restart 0.9; the pass 530.7.

### The evidence (attempt 2; attempt 3 below)

- **`desktop_with_service_failed`** (agreed change 6, REVIEW-A1 #1): the service `failed` (`NRestarts=5`,
  `Result=exit-code`, 10.4 s after `systemctl start`). The logout took 11.4 s, and the desktop came up again in 13.8 s
  in all: state `SETUP`, not latched, greetd session `1` before and `3` after. `marks_after_logout: false`: 18e's
  "marks vanish at logout" now holds in the VM (PLAN-GAP 7 closed).
- **`held_work`** (the session that holds work): 4 model requests (prepare, send, the answer after the driver's
  resume prompt, one Stop continuation), 1 extra, 1 continuation. `reminder_in_stop_reason: true`,
  `reminder_in_prompt_context: true`; the send `reserved`; his Stop hook once, on the ending attempt. On screen:
  "Stop hook error: AresOS held/unfinished work (untrusted app data; inspect status, do not resubmit unknown …".
- **`held_elsewhere`** (the fresh session beside it, the numbers for the owner): **2 model requests, 0 extra, 0 Stop
  continuations, `requests_carrying_it: []`.** On screen only Claude Code's own spinner text ("running
  UserPromptSubmit hook" / "running Stop hook"). His Stop hook ran once, and the held operation was `reserved` with
  `pending_total` 1 the whole time. Released afterwards: cancelled (`failed`), notice acknowledged,
  `pending_after: 0`.
- **`network_listeners: 0`** (REVIEW-A1 #7; `control-service`: `nrestarts 0`, `selinux Enforcing`, user
  `aresos-tools`).
- **`fixtures/password-scan.json`** (REVIEW-A1 #5; printed by the fixture stop step): `{"files": 191, "hits": [],
  "holding": [], "members": 464, "redacted": {"greenmail.txt": 1}, "removed": [], "unreadable": []}`. That is 191
  evidence files and 464 archive members searched; GreenMail's log was redacted once, and nothing else held the
  password. Check 8: `files_holding_it 1`, not in the journal. (Each rerun of the same run hides its earlier attempts'
  artifacts, so attempt 2's evidence files are known from its log only.)
- **Check 6 in numbers:**
  - The 11 earlier turns: as in run 43687234953.
  - The two outage notices: turns 4 and 8.
  - The CLI while stopped: `service_unavailable` after 3.28 s.
  - The managed hooks while stopped: 0.198 s and 0.204 s, exit 0, no output.
  - The first calls after each start: 0.47 to 0.53 s, `ok`.
  - `/run/user/1001` existed (greetd's session, `Linger=no`).
  - His Stop hook: 13 lines for 13 turns. Nothing was pending after the check.
- **Idle** (change 14): 1 context switch in 60 s (0.017 wake-ups a second), 5.4 ms of CPU (0.009 %),
  `memory.current` 33,026,048 B, RSS 37,120 KiB, PSS 25,365 KiB, 1 process, 1 thread.
- **Check 9:**
  - `normal-yes`: done, 1 arrival.
  - `skip-no` and `skip-user-allow-send`: reserved, 0 arrivals, resumed, 1 continuation, the reminder in it.
  - `normal-permission-user`: `hook_calls 1, owner_answers 0, send_arrivals 1`, equal to the container's pin; the
    prompt flashed (`prompt_shown: true`) this time.

**Attempt 3** (the same head and checks; every count equals attempt 2's, only times differ):
- **`desktop_with_service_failed`:** the service `failed` 10.2 s after `systemctl start` (`NRestarts=5`,
  `Result=exit-code`); the logout took 11.3 s and the desktop came up again in 13.7 s in all: state `SETUP`, not
  latched, greetd session `1` before and `3` after. `marks_after_logout: false`.
- **`held_work`:** 4 model requests, 1 extra, 1 continuation; `reminder_in_stop_reason: true`,
  `reminder_in_prompt_context: true`; the send `reserved`; his Stop hook once, on the ending attempt. On screen the same
  "Stop hook error: AresOS held/unfinished work (untrusted app data; inspect status, do not resubmit unknown …".
- **`held_elsewhere`:** **2 model requests, 0 extra, 0 Stop continuations, `requests_carrying_it: []`.** On screen only
  Claude Code's own spinner text. His Stop hook ran once, and the held operation was `reserved` with `pending_total` 1
  the whole time. Released afterwards: cancelled (`failed`), `pending_after: 0`.
- **`network_listeners: 0`** (`control-service`: `nrestarts 0`, `selinux Enforcing`, user `aresos-tools`).
- **`fixtures/password-scan.json`:** `{"files": 191, "hits": [], "holding": [], "members": 423, "redacted":
  {"greenmail.txt": 1}, "removed": [], "unreadable": []}`. Check 8: `files_holding_it 1`, not in the journal.
- **Check 6 in numbers:** the 13 turns' requests, extra replies, notices and Stop hook runs equal attempt 2's; the two
  outage notices in turns 4 and 8; the CLI while stopped `service_unavailable` after 3.23 s; the managed hooks while
  stopped 0.179 s and 0.181 s, exit 0, no output; the first calls after each start 0.43 to 0.45 s, `ok`;
  `/run/user/1001` existed (`Linger=no`); his Stop hook 13 lines for 13 turns; nothing pending after the check.
- **Idle:** 1 context switch in 60 s (0.017 wake-ups a second), 1.7 ms of CPU (0.003 %), `memory.current`
  33,144,832 B, RSS 37,080 KiB, PSS 25,401 KiB, 1 process, 1 thread.
- **Check 9:** the same four outcomes as attempt 2; `normal-permission-user` again `hook_calls 1, owner_answers 0,
  send_arrivals 1`, and the prompt flashed again (`prompt_shown: true`).

### Decisions the code doesn't show (JUDGMENT-CALLs for the report)

28. **The held-work wording is read from what reaches the model, not from the screen.** The terminal shows only the
    reason's first line, cut at its width, so the end of the text can't be seen there. The Stop reason is read from
    the continuation's newest user text (the last 600 characters, as for the outage notice); the prompt context from
    the session's first model request that carries held work, which must be the one after the driver's resume prompt.
    Changing it later: one function (`held_context`) and one row field.

### Findings for the lead

- **The job's limit for `check_build=control` stays 127 minutes**, as the lead allowed only the step's line. Its
  comment's sum ("tools 20 + build 80 + Control VM pass 12 + 15") now reads 16 for the pass, which leaves 11 minutes
  of margin instead of 15. The jobs so far took 48 to 62 minutes, and this part's slowest was 62 (a slow mirror). A
  one-line follow-up (131 and the comment) if the lead wants the sum kept, with `rebind.py pending` and
  `linux-aresos` told. (Done by the lead in `69943d65`: 131; see the merge section at the top.)
- **The snapshot mirror failed once** (attempt 1: 500/502/503 on every index for about 2.5 minutes). In attempt 2 the
  tools step took 16 min 31 s against its 20 (the mirror was slow but answered).
- **New Chrome build hash `91cdfeb6…69ae5`** (main's 18e fix round 2 changed `control/`), for
  `control/chrome/builds.json` and brief 18c-b, which still names `ccd0fd79…ce15`.

### Left, in order

**Superseded by "Left, in order" in the merge section at the top.** Kept for the record.

1. `linux-aresos` reads the `os/` diff (agreed change 16; the section at the end is up to date with this part).
2. Astra's review (Codex `gpt-6-astra`) before the merge.
3. The lead assembles `reviews/18c-image-test/REPORT.md`: Part A, "For the report: B2" (updated below to this part's
   runs), "Chrome follow-up", "18e in the VM pass", JUDGMENT-CALLs 1 to 28 and the findings. The owner gets the
   JUDGMENT-CALLs and the release question (agreed change 10) with check 6's numbers.
4. The last step deletes this file.

## Fix round 1, part 1 (2026-11-16, Claude agent on Opus 5.5)

From `REVIEW-A1.md` and `SECURITY-REVIEW-A1.md` (both CHANGES-NEEDED at `84f45c28`), on head `a2be05d7`. Part 1 is
code and local tests only: no CI runs, because `main` isn't merged yet and its OS image checks would fail on a known,
already-fixed 404. Opus, because the list was tight and decided. Commits: `f37d2e3a` (the wheels against the lock),
`5e2dedc5` (the password checks inside the archives), `fe245972` (checks 2 and 6, the static checks), and this file's
commit (`[skip ci]`, the one pushed). Everything changed is CI-only (`os/ci/`, `os/tests/`) or this folder; nothing in
the image, `control/` or the workflow.

### What changed, per finding, and the test that pins it

1. **REVIEW-A1 #1, agreed change 6: the desktop session with the service failed.** `os/ci/control/actions.py:958`
   `desktop_with_service_failed()`, called by check 6's `arm_failure` (`:1060`) right after `wait_failed()`, before
   the fresh session starts:
   - ares is logged out as a session end does it: `systemctl stop greetd.service`, `loginctl terminate-user ares`,
     then a wait (180 s at most) until he has no logind user, no `/run/user/1001` and no `foot`, `labwc` or Prism;
   - greetd's runfile `/run/greetd.run` is removed (`:942`): greetd runs its `initial_session` (the image's
     auto-login) only once per boot, recorded in that file (greetd(5), "runfile"); then `systemctl start greetd`;
   - `checks.py`'s own `wait_session()` and `desktop_session()` (the policy pass's) require the terminal and the
     desktop as at boot: state `SETUP`, not latched, one keeper, one supervisor, the helper, Prism in its launch
     scope; a new greetd session id; the runtime folder made again by that login (no lingering); the service still
     `failed` with the same `NRestarts`.
   - The PASS line's summary names it: `desktop_with_service_failed` with the service state, `SETUP`, the greetd
     sessions before and after, the seconds, and `marks_after_logout` (18e's "marks vanish at logout", PLAN-GAP 7: the
     logout takes the runtime folder and its marks with it; recorded, now that the pass has a logout).
   - Test: `os/tests/test_control_vm.py:419` (the order stop, terminate, runfile, start, `wait_session`,
     `desktop_session`; greetd's config has the `initial_session` and no `runfile` of its own; `checks.py` defines both
     functions; armed before the desktop). JUDGMENT-CALL 23.
2. **SECURITY-REVIEW-A1 F1: held work beside a session that never used the tools** (check 6). `ORDINARY_TURNS`
   (`actions.py:783`) gains a fifth column (his answer to our ask) and two sessions after the existing two:
   - `held-work` (turn 12): prepares and sends, he answers **No**, the send stays `reserved`. Required: the prompt
     showed, the session is told about its own held work (at least one Stop continuation), it is marked as one that
     used the tools.
   - `fresh-beside-held` (turn 13): a fresh Claude Code that only calls his own tool while that work is pending
     (`note_held`, `:1081`, proves the operation `reserved` and in `control pending` first). Required: no Stop
     continuation, no extra model request, nothing of ours on screen, his hooks once each, no mark, and none of its
     model requests carries the held operation's id or the held-work text (`:1221`; by id, so #69 may reword it).
   - The cost goes into the summary as `held_elsewhere` (model requests, extra, Stop continuations, what is on screen,
     which requests carried it).
   - **It passes only once PR #69's fix round is in** (pending reminders and outcome notices get the outage notice's
     usage gate). Before that, the fresh session gets the held-work context and one Stop block: one extra model
     request and a hook error on screen. Part 2 runs it.
   - The held operation is released afterwards (`finally`) with check 9's steps, now one function
     (`release_held`, `:927`; check 9 calls it at `:1434`). The driver's resume prompt after a No counts with the turn
     it resumes (`sessions.RESUME`, `sessions.py:30`; `actions.py:1136`).
   - Tests: `test_control_vm.py:381` (the plan: four sessions, the No only on our ask, the order) and `:400`
     (`release_held` cancels, acknowledges, ends with nothing pending).
3. **REVIEW-A1 #5: the leak checks inside the evidence archives.** New `os/ci/control/evidence_scan.py`: every evidence
   file is searched raw and, for gzip streams and tar archives, member by member (three levels deep); an archive that
   can't be read counts as holding the password (removed, the step fails).
   - `runner.sh stop` (`runner.sh:123-139`) redacts **only GreenMail's log** (it logs the password it was given), then
     removes every file that holds it, Dovecot's log included, and fails. Its report (counts and names, never the
     password) is `fixtures/password-scan.json`, replacing `redacted.txt`.
   - `control_vm.py:91` uses the same scan after check 8; `passwords-runner.json` gains `archive_members` and
     `unreadable`.
   - Tests: `test_control_vm.py:452` `EvidenceScanTest` (a hit inside a `.tar.gz` named by its member and invisible to a
     raw search; plain tar, gzip and an archive inside an archive; a broken archive; GreenMail redacted, a Dovecot hit
     fails and is removed, the report never holds the password; both callers use the scanner).
4. **REVIEW-A1 #6: the wheels against the checkout's lock.** `os/ci/check-image.sh:74-112` parses the checkout's
   `control/requirements.lock` itself, strictly (every line a pin, a hash or a comment), and requires the image's
   wheels to be exactly the lock's set, once each, every SHA-256 one of its pins, every file a `.whl`. Test:
   `os/tests/test_control_image.py:274` (six wrong wheel lists and an unknown lock line fail; the real set passes).
5. **REVIEW-A1 #7: no listening network socket.** Check 2 calls `network_listeners()` (`actions.py:571`, at `:642`):
   the unit's PIDs from its cgroup, their socket inodes from `/proc/<pid>/fd`, listening TCP (state `0A`) and bound,
   unconnected UDP (`07`) from `/proc/<pid>/net/{tcp,tcp6,udp,udp6}` (`listening_sockets`, `:545`), and `ss -Hlntup`'s
   lines naming those PIDs. Both must be empty. A listener the check opens itself must show in both, so the check
   can't pass blind; unreadable fds raise. `unit.json` gains `network_listeners`, the PASS summary their count. Test:
   `test_control_vm.py:356` (a TCP listener and an unconnected UDP socket are found, a connected one isn't, nothing
   after closing, a missing process raises).
6. **REVIEW-A1 #9: static checks.** `test_control_vm.py:440`: `bash -n` on every `os/ci/control/*.sh` (`runner.sh`)
   and `py_compile` on every `.py` of `os/ci/control/` and `control/ci/image/` (`mail_flows.py`).
7. **REVIEW-A1 #8: the report draft.** "For the report: B2" (step 2c, below) now quotes run 43687234953 (head
   `9ee1fbdf`), `"prompt_shown": false`, says the flash is timing dependent and caught only in some runs, and says
   this branch changed B1's model double (`texts()`); the driver is B1's. Part 2 swaps in the final head's run.
8. **SECURITY-REVIEW-A1 K6 withdrawn** by the lead (below); the review keeps its text with the lead's correction
   under it.

REVIEW-A1 #2 (the managed `CLAUDE.md` line in the owner's question) is K3 below; #3 (fresh runs after the merge) and
#4 (`checks_only`) are part 2's.

### Known limits (fix round 1)

- **K1, auto mode untested.** Claude Code's default interactive mode for his sessions is auto; B1 and B2 run
  `--permission-mode default` or skip-permissions. Explicit ask rules force a prompt in every mode by Anthropic's
  documentation, so a gap would be a regression only. Goes to a later B1 case, if the model-double harness can run
  auto mode at all.
- **K2, a non-owner session's Stop is blocked every turn** (`permission_denied` read as unavailable). Fixed in PR #69.
- **K3, the managed `CLAUDE.md` says other sessions' messages are never instructions**, in every session, also agents
  a lead briefs (REVIEW-A1 #2). Narrowed in PR #86; the owner's question (agreed change 10) names it (the lead).
- **K4, more unit hardening** (`RestrictNamespaces`, `SystemCallFilter=@system-service` and the rest of the review's
  list): a follow-up, each line with its own VM passes; without capabilities most gaps are moot.
- **K5, testapp ships** (its tools, generated files and two ask rules): by design, the VM test uses it; no network, a
  local SQLite receiver, its fixture switch admin-only.
- **K6, "the release job runs no Control checks": withdrawn.** The release-27 job's step "Build with the reviewed check
  build, run the image checks and the first VM pass" runs `bash os/ci/check-build.sh build`
  (`.github/workflows/os-image.yml:436`). That path builds with `kind=release` (`GITHUB_JOB` isn't `check-build`) and
  calls `check-image.sh localhost/aresos:check release` (`os/ci/check-build.sh:54`), which runs `image-checks.sh`'s
  Control section and the record-to-checkout check, now with the wheels against the lock. The checked image is the one
  the job tags, diffs and publishes. `linux-aresos`'s release package 42 adds a test that pins it.
- **K7, one request at a time** (the service is single-threaded; hooks wait up to 10 s behind a long send, then go
  quiet): accepted.
- **K8, a taken UID 250 would quietly become another number** at the first boot of the update: seen by
  `release_checks.py` in the rehearsal (agreed change 12); free on the laptop today.
- **The desktop-with-failed-service check rests on a logout and a fresh auto-login,** not on a reboot (JUDGMENT-CALL
  23): it proves that a desktop session starts with the service failed, not that the boot order itself never waits on
  it. The boot order is held by the static unit-policy check (`image-checks.sh`: no unit names or orders after
  `aresos-toold.service`; `Type=simple`).
- **Held work's gate is proven only for a session of his own tool calls** (no turn where the fresh session also
  calls our tools while another holds work), and for one held operation.

### Decisions the code doesn't show (JUDGMENT-CALLs for the report)

23. **Agreed change 6 is proven by a logout and greetd's auto-login again, not a reboot.**
    - A plain `systemctl restart greetd` would not log ares in again: greetd's `initial_session` runs once per boot
      (its runfile); greetd would start `agreety` and `wait_session` would time out.
    - Ending only the greetd session would keep his user manager and runtime folder: the desktop's instance would go
      on, and the supervisor could restore the old session's state (Prism lost its compositor: `RECOVERY`,
      `prism_failed`) instead of starting as at boot.
    - A reboot of the guest would end the CI channel and every later check, and drop the CI drop-in under `/run`.
    - So: a full logout (`terminate-user`, as when his last session ends), the runfile removed (CI only, this
      throwaway guest), greetd started: the same auto-login the boot runs. Cost: about one to two minutes of VM time
      (estimated: the logout, Prism's start in `desktop_session`). Changing it later: one function.
24. **The held-work session answers No in normal mode**, his everyday mode; B1 proved a normal-mode No in the
    container, and check 9 keeps the skip-mode No.
25. **The fresh session's check is by the held operation's id and the held-work text in its model requests**, plus the
    row checks (no continuation, no extra request, nothing of ours on screen), so #69's fix round may reword the
    reminder without breaking it.
26. **An evidence archive that can't be read counts as holding the password**: removed, the step fails. What can't be
    searched isn't published.
27. **The listener check reads `/proc` itself and takes `ss` as a second view**, with a control listener of its own so
    neither can pass blind (an `ss -p` that can't attribute sockets would otherwise find nothing).

### Checks run (all on the laptop, no containers, VMs, root or CI)

- `python3 -m unittest discover -s os/tests -p <module>`: `test_control_image` 9 OK, `test_control_vm` 34 OK (24 before,
  10 new), `test_checkout_sources` 6 OK.
- `control/`: `python3 -m unittest tests.test_reserved_words tests.test_service_user` 4 OK.
- `os/ci/control/evidence_scan.py` on a scratch folder: a `.tar.gz` holding the password removed with exit 1, then
  exit 0; GreenMail's log redacted once.
- `bash os/build.sh control-tree` not run separately: the tree didn't change (no file under `control/` or the install
  map), and `test_control_image` runs it.
- **Still to run:** `test_owner_path` and `test_owner_equality` (the lead held the owner modules while `linux-aresos`
  installed the owner tools on the laptop).

### Left for part 2, in order (done in part 2, above; kept for the record)

1. Wait until PR #69 (with its fix round) and PR #86 are on `main`.
2. Merge `origin/main` into this branch (a merge commit; never a rebase or a force-push):
   - `os/manifest/ci/16/pending-rebind.json`: take main's list, then record the merged workflow with
     `rebind.py pending` (REVIEW-A1 #3);
   - under `control/aresos_control/` take main's side (#69, the restore lock `b04c7e77`); then check that this branch's
     two config constants (`CONFIG` in `control/launch.py`, `--config` in `daemon.py`) still name
     `/usr/share/aresos/control` (agreed change 7);
   - rerun the local modules above and `bash os/build.sh control-tree os control <scratch>` for the new Chrome build
     hash.
3. The Control VM pass's step limit (12 minutes; the last pass took 7 min 50 s and 7 min 9 s): this round adds the
   logout and auto-login (estimated 1 to 2 minutes) and two sessions (about 1 minute). If the lead agrees, raise it
   before the first run (1.5 times the slower pass, linux-aresos's rule), in a commit of its own with `rebind.py
   pending`, `linux-aresos` told first (agreed change 15). Otherwise read the step's time in the first run.
4. The four CI runs on the merged head: `check_build=control` twice (the second a `gh run rerun`), `check_build=build`
   once, `checks_only` once (REVIEW-A1 #3 and #4). Watch with `gh run watch <id> --exit-status --interval 300` (60
   for `checks_only`).
5. Read the new evidence: `CONTROL_ORDINARY_SESSION_PASS`'s `desktop_with_service_failed` and `held_elsewhere` (the
   numbers for the owner's question), `CONTROL_SERVICE_SANDBOX_PASS`'s `network_listeners: 0`, the runner's
   `fixtures/password-scan.json` (GreenMail's redactions, the archive members searched). Put the final head's run IDs
   and lines into the "For the report" sections, and set change 6's row to the run.
6. `linux-aresos` reads the `os/` diff (agreed change 16; the section at the end is up to date with this round).
7. Astra's review (Codex `gpt-6-astra`) before the merge.

### Paths outside the allowed list

None needed: every change is under `os/ci/`, `os/tests/` or `reviews/18c-image-test/`.

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
| 2 Base with 23 and Chrome | done: `main` merged with PR #27 (`4cf76e63`); Chrome's startup files in the image, its checks in B2 (Chrome follow-up) |
| 3 Lists that pin enabled units | done as far as `main` has them: no list pins enabled units or users except release 27's `ci/release_diff.py` (the next release extends its own diff); image check proves the updater audit saw the unit; polkit unaffected (no rules) |
| 4 `gh` | check-resolve step done, resolve run done; **install open** (stop rule, below) |
| 5 Fixed UID/GID | done (250) |
| 6 Enabled, never holds the session | code done (fix round 1: with the service failed, ares logs out and the desktop session comes up again as at boot, `desktop_session`); the VM proof is part 2's run. Before: check 6 green with the service stopped and failed, Claude Code only (step 2c, run 43577034725) |
| 7 Config in `/usr/share/aresos/control` | done; image check done; booted-guest check `control-claude-code-files` (step 2a) |
| 8 `checks.py` hook | done (step 2a): `actions.d` |
| 9 Fixture servers, negative check | negative check done; fixture servers and CI layer done (step 2a) |
| 10 Owner's yes before merge | open (lead) |
| 11 Folders by tmpfiles | done |
| 12 Rehearsal check actions | done (step 2a): `os/ci/control/release_checks.py` |
| 13 Reserved words test | done |
| 14 Idle footprint | measured (step 2a): ~32 MB, 10 wake-ups/s, 0.35–0.67 % of one CPU; with Chrome (follow-up): 32.9–33.2 MB, 10.0–10.4/s, 0.43–1.32 % |
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
managed ask interactively in normal mode: the prompt may flash, nobody answers, the send goes out once. That is the
accepted residual, and it equals the container's pin for that case. **run** 43860663005 (the final head `dada7a9b`,
attempts 2 and 3), `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1,
"owner_answers": 0, "prompt_shown": true, "send_arrivals": 1}}` (attempts 2 and 3 alike). The managed-level and skip-mode
variants are proven in the container only (B1's pin: all four approve, one send each); the VM doesn't edit the
managed files. Without such a hook the ask asked every time, also in skip-permissions mode and with his user allow
rule for the send. B1 found the container's result equal to 18d's print-mode approval on 2.1.319 (**read**
`REPORT.md`, run 43444623151); the VM case agrees with both. The prompt's flash is timing dependent (B1) and is
recorded, not pinned: the VM caught it in runs 43572578699, 43577034725 and 43860663005 attempts 2 and 3
(`prompt_shown: true`), not in the Chrome follow-up's runs, in run 43687234953 or in run 43927257316 attempts 1 and 2
on the merge head `a1e7aad9` (`false`). The hook's outcome (one send, no answer of his) was the same in every run.

**Done.** B2's checks 1 to 9 except the Chrome lines and `gh` (moved to 18c-b), as actions of the Control test layer
(`os/ci/control/`), run by `check_build=control` in its own workflow step after the build; the fixture servers
(GreenMail, Dovecot) on the runner's loopback, Claude Code 2.1.319 from the boundary's lock, and B1's driver and model
double in the guest. This branch changed the model double once (`texts()` in `control/boundary/interactive_model.py`,
PLAN-GAP 4 of step 2b): Claude Code passes a real MCP server's result as one string, which B1's container cases never
produced; the driver is B1's as merged.

**Verified** (all **run**, the final head `dada7a9b`, run 43860663005, attempts 2 and 3; log lines as printed):
`CONTROL_IMAGE_FILES_PASS` (check 1), `CONTROL_ETC_CLAUDE_CODE_PASS` (change 7), `CONTROL_RELEASE_CHECKS_PASS` (change
12), `CONTROL_IDLE_FOOTPRINT_RECORDED` (change 14), `CONTROL_FIXTURES_REACHABLE`, `CONTROL_ENTRY_POINTS_PASS` (check
3), `CONTROL_PRECONDITION_PASS` (check 4), `CONTROL_USER_MCP_INSTALL_PASS` (check 5), `CONTROL_SERVICE_SANDBOX_PASS`
(check 2), `CONTROL_ORDINARY_SESSION_PASS` (check 6), `CONTROL_MAIL_FLOWS_PASS` (check 7),
`CONTROL_PERMISSION_REQUEST_RECORDED {…}` and `CONTROL_INTERACTIVE_ASK_PASS` (check 9),
`CONTROL_PASSWORDS_PRIVATE_PASS` (check 8), `CONTROL_SELINUX_AFTER_CHECKS_PASS` (check 2's scan again),
`CONTROL_STORAGE_TESTS_PASS` (Chrome's storage plan on the image's Python and SQLite), `CONTROL_SERVICE_RESTART_PASS`,
`CONTROL_VM_POWEROFF_CLEAN`, `CHECK_BUILD_CONTROL_PASSED`; the fixture stop step's leak scan
(`fixtures/password-scan.json`: 191 evidence files and 464 archive members searched in attempt 2, 423 in attempt 3,
GreenMail's log redacted once, nothing else held the password). Check 2 found no listening network socket (`network_listeners: 0`).
`check_build=build` on the same head: run 43870759807 (`CHECK_BUILD_PASSED`, `CHECK_BUILD_VM_PASSED`); `checks_only`:
run 43860697438 (1717 tests OK). Evidence: the `check-build-evidence` artifact of the last attempt (3 days; a rerun
hides the earlier attempt's).

**Check 6 for the owner (agreed change 10; his answer #254 "Quiet unless used", built in 18e, proven here in run
43860663005 attempts 2 and 3 on the final head, before in run 43687234953 twice).** With the service healthy, an ordinary Claude Code turn costs nothing extra and shows nothing of
ours. While the service is stopped or has failed, a session that never used our tools still shows nothing and costs
nothing extra: no notice, no extra model reply, his prompt, his own tool and his own hooks work as usual; one of our
tools called from it answers "not running" after about 3 seconds. A session that prepared or sent something with our
tools gets **one** two-line "Stop hook error: AresOS tools are not running. If you prepared or sent something with
them in this session, its outcome is unknown: tell the owner, and don't repeat it." under the first answer after the
service went down, and that turn costs one extra model reply; the following turns while it stays down are quiet and
cost nothing extra. If the service comes back and goes down again, that session is told once more. His own Stop hook
runs once per turn, at its real end. Our hooks take about 0.1 to 0.2 seconds each while the service is down, so no
turn waits for them. A session started while the service was down gets our tools as soon as the service is back,
without a restart. Once the service is back every turn is clean. **Held work stays with the session that made it:**
while one session holds a send he answered No to, that session is reminded once per turn end (one extra model reply)
and told to leave the work to him ("Don't complete, cancel, resend or acknowledge this work on your own: tell the
owner what is waiting, and let him decide."). A fresh session beside it that never used our tools gets nothing: two
model requests, no extra reply, nothing of ours on screen, and none of its requests carries the held work. **A failed
service doesn't hold up his desktop:** with the service failed, he was logged out and greetd's auto-login brought the
desktop up again as at boot in about 14 seconds. (Before 18e: one extra reply and a four-line
"connection lost" reminder in every turn of every session while the service was down; the owner chose (b) of the
three options offered then.)

**Not verified.** Real model cost (the double answers instantly; with a real model the extra reply costs one more
response); the Chrome lines (18c-b); `gh` (18c-b); the update path from release 27 (the next release's rehearsal);
his own Stop hook's behaviour on other Claude Code versions; the boot order itself with the service failed (proven by
a logout and auto-login, not a reboot: JUDGMENT-CALL 23); auto mode (K1).

**PLAN-GAPs** (B2): the receiver counts per recipient while B1's pin counts sends (fixed in the check); GreenMail
logs the fixture password (fixed in `runner.sh stop`); `chrome.sock` 0600 in today's `daemon.py` (step 2a); the
model double's string results (step 2b).

**Measured times** (run 43860663005 attempt 2, the final head): tools 16 min 31 s (a slow mirror), build to disk
33 min 16 s, Control VM step 10 min 31 s against its 16 (boot to channel 53.7 s, the pass 630.9 s: idle 59.2, check 6
234.5, check 9 128.9, storage tests 76.8, check 7 44.8, user MCP 13.5, the rest under 6 s each); the job 62 min 4 s.
Attempt 3: tools 7 min 15 s, build to disk 40 min 55 s, Control VM step 8 min 51 s (boot to channel 41.9 s, the pass
530.7 s: idle 60.1, check 6 228.9, check 9 110.0, check 7 34.8, storage tests 30.9, user MCP 9.6, the rest under 5 s
each); the job 58 min 13 s. Earlier (run 43577034725, before Chrome, 18e and fix round 1): VM step 6 min 13 s, job 48
min 19 s.

## Chrome follow-up (after PR #27; 2026-11-15)

Built by a Claude agent on Opus 5.5. Commits `4cf76e63` (merge of `origin/main` at `32fd16ec`, with Chrome's
`09cedc84`), `c58517fa` (startup files and checks), `4cf908a2` (the workflow's limits, own commit, `rebind.py pending`),
`3c7c3c66` (check 6 reads the offered tools from the session's last request).

### Done

- **Merge** (`4cf76e63`, a merge commit). Two conflicts: `control/ci/setup.sh` (main's Chrome lines, copying
  `control/chrome` and writing `chrome/build-id.json`, kept with this branch's config folder `/usr/share/aresos/control`)
  and `os/manifest/ci/16/pending-rebind.json` (main's list after 22c's rehearsal, then `rebind.py pending` re-recorded
  18c's three workflow notes plus one saying why they wait again). `os-image.yml`, `daemon.py`, `launch.py`, the
  README and the tests merged cleanly; the merged `daemon.py` keeps the config default `/usr/share/aresos/control`.
- **What the merged service needs to start** (**read** `aresos_control/engine.py`, `chrome/adapter.py`, `daemon.py`;
  **run** locally on a `control-tree` copy): the Engine builds the Chrome adapter, whose `__init__` reads
  `<code>/chrome/build-id.json` (else it runs `<code>/chrome/build.py`, which the image doesn't carry: the service would
  not start) and `<code>/chrome/qualification.json`. Nothing else: the excluded-sites file is read only once a browser
  is connected (`mode()` refuses `chrome_unavailable` first), the upload folder only on an upload, `gh` and the record
  fetch only after a native host connects. An `Engine` built from the installed tree copy started with build
  `966c2737…4352` and 0 qualification entries and answered `chrome tabs` with `chrome_unavailable` "Chrome is not
  connected; start normal Chrome with the installed extension."
- `os/build.sh`: `FILES` gains `chrome/qualification.json` → `/usr/libexec/aresos-control/chrome/qualification.json`
  (0644), `DERIVED` gains `chrome/build-id.json` = `{"build":"<hash>"}` from `python3 -I -B control/chrome/build.py`
  over `control/` of the commit (the README's rule). Both are in `control.json` like every other file, so
  `image-checks.sh` (in the image as recorded) and `check-image.sh` (equal to the checkout's `control-tree`) check them
  with no new code. The build prints `CONTROL_CHROME_BUILD <hash>` (for the lead's `control/chrome/builds.json`) and its
  self-check reads both files the way the adapter does, with the installed code (`validate_record`):
  `CONTROL_CHROME_STARTUP_FILES build <hash>, 0 qualification entries`. `control-tree` now installs 73 files.
- `os/ci/control/actions.py`:
  - `SOCKET_MODES` = `act.sock` 0666, `admin.sock` 0600, **`chrome.sock` 0666** and `SOCKET_FOLDER_MODE` 0711, the
    merged `daemon.py`'s. `os/tests/test_control_vm.py` (`ServiceModesTest`) reads them from `daemon.py` itself (the
    `for kind in (...)` loop's `os.chmod` expression and `directory.mkdir(mode=...)`), so a change there fails the
    test until the check follows. No other mode the checks assert comes from `daemon.py` (the password folder and
    file are Mail's `transport.py`, the state folders tmpfiles').
  - Check 3: `aresos-mcp chrome` answers `initialize` and `tools/list` with exactly `generated/chrome-tools.json` and
    `chrome-instructions.txt` (beside `mail` and `control`); a `tools/call` of `tabs` with no browser is an MCP error
    result naming `chrome_unavailable` (its time recorded: never a hang); `aresos chrome tabs` as `ares` is refused
    `chrome_unavailable`; another user on `chrome.sock` gets `permission_denied` ("Chrome native host must run as the
    configured owner.").
  - Check 5 needed no change: it installs every entry of `user-mcp.json`, now with `chrome`, and requires `claude mcp
    list` to show each one connected.
  - Check 6: the session's first model request must offer every shipped Chrome tool (`mcp__chrome__<name>` for all
    30), with tool search off; the summary records the offered tools per server (`tools_offered`).
  - New `control-storage-tests` (`CONTROL_STORAGE_TESTS_PASS {summary}`), last before the restart: main's handoff
    rule. The layer carries `control/chrome_tests/*.py` and `control/mail_tests/storage_faults.py` only; the action
    copies them to `/var/tmp/aresos-ci-storage/control/` (`test_engine.py` keeps scratch in `<root>/.work`), and runs
    `/usr/bin/python3 -B -m unittest -v test_full_disk_reads test_open_index_timing` as `ares` with
    `PYTHONPATH=<tests>:/usr/libexec/aresos-control:/usr/lib/aresos-control/vendor`, so the **installed**
    `aresos_control` runs on the image's own Python and SQLite (a probe first requires `aresos_control.__file__` to be
    the installed one and records Python's and SQLite's versions; the timing test's `step7-timing` line goes into the
    summary). Locally the same layout against a `control-tree` copy: 11 tests OK in 22 s, Python 3.14.8, SQLite 3.51.2.
- `os/README.md`: the paragraph names Chrome's two startup files and what 18c-b adds.
- Time limits (`4cf908a2`, own commit, `rebind.py pending`): the Control VM pass step from 10 to 12 minutes and the
  job's control limit from 125 to 127, before the first run, from an estimate (the pass took 6 min 13 s to 6 min 54 s;
  Chrome adds the storage tests, about 30 s on the laptop, and a few seconds of checks). Confirmed against the
  measured pass below.

### Decisions the code doesn't show (JUDGMENT-CALLs for the report)

15. **No excluded-sites file in 18c.** The merged service starts and answers without
    `/etc/aresos/control/chrome-excluded-sites.json` (it is read only once a browser is connected), and the brief puts
    it in Part C with the rest of the browser side. So 18c ships no file under `/etc/aresos/`; 18c-b adds it (root,
    0640, the service's group, `{"format":1,"hosts":[]}`). Changing later: one `FILES`-like entry with a group, which
    the map doesn't support yet (everything it installs is root:root).
16. **The storage tests run against the installed `aresos_control`**, not a copy of the checkout's, as `ares`, with the
    service's import path; only the test modules come into the layer. Alternative: run the whole Python suite in the
    guest (main's handoff says "the normal Python suite"; this step's brief names the two tests).
17. **`build-id.json`'s bytes** are `{"build":"<hash>"}` and a newline, the README's form; `control/ci/setup.sh` writes
    `{"build": "<hash>"}` without one. The adapter reads only the key.
18. **The time limit was raised before the first run** (an estimate, checked against the measured pass), so the two
    greens fall on one head within this step's budget of three runs.

### PLAN-GAPs (Chrome follow-up)

6. Main's Chrome CI image (`control/chrome/ci/Dockerfile`, out of reach) still makes `/etc/aresos-control`; nothing
   there reads it (its service gets its config in-process), so it is harmless, but the brief's list of places for the
   moved config path named it.

### Findings for the lead (Chrome follow-up; `control/aresos_control/` is out of reach, nothing changed there)

- **A session started while the service is down never gets the AresOS tools, also after the service is back.** Run
  43669126392, `control/ordinary/failed-fresh-session.tar.gz` (`model/requests.json`): with the service failed at
  the session's start, every request of turns 4 and 5 offered the same tools (Claude Code's 25 and his own `notes`,
  digest `c768872a…`, 71,309 bytes), also turn 5 after the service recovered. Our proxies don't connect without the
  service, and Claude Code doesn't retry them during the session. For the owner: after a service failure his open
  Claude Code sessions stay without `chrome`, `mail` and `control` until he restarts them (or reconnects with
  `/mcp`, not tried). Worth a line in his guide or in the service-down notice of #254.
- **The first request of every session goes out before our MCP servers have connected** (run 43669126392, all five
  sessions with a request record): request 1 carried only Claude Code's tools and `notes` (his stdlib server, fast);
  our servers' tools arrive from the second or third request on (digest `5f5a32aa…`, 136,504 bytes, the same in
  checks 6, 7 and 9). A first prompt given on the command line, as the checks do, is answered without our tools; typed
  by hand a few seconds later it most likely has them. The proxies' start-up (the MCP SDK's import under
  `python3 -I -S`) is the likely cost; not measured.
- Chrome added nothing to the idle cost (below): the adapter's minute maintenance returns at once without a browser.

### Runs (Chrome follow-up; budget 3 `check_build=control`)

- **run 43669126392** (`control`, head `4cf908a2`; build step 02:48:03 to 02:58:48 = 10 min 45 s, Control VM step
  02:58:48 to 03:05:08 = 6 min 20 s, the pass 379.2 s from QEMU's start): failure, one check, the new assertion of
  check 6 (the first request carried no Chrome tools; see the finding above, fixed in `3c7c3c66` by reading the
  session's last request). Every other line green: `CLAUDE_CODE_PINNED 2.1.319 …`, `CONTROL_CHROME_BUILD
  966c27379ac28abafe17c8017059186d847e75fb6048e4cbea7307b13abc4352`, `CONTROL_INSTALLED 73 files, 28 wheels, 2024
  vendored paths from 4cf908a2…`, `CONTROL_CHROME_STARTUP_FILES build 966c2737…4352, 0 qualification entries`,
  `CONTROL_GENERATED_MATCH 15 files`, image check "Control: every file, folder and vendored path control.json records
  is in the image as recorded …", `CHECK_BUILD_PASSED`, `CONTROL_IMAGE_FILES_PASS`, `CONTROL_ETC_CLAUDE_CODE_PASS`,
  `CONTROL_RELEASE_CHECKS_PASS`, `CONTROL_IDLE_FOOTPRINT_RECORDED`, `CONTROL_FIXTURES_REACHABLE`,
  `CONTROL_ENTRY_POINTS_PASS`, `CONTROL_PRECONDITION_PASS`, `CONTROL_USER_MCP_INSTALL_PASS`,
  `CONTROL_SERVICE_SANDBOX_PASS`, `CONTROL_MAIL_FLOWS_PASS`, `CONTROL_PERMISSION_REQUEST_RECORDED
  {"normal-permission-user": {"hook_calls": 1, "owner_answers": 0, "prompt_shown": false, "send_arrivals": 1}}` (the
  flash not caught this time: timing dependent, recorded, not pinned), `CONTROL_INTERACTIVE_ASK_PASS`,
  `CONTROL_PASSWORDS_PRIVATE_PASS`, `CONTROL_SELINUX_AFTER_CHECKS_PASS`, `CONTROL_STORAGE_TESTS_PASS`,
  `CONTROL_SERVICE_RESTART_PASS`, `CONTROL_VM_POWEROFF_CLEAN`.
  - Chrome in check 3: `aresos-mcp chrome` served `aresos-chrome` 0.1.0, protocol `2025-06-18`, 30 tools equal to
    `generated/` (no keys beyond them; `mail` 28, `control` 4); `tools/call tabs` answered in 0.01 s with
    `isError: true`, `chrome_unavailable` "Chrome is not connected; start normal Chrome with the installed
    extension."; the CLI the same; another user on `chrome.sock`: `permission_denied` "Chrome native host must run as
    the configured owner.". Check 5: `chrome` installed from `user-mcp.json` and "✔ Connected" beside `control`,
    `mail`, `notes`, `testapp`.
  - Check 2: `act.sock` 0666, `admin.sock` 0600, `chrome.sock` 0666, all 250:250, folder 0711.
  - Idle footprint with Chrome (60 s, one process, one thread): `memory.current` 33,218,560 B (peak 33,480,704), anon
    23,969,792 B, RSS 37,164 KiB, PSS 25,328 KiB, swap 0; 602 switches = **10.0 wake-ups/s**; CPU 256 ms =
    **0.43 %** of one CPU (without Chrome: 31.9 to 32.3 MB, 10.0 to 12.5/s, 0.35 to 1.62 %).
  - Storage tests in the guest: **Python 3.14.8, SQLite 3.51.2** (`/usr/lib64/python3.14/sqlite3`), the installed
    `aresos_control`, 11 tests OK in 27.8 s; `step7-timing` at 4,000 operations: indexed shapes 0.005 ms against scans
    of 19 to 63 ms, a Chrome read's service time 4.09 ms median (ceiling 35), `engine_pending` 52.3 ms.
  - Times (s): boot to channel 26.8, files 3.6, idle 60.0, entry points 3.9, user MCP 4.8, check 6 108.7, check 7
    32.4, check 9 104.7, storage tests 27.9, restart 1.3.

- **run 43671243430 attempt 1** (`control`, head `3c7c3c66`; job 03:13:38 to 04:09:36; tools 03:15:46 to 03:17:57,
  build step 03:18:04 to 04:01:31 = 43 min 27 s, Control VM step 04:01:31 to 04:09:31 = **8 min 0 s**, the pass 478.8 s
  from QEMU's start): **success**, every line in this order: `CLAUDE_CODE_PINNED 2.1.319 sha512-FO4Sd23B…oOQ==
  dabafec8…8eed`, `CONTROL_CHROME_BUILD 966c27379ac28abafe17c8017059186d847e75fb6048e4cbea7307b13abc4352`,
  `CONTROL_INSTALLED 73 files, 28 wheels, 2024 vendored paths from 3c7c3c66…`, `CONTROL_CHROME_STARTUP_FILES build
  966c2737…4352, 0 qualification entries`, `CONTROL_GENERATED_MATCH 15 files`, `CONTROL_FILES_RECORDED 73 files, 2024
  vendored paths, 28 wheels from 3c7c3c66…`, `CHECK_BUILD_PASSED`, `CHECK_BUILD_CONTROL_DISK_READY`,
  `CONTROL_IMAGE_FILES_PASS`, `CONTROL_ETC_CLAUDE_CODE_PASS`, `CONTROL_RELEASE_CHECKS_PASS`,
  `CONTROL_IDLE_FOOTPRINT_RECORDED {…}`, `CONTROL_FIXTURES_REACHABLE`, `CONTROL_ENTRY_POINTS_PASS`,
  `CONTROL_PRECONDITION_PASS`, `CONTROL_USER_MCP_INSTALL_PASS`, `CONTROL_SERVICE_SANDBOX_PASS`,
  `CONTROL_ORDINARY_SESSION_PASS {…}`, `CONTROL_MAIL_FLOWS_PASS`, `CONTROL_PERMISSION_REQUEST_RECORDED
  {"normal-permission-user": {"hook_calls": 1, "owner_answers": 0, "prompt_shown": false, "send_arrivals": 1}}`,
  `CONTROL_INTERACTIVE_ASK_PASS`, `CONTROL_PASSWORDS_PRIVATE_PASS`, `CONTROL_SELINUX_AFTER_CHECKS_PASS`,
  `CONTROL_STORAGE_TESTS_PASS {…}`, `CONTROL_SERVICE_RESTART_PASS`, `CONTROL_VM_POWEROFF_CLEAN`,
  `CHECK_BUILD_CONTROL_PASSED`; the fixture stop step green.
  - Chrome in check 3 and 2: as in run 43669126392 (30 tools equal to `generated/`, `tabs` refused
    `chrome_unavailable` in 0.01 s by MCP and CLI, another user `permission_denied` on `chrome.sock`; `chrome.sock`
    0666 250:250).
  - Check 6: the tools per request of the first session: requests 1 and 2 (turn 1) Claude Code's 25 and `notes` 1;
    from request 3 on also `chrome` 30, `control` 4, `mail` 28, `testapp` 13. The turns as in step 2c: model requests
    2, 3, 2, 3, 2; Stop continuations 0, 1, 0, 1, 0; his tool ran in every turn; his Stop hook once per turn (on the
    attempt that ends it).
  - Idle footprint with Chrome: `memory.current` 32,903,168 B (peak 33,689,600), RSS 36,852 KiB, PSS 25,224 KiB, swap
    0; 622 switches in 60 s = **10.4 wake-ups/s**; CPU 793.4 ms = **1.32 %** of one CPU.
  - Storage tests: Python 3.14.8, SQLite 3.51.2, the installed `aresos_control`, 11 tests OK in **60.2 s** (27.8 s in
    run 43669126392: the runner's speed).
  - Times (s): boot to channel 50.4, files 5.0, idle 60.3, entry points 5.0, precondition 2.2, user MCP 12.2, check 6
    112.6, check 7 41.5, check 9 123.2, storage tests 60.3, restart 1.9.
- **run 43671243430 attempt 2** (`gh run rerun`, head `3c7c3c66`; job 04:12:40 to 04:33:34; tools 04:14:19 to
  04:16:16, build step 04:16:21 to 04:27:07 = 10 min 46 s, Control VM step 04:27:07 to 04:33:31 = 6 min 24 s, the pass
  383.9 s): **success**, the same lines as attempt 1 in the same order, with the same
  `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1, "owner_answers": 0,
  "prompt_shown": false, "send_arrivals": 1}}`; check 6 the same numbers (2, 3, 2, 3, 2 model requests; 0, 1, 0, 1, 0
  continuations; his Stop hook once per turn) and the same tools per request (our servers from request 3 on); idle
  33,161,216 B, 600 switches in 60 s = **10.0 wake-ups/s**, 248.2 ms = **0.41 %** of one CPU; storage tests 11 OK in
  28.8 s on Python 3.14.8 and SQLite 3.51.2; the fixture stop step green. Times (s): boot to channel 29.4, check 6
  108.6, check 7 32.4, check 9 105.4, storage tests 28.8.
- **run 43675804962** (`build`, head `3c7c3c66`; job 04:33:37 to 05:17:33 = 43 min 56 s, build step 04:37:06 to
  05:17:28 = 40 min 22 s, the Control VM step skipped as it should be in this mode): **success**,
  `CONTROL_CHROME_BUILD 966c2737…4352`, `CONTROL_INSTALLED 73 files, 28 wheels, 2024 vendored paths from 3c7c3c66…`,
  `CONTROL_CHROME_STARTUP_FILES build 966c2737…4352, 0 qualification entries`, `CONTROL_GENERATED_MATCH 15 files`,
  `CONTROL_FILES_RECORDED 73 files, 2024 vendored paths, 28 wheels from 3c7c3c66…`, `CHECK_BUILD_PASSED`,
  `CHECK_BUILD_VM_PASSED` (the policy VM pass sees the image with Chrome's files).
- **The time limit:** the Control VM step took 6 min 20 s (run 43669126392) and 8 min 0 s (run 43671243430); the
  12 minutes set in `4cf908a2` are 1.5 times the slower one. The old 10 would have been 1.25 times it: the raise was
  needed.
- PR #58's own workflows on `3c7c3c66`: Control base, boundary and Mail green; **Control Chrome** failed `latency
  (audit)` (main's known p95 tail, board #276) and `fixtures (policy, recheck2)` with its `aggregate (policy)`:
  "GROUP 8 closing or releasing an opener ends popup control and clears badges FAIL Error: opener badge before close:
  undefined" (run 43671248371, job 132684122631), a browser-timing case. Not this branch's: `3c7c3c66` changes only
  `os/` against `4cf908a2`, whose Control Chrome run 43669130757 passed every job. Noted, not fixed (`control/chrome/`
  is out of reach).

- **What ran locally** (quick tests only): `os/tests` `test_control_image.py` and `test_control_vm.py` (27 run, OK),
  `test_checkout_sources.py` (6), `test_owner_equality.py` (10), `test_owner_path.py` (47), `test_owner_step_limits.py`
  (4), `test_ways_back_probe.py` (57), all OK after the merge (they read the pending list); `test_ways_back_model.py`
  did not finish within 10 minutes on the laptop (a heavy model run, untouched here; the checks-only job runs it). The
  two storage tests against a `control-tree` copy: 11 OK.
- **Done:** `check_build=control` green twice on the final head `3c7c3c66` (run 43671243430, attempts 1 and 2) and
  `check_build=build` green once on it (run 43675804962). Only this file changed after `3c7c3c66`. **Runs used:** 2 of
  3 `check_build=control` (43669126392, 43671243430 with its rerun as the second green) and 1 `check_build=build`. In
  the whole package: 1 resolve, 4 build, 10 control (2a 2, 2b 2, 2c 3 with its rerun, this step 3 with its rerun).

### For the report: Chrome follow-up (append to `reviews/18c-image-test/REPORT.md`)

**Done.** `main` with the Chrome tool (PR #27) merged into the branch. The image now carries what the merged service
needs to start with its Chrome adapter, and nothing of the browser side: `chrome/qualification.json` (the shipped,
empty baseline: conservative mode) and `chrome/build-id.json` (the hash `control/chrome/build.py` computes over
`control/` of the build commit; without it the adapter would run `build.py`, which the image doesn't carry, and the
service would not start). Both are in `control.json`, checked in the image and against the checkout like every
other file; the build prints the hash for `control/chrome/builds.json`. The VM test's socket modes now come from the
merged `daemon.py` (`chrome.sock` 0666, pinned by a static test that reads `daemon.py`), and its checks cover Chrome
as far as no browser is needed. Chrome's storage plan and timing tests ran on the image's own Python and SQLite.

**Verified** (**run**, head `3c7c3c66`, run 43671243430 attempts 1 and 2, `check_build=build` run 43675804962):
`CONTROL_CHROME_BUILD 966c2737…4352` and `CONTROL_CHROME_STARTUP_FILES … 0 qualification entries` at build; check 1
with the two files; check 2 with `chrome.sock` 0666 `aresos-tools`; check 3: `aresos-mcp chrome` serves exactly the
30 generated tools and instructions, a read with no browser is a clear refusal (`chrome_unavailable` "Chrome is not
connected; start normal Chrome with the installed extension.", 0.01 s, MCP and CLI), another user is refused on
`chrome.sock`; check 5: the `chrome` entry installed from `user-mcp.json` and connected; check 6: his session offers
all 30 Chrome tools once the servers are up; `CONTROL_STORAGE_TESTS_PASS`: 11 tests on **Python 3.14.8 and SQLite
3.51.2** against the installed code (CI had 3.45.1, the Mac 3.50.4). Every earlier B2 line stays green.

**Idle footprint with Chrome** (60 s, nothing using the service): 32.9 to 33.2 MB, 10.0 to 10.4 wake-ups a second,
0.43 to 1.32 % of one CPU: the same as without Chrome.

**Not verified** (18c-b): everything that needs the extension, the native host or a real Chrome (the list below).

**Findings for the owner's picture:** the first request of a session may go out before our tools are connected (a
prompt typed at once may not see them). The other finding of this step, a session started while the service is down
staying without our tools until it is restarted, is fixed by 18e (item 7) and proven in check 6 (run 43687234953).

**Measured time:** the Control VM pass 6 min 20 s and 8 min 0 s (the step's limit now 12 minutes, about 1.5 times the
slower); the build to the disk 10 min 45 s to 43 min 27 s (the runner's cache and speed).

### For 18c-b (the Chrome lines of B2 that need the browser side)

- The extension, its policy (force-install, toolbar pin), the native host manifest and launcher, the excluded-sites
  file, the polkit action and `/usr/bin/pkcheck`, and `gh`, each in the install map and `control.json` with its image
  check.
- In the VM: the native host reaches `chrome.sock` as `ares` (this step proves only the socket's mode and that another
  user is refused); Chrome's asking tools ask through B's interactive driver; a read with a browser connected (today
  only the `chrome_unavailable` refusal); "Allow editing" through his real polkit agent; the daily record refresh
  once under the real unit as `aresos-tools` (`gh attestation verify` in the sandbox, its cache under
  `/var/lib/aresos-tools`), the "refused, held record retained" path and an offline bundle verification.
- Test group 12 in 18d's container harness.

## 18e in the VM pass (2026-11-15)

Built by a Claude agent on Opus 5.5. Commits `86ad8e12` (merge of `origin/pkg/18e-service-fixes` at `13e9e1e4`, PR
#69; 18e is cut from main `c746075d`, so main came up to that base too), `9ee1fbdf` (the VM pass takes in 18e).
**When 18e merges to main, this branch merges `origin/main` again** (a merge commit, as before).

### Done

- **Merge** (`86ad8e12`, no conflicts): 18e changes only `control/` (the client's connect wait and
  `service_unavailable`, the admin hint, the deadline loop, the unit's start limit, the refusal text, `usage.py`'s marks,
  the proxy's own catalogue without the service) and its brief and PROGRESS.md; main between the two bases changed
  only `STATE.md`.
- **What the merge made stale:** nothing in the image build. The image check pins the unit by its bytes through
  `control.json` (the hash `build.sh control-tree` makes from the checkout), so 18e's three `[Unit]` lines follow
  without a change; no test in `os/tests` held the unit's text or hash. The VM's own pin of the unit is check 2's
  `systemctl show` table (`SANDBOX`): it now also requires `StartLimitIntervalUSec=30s` and `StartLimitBurst=5`.
  `control.json`, the manifest list and `pending-rebind.json` are unchanged (the workflow's bytes didn't change).
- `os/ci/control/actions.py`:
  - **Check 6 rebuilt** for "quiet unless used" (the plan is data, `ORDINARY_TURNS`; 11 turns in 2 sessions, his own
    MCP tool and hooks beside ours throughout):
    - session `used-later`: turn 1 healthy; `systemctl stop`; turn 2 (never used: quiet, 2 model requests);
      start; turn 3 prepares and sends (`testapp prepare_send`, the managed ask answered Yes, `done`): the session has
      used the tools; stop; turn 4 exactly one notice; turns 5 and 6 still stopped: none; start; turn 7 clean; stop;
      turn 8 exactly one notice again.
    - session `failed-fresh-session`: the drop-in sets only `ExecStartPre=/usr/bin/false` (**`Restart=no` dropped**);
      after `systemctl start` the unit must stay `failed` with `Result=start-limit-hit` (or `exit-code`), `NRestarts`
      ≤ 5, within 20 s; a fresh session: turn 9 his tool (quiet), turn 10 `testapp list` answers `service_unavailable`
      (quiet), recovery, turn 11 `testapp list` answers `ok` in the same session.
    - per turn: model requests, Stop continuations, the notice in the continuation's text
      (`continuation_tails`) and on screen, never "Service connection lost" or `operation_status` in a hook line or a
      continuation, his tool and his hooks as before; turns of his own tool show nothing of ours.
    - the marks (`/run/user/<uid>/aresos-control/used/`): none before use; after turn 3 exactly
      `<pid>-<start>` of the running Claude Code (found independently: the top process of the claude binary, its start
      from `/proc/<pid>/stat` field 22), an empty file 0600 of `ares`, both folders 0700 of `ares`; `<key>.told` there
      before turns 5 and 6, gone before turn 8 (turn 7's hooks reached the service), there again after turn 8; the
      fresh session never marked.
    - the probes: with the service stopped `aresos control pending` answers `service_unavailable` ("not running",
      "nothing was sent") after 2.5 to 10 s; the managed `UserPromptSubmit` and `Stop` commands, run exactly as Claude
      Code runs them (`sh -c`, as `ares`, an unmarked caller), exit 0, print nothing and end in under 1.5 s; right after
      each `systemctl start` (turns 3, 7, 11) the first call answers `ok` (no transport error).
    - `/run/user/<uid>`: see JUDGMENT-CALL 19.
  - Check 2: the start limit in the `systemctl show` table. Check 3: `aresos admin …` as `ares` is
    `permission_denied` "Admin commands need sudo: run sudo aresos admin testapp fixture_configure (same options).",
    nothing about a password on stderr. Check 7: the outside-folder refusal is exactly `file_refused` "Path is outside
    the allowed folders; choose ~/Documents or ~/Downloads.". The idle check (change 14) now fails above one
    wake-up a second or with more than one process or thread. The restart check: no miss before the first answer.
- `os/ci/control/sessions.py`: a turn that another turn of the same session follows settles in 10 s
  (`SETTLE_NEXT`); a session's last turn keeps 20 s (JUDGMENT-CALL 20). Each turn records `active_seconds` (start to
  its last model request) and `continuation_tails` (the newest user text of each Stop continuation).
- `os/tests/test_control_vm.py` (`ServiceFixesTest`, 4 tests, and one in `EvidencePackingTest`): the start limit
  check 2 expects is the unit's; the admin hint is `cli.py`'s text; the refusal is `FilePolicy`'s for `build.sh`'s
  `FOLDERS`; the drop-in sets no `Restart=`; check 6's prompts are unique substrings; the continuation tail.

### Decisions the code doesn't show (JUDGMENT-CALLs for the report)

19. **`/run/user/<uid>` in the VM.** Fedora's `runuser` PAM stack has no `pam_systemd` (read on the laptop's own
    Fedora 44 base), so the checks' sessions open no logind session. The image's greetd logs `ares` in
    (`initial_session`), which makes the folder. Check 6 uses it when it exists and records `loginctl`'s view; only if
    it is missing does it enable lingering for `ares` (CI only, the throwaway guest) and wait for the folder. The run
    records which way it went (`runtime.existed`, `runtime.linger_enabled`): in both runs the folder existed
    (greetd's session on tty1, `Linger=no`), so lingering was never used.
20. **Settling 10 s between turns.** 18e's hooks make one connect attempt and end at once (check 6 now times them:
    under 1.5 s required); a continuation later than 10 s would be counted in the next turn and fail it, so the shorter
    window can't hide one. A session's last turn keeps 20 s (the hook's 15 s timeout and a margin), since nothing after
    it would catch a late one; checks 7 and 9 (one turn per session) are unchanged.
21. **The used turn sends for real** (a fixture send through the managed ask, answered Yes) instead of only
    preparing: a preparation alone leaves a reserved operation, which with the service up adds the held-work reminder
    to that turn and to every later turn with the service up. The send's result names its operation too.
22. **The fresh session's first turn calls his tool, not ours:** the first request of a session goes out before our
    servers connect (Chrome follow-up finding), and with the service down a proxy waits 3 s before offering its own
    catalogue. Our tool is called from its second turn on.

### PLAN-GAPs (this step)

7. 18e's assertion "after logout the mark is gone" is not checked: the guest's only login is greetd's session (or
   lingering), and ending it would end more than this check.

### Findings for the lead (this step; `control/aresos_control/` is out of reach, nothing changed there)

- **None in 18e's code.** Every assertion of 18e's "For 18c's next VM pass" (checks 1 to 11, except the logout part of
  2, PLAN-GAP 7) held under the real unit in both control runs.
- The failed state ends with `Result=exit-code`, not `start-limit-hit` (both runs: `NRestarts=5`, failed 10.2 s after
  `systemctl start`, then held). 18e allowed either; systemd keeps the last start's result when the limit refuses the
  next automatic restart. Worth a line if the README names `start-limit-hit`.
- `control/` changed, so the Chrome build hash changed: `CONTROL_CHROME_BUILD
  ccd0fd79190f492dbb0ca9889a288c0c004e0d46da3458e0f4446c80b5f5ce15` (was `966c2737…4352`), for
  `control/chrome/builds.json` when the lead records it. The image now installs 74 files (18e's `usage.py`).

### Runs (this step; budget 3 `check_build=control`)

- **run 43687234953 attempt 1** (`control`, head `9ee1fbdf`; job 06:50:17 to 07:45:50; tools 06:51:35 to 06:54:59, build
  step 06:55:04 to 07:37:55 = 42 min 51 s, **Control VM step 07:37:55 to 07:45:45 = 7 min 50 s** against its 12-minute
  limit, the pass 470.2 s): **success**, every line in this order: `CLAUDE_CODE_PINNED 2.1.319 sha512-FO4Sd23B…oOQ==
  dabafec8…8eed`, `CONTROL_CHROME_BUILD ccd0fd79…ce15`, `CONTROL_INSTALLED 74 files, 28 wheels, 2024 vendored paths
  from 9ee1fbdf…`, `CONTROL_CHROME_STARTUP_FILES`, `CONTROL_GENERATED_MATCH 15 files`, `CONTROL_FILES_RECORDED`,
  `CHECK_BUILD_PASSED`, `CHECK_BUILD_CONTROL_DISK_READY`, `CONTROL_IMAGE_FILES_PASS`, `CONTROL_ETC_CLAUDE_CODE_PASS`,
  `CONTROL_RELEASE_CHECKS_PASS`, `CONTROL_IDLE_FOOTPRINT_RECORDED {…}`, `CONTROL_FIXTURES_REACHABLE`,
  `CONTROL_ENTRY_POINTS_PASS`, `CONTROL_PRECONDITION_PASS`, `CONTROL_USER_MCP_INSTALL_PASS`,
  `CONTROL_SERVICE_SANDBOX_PASS`, `CONTROL_ORDINARY_SESSION_PASS {…}`, `CONTROL_MAIL_FLOWS_PASS`,
  `CONTROL_PERMISSION_REQUEST_RECORDED {"normal-permission-user": {"hook_calls": 1, "owner_answers": 0,
  "prompt_shown": false, "send_arrivals": 1}}`, `CONTROL_INTERACTIVE_ASK_PASS`, `CONTROL_PASSWORDS_PRIVATE_PASS`,
  `CONTROL_SELINUX_AFTER_CHECKS_PASS`, `CONTROL_STORAGE_TESTS_PASS {…}`, `CONTROL_SERVICE_RESTART_PASS`,
  `CONTROL_VM_POWEROFF_CLEAN`, `CHECK_BUILD_CONTROL_PASSED`; the fixture stop step green (GreenMail's log 1 redaction).
  Times (s): boot to channel 42.3, files 4.6, idle 59.5, entry points 4.0, precondition 1.9, user MCP 8.9, **check 6
  165.6** (was 108.6 to 112.6 with 5 turns), check 7 34.6, check 9 109.7, storage tests 34.5, restart 0.9.
  - Check 3: `ares_admin_cli` `permission_denied` "Admin commands need sudo: run sudo aresos admin testapp
    fixture_configure (same options).". Check 7: `outside_refused` `file_refused` "Path is outside the allowed folders;
    choose ~/Documents or ~/Downloads.". Restart: `calls_before_the_sockets_answered: []`, `NRestarts` 0.
- **run 43687234953 attempt 2** (`gh run rerun`, head `9ee1fbdf`; job 07:51:38 to 08:19:22; build step 08:01:42 to
  08:12:10 = 10 min 28 s, **Control VM step 08:12:10 to 08:19:19 = 7 min 9 s**, the pass 428.8 s): **success**, the
  same lines in the same order, the same `CONTROL_PERMISSION_REQUEST_RECORDED`; check 6 the same numbers (below) in
  163.1 s; idle 1 switch in 60 s. Times (s): boot to channel 26.1, check 6 163.1, check 7 32.0, check 9 104.4, storage
  tests 27.2.
- **run 43691820743** (`build`, head `9ee1fbdf`; job 08:19:25 to 09:06:21 = 46 min 56 s, build step 08:28:38 to 09:06:18
  = 37 min 40 s, the Control VM step skipped as it should be): **success**, `CONTROL_CHROME_BUILD ccd0fd79…ce15`,
  `CONTROL_INSTALLED 74 files, 28 wheels, 2024 vendored paths from 9ee1fbdf…`, `CONTROL_CHROME_STARTUP_FILES build
  ccd0fd79…ce15, 0 qualification entries`, `CONTROL_GENERATED_MATCH 15 files`, `CONTROL_FILES_RECORDED 74 files, 2024
  vendored paths, 28 wheels from 9ee1fbdf…`, `CHECK_BUILD_PASSED`, `CHECK_BUILD_VM_PASSED`.
- PR #58's own workflows on `9ee1fbdf`: Control base, boundary, Mail, Chrome (with both latency gates), Chrome polkit
  and Chrome qualification all green.
- **The time limit:** the VM step took 7 min 50 s and 7 min 9 s; the 12 minutes stay (1.5 times the slower one).
  Check 6 grew by about 55 s; the shorter settle between turns (JUDGMENT-CALL 20) kept it from growing by about 140 s.
- **Done:** `check_build=control` green twice on the final head `9ee1fbdf` (run 43687234953, attempts 1 and 2) and
  `check_build=build` green once on it (run 43691820743). Only this file changed after `9ee1fbdf`. **Runs used:** 1 of 3
  `check_build=control` (with its rerun as the second green) and 1 `check_build=build`. In the whole package: 1
  resolve, 5 build, 12 control (with reruns).

### Check 6 in numbers (run 43687234953, attempts 1 and 2 alike)

Each turn his model double calls one tool and answers; "requests" are model requests, "active" the seconds from the
turn's start to its last request (the quiet window after it not counted).

| Turn | Session | Service | His model calls | Requests | Extra | Notice | His Stop hook | Active (s) |
|---|---|---|---|---|---|---|---|---|
| 1 | used later | healthy | his `note` | 2 | 0 | | once | 2.0 / 1.4 |
| 2 | used later | stopped, never used | his `note` | 2 | 0 | | once | 0.5 / 0.4 |
| 3 | used later | started again | `testapp prepare_send`, then `send` (asked, Yes, done) | 3 | 0 | | once | 2.2 / 2.0 |
| 4 | used later | stopped, used | his `note` | 3 | **1** | **one** | once (on the ending attempt) | 1.0 / 0.9 |
| 5 | used later | still stopped | his `note` | 2 | 0 | | once | 0.5 / 0.4 |
| 6 | used later | still stopped | his `note` | 2 | 0 | | once | 0.5 / 0.4 |
| 7 | used later | started again | his `note` | 2 | 0 | | once | 0.5 / 0.4 |
| 8 | used later | stopped again | his `note` | 3 | **1** | **one** | once (on the ending attempt) | 1.0 / 0.9 |
| 9 | fresh, started while failed | failed | his `note` | 2 | 0 | | once | 1.2 / 1.0 |
| 10 | fresh | still failed | `testapp list`: `service_unavailable` | 2 | 0 | | once | 3.5 / 3.4 |
| 11 | fresh | recovered | `testapp list`: `ok` | 2 | 0 | | once | 0.5 / 0.4 |

The notice, under the model's answer in turns 4 and 8:

```
● Ran 1 stop hook
  ⎿  Stop hook error: AresOS tools are not running. If you prepared or sent something with them in this session, its
  outcome is unknown: tell the owner, and don't repeat it.
```

In every other turn the only trace is Claude Code's own spinner text "running UserPromptSubmit hook" / "running Stop
hook" for a moment (his own hooks cause it too). Never "Service connection lost" or `operation_status`.

The probes, both runs: `/run/user/1001` existed (greetd's session on tty1; no lingering); the mark `<pid>-<start>` of the
running Claude Code appeared at turn 3 (empty, 0600, `ares`; both folders 0700), `.told` after turns 4 and 8 and gone
after turn 7; the fresh session was never marked. With the service stopped: `aresos control pending` answered
`service_unavailable` "The AresOS tool service is not running; nothing was sent. Try again later." after 3.24 s / 3.17
s; the managed `UserPromptSubmit` and `Stop` commands took 0.18 s / 0.12 s each, exit 0, no output. The first call
right after each `systemctl start` (turns 3, 7, 11) answered `ok` in 0.37 to 0.45 s. The failed state: 10.2 s after
`systemctl start`, `NRestarts=5`, `Result=exit-code`, held. The fresh session's requests offered our tools from its
third request on (`chrome` 30, `control` 4, `mail` 28, `testapp` 13), as the first session's did.

**Idle with 18e** (change 14, 60 s, nothing using the service, one process, one thread): **1 context switch in 60 s
(0.017 wake-ups a second), 1.8 ms of CPU (0.003 % of one CPU)**, `memory.current` 33,062,912 B / 32,968,704 B, RSS
37,080 KiB, PSS 25,336 KiB, swap 0. Before 18e: 10.0 to 12.5 wake-ups a second, 0.35 to 1.62 % of one CPU.

### For the report: 18e in the VM pass (append to `reviews/18c-image-test/REPORT.md`)

**Done.** The branch merged 18e (PR #69) and the Control VM pass proves its fixes under the real systemd: check 6
rebuilt for "quiet unless used", the failed state reached by the unit's own start limit (the CI drop-in no longer sets
`Restart=no`), the start limit in check 2's unit table, the admin hint in check 3, the refusal's folders in check 7,
the idle bound (at most one wake-up a second, one thread) in change 14, no missed call after a restart.

**Verified** (**run**, head `9ee1fbdf`, run 43687234953 attempts 1 and 2, `check_build=build` run 43691820743): every
PASS line of B2 and the Chrome follow-up, now with 18e's assertions; check 6's numbers above; idle 1 switch in 60 s.

**Not verified:** a real model's cost of the one extra reply. (The mark's removal at logout, PLAN-GAP 7, is verified
since fix round 1: `marks_after_logout: false` in run 43860663005.)

## Left, in order (after 18e in the VM pass)

**Superseded by "Left for part 2" in fix round 1, at the top.** Kept for the record.

1. When PR #69 (18e) merges to `main`: this branch merges `origin/main` again (a merge commit, never a rebase or a
   force-push). If 18e changes after `13e9e1e4` (its review), merge `origin/pkg/18e-service-fixes` again first and
   rerun `check_build=control` twice and `check_build=build` once on the new head.
2. The lead: assemble `reviews/18c-image-test/REPORT.md` (a Claude builder can't create that file name): Part A's
   section, "For the report: B2" (step 2c), "For the report: Chrome follow-up" and "For the report: 18e in the VM
   pass" (above), the JUDGMENT-CALLs (1 to 22) and the findings. Record the new Chrome build hash `ccd0fd79…ce15` in
   `control/chrome/builds.json` if the lead keeps that file per build.
3. The reviews (the lead's job): a package review and a high-stakes security review of the whole package.
4. `linux-aresos` reads the `os/` diff (agreed change 16): the section below is up to date.
5. The owner's yes to a release carrying Control (agreed change 10), with check 6's numbers (now "quiet unless used").
6. The last step deletes this file.

Lead, 2026-11-14 (after step 2c), kept for the record: the report is assembled once, by the lead, after the Chrome
follow-up and before the reviews (Codex from 2026-11-17).

## The `os/` diff for `linux-aresos`

Against `origin/main` (`5bb1500e`, merged in fix round 1 part 2 as `e00bf60f`); brought up to date in the Chrome
follow-up, after the 18e merge `86ad8e12` (2026-11-15; 18e changes only `control/`, nothing under `os/`), in fix round 1
(2026-11-16: CI-only files and `check-image.sh`, nothing in the image) and in its part 2 (the merge, the VM step's
limit, check 6's wording; nothing in the image). The lead's merge of `main` at `91487807` (`a1e7aad9`, 2026-11-16)
changed no file under `os/` or `.github/`: `main` changed none there since `5bb1500e`, so this diff stands against
`91487807` too. Fix round X1 (2026-11-17) changed CI-only files: `check-image.sh`, `os/ci/control/` (two new modules,
three changed files) and the two test modules; nothing in the image. Fix round X2 (2026-11-17) changed CI-only files
again (`os/ci/control/vendor_check.py`, `tree_scan.py`, `actions.py`, `evidence_scan.py` and the two test modules;
`check-image.sh` unchanged) and **merged `main` at `04aef030`** (`dcbb70dd`; packages 48, 50 and 51): this diff now
stands against `04aef030`. The merge's two conflicts were 18c's `os/ci/check-build.sh` (50's console keymap grep put in
the `build` branch) and the pending list (regenerated with `rebind.py pending`); `main`'s other `os/` changes merged
untouched (fix round X2, "The merge"). Fix round X3 (2026-11-17) changed CI-only files once more
(`os/ci/control/tree_scan.py`, `os/ci/control/actions.py` and `os/tests/test_control_vm.py`; nothing else under `os/`)
and **merged `main` at `3a5eea14`** (`537790a2`; packages 52, 46 and 79; no conflict, the pending list untouched): this
diff now stands against `3a5eea14`. That merge brought two `os/` files, both `main`'s and untouched:
`os/minecraft/desktop.lock.json` (package 52's pin by commit) and `os/tests/test_aresos_desktop.py` (package 46). Image
side first, then CI only.

Fix round X4 (`16bcc784`, 2026-11-17) changes only `os/ci/control/tree_scan.py` and
`os/tests/test_control_vm.py`: immediate registration of entries from partial/repeated/verification listings,
owner coverage for the names a refused listing already observed, and identity exceptions established from
mountinfo plus the portal constant. The ordinary second-listing heuristic is removed. Repeated identities cannot
be overwritten, and a failed inode lookup is a hard error. X3's records and descriptor reads remain. The VM test
module now has 62 tests (eight more); the three escape regressions and related cases fail behaviorally on X3.
No image, action, workflow or bound-file change in X4. `origin/main` at `58d2ae1b` has no newer `os/` changes and
was not merged; the diff below therefore still stands against the fetched main.

- `os/Containerfile`: the aresos stage copies `/source/control` from the existing source stage and runs `build.sh
  control` before `configure`; `FROM` lines and the other stages unchanged.
- `os/build.sh`: `source` also extracts `AresOS-<commit>/control`; new `control` mode (pip vendor, install map,
  manifest, self-checks) and `control-tree` (the map alone, for checks and tests). The map includes Chrome's two
  startup files in `/usr/libexec/aresos-control/chrome/` (`qualification.json` as shipped, `build-id.json` from
  `control/chrome/build.py` over `control/` of the commit; the build prints `CONTROL_CHROME_BUILD <hash>` and its
  self-check reads both with the installed code). `packages` and `configure` unchanged.
- `os/ci/image-checks.sh`: early not-at-build check for `aresos-tools`/250 and the two folders; a Control section at
  the end (files, managed files, unit policy, sysusers, tmpfiles, config, launcher, no fixture traces).
- `os/ci/check-image.sh`: a new block after the existing lock check: `control.json` equals what `build.sh control-tree`
  makes from the checkout, from `HEAD`; the recorded wheels are exactly the checkout's `control/requirements.lock`
  (its own strict parse, every SHA-256 one of the pins; fix round 1). Since fix round X1 a third block binds the
  vendored tree to those wheels: `os/ci/control/vendor_check.py` fetches the recorded wheels from PyPI (each with its
  recorded SHA-256) on the runner, then, in a `--network=none` container of the built image, derives the tree they
  install, compiles it with the build's command where the build did and requires the installed tree and its record
  to equal it (`CONTROL_VENDOR_FROM_WHEELS`). The release job reaches all of it too (`check-build.sh build`,
  `kind=release`).
- `os/ci/check-resolve.sh`: **unchanged** (equal to main's; `gh` moved to 18c-b).
- `os/README.md`: one paragraph on Control in the image (with Chrome's startup files).
- `os/tests/test_control_image.py` (15 tests, new; 6 since fix round X1; X2 adds the sibling cases to one) and `os/tests/test_aresos_desktop.py` (the source-stage test
  expects `control/` beside `mod/`, JUDGMENT-CALL 6).
- CI only, never in a release:
  - `.github/workflows/os-image.yml` (`check-build` job only, no new permission or secret): `check_build` gains
    `control`; the job's limit is `${{ inputs.check_build == 'control' && 131 || 120 }}`; two steps run only for
    `control`: "Control VM pass" (`check-build.sh control-pass`, `timeout-minutes: 16` since fix round 1 part 2;
    the first pass took 10 min 31 s) and an `always()` step stopping the fixture servers (`runner.sh stop`). The
    build step keeps its 80 minutes for every mode. Six commits, each its own (`1ee81d1b`, `0af04070`, `2d1ad22f`,
    `4cf908a2`, `284eb1bb`, and the lead's `69943d65`: the job's limit for `control` 127 → 131, so it can't cut a
    slow pass before the step's own 16), each recorded with `rebind.py pending`.
  - `os/manifest/ci/16/pending-rebind.json`: the workflow's bytes wait for the next rehearsal; after main's 22c
    rehearsal, and again after 22d's (fix round 1 part 2: main's list taken, then `rebind.py pending`), the merge
    re-recorded 18c's notes (those bindings don't include them). X2's merge: the branch's list, then `rebind.py
    pending` with `main`'s two new notes and the merge's, so the rows are `main`'s plus `os-image.yml`.
  - `os/ci/check-build.sh`: `control|build)` share the build; `control` starts the fixtures first, builds the Control
    layer after the CI layer and makes the disk from `localhost/aresos:control` (`CHECK_BUILD_CONTROL_DISK_READY`);
    new `control-pass` boots it with `control_vm.py` (`CHECK_BUILD_CONTROL_PASSED`). `build` mode unchanged: since
    the X2 merge it carries `main`'s console keymap grep (package 50) between the polkit grep and
    `CHECK_BUILD_VM_PASSED`, as on `main`.
  - `os/ci/overlay/checks.py`: the hook (agreed change 8): `layer_actions()` loads `actions.d/*.py` after the fixed
    actions; a layer adds actions, never replaces one.
  - `os/ci/control/` (new): `Containerfile` (the test layer `FROM localhost/aresos:vm`), `runner.sh` (fixture CA,
    GreenMail and Dovecot on the runner's loopback, Claude Code from the boundary's lock, the layer, the stop and
    password-leak check), `evidence_scan.py` (that check, also inside the evidence's archives; fix round 1; since
    X1 it fails on what it can't search: archives below its depth, damaged tars, formats it doesn't unpack; since
    X2 a tar is whatever tarfile reads, magic or not), `tree_scan.py` (X1: check 8's file search, which fails on
    whatever it can't read; since X2 also on runtime content that vanished unread, and root walks a FUSE mount first,
    its owner only where root is refused; since X3 one record per path it learns, each file opened once as a handle
    and held to the inode number its folder's listing gave it, no second try, and what root is refused in a FUSE
    mount stays an error until the owner's walk names that path as searched; X4 registers entries immediately,
    preserves partial and verification listings, and restricts numbering exceptions to mountinfo-backed mount
    points or the FUSE portal constant; the layer copies it), `vendor_check.py` (X1: Part A's vendor check above;
    since X2 it derives all of `/usr/lib/aresos-control`, so a sibling of `vendor/` fails),
    `control_vm.py` (boots the disk, runs the checks, prints the PASS lines), `actions.py` (the guest's checks; since
    fix round 1 check 6 also logs ares out of the throwaway guest and lets greetd's auto-login start the desktop again
    while the service has failed, and check 2 looks for network listeners; since part 2 check 6 requires 18e's merged
    held-work wording; since X3 check 8 hands the owner's walk the paths root was refused in a FUSE mount and keeps
    each refusal as an error until that path is named as searched), `sessions.py` (Claude Code sessions with
    B1's driver), `release_checks.py` (agreed change 12: the rehearsal's check actions), `own-mcp.py` and
    `own-hook.py` (his own server and hooks). The layer also
    carries `control/boundary/interactive_{driver,model}.py`, `control/ci/image/mail_flows.py` and, for the storage
    tests, `control/chrome_tests/*.py` and `control/mail_tests/storage_faults.py`.
  - `os/tests/test_control_vm.py` (62 tests, new; 11 since fix round X1; X2 replaced two and added four, and
    `LayerHookTest` copies `console_keymap.py` beside `checks.py` since the merge; X3 added six and changed the end of
    one; X4 adds eight and replaces the old numbering-heuristic test with mountinfo-backed cases).
- Not changed: base digest, `packages.lock.json`, Chrome pin, accounts, sudo, polkit, masks, session, PATH,
  repositories, `os/config/`, `os/policy/`, `os/release/`, `os/owner-tools/`, `os/manifest/` (except the pending
  list above), `ci/check-resolve.sh`, and every other job of `os-image.yml`.
