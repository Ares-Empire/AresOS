Codex gpt-6-astra, 2026-11-17.

Read `AGENTS.md`, `RECHECK-X1.md`, `REVIEW-X1.md`, `SECURITY-REVIEW-X1.md`, the design, relevant brief sections, X2’s PROGRESS record, `8cbdfd02..fda41017`, and both merge-parent diffs.

Ran both requested diff stats, diff checks, six Python syntax compilations in memory, merge-tree/hash comparisons, and memory-only old/new behavioral probes. Attempted `test_control_image`: **15 tests, 13 setup errors** because no temporary directory is writable. A five-test selection from `test_checkout_sources` produced **3 passes, 2 read-only-filesystem errors**. I did not run the full VM module. Independently read the four hosted runs’ job logs.

No files changed or prohibited commands ran. The pre-existing untracked `RECHECK-X2.md` was left untouched.

| RECHECK-X1 finding | Closed? | Regression evidence |
|---|---|---|
| **#1: untrusted siblings of `vendor/`** | **Yes.** The entire dependency directory is reconstructed. Extra files, bytecode and directories cannot survive by being included in the manifest. | `test_the_record_must_be_what_the_locked_wheels_install`, [os/tests/test_control_image.py:403](../../os/tests/test_control_image.py#L403), sibling cases at [448](../../os/tests/test_control_image.py#L448). The added assertions would fail on `48570285`. Memory-modeled filesystem probes executing the actual comparison function accepted sibling source, bytecode and an empty directory on the baseline and rejected all three on X2. |
| **#2: incomplete password scanning** | **Not fully.** Unknown content that remains vanished now fails; replacement and FUSE-handover gaps remain below. | `test_runtime_content_that_vanishes_unread_fails_and_is_named`, [os/tests/test_control_vm.py:639](../../os/tests/test_control_vm.py#L639), would fail on the baseline’s empty `errors`. `test_root_walks_a_fuse_mount_first_and_its_owner_only_where_root_is_refused`, [718](../../os/tests/test_control_vm.py#L718), would fail because the baseline always invokes the owner. These tests do not establish coverage of the two remaining cases. |
| **#3: readable tar archives misclassified as ordinary bytes** | **Yes, within the documented recognition limit.** | `test_every_tar_tarfile_reads_is_searched_whatever_its_magic`, [os/tests/test_control_vm.py:870](../../os/tests/test_control_vm.py#L870). Memory-only probes reproduced zero hits on `48570285` and the compressed-password hit on X2 for V7, version-`01` and unknown-type members. Thus its hit assertions would fail on the baseline. Ordinary-evidence coverage remains at [914](../../os/tests/test_control_vm.py#L914). |

For #1, [os/build.sh:61](../../os/build.sh#L61) requires `/usr/lib/aresos-control` absent, installs wheels into `vendor/`, and compiles there. Its other install mappings place nothing alongside `vendor/`. X2’s whole-directory reconstruction matches that contract.

For #3, the first-header parser covers tarfile-readable headers, while recognizable damaged headers fail closed. The existing depth and trailing-content checks remain. Text containing `ustar` and ordinary PNG bytes passed my probes; damaged POSIX tar and excessive nesting raised `Unreadable`. A damaged first V7 header remains ordinary bytes. That is an acceptable **documented recognition limit for this scope**, not evidence that arbitrary damaged archives are fully searchable.

The merge is correctly joined.

- `git show --remerge-diff dcbb70dd` failed with **“unable to create temporary object directory.”** I instead compared the merge base, both parents and the result.
- [os/ci/check-build.sh:77](../../os/ci/check-build.sh#L77) retains the Control/build split. `CONSOLE_KEYMAP_PASSED` is required in the `build` VM branch, where main required it. Control’s checks remain intact.
- [os/manifest/ci/16/pending-rebind.json](../../os/manifest/ci/16/pending-rebind.json) retains both parents’ notes and paths. Its **10 rows are unique**, every hash matches the merged file, and nothing is listed as removed.
- No unilateral change was dropped or altered unexpectedly. Inspection of files changed by both parents found no dropped or duplicated CI checks or tests. The `console_keymap.py` copy in `LayerHookTest` correctly supplies the newly imported module.
- The X2 fixes themselves touch only the four CI helpers and two test files. Production changes in the round come from main. The `04aef030...fda41017` comparison includes the PR’s earlier Part A/B2 work; it does not mean the entire PR is CI-only. `fda41017..HEAD` changes only PROGRESS.

Hosted evidence agrees with the recorded results: [44097419307](https://github.com/Ares-Empire/AresOS/actions/runs/44097419307) reports **1758 tests, OK, skipped=4**. [44103926487 attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/44103926487/attempts/2) and [44117467369](https://github.com/Ares-Empire/AresOS/actions/runs/44117467369) contain the vendor, interactive, password and final Control PASS lines. Check 8 reports **1866 / 1874 root-searched files**, no vanished paths, and the owner fallback for the portal. Final evidence scans report no hits or unreadable archives.

[44129709609](https://github.com/Ares-Empire/AresOS/actions/runs/44129709609) stops at the metadata-pin assertion on log line 1551. I do not count that upstream failure against X2. The three fixes have evidence from the successful Control runs; **execution of the merged build-only keymap path on this head remains unverified** by that failed run.

Two remaining findings:

1. **SHOULD-FIX — replacement bytes can stand in for unread content.**  
   [os/ci/control/tree_scan.py:118](../../os/ci/control/tree_scan.py#L118)

   The scanner successfully stats `/tmp/control-debug.log`, which holds the synthetic password. Before opening it, a process removes it; opening returns ENOENT, and a clean replacement appears before `gone()` checks the pathname. The retry reads the replacement and returns **`errors: []`, `vanished: []`, no hit**. The original content was never searched.

   I reproduced this with the actual scanner on both the baseline and X2. Feeding that scan outcome, alongside the legitimate stored-password hit, into the actual `passwords()` function with otherwise passing mocked state returned **0**.

   The existing replacement test at [os/tests/test_control_vm.py:687](../../os/tests/test_control_vm.py#L687) raises ENOENT without replacing the original file, so it misses this case. Fail an observed unread disappearance even if the name reappears, or establish that the retry reads the same file instance.

2. **SHOULD-FIX — owner fallback can discard a known unread FUSE path.**  
   [os/ci/control/actions.py:1531](../../os/ci/control/actions.py#L1531), [os/ci/control/actions.py:1539](../../os/ci/control/actions.py#L1539)

   Root lists a FUSE directory and receives EACCES opening `private.log`. Before the owner walk, that file disappears—or the owner’s FUSE directory view omits it. The owner successfully walks an empty directory. Its empty `errors` replaces root’s known refusal, leaving **zero files searched and no error for that content**.

   My memory-only probe reproduced this through the actual `scan()` and `search_for()` functions; the resulting otherwise-clean password check returned **0**.

   Partial-subpath refusals do trigger fallback correctly, and an explicit owner-side refusal correctly fails. The gap is that the fallback request contains only the mount root: no check establishes that each previously refused path was actually covered. Preserve structured refused paths and require owner-side coverage of them; disappearance or omission must remain an error. Add a partial-denial regression covering both successful recovery and omission.

These findings concern CI coverage. X2 does not change the production behavior judged SAFE by `SECURITY-REVIEW-X1`. Its limits remain unchanged: one deliberate Stop JSON diagnostic on hook errors, UID/GID 250 dependent on release rehearsal, and auto mode unexercised under K1.

CHANGES-NEEDED