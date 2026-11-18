Codex gpt-6-astra, 2026-11-18.

Read `AGENTS.md`, the design and relevant brief, `RECHECK-X3.md`, its scratch notes/probes, PROGRESS’s “Fix round X4”, the complete diff, and the X2/X1 reviews. Reviewed `16bcc784`; HEAD `8063abac` changes only PROGRESS.

Ran the requested modules separately:

- `test_control_vm`: **62 tests; 61 passed, one sandbox error** creating an AF_INET socket. All **21 scanner tests passed**.
- `test_control_image`: **15 tests, OK**.
- `test_checkout_sources`: **8 tests, OK**.
- Python syntax compilation: **12 files, OK**.
- Current scanner tests against byte-verified X3 dependencies: **21 tests, seven behavioral failures**, matching the builder’s baseline.
- Adapted X3 probes: **7 passed**. Additional probes: **10 passed**, including assertions demonstrating the two limitations below.
- `git diff --stat 6c172793 16bcc784`: **two files, 291 insertions, 82 deletions**, confined to `os/ci/control/tree_scan.py` and `os/tests/test_control_vm.py`. Diff whitespace check passed.

| RECHECK-X3 finding | Closed? | Checked-in test proving closure |
|---|---|---|
| #1: names from partial or verification listings receive no record | **Yes, both routes.** | `test_partial_listing_refusal_discards_yielded_names`, `os/tests/test_control_vm.py:971`: observed file enters owner `cover`; omission fails and recovery succeeds. `test_second_listing_learns_a_new_name_then_discards_it`, `:945`: the late file is searched. Both fail behaviorally on X3. |
| #2: double rename authorizes a replacement on an ordinary filesystem | **Yes.** | `test_double_rename_fools_numbering_detection`, `os/tests/test_control_vm.py:909`: mismatch errors before another listing. `test_non_fuse_non_mount_point_numbering_mismatches_are_errors`, `:891`: ordinary, nested-non-FUSE, shifted and mixed numbering are rejected. Both fail behaviorally on X3. |

The copied X3 probes needed the new listing callback interface. The verification-listing probe also supplies modeled FUSE mount facts; its original constant-number setup without those facts now errors.

| Probe rerun | X4 result |
|---|---|
| Double rename with distinct real A/B inodes | Named identity error after one listing; replacement not credited. Actual final password assertion rejects. |
| Partial listing observes a file, then denies; file disappears before owner subprocess | File remains in `cover`; missing owner coverage errors. Final password assertion rejects. |
| Verification listing observes new `late.log` | Password found; five learned paths = three searched files + two listed directories. |
| Parent replaced by symlink after listing | Original held directory supplies children; original password found. |
| Harmless atomic rewrite | Named identity error. |
| Unsettled record | Named “learned and never read” error. |
| 510-directory depth | `RecursionError`; no successful incomplete answer. |

**Every observed name now creates or reuses an accounting obligation.** Registration precedes inode lookup at `os/ci/control/tree_scan.py:211`. Verification listings append new names to the same work list. Unfinished records become named errors, including records whose internal outcome remains unset.

Partial refusals preserve identified names for owner coverage at `tree_scan.py:186`. Missing identities stay errors. Owner coverage must settle each refused path; existing errors remain in `os/ci/control/actions.py:1547` and `:1552`.

The sibling fixes hold:

- Repeated names retain their first inode; changes error: `test_repeated_name_cannot_overwrite_its_first_observed_identity`, `os/tests/test_control_vm.py:1003`.
- Initial and repeated inode-lookup failures remain hard errors: tests at `:1025` and `:1055`.

Additional probes covered EIO/ENOENT, identity changes noticed after an earlier file was searched, repeated unchanged entries, partial-listing EIO, and partial verification denial followed by owner omission. None escaped accounting.

Mountinfo read/parse failures abort. Octal escapes, optional fields and component boundaries behaved correctly. With stable root paths and mounts, an ordinary mismatch requires either an exact recorded mount point or a deepest FUSE mount with the constant numbering convention. A nested non-FUSE mount blocks that FUSE exception. File bind-mount probes accepted the mounted file while rejecting its ordinary sibling. The parser uses the documented mountinfo fields. [Linux mountinfo documentation](https://www.man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html)

Two new findings:

1. **NIT — cached mount paths can excuse a replacement after coordinated root/file renames.**  
   `os/ci/control/tree_scan.py:162`, `:201`.

   Capture a mount at `R/state/debug.log`, then rename ancestor `R` aside and put an ordinary tree at `R`. Its listing observes password-bearing A; replace A with clean B before open. The cached mount pathname excuses the mismatch.

   My probe used real ancestor/A/B renames and modeled mountinfo moving with the ancestor. It produced empty errors and an accepted final password assertion. X3 rejected the corresponding single replacement. No actual mount was created.

   This needs coordinated hostile mutation inside the throwaway guest, so it is **NIT under the requested boundary**. It prevents an unconditional identity guarantee across every possible interleaving.

2. **NIT — an unmounted nested btrfs subvolume is now rejected.**  
   `os/ci/control/tree_scan.py:200`.

   A subvolume directory need not have its own mountinfo entry. Its listing can report the subvolume ID while its opened root has inode 256. X4 rejects that mismatch; my modeled case passed on X3. This matches the [btrfs directory-listing and root-lookup implementation](https://raw.githubusercontent.com/torvalds/linux/v6.17/fs/btrfs/inode.c).

   Separately mounted subvolumes receive the mount-point exception; scan roots themselves have no parent-listing comparison. I found no current B2 fixture creating an unmounted nested subvolume under these roots. Document/test this limitation before expanding the scanned trees.

**Ordinary VM operation:** I found no evidence that mount numbering makes flaky failure likely in the current trees. Both actual scans passed. X3’s benign rewrite/disappearance risk under `/run` and `/var/log` remains: an overlapping replacement deliberately fails coverage. Two passing runs do not establish a future failure rate.

I independently checked the hosted logs and matched the existing artifact ZIPs against GitHub’s SHA-256 digests:

- [44180217274](https://github.com/Ares-Empire/AresOS/actions/runs/44180217274): `16bcc784`, **1,772 tests, OK (skipped=4)**.
- [44184266040](https://github.com/Ares-Empire/AresOS/actions/runs/44184266040) and [44195810105](https://github.com/Ares-Empire/AresOS/actions/runs/44195810105): reported Control PASS markers and exact count sums confirmed. Both password artifacts have empty errors/vanished and one owner-covered portal refusal.
- [44199832455](https://github.com/Ares-Empire/AresOS/actions/runs/44199832455): `CONSOLE_KEYMAP_PASSED`, then `CHECK_BUILD_VM_PASSED`.

**Security:** X4 changes CI scanning and tests only. Nothing changes `SECURITY-REVIEW-X1.md`’s production SAFE judgment or its stated limits. The existing snapshot, inode-reuse, constant-number FUSE, equivalent-remount and depth limits also remain.

The reviewer's longer notes and reproducible evidence stayed in its scratch folder, `.work/recheck-x4/` (not committed). No tracked changes, prohibited commands, owner modules, commits or pushes. The pre-existing untracked review remains untouched; no `.work/` file exceeds 500 MB.

SAFE