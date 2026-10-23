# 11c: Narrow firmware-entry rule, then the real installs

Follow-up on branch `pkg/11-two-disk-rehearsal` (draft PR #11). Continue from the "11b" section of `reviews/11-two-disk-rehearsal/REPORT.md`.

## First: the history was rewritten

On 2026-10-23 at 09:34 UTC the owner rewrote the whole repo history. The personal commit email was replaced with the GitHub no-reply address, and `.github/workflows/privacy-check.yml` and `.gitleaks.toml` were added on `main`. Every commit SHA changed. The tree content didn't change, apart from that email swap in a few captured CI JSON files.

- Your branch is now GitHub's rewritten branch. **Never force-push.** Never push any `pre-rewrite/*` branch.
- SHAs cited in the 11 and 11b sections (for example `24118e1`) name pre-rewrite commits. Their CI runs and artifacts are still valid evidence. Add one short note with an old → new mapping for the cited source commits (match them by subject). Don't rewrite the evidence itself.
- The privacy check must pass on PR #11:
  - no secrets
  - only no-reply commit emails
  - no personal emails or names in committed files (redact captured API JSON the way the rewrite did)

## Integrator decision: firmware-owned boot entries

This resolves 11b's PLAN-GAP.

**What happened:** detaching the ISO and the empty target made OVMF prune its own automatic boot options for those two devices. Probe 11's removed entries were:
- `Boot0002`: the detached SATA DVD, `Pci(0x1f,0x2)/Sata(0,…)`
- `Boot0004`: the empty target, `Pci(0x3,0x0)`

Both carry exactly 16 bytes of OptionalData: the EDK2 auto-created-option GUID `8108ac4e-9f11-4d59-850e-e21a522c59b2` (efibootmgr shows it as `{auto_created_boot_option}`). Physical firmware does the same when a USB stick is removed.

**The NVRAM contract becomes:**

1. **Unchanged and absolute:**
   - The Windows-like entry stays byte-identical at every stage and stays in BootOrder, first wherever the guide says Windows is the default.
   - The protected-disk checks (bytes, GPT, EFI files, write counters) are untouched.
2. **Unchanged:** an OS-made change may only add or reorder a separate Linux entry (Fedora/Bazzite) on the target's own ESP.
3. **New, narrow rule:** an option counts as **firmware-owned** only if its OptionalData is *exactly* that 16-byte GUID. Verify the GUID against the OVMF build the runner uses and against the baseline store.
   - A firmware-owned option may be **removed** only if its device path's hardware node names a device that was **not attached** in that boot.
   - It may be **added** only if it names a device that **was attached** in that boot.
   - Decide "attached" from the harness's own per-stage record of devices (QEMU PCI address or SATA port), never from labels.
4. **Everything else still fails:**
   - a firmware-owned option changing, or disappearing while its device is attached
   - any entry that isn't firmware-owned changing or disappearing
   - any addition that is neither Linux nor firmware-owned
   - the Windows entry changing in any way, including gaining OptionalData

   The Windows fixture entry has no OptionalData, so it can never qualify.
5. **Every exempted change is listed** in that stage's NVRAM record with its device and reason. Nothing is silently ignored. Keep the raw stores.
6. **Regressions:**
   - Probe 11's real before/after stores must pass with exactly the two exempted removals.
   - Each of these must still fail:
     - the Windows entry removed or changed
     - an auto option removed while its device is attached
     - an auto option whose device path doesn't match the detached device
     - an entry that isn't auto removed
     - an addition that is neither auto nor Linux
     - OptionalData that only *contains* the GUID among other bytes

If a firmware behaviour appears that this contract doesn't cover, **stop and report it as a PLAN-GAP**. Don't widen the exemption yourself.

If `docs/INSTALL.md` or `docs/EMERGENCY.md` implies the F12 list never changes, correct it plainly: the laptop may drop entries for devices that were unplugged, like the installer stick, and that's normal.

## Then finish A and B

1. Run a fresh probe on the new harness commit. The 11b probe-before-full-run rule still applies.
2. Then the full runs. **Part A** in both drive orders:
   - switch, policy, tty3 recovery, rollback, default undo
   - the Windows-like boot without the Linux disk, after install and again after undo
   - an offline protected-disk audit and an NVRAM diff at every stage
3. Then **Part B**.

Every rule from briefs 11 and 11b still holds:
- any protected-disk change means stop and report
- never weaken any other check
- no image rebuild, no visibility change, no owner token
- no mod, Gradle or Minecraft
- agents never touch the real laptop's disks

## Budget

About **450 GitHub Actions minutes** are left in October for the **whole account** (other repos share them). This follow-up may use **at most 330 rounded minutes** and **at most 3 full runs**. Probes count toward the minutes. Give the guard a separate 11c allowance and ledger. If the cap is reached, stop and report what's left.

## Acceptance

- Part A green in both orders.
- Part B green, or a clearly stated blocker.
- INSTALL.md and EMERGENCY.md gates updated honestly.
- An "11c" REPORT section with:
  - a gate → evidence table
  - the exempted firmware changes per stage
  - the minute ledger
- privacy-check green on PR #11.
- Push (fast-forward only). Mark PR #11 ready for review if acceptance is met, otherwise keep it draft. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the 11b session).
