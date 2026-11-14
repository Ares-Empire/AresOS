Reviewed commit `62b0fc9`. Three findings:

1. **Blocking — changing partition lists can bypass the wait.** At [offline_journal.py:91](/var/home/ares/AresOS-27d-nbd-probe/os/ci/offline_journal.py:91), each poll replaces `names`. I reproduced four listed partitions with p2 missing, followed by a list omitting p2: the function returns p4 successfully after 0.5 seconds. An initially incomplete list can likewise hide a second Btrfs root. **Fix:** establish the complete expected partition set, retain missing partitions across polls, and validate that enumeration remains complete through probing. Add tests for shrinking and expanding lists.

2. **Blocking — quiet exit 2 does not exclude every probe error.** At [offline_journal.py:107](/var/home/ares/AresOS-27d-nbd-probe/os/ci/offline_journal.py:107), empty stderr makes exit 2 acceptable. Upstream `blkid` can also reach that result after a negative low-level probe return without emitting a diagnostic. Consequently, a probe failure on another partition could become `none` while the remaining Btrfs root passes. [Upstream implementation](https://github.com/util-linux/util-linux/blob/v2.39.3/misc-utils/blkid.c#L476-L546). **Fix:** preserve the underlying probe error separately from “no signature”; add an I/O-error test alongside an otherwise valid root.

3. **Should-fix — exit 2 with stdout is accepted.** The same assertion checks only stderr. Using the existing test helper with p4 returning exit 2, stdout `btrfs\n`, and empty stderr produces `status='passed'`, contradicting the stated “printed nothing” rule. **Fix:** require both stdout and stderr to be empty for exit 2, and add regression coverage.

Other checks:

- Zero and two Btrfs roots fail with per-partition diagnostics when enumeration is complete.
- The nominal wait is 10 seconds; individual subprocesses have 120-second timeouts, so 10 seconds is not a strict wall-clock bound, but polling cannot run indefinitely.
- The remaining reader behavior and workflow are unchanged.
- All 17 tests passed with filesystem operations redirected to memory. Removing `-p` or the node wait failed the corresponding test.
- The [hosted build log](https://github.com/Ares-Empire/AresOS/actions/runs/43552814334/job/132318879998) confirms the reviewed commit, runner image `20261111.127.1`, the reported `none/vfat/ext4/btrfs` types, and the offline journal pass.

No files were changed or privileged commands run.

CHANGES-NEEDED