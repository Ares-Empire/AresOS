# 13e: Repair the keyboard on stock's real two-entry state, and read the key map correctly

Follow-up on branch `pkg/13-keyboard-layout` (PR #12, draft). Read the 13d section of the REPORT. Briefs 13 to 13d still apply, plus the changes below.

## Where 13d stopped

The fresh probe passed. Qualification 40170232822 installed and reached the first stock login, then `system-keyboard.sh` stopped at its own precondition: `expected one stock deployment`. It stopped before reading or changing any kernel argument. Every disk, NVRAM and BootNext audit stayed clean.

## Cause (integrator, from retained evidence)

The one-deployment assumption is wrong for real stock Bazzite. `bazzite-hardware-setup` applies kernel arguments with rpm-ostree on the first start and reboots once. That leaves **two deployments of the same stock commit**. Package 11 already recorded this state: `os/manifest/ci/11f/full-2/two-disk/stock-status.json` shows the booted deployment at serial 1 and a rollback at serial 0, both checksum `aa669eff…0c71`. 13d's two BLS entries (`ostree:0` with the added `bluetooth.disable_ertm=1`, `ostree:1` without it) match. The qualified `pin-stock.sh` already handles this: it requires exactly one booted deployment and resolves its index, without requiring a single deployment. Only the new 13 script and its unit fixtures assumed one. Confirm this from the retained files and the pinned Bazzite source; if the evidence disagrees, stop and report.

## Integrator decision

1. **Accept stock's real starting state, and nothing looser.** Before the repair, require:
   - exactly one booted deployment, with the qualified stock digest, and the bootc and rpm-ostree checksums agreeing
   - nothing staged, no rollback queued, no active transaction, nothing pinned yet
   - every deployment (one or two of them) is unmodified stock with the booted deployment's checksum and the same origin
   - at most two deployments
   Anything else stops, as before. Don't select anything by menu or file digits.
2. **Repair only the booted deployment.** Verify from the pinned ostree source that `ostree admin instutil set-kargs` changes only the booted deployment's arguments and adds no deployment. The identity check compares the **whole** deployment list (checksum, serial, osname, booted, pinned) before and after; count and identities must not change. Leave the non-booted stock entry untouched. Don't remove it.
3. **Know what happens to that entry, and document it.** Work out from the pinned rpm-ostree/bootc source what happens to the unpinned old stock entry when pin-stock pins the booted one and the signed switch adds AresOS. In qualification, export and assert the real deployment list after the pin, after the switch and after the rollback. INSTALL and EMERGENCY must describe exactly the boot entries that really exist at each point. If an unrepaired stock entry survives into the final state, stop and report; don't remove it on your own.
4. **Key-map notation.** The retained 13d rows read `keycode  21 = +z` and `keycode  44 = +y` (`os/manifest/ci/13/qualification-1/diagnostic-summary.json`). `keyboard_state()` in `os/ci/keyboard_vm.py` requires a bare `z`/`y`, so it would fail on a correct German map. Verify the notation in the pinned kbd source (`+` marks letter keys that Caps Lock affects). Accept that notation, and keep the assertions layout-sensitive: German means keycode 21 is z and 44 is y; US means the reverse. Test the parser against the retained 13d rows and against a US example built from the same source.
5. **Fixtures and the audit.** Add unit fixtures for the real two-entry state, shaped like the retained 11f status and the pinned rpm-ostree JSON. Search everything new in package 13 for any other single-deployment or single-entry assumption, and fix each one the same way.
6. **Export before deciding.** The qualification must export the raw `rpm-ostree status --json` and `bootc status --json` (read-only) **before** the repair, so any future stop has the data.
7. **No new image.** `system-keyboard.sh` runs on stock before the switch and isn't a frozen release path. Confirm that no frozen runtime path changes. If one would have to change, stop and report: there's no image or publication budget.

Everything else from 13d stays, including the live-desktop step on the laptop gate.

## Budget

Same ledger: 180 of 380 minutes used. Allow **one fresh probe** (the harness changes) and then **one qualification**. Run them only if a fresh guard shows that probe, a full qualification and the closing reserve fit under 380. A second qualification is allowed only if a fresh guard shows that it fits as well. No image dispatch or publication. If the guard can't fit the plan, stop and report.

## Acceptance

13d's acceptance, plus:
- the repair passes on the real two-entry stock in both starting states (`de` and injected `us`)
- the full deployment list is exported and asserted at each stage
- the key-map parser is tested on the retained rows
- INSTALL and EMERGENCY match the real entry list

Push fast-forward only. Mark PR #12 ready for review if acceptance is met. Don't merge, and never make anything public.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
