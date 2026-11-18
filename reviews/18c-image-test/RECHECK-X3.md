Codex gpt-6-astra, 2026-11-17.

Read `AGENTS.md`, the X2 and X1 rechecks, both X1 reviews, PROGRESS’s “Fix round X3”, the design, relevant brief sections, `23bff734..537790a2`, and both merge-parent comparisons.

The reviewer's longer notes and reproducible probes stayed in its scratch folder, `.work/recheck-x3/` (not committed).

Ran the requested modules separately:

- `test_control_vm`: **54 tests; 53 passed, one sandbox error** creating an AF_INET socket. All 13 scanner tests passed.
- `test_control_image`: **15 tests, OK**.
- `test_checkout_sources`: **8 tests, OK**.
- Python syntax compilation: **12 files, OK**.
- Builder’s X2 baseline: **13 tests, 4 failures and 3 missing-interface errors**, matching its report. Verified the baseline helpers equal `fda41017`.
- Seven independent scratch probes, including the escapes below.
- Both requested diff stats, merge byte comparisons, and scoped diff checks.

Independently inspected the hosted Control, build and pre-merge checks_only logs. The merged checks_only run remained in progress when checked.

| RECHECK-X2 finding | Closed? | Test proving the original case |
|---|---|---|
| #1: replacement bytes substitute for content removed after stat | **Yes, for the reported race.** The broader identity guarantee still fails below. | `test_a_file_removed_and_replaced_once_the_scanner_has_stated_it_is_the_one_searched`, `os/tests/test_control_vm.py:762`: passes now; behaviorally fails on X2. X3 searches the original held file. |
| #2: owner fallback discards a known refused file | **Yes, for the reported omission.** A partial-listing variant remains below. | `test_what_root_is_refused_inside_a_fuse_mount_its_owner_must_search_path_by_path`, `os/tests/test_control_vm.py:1026`: passes now; X2 returns empty errors when the refused file disappears. |

The invariant holds **after a record exists**, but it does not hold for every observed name. `Scan.answer()` accounts for all existing records, including unset outcomes. However, some directory entries never reach `learn()`, and the numbering heuristic can mark a replacement file as searched. Consequently, perfectly summing counts do not establish complete coverage.

Root and owner errors are appended rather than replaced. Missing owner coverage, failed owner processes and unexpected refusal destinations fail. Exceptions escaping the action become failed checks. The final password assertion remains strict. Those protections cannot detect an omitted record or an incorrect identity decision.

| Race exercised | X3 result | Test |
|---|---|---|
| Listed file removed before open, including immediate recreation after ENOENT | Named error; replacement not retried | `test_runtime_content_that_vanishes_unread_fails_and_is_named`, `os/tests/test_control_vm.py:706` |
| Directory removed before open or as listing begins | Named error | Same test |
| File removed/recreated after descriptor stat | Original bytes searched; password found | `…once_the_scanner_has_stated_it…`, `:762` |
| Rename over a listed file; directory replaced by directory or symlink; file replaced by directory | Identity error | `test_what_is_put_under_a_listed_name_before_it_is_opened_is_never_searched_in_its_place`, `:780` |
| Parent directory replaced by a symlink after listing | Original directory handle still supplies children; password found | Scratch `test_parent_swapped_for_link_after_listing` |
| Constant/shifted listing numbers; original restored before second listing | Checked-in expectations pass | `test_a_listing_that_numbers_otherwise_is_asked_a_second_time`, `:844` |
| Original restored for second listing, then replacement restored before stat | **Silent escape** | Scratch `test_double_rename_fools_numbering_detection` |
| New password file returned by a verification listing | **Name discarded without a record** | Scratch `test_second_listing_learns_a_new_name_then_discards_it` |
| Listing yields a password-file name, then PermissionError; file disappears before owner fallback | **Known name lost and directory refusal cleared** | Scratch `test_partial_listing_refusal_discards_yielded_names` |
| Root-refused file disappears, changes identity or remains unreadable before owner walk | Errors retained | `…its_owner_must_search_path_by_path`, `:1026` |
| Harmless file atomically rewritten before open | Fails closed | Scratch `test_benign_atomic_rewrite_fails_closed` |

The scratch tests are in `.work/recheck-x3/probes.py`; outputs are in `.work/recheck-x3/probe-results.json`. Renames, removals, file contents and symlinks use real temporary filesystem objects. FUSE numbering, mountinfo and the partial readdir denial are simulated. Nothing was mounted or unmounted. Additional probes confirmed that an unset record becomes an error and 510 directory levels raise `RecursionError`.

The stricter replacement policy is reasonable for CI, but two passing runs do not establish freedom from intermittent failures. Known rewriters exist: logind replaces state under `/run/systemd/sessions` and `/run/systemd/users`, and journal rotation renames active files and creates replacements. [Systemd session implementation](https://github.com/systemd/systemd/blob/v259/src/login/logind-session.c), [user-state implementation](https://github.com/systemd/systemd/blob/v259/src/login/logind-user.c), [journal rotation documentation](https://www.freedesktop.org/software/systemd/man/257/journalctl.html).

The two short, successful VM scans support practical operation. They do not measure the likelihood of a benign rewrite overlapping the scan. Such an overlap should remain a named coverage failure; this review justifies no broad exemption.

The stated limits are acceptable for a bounded CI walk:

- Tmpfs and btrfs normally advance inode allocation within a mounted instance; that is not a universal guarantee across wraparound or remounts. The guest disk configuration specifies btrfs. [Tmpfs allocation](https://github.com/torvalds/linux/blob/master/mm/shmem.c), [btrfs allocation](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux.git/+/c17fdf62aeecbbaf2c2fd5c494e2089c02b0e75b/fs/btrfs/disk-io.c).
- The portal’s `0xffffffff` listing value is real and necessarily weakens listing-to-file identity. [Portal implementation](https://github.com/flatpak/xdg-desktop-portal/blob/main/document-portal/document-portal-fuse.c).
- A walk cannot establish a snapshot of changing contents or names never observed.
- Mountpoint/type/UID comparison cannot detect an equivalent unmount/remount.
- Excessive depth fails the action; “about 490” depends on the calling stack.

Neither finding below depends on inode reuse, remounting or a snapshot requirement.

The merge is consistent. X3’s own implementation changes are exactly the three claimed files. Main introduces the desktop metadata pin and test changes under `os/`; no workflow change enters through this merge. Unilateral files match their respective parents, and the shared desktop test retains both sides. `pending-rebind.json`, `evidence_scan.py` and `vendor_check.py` are byte-for-byte X2. HEAD adds only PROGRESS changes.

The hosted evidence is genuine:

- [44147238097](https://github.com/Ares-Empire/AresOS/actions/runs/44147238097) and [44152536778](https://github.com/Ares-Empire/AresOS/actions/runs/44152536778) identify `537790a2`, contain the reported PASS lines, and report 1851/1891 root-searched files with exactly summing record counts. Final evidence scans have no hits or unreadable archives.
- [44166220023](https://github.com/Ares-Empire/AresOS/actions/runs/44166220023) reaches `CONSOLE_KEYMAP_PASSED` and `CHECK_BUILD_VM_PASSED`.
- [44140465984](https://github.com/Ares-Empire/AresOS/actions/runs/44140465984) reports 1764 tests, OK, skipped=4, before the merge.

X3 does not change the production behavior judged SAFE by `SECURITY-REVIEW-X1`. Its stated limits remain, including bounded Stop JSON diagnostics, deployment checks for UID/GID 250 and unexercised auto mode. The findings concern CI coverage.

1. **SHOULD-FIX — observed names can disappear before accounting starts.**  
   `os/ci/control/tree_scan.py:125`, `:146`, `:203`; handover consequence at `os/ci/control/actions.py:1552`.

   `listing()` constructs its entire dictionary before creating records. If readdir yields `private.log` and then raises PermissionError, that observed name is discarded. Only the directory becomes REFUSED. If the file disappears before the owner walk, the owner can successfully list the directory and clear its refusal.

   My probe yielded a real DirEntry, injected the subsequent denial, removed the real password file and executed the actual owner scanner subprocess. Result: **errors `[]`, only the legitimate password hit**. The actual `passwords()` function returned **0** with unrelated permission/mode preconditions stubbed.

   A second route needs no listing failure: `numbered_otherwise()` calls `listing(folder).get(name)` and discards every other returned name. Under the documented constant-number convention, subsequent listings returned a newly created `late.log`, but it received no record: **learned 4, searched 2, listed 2, errors `[]`, no password hit for that file**.

   Register entries when observed, including partial and verification listings, and preserve their obligations through handover. Alternatively, fail the affected listing conservatively. Comparing existing counts cannot catch this.

2. **SHOULD-FIX — repeated listing numbers can authorize the wrong file on an ordinary filesystem.**  
   `os/ci/control/tree_scan.py:146`, `:148`, `:194`.

   Let A contain the password and B be clean, with distinct inode numbers:

   - First listing sees A at `debug.log`.
   - Move A aside and B into that name; the scanner opens B.
   - Restore A for the second listing; it reports A’s original number.
   - Restore B before the following stat; it matches the held B.

   Both conditions at line 148 pass. The scanner concludes that the directory numbers differently and searches B in A’s place.

   The probe performs these renames on real files without falsifying any inode/stat result. It returns **learned 5, listed 2, searched 3, errors `[]`, vanished `[]`, only the legitimate password hit**. The actual final password check returns **0** with unrelated preconditions stubbed.

   The checked-in test at `:844` restores A for the second listing but leaves A there for stat, so it misses the final switch. Ordinary-filesystem inode mismatches must remain errors; numbering exceptions need independently established filesystem or mount facts.

Only scratch files were written. Final `git status` shows no tracked change; the pre-existing untracked review remains untouched. No prohibited commands, owner modules, commits or pushes ran.

CHANGES-NEEDED