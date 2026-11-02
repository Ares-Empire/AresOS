# 14z: Decide firmware entries from the raw device-path bytes, not the text; probe 14 and qualification 4

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14y still apply, with the change below.

## Diagnosis (integrator, from the real output qualification 3 exported)

`tools-install-owner-diagnostics.json` holds the guest's real `efibootmgr -v` output (efibootmgr 18 / efivar 39). For each entry it prints three things:
1. `Boot####* <label>\t<rendered path>`
2. one or more `dp: <hex>` lines with the raw EFI device-path bytes
3. sometimes `data: <hex>` with the optional data

OVMF's own entries (UEFI Misc Device, PXE, HTTP) render their optional data as `{auto_created_boot_option}`. The 14v parser cross-checked the rendered text against a GUID rendering, and refused on those unrelated lines. The real laptop will have its own vendor entries too (Lenovo BBS/USB/network). So text strictness on unrelated entries is the wrong place to be strict.

## Fix (owner tools)

1. **Parse the output into entries:** each Boot#### line plus its indented `dp:` and `data:` lines. Decode the `dp:` hex as the EFI device path, following the UEFI spec:
   - HD media node: type 0x04, subtype 0x01. Read the partition number, start, size and signature type, plus the GPT GUID in mixed-endian layout.
   - File path node: type 0x04, subtype 0x04, a UTF-16LE path.
   - End node: 0x7f 0xff.
   - Bounds-check every length. A malformed dp is a STOP only for entries that need classifying.
2. **Matching:** an entry is "ours" only if its decoded HD node has the target ESP's GPT GUID and its File node is under `\EFI\` (case-insensitive). Require **exactly one** such entry, as before.
   - Entries without an HD node for the target GUID are ignored, whatever their text or optional data says.
   - Use the rendered text only for display and diagnostics.
   - If `-v` output has no `dp:` lines at all, STOP. Never fall back to text.
3. **Fixtures:** use the **real** retained output from qualification 3 (the VM disk GUIDs aren't private). Also add cases:
   - two entries for the target GUID: STOP
   - a target-GUID entry with a non-`\EFI\` path: not counted
   - a truncated dp: STOP
   - an entry for the Windows ESP GUID: ignored
4. **Same approach elsewhere:** anywhere else in the payload that reads firmware entries (title, records, verify, rollback, keep-stock) must use the same decoder. The firmware audit in the harness is separate; leave it unchanged.
5. Regenerate the payload and fingerprint, and update every place that states it.
6. **Later commands:** check every later owner command's parsers (`prepare`, `records`, `title`, `login`, `verify`, `switch`, `layout`, `rollback`, `keep-stock`) against **real retained outputs** from the qualifications and from packages 11 and 13 wherever they exist, and add them as fixtures. Each remaining bug found only in CI costs about an hour.

## Budget (owner's $3 cap)

About $1.05 is used. One push (about 6) plus a probe of at most 72 plus a qualification of at most 160 is about 238 minutes, roughly $1.43, which fits. Settings for package `14` only:
- `minute_cap`: **800**
- `dispatch_caps.probe`: **14**
- `owner-tools`: **4**

## Then

1. Pinned local gitleaks, the replay and strict checks. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 14**. Only if it passes, **qualification 4 on the same head**.
4. The artifact rules from 14v apply.
5. Any stop: report it, no rerun.
6. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
