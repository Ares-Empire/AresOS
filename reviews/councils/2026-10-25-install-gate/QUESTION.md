# Council: safety and followability of the install guide (2026-10-25)

This is the "Safety + followability council" item in the [Maintainer release gate](../../../docs/INSTALL.md#maintainer-release-gate). It is the last gate that doesn't need the laptop. Review `main` at the commit checked out in this worktree.

**Under review:**
- `docs/INSTALL.md`: the owner's guide (1051 lines)
- `docs/EMERGENCY.md`: the one-page card on the owner's phone
- `docs/INSTALL-RECORD.md`
- `docs/install-tools/InstallRecord.psm1`
- `docs/design/OS-BASE.md` §8 and Appendices C and D
- The owner scripts the guide tells the owner to run: `os/release/system-keyboard.sh`, `os/release/pin-stock.sh` and `os/release/pause-stock-updates.sh`, plus the manifests in `os/manifest/` that the guide checks against

Background, read as needed:
- `CLAUDE.md` hard rule 1 and "Owner decides"
- `STATE.md` "Owner decisions"
- The last council on this guide: `reviews/councils/2026-10-22-own-ssd/` (VERDICT, VERDICT-DELTA, CHANGES)
- The evidence reports the guide links to: `reviews/06-image-release/`, `reviews/11-two-disk-rehearsal/`, `reviews/13-keyboard-layout/`

## Context

- **The owner:** a student, not a Linux expert. They use German Windows 11 Home on a Lenovo LOQ 15IRH8 (82XV) with a German keyboard.
- **The plan:** they fit a Crucial P310 500 GB NVMe into the free M.2 2280 slot themselves, install Bazzite onto that whole drive, then switch it to the signed AresOS image. The Windows SSD (Micron 512 GB, 2242) must never be written.
  - The parts (SSD, USB sticks, PH0/PH1 screwdrivers) arrive 2026-10-26.
- **What changed since the last council** (2026-10-22, at 158 lines, READY-TO-MERGE), now 1051 lines:
  - the switch and rollback recipe (PR #10)
  - the stock pause and pin, the GRUB recovery entry and the Windows-default timing (PR #11)
  - the keyboard-layout repair (PR #12)
  - the emergency card
  - Much of it was proven in CI virtual machines, none of it yet on the real laptop.
- **Already open and owner-only:** the hardware items in the gate need the laptop and the owner. Don't re-report them as missing; judge whether the guide handles them safely:
  - fitting and firmware screens
  - helper trials
  - the real GRUB menu
  - live-desktop typing
  - the media and novice trial
- **Owner decisions:** challenge one only with a concrete scenario where it causes harm.
  - AresOS on its own SSD
  - Secure Boot off
  - the backup Bazzite stays frozen and keeps the installer's keyboard layout
  - Windows stays the firmware default after §5, and Linux is picked once with F12
  - F12 → Windows on a failed first switch boot
  - the `ares` / `ares-recovery` account split

## Questions

1. **Safety.** Can following the guide as written cause any of these?
   - writing to the Micron drive, its partitions or Windows' boot files
   - losing personal data
   - physically damaging the laptop
   - locking the owner out: passwords, keyboard layout at a recovery login, the wrong account, a token left behind

   Can a command, as the owner would type it, hit the wrong disk or deployment? Are the stop conditions enough?
2. **Followability.** Where will a non-expert most likely go wrong on install day?
   - skipping a step
   - mistyping a long command, typed by hand with a German layout while reading the guide on a phone
   - misreading German UI names
   - losing their place in a 1051-line guide
   - confusing owner steps with maintainer evidence

   Does each risky step say what they should see before acting, and what to do if they see something else?
3. **Recovery.** At each point that can fail, does the owner know what they will see, and does EMERGENCY.md get them back to Windows, or to a working Linux, without outside help? The points are:
   - live boot
   - installer
   - first stock boot
   - pause/pin
   - private pull
   - switch
   - first AresOS boot
   - layout change
   - rollback
   - undo

   Do INSTALL and EMERGENCY agree?
4. **Honesty.** Is every claim marked correctly as VM-proven, source-verified or physically untested? Is anything presented as proven that isn't?
5. **Proportionality.** What is the minimal safe version for the owner? What could move out of the owner's path (into the release gate or the reports) without losing a check?

## Output

Follow `docs/REVIEW.md` (councils). For every finding give:
- the gap in one line
- a concrete scenario
- the impact
- the fix
- the check

Put the most severe first, with the file and line. Do not edit any files.

**Decision that depends on this:** whether the guide itself is ready for the owner's laptop-side gates. Physical installation stays NOT RELEASED until every gate item passes, whatever this council finds.
