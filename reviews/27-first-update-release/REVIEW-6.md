Reviewed only `930d4b37..c9072528`. No blocking or should-fix findings. No files modified.

**Nit — cleanup errors can obscure the original failure.**  
Where: [owner_vm.py:1101](C:/Users/pab/AresOS-27-review/os/ci/owner_vm.py:1101). An edit failure followed by an unmount failure can be superseded again by `rmdir` failing on the still-mounted directory. A detach failure can supersede any earlier exception. Python retains the earlier exceptions in the chain, but the primary error changes. **Fix:** preserve the original exception, collect cleanup errors as secondary diagnostics, and add injected unmount/removal/detach failure tests. This affects runner cleanup and diagnosis; it cannot produce a passing rehearsal.

The requested checks:

1. **Partition rule: correct and complete.** One `wait_loop_partitions(loop, image)` call occurs immediately after partscan and before partition paths are constructed or `blkid` runs. Paths come from its validated GPT partition numbers. Importing `prepare_two_disks` does not execute `main()` or create images; it defines helpers/constants. It was already imported through `owner_media`.

2. **Cleanup:** wait failure and the `blkid`/layout assertion reach detachment directly. Mount failure removes the directory without attempting unmount, then attempts detachment. Edit, unmount and directory-removal failures also reach the outer detach. This guarantees a **detach attempt**, not immediate resource release: failed unmounting can leave a mounted filesystem and defer loop removal. Original errors remain primary when cleanup succeeds. No deterministic new rejection of a correct install was found; the shared bounded readiness check can still fail a slow runner.

3. **Image scope:** the changed path attaches only `WORK/target.raw`; the helper verifies that backing file before partition access. Nothing in this delta attaches or edits another image. Owner-tool files are unchanged.

4. **Tests:** the AST rule enforces exactly one wait after partscan. The serial-pin test additionally requires command order `losetup → wait → blkid`, checks expected partition nodes, and verifies final detachment. The injected mount failure checks no unmount, directory removal, detachment and no passing evidence. Reverting the implementation would fail these tests; a literal revert also removes the attribute patched by the new fixture. Unmount/removal/detach failures are not injected.

5. **Hashes:** all **49 pending-list** and **250 host-walk** hashes match `c9072528` under declared checkout conversions, including CRLF for PowerShell. The cap change and its test consistently use 15.

`git diff --check` passed. Python tests and VM boots were not run: `py -0p` reports no installed Python.

SAFE