# 14zr: One --property per loginctl selector; scoped diagnostics; probe 25 and qualification 14

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zq still apply, with the change below.

## What qualification 13 proved

- The hold fix works (the exact helper was confirmed in the VM). `title` passed after `switch`.
- **AresOS booted.** The physical tty3 login and sudo on AresOS passed.
- `layout begin us` passed the recovery-state and disk gates, then stopped, with zero mutations, at the session identity: `loginctl show-session 5 --property=Id,TTY,Audit,Scope`.

## Fix

1. **loginctl selectors (owner-tool bug).** `loginctl` stores each `--property` argument as **one** selector and doesn't split commas (systemd `loginctl.c`, cited in your report). Two calls are affected:
   - `owner.py:880` (`Id,TTY,Audit,Scope`)
   - `owner.py:888` (`Service,Type,Remote,Name,User`)

   Pass **one `--property=` per property**, or one call per property with `--value`. Parse the real output format (`Key=Value` lines, in the order systemd prints them), and require every requested key exactly once.
2. **Audit every `--property`/`-p` use** in the payload and the harness, tool by tool. Check each one against the pinned systemd 258 source, citing the source:
   - `systemctl show` documents comma lists, so it's fine if that holds.
   - `loginctl`, `busctl` and `localectl` may not split commas.
3. **Real-format tests:** fixtures built from the systemd source's real output for each tool. A comma-joined selector must fail the test.
4. **Scope the owner diagnostics' journal capture to what the decision needs**, for example `-u systemd-logind` and the tool's own unit, with a bounded line count. Kernel messages and unrelated services then don't land in the owner's private records or in CI artifacts.
   - If a kernel `Loaded X.509 cert '<name>: <40 hex>'` message can still appear inside a journal JSON `MESSAGE` field, extend the 14v artifact class to exactly that decoded field value (with `_TRANSPORT=kernel`), recorded per occurrence.
   - Anything else stays a STOP.
5. Regenerate the payload and fingerprint everywhere. Package 15 takes the new fingerprint later.

## Budget (owner's $10 cap; about $7.55 billed)

One push, plus probe 25, plus a qualification of at most 160 is about $1.43 at worst, which fits. Settings for package `14` only:
- `minute_cap`: **1800** (1523 + 238 = 1761)
- `dispatch_caps.probe`: **26**
- `owner-tools`: **15**

If the guard computes that the $10 can't cover the worst case, stop and report. Don't dispatch.

## Then

1. Pinned local gitleaks, the replay and strict checks; a local Windows retry is allowed. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 25**. Only if it passes, **qualification 14 on the same head**.
4. Any CI stop: report it with diagnostics, no rerun.
5. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
