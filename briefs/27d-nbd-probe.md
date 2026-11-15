# 27d: the harness reads filesystem types from the disk

Empire board brief 289. A harness fix found on package 30b's check build.

**Goal:** the check build's offline journal step finds the guest's Btrfs root from the disk itself, so a runner image whose udev probes the disk late or never cannot fail a build whose image and guest checks all passed.

**The problem:** `os/ci/offline_journal.py` reads the powered-off VM disk after a check build. It runs `qemu-nbd --read-only --connect`, then `udevadm settle`, then `lsblk --json --paths --output NAME,FSTYPE,RO`, and asserts exactly one partition with `fstype == 'btrfs'`. On run 43548237383 (both attempts, branch `pkg/30b-launch-hints`, runner image ubuntu-24.04 version 20261111.127.1) `lsblk` showed `fstype: null` on all four partitions `/dev/nbd0p1..p4`, so the assert failed after every image and guest check had passed. Run 43542914709 passed the same step on version 20261111.370.1. `udevadm settle` only waits for events already queued; the partitions' probe can come later, or udev may not probe nbd devices at all on that image. `lsblk`'s FSTYPE comes from udev's database, not from the disk.

**The fix:**
- For each partition of the nbd device, read its type with `blkid -p -o value -s TYPE <partition>` (low-level probe, no cache).
- Before probing, wait a bounded few seconds (polling) for the partition nodes to appear.
- Keep the assert of exactly one Btrfs root; its message shows what was seen per partition.
- Everything else in the function stays as it is.
- Look in `os/ci/` for other places that read `fstype` from `lsblk` after `qemu-nbd` or a loop device, and treat them the same way if they have the same pattern; list what was found.

**Out of scope:** the owner tools, the guest-side `lsblk` calls (they run inside the VM), anything under `os/manifest/ci/27/`.

**Acceptance:**
- A unit test in `os/tests` fakes `blkid` and `lsblk` and proves: the type comes from `blkid -p`; a missing node is waited for within the bound; zero or two Btrfs roots fail with a message naming each partition's type.
- The check build passes on a hosted runner (`gh workflow run "OS image" --ref pkg/27d-nbd-probe -f check_build=build`), and its log shows what `blkid -p` returned for each partition. A `checks_only` run on the branch passes too.

**If unsure:** change less and report.

**Model:** a Claude agent on Opus 5.5 (a small harness fix; no Codex brief needed). Review: a fresh reviewer.
