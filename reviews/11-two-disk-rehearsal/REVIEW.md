Reviewed commit `d7f0ac4`. Four findings:

1. **Should-fix — The harness restores Windows-first earlier than the owner guide does.**  
   [two_disk_vm.py:831](../../os/ci/two_disk_vm.py#L831), [INSTALL.md:351](../../docs/INSTALL.md#L351), [EMERGENCY.md:36](../../docs/EMERGENCY.md#L36).  
   Immediately after installation, the harness calls `restore_windows_order()`. The owner instead gets an F12 Windows selection in §5; persistent Windows-first restoration appears only in §8, after switching and recovery checks. F12 selects one boot, so following the guide can leave Linux as the firmware default while the emergency card promises Windows will start unattended. The rehearsal therefore includes a safety step missing from the owner’s sequence.  
   **Fix:** after successful first-login pause/pin, explicitly restore Windows-first and verify an unattended Windows boot before switching. Align the harness with that documented sequence.

2. **Should-fix — Stock identification and GRUB position are incorrectly coupled to BLS filename digits.**  
   [two_disk_vm.py:359](../../os/ci/two_disk_vm.py#L359), [two_disk_vm.py:563](../../os/ci/two_disk_vm.py#L563).  
   The retained installed entries contain **one** checksum-matching stock deployment, but the suffix-required regex accepts **zero** candidates. Also, `menu_index=int(match[1])` is invalid: actual `ostree-2` is titled `Bazzite (ostree:0)`. Allowing bare IDs alone would leave the position bug. The synthetic selector test encodes the same assumption.  
   **Fix:** identify stock by resolving each actual BLS `ostree=` target and matching the exact recorded deployment checksum. Independently obtain its position from the installed GRUB menu inventory—or reproduce that pinned `blscfg` implementation’s ordering and configuration—then confirm the rendered menu before sending keys. Fedora documents filename comparison rules, not an ID-digit-to-position mapping. Add regressions using the retained bare-ID entries and mismatched ID/title numbers. [Fedora BLS ordering](https://fedoraproject.org/wiki/Changes/BootLoaderSpecByDefault)  
   **Owner steps:** INSTALL/EMERGENCY do **not** share the filename-digit assumption; they request a recorded entry, and `default-stock.sh` resolves the deployment index from status. However, INSTALL’s instruction to “record … current GRUB entry” provides no checksum-to-menu mapping procedure. Add one, including the observed fact that both entries can be labelled **Bazzite**. Keep Part B explicitly unqualified until rehearsed.

3. **Should-fix — Firmware auditing accepts arbitrary `BootNext` changes.**  
   [disk_audit.py:316](../../os/ci/disk_audit.py#L316).  
   `compare_nvram()` skips every `BootNext` change without validating its length, destination, authorization or consumption. Windows can remain byte-identical and first in `BootOrder` while an unexpected `BootNext` redirects the next unattended boot. Subsequent installed boots overwrite it in the harness constructor, potentially hiding that regression. The retained full-run captures have no pending `BootNext`; this is a checker gap, not evidence that this run redirected Windows.  
   **Fix:** record and validate each harness-authorized one-time selection before boot, require its consumption afterward, and reject unexpected or malformed values. Add negative tests for an unknown destination and a retained override at a Windows-default checkpoint.

4. **Should-fix — The owner’s switch command omits the newly rehearsed pending-deployment guard.**  
   [switch.sh:10](../../os/release/switch.sh#L10), [INSTALL.md:425](../../docs/INSTALL.md#L425).  
   CI executes a fresh check rejecting `staged` or `rollbackQueued` immediately before `bootc switch`. The owner’s block directly switches after the intervening authentication/signature steps. Earlier pinning does not enforce the required state at the switch boundary.  
   **Fix:** include the same guard in the owner block and test that both switch paths retain equivalent preconditions.

The four owner-facing scripts passed Bash syntax checks; the owner pin block matches the script. Python/VM tests were not rerun because no Python runtime is installed locally. No exposed credential was found in the inspected changes.

CHANGES-NEEDED

---

## Fix re-review of `d7f0ac4..5d69724` (2026-10-25, fresh Codex gpt-6.1-sol high, read-only)

Reviewed `d7f0ac4..5d69724`. **All four earlier findings are fixed; I found no remaining merge-blocking issue within the requested scope.** Physical installation must remain **NOT RELEASED**.

The four fixes:

1. **Windows-default timing — resolved.** [INSTALL.md:351](../../docs/INSTALL.md#L351) now requires F2 → Windows first → Save and Exit → an unattended Windows start after first-login pause/pin. EMERGENCY correctly limits its default-Windows promise to after that checkpoint. The harness follows this sequence, including Linux-default initialization boots without BootNext and subsequent attached/detached Windows markers.

2. **Stock identity/menu position — resolved.** [grub_bls.py:15](../../os/ci/grub_bls.py#L15) matches the exact resolved deployment checksum, then independently derives and checks position against the restricted pinned filename/title/version/status rule. Ordered rendered-menu OCR must agree before selection keys. Regressions cover bare IDs, mismatched filename/title numbers, missing/duplicate stock and OCR disagreement. Owner instructions now explain checksum-to-title mapping and the two “Bazzite” labels.

3. **BootNext auditing — resolved.** [disk_audit.py:294](../../os/ci/disk_audit.py#L294) validates length, attributes, destination and authorization, then requires absence after boot. The constructor rejects a leftover override before writing another. `compare_nvram()` no longer exempts BootNext. The negative tests retain protection against unknown destinations, malformed values and pending overrides at Windows-default checkpoints.

4. **Owner switch guard — resolved.** The INSTALL block exactly matches `switch.sh` with the release reference substituted, including account/auth checks and the staged/rollbackQueued guard immediately before switching. I independently checked block equality.

The pagination and fixture changes preserve their claimed protections. [rehearsal_guard.py:69](../../os/ci/rehearsal_guard.py#L69) requires consistent totals, exact page sizes, unique valid IDs and bounded completeness; errors fail closed. [test_shell_assertions.py:58](../../os/tests/test_shell_assertions.py#L58) supplies temporary prerequisites while executing the actual owner block and Python guard. Its negative cases stop before switching; transaction-failure cases still require exit 42 and no subsequent command.

**Part B’s functional pass is supported by retained evidence.** Stock booted at index 1 while AresOS remained default at index 0; promotion then made stock default, and the next Linux boot used the exact stock checksum/digest with no pending transaction. I checked all 10 Part B protected-disk records against baseline, final zero-write counters, unchanged Windows entry, post-boot BootNext absence and four recorded/consumed Linux selections. Both Windows markers identify the original protected ESP. The artifact ZIP hash matches the report. These establish the VM result, without qualifying real Windows firmware or hardware behavior.

Two open findings belong to later gates:

- **Should-fix before physical release; does not block this merge — conflicting console keymap.** Both retained BLS entries contain `vconsole.keymap=us`, while `/etc/vconsole.conf` specifies `de`; see [INSTALL.md:586](../../docs/INSTALL.md#L586). The kernel argument overrides the file setting. [systemd documentation](https://www.freedesktop.org/software/systemd/man/latest/vconsole.conf.html) Thus German file checks can pass while tty3 uses US mappings, potentially preventing emergency password login/sudo on the laptop. Fix the persistent generated kernel arguments to agree with German configuration, then verify the active command line, loaded tty3 map and actual German-keyboard login after stock, AresOS and recovery boots.

- **Nit for this merge; later capture/manual-menu gate — selected-highlight evidence is inconclusive.** [two_disk_vm.py:549](../../os/ci/two_disk_vm.py#L549) captures after a fixed delay. The selected PNG is byte-identical to frames 05/06 and visibly highlights row 0. It proves no post-Down highlight; capture latency remains unproven. The independently verified stock boot supports functional selection. Fix capture synchronization by waiting for and validating the stock-row highlight before Enter. On the laptop, verify the recorded title and visible highlight before confirming; physical menu usability remains unqualified.

No files changed. Tests were not rerun: no installed Python was available, and WSL returned access denied.

SAFE