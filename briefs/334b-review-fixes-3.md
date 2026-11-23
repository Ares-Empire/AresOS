# 334b review fixes, round 3

`reviews/334b-bench-laptop-safety/REVIEW-3.md` (strict bar: harm in normal use only) came back CHANGES-NEEDED with two
must-fixes and one should-fix. Fix them on `pkg/334b-bench-laptop-safety`. Earlier decisions and Rules hold. Model:
Codex `gpt-6.2-sol`, effort `xhigh`. Keep the changes small and local.

1. **Recheck the launch gates right before `exec`** (must fix 1). In the pre-exec helper, after scope activation and
   the ownership check, run the battery and Lunar gates again. Keep memory as the very last read. Add regressions:
   switching to battery, or a Lunar stand-in appearing after the first gate, returns 75 before `exec`.
2. **Btrfs copy-on-write can't overrun the reserve** (must fix 2). The lead's decision:
   - On Btrfs, a fixed-size disk image counts at its virtual size **only** if its file has the No_COW attribute
     (`FS_NOCOW_FL`) set and verified before the first write. Set it on the store's disk directory, so new files
     inherit it; the owner of a file may set it without privilege.
   - A disk image without a verified No_COW attribute counts at **twice** its virtual size.
   - Other filesystems keep today's rule.
   - Test both paths with a fake attribute reader. Report what a real `chattr +C`/`lsattr` check showed in a temporary
     directory on the laptop's home filesystem, without writing inside the real store.
3. **Pools are combined conservatively** (should fix). On Btrfs, `f_fsid` includes the subvolume ID, so two subvolumes
   of one filesystem look like different pools. Identify the pool filesystem-wide (the Btrfs filesystem UUID, from
   mountinfo or sysfs). When it can't be determined, combine all bench paths into one pool. Test distinct subvolume
   IDs sharing one pool. Correct the REPORT's pool claims.

Add REVIEW-3's Known limits to the REPORT, and "Review fixes, round 3" with each item and the run IDs. Verify: the
touched modules one at a time on the laptop; hosted `checks_only=true`. Push, leave the PR open, never merge.
