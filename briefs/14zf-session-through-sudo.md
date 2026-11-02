# 14zf: Identify the physical recovery session through sudo's pty; probe 16 and qualification 6

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14ze still apply, with the change below.

## Integrator decision on the 14ze PLAN-GAP

**The defect:** `Tools.session()` requires `os.ttyname(0)` to be `/dev/tty3` or `/dev/tty4`. With the pinned sudo 1.9.17's default `use_pty`, every owner command typed as `sudo …` sees a `/dev/pts/N`, so all layout actions refuse on the real laptop. The handler fixtures faked the tty name.

**Keep the purpose, which is unchanged:** layout actions run only from a local, non-remote text-console login of `ares-recovery`, on tty3 or tty4. The other checks stay as they are: loginuid 1000, the logind facts `Service=login`, `Type=tty`, `Remote=no`, `Name=ares-recovery`, `User=1000`, the session start time and the boot ID.

**Fix:** derive the physical tty from the process's **logind session**, not from stdin's name.
1. Find this process's logind session from `/proc/self/cgroup` (`session-<id>.scope`). Require exactly one, and require it to be the one `loginctl` lists for `ares-recovery` with `TTY` tty3 or tty4. Cross-check `/proc/self/sessionid`, the audit session, if it's available and consistent; otherwise STOP.
2. Stdin must be a tty. If it is **the physical tty itself**, that's the old case: accept it.
   If it is a **pts**:
   - Walk the process ancestry from this process upwards. It must reach a `sudo` process whose controlling tty (`tty_nr`) is that session's physical tty.
   - Every process between sudo and this one must sit on that same pts, sudo's own pty.
   - No other terminal-owning program (terminal emulator, sshd, tmux, screen) may appear.

   Anything else STOPs with the existing message.
3. **Tests**, modelled as `/proc` and cgroup trees, plus the real local pts reproduction you made:
   - direct tty3: pass
   - sudo `use_pty` on tty3: pass
   - sudo on tty4 for the fresh-login proof: pass
   - Konsole pts in a graphical session: refuse
   - an sshd pts with `Remote=yes`: refuse
   - tmux or screen inside a tty3 sudo: refuse
   - a session or tty mismatch: refuse
   - a missing cgroup session: refuse
   - the actual qualification 5 process shape: pass
4. **Audit every other `os.ttyname`/tty assumption** in the payload and the harness for the same `use_pty` effect, and fix it the same way.
5. Regenerate the payload and fingerprint everywhere. Package 15 will take the new fingerprint later.

## Then (owner's $6 cap; about $2.20 billed)

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push, carrying 14ze and 14zf.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 16**. Only if it passes, **qualification 6 on the same head**. Allowances: cap 1100, probe 16, owner-tools 6.
4. Any CI stop: report it with the exported diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
