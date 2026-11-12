# 21: review fixes

Follow-up on `pkg/21-everyday-account-and-chrome` (PR #31). Brief 21 still applies. Read `reviews/21-everyday-account-and-chrome/REVIEW.md` (CHANGES-NEEDED at `80458b47`, gpt-6-astra high). Fix all three points as the review proposes:

1. **Blocker: sudo password reuse.**
   - `timestamp_type=ppid` lets a child of an authenticated shell `exec sudo -n …` with the cached ticket. Set `timestamp_timeout=0`, so every sudo asks for the password, like Windows' Yes prompt.
   - Correct the JUDGMENT-CALL text in the REPORT.
   - Add a test that reuse after a successful authentication fails; the locked-account tests can't show this.
2. **Blocker: passwordless boot and firmware control.**
   - Deny `ares` the logind actions that change the next boot explicitly: `org.freedesktop.login1.set-reboot-to-firmware-setup`, the boot-loader entry and menu selection actions, and any similar action your polkit evidence shows as `yes`.
   - Test them independently of wheel membership, because the wheel-difference audit misses inherited grants.
   - Ordinary power actions (power off, reboot, suspend) stay as they are.
   - This guards hard rule 1: Windows stays the firmware default, and the boot order only changes with the owner.
3. **Should-fix: the recovery terminal resolves `foot` through PATH.**
   - Use `/usr/bin/foot`, and an absolute shell path, in `aresos-terminal`.
   - Test recovery with a broken `foot` that shadows it on PATH.

Rebuild with the throwaway CI path and rerun the in-image checks, plus the native regressions. Owner question board #156 is open; keep the current behaviour for its points (Homebrew via UID 1000, system-wide Wi-Fi and Flatpak asking for the password). Same rules and resource gates as before:
- The owner may be playing Minecraft: never start a Minecraft client.
- A full WSL suite needs at least 4 GB free RAM, one suite at a time.

Add a "Review fixes" section to the REPORT, then push.
