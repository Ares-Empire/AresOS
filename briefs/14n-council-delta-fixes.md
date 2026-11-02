# 14n: Fix the two council delta defects in the owner tools (before the November qualification)

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14m still apply. The council chair's delta check (on package 15's branch: `reviews/councils/2026-10-25-install-gate/delta/VERDICT.md`, also quoted below) found two defects in package 14's tools. The tests missed both. Fix them here, locally, before the 1 November qualification.

## A. Blocking: disk helpers read a flat `lsblk` list but walk a device tree

**The defect:**
- `disk_record` in `os/owner-tools/owner.py` asks `lsblk --json --output PATH,TYPE,...` with neither `NAME` nor `--tree`, so the JSON is flat: partitions come back as separate top-level rows. Then it looks for the EFI partition under the selected disk's `children`.
- On a correct install, `install` therefore refuses with "Linux EFI is not on target".
- `media.find` (`os/owner-tools/media.py`) has the same assumption: a partitioned ARESTOOLS stick's partition becomes its own top-level row without the disk's `TRAN`/`RM`.
- The complete-handler tests stub `disk_record`, so they hid this. The 13f and 14i VM runs never reached `install`.

**Fix:**
1. Request tree JSON explicitly (`--tree`, plus `NAME` if needed) in both helpers. Validate the structure: every partition must sit under exactly one disk, and an unexpected shape is a STOP, never a guess.
2. Audit every other JSON query in the payload (`findmnt`, `sfdisk`, `rpm-ostree`, `bootc`, `busctl`, `loginctl`) for the same kind of shape assumption, and fix any you find.
3. Regenerate the payload and its manifest fingerprint, and update every place that states the fingerprint.

**Tests:**
4. Unit tests: run the real `disk_record` and `media.find` on realistic fixtures in both shapes:
   - the tree shape, with a partitioned target holding an EFI child, a protected disk, and a partitioned USB stick: must PASS
   - the flat shape: must STOP clearly
   - the protected disk with a mounted child: zero mutations
   - two ARESTOOLS labels: refused
5. A native-runner test (it runs in the probe's native suite on 1 November, not locally): create a small partitioned loop image with an EFI-type partition and an exFAT partition labelled ARESTOOLS. Run the exact `lsblk` and `findmnt` queries and the real helpers against it. Use only loop devices on the disposable runner.

## B. Should-fix: layout PASS lines the CLI never prints

The guide expects `PASS layout begin us-intl`, `PASS layout proof`, `PASS layout revert` and `PASS layout finish`. The entry point prints only `PASS layout` for every subcommand.

**Fix:**
1. Make the entry point print the full action, for example `PASS layout begin us-intl`. Do the same for any other multi-word command, so each documented PASS line is exact.
2. Add a test that runs the real entry point (with the existing shims) for every command in `commands.json` and compares its actual stdout PASS line with what package 14's guide documents.

## Rules

- Local commits only, with the pinned local gitleaks before committing. **No push and no dispatch before 1 November.** The November resume pushes once, then runs probe 7 and the qualification.
- Run the local suites and the replay as before. Update the REPORT with a short 14n section.
- Package 15's docs follow in their own branch afterwards. Don't edit package 15's worktree.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
