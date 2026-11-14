Reviewed PR #60 at `a575e3a02bc00928f0b9ebd63d790b4687308c7a`, limited to `62b0fc9c..HEAD`. All three findings are closed.

1. **Blocking — partition enumeration: closed.** [offline_journal.py:93](/var/home/ares/AresOS-27d-nbd-probe/os/ci/offline_journal.py:93) fixes the expected set at p1–p4, requires every block node, and checks again after probing. Replaying four listed partitions with p2 missing, followed by a list omitting p2, now fails at simulated **10.0 seconds**, with **zero probes**, no mount, and disconnect last. Growing, incomplete, extra-partition and post-probe changes are covered.

2. **Blocking — quiet probe errors becoming `none`: closed.** [offline_journal.py:110](/var/home/ares/AresOS-27d-nbd-probe/os/ci/offline_journal.py:110) requires exit 0 plus `PART_ENTRY_SCHEME=gpt` and the expected partition number. Quiet exit 2 on p1, alongside a valid p4, becomes **`unread (exit 2, entry None)`** and fails before mounting. Loud I/O errors also fail. I additionally replayed exit 0 without p1’s GPT entry: that fails too.

3. **Should-fix — exit 2 with stdout: closed.** [offline_journal.py:118](/var/home/ares/AresOS-27d-nbd-probe/os/ci/offline_journal.py:118) rejects nonzero exits regardless of output. Both the original `btrfs\n` case and valid exported Btrfs/GPT tags accompanied by exit 2 fail before mounting.

I read **upstream util-linux 2.39.3 source**, alongside Ubuntu Noble’s documentation for **2.39.3-9ubuntu6.6**. Low-level probing enables partition details; finding the parent GPT entry supplies tags and success even without a filesystem. Negative chain results stop safe probing, and the CLI skips printing tags on that error path. “Prints nothing” means **stdout**; stderr may contain diagnostics. Sources: [Ubuntu documentation](https://manpages.ubuntu.com/manpages/noble/man8/blkid.8.html), [partition entry handling](https://github.com/util-linux/util-linux/blob/v2.39.3/libblkid/src/partitions/partitions.c#L611-L765), [safeprobe](https://github.com/util-linux/util-linux/blob/v2.39.3/libblkid/src/probe.c#L1505-L1543), [CLI error handling](https://github.com/util-linux/util-linux/blob/v2.39.3/misc-utils/blkid.c#L476-L546).

The “always” claim is conditional on successful GPT-entry discovery, not universal for every partition. Missing or renamed tags, changed layout, and nonzero errors—even with stdout—**fail loudly**. A future implementation returning **exit 0 with valid GPT tags while suppressing a filesystem-probe error** could pass silently for p1; no version gate detects that contract change.

The wait is bounded: a monotonic 10-second deadline with 0.5-second polling. **Ten seconds is not a strict wall-clock limit**, because each subprocess retains its 120-second timeout.

Verification used `python3 -B`, with filesystem operations redirected to memory and subprocesses mocked:

- **20 tests passed.**
- In-memory mutations restoring dynamic enumeration, quiet-exit-2 acceptance, or exit-2-with-output acceptance produced **5, 2 and 1 failures**, respectively.
- Removing the post-probe check produced **3 failures**; restoring HEAD returned all 20 tests to green.
- The [head’s hosted build](https://github.com/Ares-Empire/AresOS/actions/runs/43556134501/job/132329289992) confirms `none/vfat/ext4/btrfs` and the offline journal pass.

No files were edited; no privileged commands or real `qemu-nbd` were run.

SAFE