# 14: Owner tools: short checked commands instead of hand-typed blocks

**Goal:** on install day the owner types one short command per Linux step instead of hundreds of lines.
- Each command runs reviewed code with every existing check.
- It prints a short PASS, or a STOP that says what to do next.
- It saves the full diagnostics to a file.
- CI types exactly the same commands.

This fixes council findings 2, 3, 5, 6 and 7 (all blocking). Package 15 then rewrites the guide's owner path and the emergency card around these commands (findings 1, 4 and 8–11). So change the guide here only as far as it takes to stay true and keep its equality tests meaningful.

**Read first:**
- `AGENTS.md`
- `reviews/councils/2026-10-25-install-gate/` (VERDICT and the three member files)
- `docs/INSTALL.md` §4–§9, `docs/EMERGENCY.md` and `docs/INSTALL-RECORD.md`
- `os/release/*.sh` and `docs/install-tools/InstallRecord.psm1`
- the VM harness in `os/ci/`
- the 13f section of `reviews/13-keyboard-layout/REPORT.md`

## Owner decisions for this package (2026-10-25)

1. **Two sticks, no third.** The owner has only the two 64 GB sticks: WINDOWS RECOVERY (keep) and ARESOS INSTALLER (erase OK). The installer stick is needed only for the install; afterwards it becomes the tools stick.
   - **Windows side, the stick:** turn it back into a normal stick with the pinned Fedora Media Writer 5.3.2's restore function. Verify from the 5.3.2 source that the function exists, what it does and its German labels. The guide never uses Disk Management, diskpart or Format on the laptop.
   - **Windows side, the bundle:** it comes from the reviewed repository copy the owner already uses for the record helper. A Windows step copies it onto the stick and checks every file's SHA-256 against the bundle manifest. It refuses any destination that isn't a removable USB drive (never C:, never a fixed disk). It prints one fingerprint that the guide also states.
   - **Linux side:** one first command installs the bundle from the stick into a root-only location that both stock and AresOS can see, for example under `/var`, which both deployments share. Check that the AresOS image doesn't shadow it. After that the stick isn't needed.
     - Every later command re-checks its own files against the manifest and refuses on any mismatch.
   - **Records:** the stick can also carry the saved records back to Windows ("copy records off-device").
2. **Offline until updates are paused.** The tools reach Linux only after a Windows round trip. Today the pause must run before the first shutdown, because shutting down finalizes a staged update. So the laptop stays offline from the live session until the tools have paused updates: no Wi-Fi in the live session and no network cable. Stock then can't download an update, and the round trip can't finalize one.

## Verify first, at zero cost, before any dispatch

Use the pinned versions and their sources, and the retained 11k/11n/13f evidence:
- Does Anaconda copy live-session network profiles into the installed system? Either way, the guide forbids connecting in the live session.
- Does the pinned live installer install fully offline?
- Does stock's first boot work offline? That covers hardware setup, its automatic reboot and login. It must leave no staged or queued work, and no first-boot service may hang on, or stage work for, a network that only comes up later.
- What happens when the network first comes up after the pause? Updaters, Flatpak or first-run setup, and anything else that could change a deployment.
- What does the 5.3.2 restore actually do, and what does it show in German?

Record versions and source links. **If offline installation or offline first boot doesn't work, stop and report a PLAN-GAP before any dispatch.** Don't fall back to hand-typed blocks or a third stick yourself; that's the owner's call.

## In scope

1. **The bundle and its commands** (for example `os/owner-tools/`).
   - **The command shape:** one entry command with a few subcommands, short to type on a German keyboard.
   - **On screen:** each one prints a result that fits on one text-console screen (finding 7). That's PASS with the exact values the owner must record, or STOP with the next step.
   - **Diagnostics:** the full diagnostics go to a dated file in a records folder, and to the stick if it's mounted.
   - **Checks:** keep or strengthen every existing check; weaken none.
   - **Code reuse:** where an existing script does a step (`switch.sh`, `verify.sh`, `rollback.sh`, `default-stock.sh`, `stock-session.sh`, the three stock-preparation scripts), call it or replace it. Each step has one implementation, used by both the owner and CI.

   The steps (the names are examples):
   - **`install`:** from the stick, with the manifest check.
   - **`prepare`:** finding 5. One first-login sequence:
     1. pause the updaters and wait for idle
     2. validate and discard only the permitted pending update
     3. repair the booted stock's keyboard override
     4. pin and record

     It handles clean stock, two stock serials, updater activity and the retained staged-update fixture, and refuses everything else with a precise STOP. It's safe to rerun: on correctly prepared stock it reports PASS and changes nothing.
   - **`records`:** the post-install record C items (Crucial's GUIDs, the EFI mapping, firmware entries), saved to a file and shown compactly.
   - **`title`:** finding 7. A compact stock-identity report: checksum, serial, stateroot, pin, pending/transaction state and the resolved BLS title, checked against the saved record. It's run after every reorder.
   - **`login`, `verify`, `switch`:** the account checks, the private-pull login, signature verification and the switch, with today's checks.
     - The token is typed only at a hidden prompt.
     - It is never in an argument, a log, a record or any file other than `/etc/ostree/auth.json`.
   - **`rollback`:** finding 2. Before changing anything it requires:
     - booted AresOS
     - the saved stock checksum, serial and stateroot
     - the digest and reference
     - the pin
     - no pending work

     It refuses on booted stock and points to the keep-stock step. Owner and CI use this one implementation.
   - **`keep-stock`:** making recovered stock the default, with the same guards.
   - **`layout`:** finding 3.
     1. Change the layout while the current administrator session stays open.
     2. Before any reboot, the owner proves physical typing and a fresh password login on a second console with the new layout.
     3. If either fails, a prepared revert restores the old settings.
     4. The reboot only happens after the proof.
     5. After the next boot, check the console and labwc as today.
2. **CI types the owner's commands.**
   - The harness types the exact owner commands through the physical typer, from a virtual tools stick built the same way as the owner's (manifest, check, install).
   - Replace the exact-block equality tests with equivalents that check two things: every command the guide tells the owner to type equals what CI types, and the bundle CI installs equals what the Windows step produces.
3. **Unit tests for every refusal**, with retained JSON fixtures and fake `bootc`/`rpm-ostree`/`ostree`/`systemctl` shims that record calls. Every refusal makes **zero mutations**. Cover at least:
   - the wrong booted image, wrong serial, wrong target, and same checksum with the wrong serial
   - pending work, an active transaction, and a staged update that isn't upstream Bazzite
   - rollback from booted stock
   - a tampered or partial bundle
   - a wrong destination drive on Windows, tested in PowerShell like the record helper
4. **The guide and card, minimally.**
   - Replace each hand-typed block in INSTALL.md and EMERGENCY.md with its short command, the expected PASS/STOP lines and what to do on STOP.
   - Add the offline rule, the stick round trip and the new first-login order.
   - Keep both documents consistent and truthful.
   - Leave the restructure to package 15, and list in the REPORT what 15 must pick up.

## VM qualification (after the verification, unit tests and the local whole suite)

One drive order (protected disk second), with every existing protected-disk, NVRAM and BootNext audit at every stage:
1. The live install with the network link down, following the guide's steps.
2. The first stock boot offline, including hardware setup and its reboot.
3. A shutdown, a detached Windows-like boot for the round trip, then the virtual tools stick attached.
4. `install` and `prepare` by physical typing, then the network comes up. Prove no update was staged or finalized.
5. `records`, `title`, `login`, `verify`, `switch`, the AresOS boot and the final pair, with the title refreshed after each reorder.
6. `layout` with an administrator passphrase that contains an umlaut and layout-sensitive punctuation:
   - the failure branch: change to `us`, the second login fails, revert, and it works again
   - one successful change and back
7. `rollback` to stock and its boot, then `keep-stock`, as today.

**Budget:** a new ledger for branch `pkg/14-owner-tools`, starting at this package's first dispatch, with a **cap of 350 minutes** and at most **one probe and two qualification runs**.
- **Guard:** before each dispatch it must show that the reservation fits under the cap and leaves at least 150 free org minutes for other repos (billing usage API, read-only). About 590 minutes are left in October; the quota resets 1 November.
- **Cost:** the org's Actions spending limit is $0 with usage blocked, so nothing costs money.
- **Stops:** if a run doesn't fit, stop and report. All of package 11's and 13's stop rules hold: never touch the real laptop, never weaken an audit, and stop on anything the rules don't cover.

## Out of scope

- An image rebuild, a new release or any publication. The AresOS image stays frozen; if the tools need an image change, stop and report a PLAN-GAP.
- The guide and card restructure (package 15).
- Part B / the GRUB menu, and both-order reruns.
- Physical installation (stays NOT RELEASED) and the laptop-side gates.

## Acceptance

- The verification results with versions and source links.
- The bundle, the Windows copy step and the Linux commands, with unit tests for every refusal and a local whole-suite run. As in 13f, list what can't run locally and run it natively in CI before the probe.
- VM evidence for every stage above, including:
  - the offline install with nothing staged
  - the layout failure branch and its revert
  - the rollback guard
- INSTALL and EMERGENCY updated minimally and consistently, with the release-gate items updated honestly.
- `reviews/14-owner-tools/REPORT.md` with the budget table and a "for package 15" list.

Push the branch and open a PR. Don't merge.

**If unsure:** keep every check, and prefer a clear STOP over a guess.

**Model:** gpt-6.1-sol, xhigh (resuming the Codex session that built packages 11 and 13).
