# 13: One keyboard layout everywhere

**Goal:** the owner picks the keyboard layout once, in the normal system setting, and every screen follows it: the stock Bazzite desktop, AresOS's labwc session, the tty3 emergency login and the backup Bazzite after a recovery. On the owner's laptop that means German, and a password with `y`, `z`, `-` or `/` works on every screen.

**Read first:** `AGENTS.md`, the 11n section of `reviews/11-two-disk-rehearsal/REPORT.md` and its second `REVIEW.md` section, `docs/INSTALL.md` (§4 keyboard steps, §6, the release gate), `docs/EMERGENCY.md`, `os/config/usr/bin/aresos-session`, `os/config/usr/share/aresos/labwc/`, and the existing VM harness (`os/ci/`).

## What we know

1. **Kernel override.** Both installed BLS entries in 11n (`os/manifest/ci/11n/b-1/two-disk/b-bls-entries.json`) contain `vconsole.keymap=us`, while the installed `/etc/vconsole.conf` says `de`. The kernel argument overrides the file, so tty3 most likely types US layout. Our installed-keyboard check read only the files, so it passed anyway.
2. **The AresOS session sets no layout.** `aresos-session` starts labwc without any XKB layout (no `XKB_DEFAULT_*`, no labwc `environment` file), so labwc most likely falls back to US no matter what the system says. The future Minecraft shell runs in this session.
3. **The tests may hide it.** Check whether the tty3 QMP typing and the CI password only use characters that are identical on US and German layouts. If so, the existing login test can't tell the two layouts apart.

## In scope

1. **Verify first, at zero cost, before any dispatch.** Use the pinned versions from the retained inventory and their source at those tags:
   - Where `vconsole.keymap=us` comes from: the live ISO's boot arguments, Anaconda's bootloader or localization step, or the ostree/bootc deploy. Why does it differ from the installed `vconsole.conf`?
   - Whether new deployments (pin, `bootc switch`, rollback) inherit it.
   - How the pinned labwc and libxkbcommon pick a layout, and what the session would use today.

   Record versions and source links. If the findings contradict this brief, stop and report a PLAN-GAP before any dispatch.
2. **The fix.** One normal system setting decides, and nothing silently overrides it:
   - **The setting:** `localectl` (console keymap and X11 layout, variant and options). No conflicting `vconsole.keymap` may remain on the kernel command line of any entry the owner can boot: stock, AresOS, and the backup after rollback or GRUB recovery.
   - **The AresOS session** reads the system's X11 layout, variant and options and applies them to labwc, so the daily terminal and later Minecraft type like the rest of the system.
   - **Never hardcode German** into the image or its scripts. Only the owner's guide picks German. The image follows the system setting, so the repo stays publishable and another layout works too.
   - **Pick the simplest fix the verification supports.** If it needs an owner step on install day, that step is one copy-paste block, rehearsed exactly as written (like the switch block equality test).
   - **Keep the stock identity checks intact.** A kernel-argument change creates a new deployment with the same checksum. The pin, rollback and GRUB recovery checks select by checksum and require exactly one match. Either the fix avoids an extra stock deployment, or those checks are updated with evidence that they still select the right one. Never weaken them.
3. **Changing it later.** Add one tested command to INSTALL.md (and a line to EMERGENCY.md) for switching the layout later, for example `sudo localectl set-keymap …` plus `set-x11-keymap …`. The next boot and session must follow it.
4. **Tests that can tell layouts apart.** The VM checks type by **physical key position**, as a German keyboard sends it. Use text and a test password containing characters that differ between US and German (for example `y`, `z`, `-`, `/` and one symbol), and require the German result:
   - on tty3: a real login and password sudo
   - in the AresOS labwc session: the foot terminal

   Also check `/proc/cmdline` and the loaded console keymap after each boot below. Then switch the setting to another layout once, prove both screens follow, and switch back.
5. **Per-package budget ledger.** Move `rehearsal_guard.py`'s ledger settings (branch, start, caps) out of package 11's constants into per-package settings. Keep package 11's values as recorded history, and keep all its pagination, retry and fail-closed tests.

## VM qualification (after the verification and local tests pass)

One drive order (protected disk second), all existing protected-disk, NVRAM and BootNext audits at every stage:
- install with the owner's exact §4 keyboard steps
- the first stock boot: cmdline, loaded map and tty3 typing
- pause/pin, the signed switch
- AresOS: cmdline, loaded map, tty3 login/sudo and labwc typing
- the layout change and back
- rollback to stock: cmdline and tty3 typing on the backup

Don't repeat Part B (GRUB menu). If the fix changes the kernel arguments of the backup entry, prove the recovered entry carries the corrected arguments through the rollback boot.

**Budget:** a new ledger for branch `pkg/13-keyboard-layout`, starting at this package's first dispatch, **cap 250 minutes**, at most **one probe and two qualification runs**. The org's October quota is shared (about 1,100 minutes left on 2026-10-25, reset 1 Nov). If the guard can't fit a run, stop and report. All of package 11's stop rules hold: never touch the real laptop, never weaken an audit, and stop on anything the rules don't cover.

## Out of scope

The Minecraft shell's own keyboard handling, an in-hub layout picker (later), Part B, both-order reruns, physical installation (stays NOT RELEASED), image publishing changes or a new release.

## Acceptance

- The verification results with versions and source links.
- The fix, with unit tests and the local whole-suite run (as in 11n: list anything that can't run locally, and run it natively in CI before the probe).
- VM evidence for every boot above, showing the German result from physical-key typing on tty3 and in labwc, no conflicting keymap in `/proc/cmdline`, the layout change following through, and the rollback.
- INSTALL.md and EMERGENCY.md updated. Update the release gate's "loaded keyboard" item.
- `reviews/13-keyboard-layout/REPORT.md` with the budget table.

Push the branch and open a PR. Don't merge.

**If unsure:** choose the fix that changes the least on the owner's system, never hardcode a layout, and stop rather than weaken an identity or disk check.

**Model:** gpt-6.1-sol, xhigh (resuming package 11's Codex session, which knows the harness).
