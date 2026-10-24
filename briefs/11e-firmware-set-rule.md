# 11e: Judge firmware-owned entries as a device set, then finish A and B

Follow-up on branch `pkg/11-two-disk-rehearsal` (draft PR #11). Read the "11d" section of `reviews/11-two-disk-rehearsal/REPORT.md`. Briefs 11c and 11d still apply, except the NVRAM rule below.

## What stopped 11d

Reverse order, detached Windows boot. Before the boot, OVMF had two automatic options:
- `Boot0003`, "UEFI Misc Device", for the target at PCI 2.0
- `Boot0004`, "UEFI Misc Device 2", for the protected disk at PCI 3.0

After the target was detached, the protected disk was the only Misc device. EDK2 makes auto-option descriptions unique by enumeration count (`BmMakeBootOptionDescriptionUnique`). Its refresh matches existing options by **description** as well as device path (`EfiBootManagerFindLoadOption`). So it deleted the "…Device 2" option and created a new "UEFI Misc Device" option for the same PCI 3.0 device. The new option reused the lowest free number, `Boot0002` (freed by the DVD removal), and was appended to BootOrder.

That is relabeling and number recycling by the firmware itself, and it is invisible in the first order. Windows `Boot0000` stayed byte-identical and first, and the protected disk had zero writes.

## Integrator decision: replace 11c rule 3 with a set rule

Firmware-owned options are compared as a **set of devices per boot**, not by option number, description or BootOrder position.

1. **Ownership** is unchanged: OptionalData is exactly the 16-byte EDK2 auto GUID, checked against the runner's OVMF source.
2. **Each boot:** every firmware-owned option must name a device that is **attached in that boot**, using the per-boot QMP record. An option for a detached or unknown device fails.
3. **Not judged for firmware-owned options:** the option number, the description, the BootOrder position, and whether an attached device has an auto option at all. Record every removal, addition, relabel and renumber in the stage record with its device. Nothing is silent.
4. **Number recycling:** a firmware-owned option may take a number only if that number was free, or was held by a firmware-owned option removed in the same transition. Taking the number of the Windows entry, a Linux entry, or any other entry that isn't firmware-owned fails.
5. **Unchanged and strict:**
   - Windows stays byte-identical, keeps its number, stays in BootOrder, and stays first wherever the guide says Windows is the default.
   - Entries that aren't firmware-owned keep their relative order in BootOrder.
   - Any other change to an entry that isn't firmware-owned fails, with one exception: a Linux entry that names only the target's own ESP and Fedora loader may be added, re-created or changed by the Linux side (shim, bootupd), as long as it still names only the target ESP.
   - Any addition that is neither Linux nor firmware-owned fails.
   - The protected-disk bytes, GPT, EFI files and zero-write checks are untouched.
6. **Regressions:**
   - Replay the 11d reverse-order raw stores and QMP context. They must pass with exactly these three changes: the DVD removal, the target removal, and the protected-disk option relabeled/renumbered `Boot0004` → `Boot0002`.
   - Replay the 11b/11c first-order stores. They must still pass.
   - Each of these must fail:
     - a firmware option naming a detached or unknown device
     - a firmware option taking the Windows or a Linux entry's number
     - Windows changed, renumbered, or no longer first where required
     - a non-auto, non-Linux entry added or changed
     - a Linux entry that names the protected disk's ESP
     - GUID-plus-extra-bytes ownership

If yet another firmware behaviour isn't covered, **stop and report it as a PLAN-GAP**. Don't widen the rule yourself.

## Then

1. Run a fresh probe on the new commit.
2. Then the full runs as brief 11c says:
   - **Part A** in both drive orders: switch, policy, tty3, rollback, default undo
   - the Windows-like boot without the Linux disk, after install and again after undo
   - audits and NVRAM diffs at every stage
3. Then **Part B**.

Brief 11d's token rules apply unchanged.

## Budget

These minutes come from the **shared 11c/11d allowance: 330 rounded minutes and 3 full runs in total**. 68 are already used, and the ledger continues. About 380 account minutes are left in October. Prefer one complete full run that covers both orders and Part B over several partial ones. If the cap is reached, stop and report what's left.

## Acceptance

11c's acceptance, plus an "11e" REPORT section with:
- the set-rule changes recorded per stage
- the gate → evidence table
- the minute ledger

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
