# 14zn: Find where the typed token stops; shorter token wait; probe 21 and qualification 9-retry

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zm still apply, with the change below.

## What we know

Qualification 9 typed the visible `GitHub username:` through both sudo relays, and the tool accepted it and showed `Read-only token (hidden): `. Readiness then proved Python 7609 on the inner pts2, ECHO off, and the exact prompt. `GH_TOKEN` was typed once with `owner_keys.physical_keys(…, 'de')`, then `ret`. Fourteen minutes later the cursor was still right after the prompt: getpass never wrote its newline.

**Integrator reproduction (zero cost, WSL as root, real sudo 1.9.15 with `use_pty`, Python 3.12, a pty driven at 0.12 s per byte):** `sudo -i`, then `sudo python3 -c '…input("GitHub username: ")…getpass.getpass("Read-only token (hidden): ")…'`, a visible username, then a dummy token `ghs_AbC123xYz_9Q0` plus CR. **It returns normally**, with one relay and with two. So nested sudo plus getpass is fine in principle, and so is the guide's route. The difference must be the VT and keyboard path, the guest versions (sudo 1.9.17, the guest Python), or the token itself.

## Do

1. **Diagnostics, captured over serial at the token-completion wait and on any hidden-completion timeout.** No secret values; counts and flags only.
   - Input and output queue byte counts (`TIOCINQ`/`TIOCOUTQ`) for tty3, every relay pts and the reader's pts.
   - termios flags (ICANON, ECHO, ICRNL, IXON, IEXTEN, ISIG) for each.
   - For every process in the chain: `state`, `wchan` and the syscall number from `/proc/<pid>/syscall`.
   - The active VT (`/sys/class/tty/tty0/active`), tty3's `KDGKBMODE` and LED state.
   - The guest Python and sudo versions.
   - The **length** of the token typed, the number of key events sent, and whether the last one was `ret`.
   - Whether any character in the token needed a non-default mapping (character classes only).
2. **Token wait:** the tool's own `login` finishes within about 2 minutes (podman's timeout is 90 s). Wait **180 s** for the token reader to complete, then capture the diagnostics above and STOP. Other waits stay as they are.
3. **Guest versions:** check from the pinned image whether its Python's `getpass` differs from 3.12 (for example any 3.13/3.14 change), and whether sudo 1.9.17 changed input relaying compared with 1.9.15. Cite the source.
4. **Local tests** for the diagnostics collector, using modelled `/proc` and ioctl results. Don't change the owner tool.

## Budget (owner's $10 cap; about $5.14 billed)

One push, plus probe 21, plus a qualification of at most 160 is about $1.43 at worst, which fits. Settings for package `14` only:
- `minute_cap`: **1500** (1124 + 238 = 1362)
- `dispatch_caps.probe`: **22** (21 is the next)
- `owner-tools`: **11** (10 is the next)

## Then

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 21**. Only if it passes, **qualification 10 on the same head**.
4. Any CI stop: report it with the new diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
