# 14zi: Detect a hidden prompt on the innermost pts, not on tty3; probe 18 and qualification 8

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zh still apply, with the change below.

## Diagnosis (integrator, from the code; please confirm with the retained evidence)

`owner_vm.Console.hidden()` decides "hidden prompt ready" from **physical tty3's** termios: ECHO off, and the foreground not an idle shell.

Inside the guide's `sudo -i` relay, sudo keeps tty3 in **raw mode with ECHO off** the whole time. So the check is true as soon as anything non-shell is in the foreground, for example the owner tool still starting up, or still at an earlier prompt.

The tool reads the token with `getpass.getpass('Read-only token (hidden): ')`. On Unix, `getpass` first calls `tcsetattr(TCSAFLUSH)` on its `/dev/tty`, which is the innermost pts, and only then writes the prompt. **TCSAFLUSH discards any input already waiting.** So the token and Enter typed after the false "ready" were thrown away, and the tool waited at the prompt forever. That matches qualification 7's screen, and very likely qualification 4's.

The account `Password:` from getty, and sudo's own password prompt for the outer `sudo -i`, are read on tty3 itself. For those, checking tty3 is correct.

## Fix (harness only)

1. **Hidden-prompt readiness** for any input read inside a sudo relay chain must require all of these:
   - The innermost foreground process is the expected reader, found through the 14zg chain: the owner tool, or sudo for a password.
   - **The innermost pts** (the one that process reads) has ECHO off.
   - The expected prompt text (for example `Read-only token (hidden): `) is at the end of the physical cursor line.

   `getpass` flushes before printing its prompt, so these together mean it's safe to type. Keep the tty3 check for reads directly on tty3.
2. **After typing** the hidden value and Enter, wait for the reader to leave its read: the innermost pts' ECHO comes back on, or the tool's result appears. Record it without the value. If the prompt is still there after a bounded wait, STOP with the redacted chain. Never retype a secret automatically.
3. **Apply the same rule** to every hidden input in every stage: login, layout proof passwords, and the second-console sudo.
4. **Local tests**, with a real pty pair where possible (Python `pty` module: a child running `getpass` behind a relay) plus modelled `/proc`:
   - the old tty3-only check fires too early, and input is lost to TCSAFLUSH
   - the new check waits for the real prompt, and input is delivered
   - a busy reader that hasn't reached the prompt yet: not ready
   - the qualification 7 shape: not ready until the prompt
5. Confirm or refute this diagnosis from the qualification 4 and 7 evidence, and say which.

## Budget (owner's $6 cap; about $3.80 billed)

One push (about 6), plus a probe of at most 72, plus a qualification of at most 160 is about $1.43 at worst, which fits. Settings for package `14` only:
- `minute_cap`: **1200**
- `dispatch_caps.probe`: **18**
- `owner-tools`: **8**

## Then

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 18**. Only if it passes, **qualification 8 on the same head**.
4. Any CI stop: report it with the exported diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
