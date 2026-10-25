# 14h: Write the virtual tools stick with exfat-fuse; check runner capabilities first

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Read "14g" in `reviews/14-owner-tools/REPORT.md`. Briefs 14 to 14g still apply, with the change below.

## Integrator decision

Stopping was right. Probe 3 proved everything the earlier rounds fixed: the git-only binding, all four CI-only access checks, the signature, the pull and the ISO pin. It then failed on a host capability, before any VM booted.

**Why this route:**
- The runner's Azure kernel has no exFAT driver.
- The host only plays the owner's Windows copy step: it writes the bundle onto an exFAT stick. Inside the guest, Bazzite mounts the stick with its own kernel driver, and that is the part the owner route depends on.
- So the host shouldn't depend on whatever kernel the runner happens to have. The job already mounts NTFS through FUSE (`ntfs-3g`), so FUSE works on these runners.

So:
1. **Use `exfat-fuse` on the runner.** Add `exfat-fuse` to the rehearsal job's apt install line (recorded in the host package list like the others). In `os/ci/owner_media.py`:
   - Format with `mkfs.exfat` as now.
   - Mount the partition with `mount.exfat-fuse`, keeping `nodev,nosuid,noexec`.
   - Check that the mount is the FUSE exFAT filesystem before writing anything.
   - Copy the bundle, sync, unmount, and check that the unmount completed before the loop device is detached.
   - Don't fall back to the kernel driver or to another filesystem.
2. **Prove the stick before hot-plugging it:**
   - After unmounting, run `fsck.exfat -n` on the partition.
   - Mount it read-only with FUSE and check every bundle file against the manifest, then unmount.
   - Only then compute the backing hash for the QMP attach check, as now.
3. **Check runner capabilities first:**
   - Add a short native prerequisite step that runs before ISO inspection and the other expensive steps.
   - It proves every host capability the media and VM stages use: loop devices, the FUSE exFAT read-write and read-only mount on a small throwaway image, `fsck.exfat`, and anything else the later stages need from the host (QEMU, OVMF, QMP).
   - A missing capability must fail within the first minutes of the job.
   - Add the same step to the qualification job.
4. **Local proof:** test the media code with shims or fixtures. Don't install packages on the laptop or in WSL (installing tools on the owner's machines is the owner's call).
5. **Budget:**
   - One more probe allowance (4 in total; 3 are spent, 24 minutes).
   - One qualification is planned. The second stays optional, behind its own fresh guard.
   - Cap 350. Org reserve 150.
   - Recheck the ledger, billing and privacy CI right before dispatch.

## Then

Pinned local gitleaks before every push. The local replay as in 14e and 14f. Then the fourth probe, then the qualification, per briefs 14 to 14g. If a new host capability is missing, stop as before; don't swap filesystems or widen anything. Mark PR #13 ready for review when acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
