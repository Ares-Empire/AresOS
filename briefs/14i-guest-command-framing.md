# 14i: Fix the guest command framing; check every composed command locally; fifth probe

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Read "14h: Actual fresh gates, native success and framed-heredoc STOP" in `reviews/14-owner-tools/REPORT.md`. Briefs 14 to 14h still apply, with the change below.

## Integrator decision

Stopping was right. The new FUSE media and the capability step worked. The fault is in `switch_vm.framed`: it appends ` > "$result"` directly to the command text. When a command ends with a heredoc, its closing delimiter line becomes `PY > "$result"`, so the heredoc never closes.

The local walk missed this because it used stand-in guest responses and never ran the composed shell text.

So:
1. **Fix `framed`:** put the command in a brace group, with the redirect on the group:
   - `{` on its own line, then the command, then a newline, then `} > "$result"`.
   - A heredoc then closes on its own line.
   - Single-line commands, which packages 11 and 13 qualified, behave the same: same stdout capture, same `set -e`, same exit status.
   - Don't change the export protocol.
2. **Execution regression:** run `framed()` output in a real local `bash` (Git Bash or the existing WSL bash; no package installs) for:
   - a single-line command
   - a multi-line command
   - a command ending in a heredoc, with and without a trailing newline
   - a failing command (the non-zero exit propagates, with no export)
   - a command whose stderr is noisy

   Each case must decode the checksum-framed JSON exactly, or fail exactly.
3. **Check every composed command:** at the stand-in walk's stub boundary, run `bash -n` on every command the harness would send to the guest. Treat any stderr output, warnings included, as a failure.
   - Do the same for any other wrapper that joins command text, if there is one.
   - This is the zero-cost guard for the class of bug that cost probe 4.
4. **Budget:**
   - One more probe allowance (5 in total; 4 are spent, 46 minutes).
   - One qualification is planned. The second stays optional, behind its own fresh guard.
   - Cap 350. Org reserve 150.
   - Recheck the ledger, billing and privacy CI right before dispatch.

## Then

Pinned local gitleaks before every push. The local replay as in 14e and 14f. Then the fifth probe, then the qualification, per briefs 14 to 14h. If the probe hits a new, different blocker, stop and report as before; don't rerun. Mark PR #13 ready for review when acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
