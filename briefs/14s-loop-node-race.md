# 14s: Wait for loop partition nodes before formatting; classify the ISO listing; local only

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14r still apply, with the change below.

## Diagnosis (integrator, from the code)

`os/ci/owner_media.py` `mounted()` runs `losetup --find --show --partscan` and then `create()` immediately runs `mkfs.exfat` on `<loop>p1`. There's no `udevadm settle` and no wait for the partition node. `owner_devices.py`, which ran just before in probe 9, does settle.

In probe 9 the native loop test had just detached `loop0`, and the media step reused `loop0` straight away. Its `p1` node wasn't there yet, because udev still had the earlier remove and add events queued. In probe 5 the media step was the first loop user, so it won the race by luck. This is CI-harness only; the owner tools aren't affected, since a real stick's partitions have long settled.

## Fix (CI harness only)

1. After every `losetup --partscan` in the harness (`owner_media.mounted`, `prepare_two_disks`, and any other place), run `udevadm settle`. Then wait, with a bound of about 15 seconds, until `/dev/<loop>p<N>` exists as a block device and `/sys/block/<loop>/<loop>p<N>/start` and `size` match the GPT you just wrote.
   - If it's still missing, run `partx --update <loop>` once, settle again and recheck.
   - If it's still missing after that, STOP with the sysfs and udev state shown.
   - Never guess another device.
2. After detaching loops in `owner_devices.py`, run `udevadm settle`, so the next stage starts from a quiet udev queue.
3. Add a local unit test: the wait logic with a fake that shows the node only on the second check, and one that never shows it (it must STOP).

## The 507 artifact findings

All 507 are generic-api-key matches in `evidence/installer/squashfs-files.txt`: the pinned public Bazzite ISO's own file listing. It lives in the private run artifact and is never committed. Integrator classification: public third-party file names, not repository content. The privacy gate covers what we commit, and that stays unchanged. Record this classification in the REPORT. Don't commit the listing, and don't add any ignore entry. If anything other than that listing has findings, it's a STOP.

## Rules

- Commit locally only, with the pinned local gitleaks. **No push and no dispatch:** October's free minutes are nearly gone (155 left; the plan needs 178 at worst). The owner decides whether a small paid Actions budget covers the gap now, or whether it waits for 1 November. I'll resume you with that decision.
- Update the REPORT with a short 14s section.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
