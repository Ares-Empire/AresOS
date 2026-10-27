# 14zb: Diagnose and fix the stalled private-login capture; local only

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14za still apply, with the change below.

**Where qualification 4 got:** further than any run before.
- Passed: install with the binary firmware check, prepare and its zero-change rerun, network invariance, records/title/export, tools removal, the unattended Windows round trip, corrected stock, and recovery login.
- Stopped: `console.run('login','private-owner-login',…)` passed its username and hidden-input readiness checks. Then `capture_json` never got `ARESOS_CMD_DONE`. The 116-byte serial transcript shows **continuation prompts**: the guest shell was waiting for more input, as if a quote, brace or heredoc terminator never arrived.

## Do (zero cost, from the retained evidence)

1. **Find the cause.** Compare the reconstructed command bytes (2,652 framed / 3,633 wire, at most 1,024 per line) with what the guest received and echoed. Candidates:
   - dropped or reordered serial input (no pacing, or tty buffer limits)
   - a line-length limit
   - the login tool's hidden-input read consuming part of the next command (for example a newline left over from the token entry)
   - a quoting or heredoc defect in this specific command

   Prove the cause where you can (for example with a local pty or serial-like reproduction), and say clearly what is only likely.
2. **Fix the transport for any command over a small size.** Stage it into a root-only tmpfs file through short, individually acknowledged chunks; verify the file's SHA-256 in the guest; only then run it. Keep the existing checksum-framed result protocol.
   - Commands that carry a secret never go through the serial echo. The token stays typed only at the tool's hidden prompt, as now.
   - Never write a credential into evidence, a staged file or a log.
3. **Hidden prompt:** if the hidden-input step can leave stray input, make the harness drain and resync to an idle prompt (the 14j rules) before the next framed command, and record it.
4. **Deadlines:** align the diagnostic reader's 1,800 s with the outer 900 s (or the reverse) so they can't contradict each other. Document the choice.
5. **Local tests:**
   - the exact login-stage command sequence through a simulated serial line that drops or limits input: it must either complete correctly or STOP, and never hang
   - the chunked staging, including the SHA mismatch STOP
   - bash `-n` on every staged script
6. **Check the later stages for the same pattern**, with real retained outputs: verify, switch, the AresOS boot, layout, rollback and keep-stock.

## Rules

Commit locally only, with the pinned local gitleaks. **No push and no dispatch:** the qualification allowance (4) is spent, and the owner's $3 is nearly used. The owner decides on more budget now or the free reset on 1 November.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
