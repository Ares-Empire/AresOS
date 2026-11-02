# 14zg: Allow a verified chain of nested sudo relays; probe 16 and qualification 6

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zf still apply, with the change below.

## Integrator decision on the 14zf PLAN-GAP

The guide's route nests relays:
- `sudo -i` on tty3 opens a root shell on pts A.
- `sudo /var/lib/ares/at …` inside it runs the tool on pts B.

My 14zf "one pts throughout" rule was too narrow. Replace it with a **verified relay chain**:

1. Walk the ancestry from this process up to the logind session's physical tty (T0, tty3 or tty4, from 14zf's cgroup session).
2. Between consecutive processes, the controlling tty may change **only** at a `sudo` process:
   - Each `sudo` S_i has its own controlling tty equal to T0, or to the pts created by the previous sudo.
   - The processes below S_i (its monitor, the command, any shells) sit on the new pts P_i.
   - P_i must be a pts that appears first at S_i's direct descendants. Nothing above S_i may already use it.
3. **At most 3 sudo hops.**
4. Any other tty change STOPs with the existing message. That includes a non-sudo process on a new pts, tmux, screen, `script`, ssh or a terminal emulator.
5. The innermost process must be this tool, on the last P_i, or on T0 if no sudo is in between.
6. All the other 14zf and session checks stay as they are.

**Tests** (modelled `/proc` trees):
- direct tty3: pass
- one sudo: pass
- the guide's `sudo -i` then `sudo at`: pass
- three hops: pass
- four hops: refuse
- sudo on a pts not created by the previous sudo: refuse
- tmux or `script` anywhere in the chain: refuse
- a graphical or remote session: refuse
- a pts reused above its sudo: refuse
- the real local pts reproduction: as appropriate

Also check that the harness's typed route matches the guide (`sudo -i`, then `sudo …`) and the commands in `commands.json`. Regenerate the payload and fingerprint everywhere.

## Then (owner's $6 cap; about $2.20 billed)

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push, carrying 14ze, 14zf and 14zg.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 16**. Only if it passes, **qualification 6 on the same head**.
4. Any CI stop: report it with the exported diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
