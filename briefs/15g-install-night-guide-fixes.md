# 15g: Install-night guide fixes

New package on branch `pkg/15g-install-night-guide-fixes`, from main after PR #22 (15f).

On 2026-11-07/08 the owner ran step 4 on the real laptop, guided by a Claude session on the Mac. Step 4 passed in the end, but the guide was wrong or silent in the places below. Fix the owner pages so the next run (a reinstall, or someone else) follows them without improvising.

**Don't change the tools, payload, image, workflows or Windows helpers.** `git diff main -- os/owner-tools os/release os/manifest/release.json docs/install-tools .github` must stay empty. Only exception: `os/manifest/ci/16/pending-rebind.json` (see Rules).

## What happened, and what to change

1. **Micron serial format (board #122).**
   - Record A's `Disk.Serial` for the Micron is Windows' EUI-64 drive ID: the form `xxxx_xxxx_xxxx_xxxx.`, which Windows reports for NVMe drives. Linux `lsblk` SERIAL shows the **printed** serial.
   - The printed serial comes from Windows as `(Get-PhysicalDisk | Where-Object FriendlyName -like 'Micron*').AdapterSerialNumber`, the part before `_`, trimmed. That's the same disk as record A, because its `SerialNumber` equals record A's `Disk.Serial` and its disk GUID matches.
   - INSTALL-RECORD §C says to match the Micron "by model + serial … matching windows-before.json", which can't pass as written.
   - Fix in INSTALL-RECORD §C and at step 4's `at install` prompt ("Windows baseline Micron serial"):
     - say which serial is meant and how to read it on Windows, read-only;
     - say that the record A Serial ↔ SerialNumber match ties it to record A.
   - Keep the Crucial rule: the printed label serial.
2. **German layout in the live session (#99, #100).**
   - Live Plasma (Wayland) ignored the German layout set in System Settings: Y still typed z.
   - What worked was Konsole → `sudo localectl set-x11-keymap de`. After that the live KWin followed the system layout.
   - It has to be typed while the US layout is still active. On the German keyboard, `-` is the key labelled ß, `y` is the key labelled Z, and space works as usual. Check the US-on-German key positions and state them exactly.
   - Rewrite step 4 box 2 and INSTALL-RECORD §C's "Before opening Konsole" note:
     - the localectl route first;
     - then the existing typing test (`y z / - " $ ä ö ü`);
     - keep a STOP if the test still fails.
   - Keep the installer's own target-keyboard setting as it is.
3. **Reinstall route (#114).**
   - The first install's ares-recovery passphrase was refused at sign-in, and the layout was ruled out. The owner chose to reinstall.
   - Step 4 has no route for this, and its "Crucial empty" check can't pass a second time.
   - Add a bounded route: when the first install of step 4 fails before the tools are installed, return to step 4 box 1. On that pass, the Crucial-empty check is replaced by:
     - Crucial holds only the partitions that the failed install made (EFI, boot and system), nothing else;
     - Micron is unchanged, as always.
   - Then reinstall with "Use entire disk" on Crucial only, exactly as before.
   - Anything else on Crucial → STOP.
   - Make the passphrase rule part of Create Account for every install: lowercase letters `a`–`x` and top-row digits only. Those type the same in US and German layouts. It must still be long, for example several words.
4. **First boot showed the MOK screen.**
   - After the install, the blue shim "Perform MOK management" screen appeared. "Continue boot" was chosen, nothing was enrolled, and stock booted normally.
   - The guide treats any enrollment screen as unexpected → stop. Make this one screen expected: choose **Continue boot**, never enroll or change keys.
   - Any other signature, enrollment or error screen still stops.
   - Check against the pinned shim/MokManager source or retained evidence, and say what the screen looks like.
5. **Who does what (CLAUDE.md hard rule 1, owner 2026-11-08).**
   - INSTALL.md's intro says "Agents do none of those actions." That's no longer true.
   - Now: the maintainer (Claude) runs the Windows-side commands itself and explains anything impactful first.
   - The owner still does F2/F12 and every firmware screen, types every passphrase or token himself, and types the offline Linux commands with a guiding session.
   - Update the intro, and any other owner-page line that says agents do nothing.
6. **Smaller notes from the night:**
   - **Bootstrap rerun.** In the same root shell, the 13-line block may be recalled from history instead of retyped. Show it first, and check that line 8 matches the guide before running it. Say this once, briefly, at the bootstrap.
   - **Console fallback.** tty3 froze after an accidental dead key. Using tty4 (same login) worked. Add that as the fallback in INSTALL-REFERENCE "Console".
   - **Black screen on console switch.** The first console switch after networking gave a black screen, with the monitor off for a few seconds; it recovered by itself. Say to wait and not to reboot.
   - **Hung shutdown or restart.** Installed Bazzite's restart hung once, and so did the live session's. The owner forced it off. Write a guarded instruction:
     - how long to wait;
     - when forcing off is acceptable;
     - especially during the restart after `at switch`. Check ostree's staged-deployment finalization (pinned sources or upstream docs, cited): what an interrupted finalization leaves behind, and what `at check` would then report.
     - Mark this as a JUDGMENT-CALL in the REPORT, with your recommendation.
   - **The F12 list.** It shows **Bazzite** (the installer's entry) and Lenovo's own **Fedora** entry. Step 8 already explains this (15f). Make every "recorded Linux entry" mention in steps 4–7 say **Bazzite**, and point to step 8 once.
7. **INSTALL-STATUS.**
   - Record that step 4 passed on 2026-11-08.
   - Record that the tools changed after the Stage C release (PR #22, fingerprint `3ef85c4a…`, unit-tested and reviewed). The owner approved going on without a new VM rehearsal; `os/manifest/ci/16/pending-rebind.json` lists what the next rehearsal rebinds.
   - Keep the gates and the trial rows accurate. Don't release anything new.

## Rules

- **Privacy:** no serials, GUIDs, photos or personal data. Use invented examples marked as examples, like the existing ones.
- **Pending rebind:** every owner page you change that the package 16 walk binds must get its new checkout hash in `os/manifest/ci/16/pending-rebind.json`. Regenerate it with `checkout_sources.records`, as `reviews/15f-lenovo-firmware-entry/REPORT.md` describes. `test_checkout_sources` must pass. Never rebind the walk tables themselves.
- **Keep the style:** the owner reads these pages on a phone. Use short numbered steps, exact German labels, a PASS/STOP for each check and explicit returns. Keep EMERGENCY.md consistent with every route you change.
- **Tests:**
  - Extend `os/tests/test_owner_path.py` (or the right owner-path test) so each fix is pinned: the serial explanation, the localectl route, the reinstall route and its STOP, the MOK screen, the who-does-what line, and the Bazzite naming.
  - Run in WSL, with and without `-B`: `test_owner_path`, `test_owner_equality`, `test_checkout_sources`, `test_owner_step_limits`, and the whole `os/tests` suite. Known WSL-only failures on main: `test_greeter` (3), `test_inherited_homebrew` (6) and `test_sysusers` (1). Anything else must pass.
  - Run the pinned gitleaks.
- **Delivery:** commit, push once through the privacy hook (never `--no-verify`), and open a PR. Write `reviews/15g-install-night-guide-fixes/REPORT.md` with Done / Verified / Not verified / JUDGMENT-CALL / PLAN-GAP. Don't merge.

**Model:** gpt-6-astra, xhigh. These owner pages are used on the real laptop at the next steps, and the weekly allowance is at 18%.
