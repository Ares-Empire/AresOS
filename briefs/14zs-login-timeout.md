# 14zs: Keep each console login inside login's timeout; restart safely if the reader changes; probe 26 and qualification 15

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zr still apply, with the change below.

## What qualification 14 proved

- The loginctl fix works: six real queries with separate `--property=` arguments.
- The scoped journal works.
- `layout begin us`, the rejected plain-US login, the refused reboot during the unproven trial, and `layout revert` all passed on AresOS.
- Then the tty4 login reached its hidden password prompt (`login` PID 13852, canonical, ECHO off, in read). The 30-character password window delivered 64 of 64 events. **Before Enter, PID 13852 was gone** and an unexpected reader (PID 20186) was in the foreground. The guard correctly withheld Enter.

## Diagnosis (integrator; confirm it)

util-linux `login` exits after **`LOGIN_TIMEOUT`**: 60 s by default, or the `/etc/login.defs` value. The getty then respawns.

Between the username and the password, the harness spends time on readiness observers, counter setup and staged serial transfers. That can push the username-to-Enter time past the timeout. The password keys typed after the old `login` exited would then land in the new getty as a **visible username**. Enter was withheld, but the test password may have been shown on tty4.

Confirm the guest's `LOGIN_TIMEOUT`, and the timing between the username, the prompt and the replacement, from the image and the retained receipts.

## Fix (harness only)

1. **Prepare first, then type fast:** set up the counters and readiness observers **before** typing the username. Keep username → password → verified Enter inside a measured budget: at most half of the guest's `LOGIN_TIMEOUT`, read from `/etc/login.defs` or the binary default. Record the elapsed time.
2. **Check the reader before every secret:** right before typing any hidden value, re-verify that the reader is the same `login` PID and still within budget. If not, don't type the secret.
3. **If the reader changes before Enter:**
   - Clear the new reader's line with the line-kill key.
   - Prove the screen and reader are back at a fresh `login:` prompt.
   - Restart the whole login once (username, then password).
   - A second replacement STOPs.
   - Record in the evidence whether any secret keys went to a non-hidden reader (counts only), and mark that run's VCSA and screenshots as secret-tainted, kept private and never committed.
4. **Apply the same rule** to the tty3 and tty4 logins in all stages.
5. **Local tests:**
   - timing budget: pass
   - budget exceeded, so no secret is typed
   - reader replaced before Enter: kill-line, restart, pass
   - replaced twice: STOP
   - the qualification 14 shape

## Budget (owner's $10 cap; about $8.12 billed)

One push, plus probe 26, plus a qualification of at most 160 is about $1.43 at worst. The guard must confirm the remaining $10 allowance covers it; otherwise stop and report. Settings for package `14` only:
- `minute_cap`: **1900** (1619 + 238 = 1857)
- `dispatch_caps.probe`: **27**
- `owner-tools`: **16**

## Then

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 26**. Only if it passes, **qualification 15 on the same head**.
4. Any CI stop: report it with diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
