# 19b final fix round

**Against** the final reviews on `79ae5de1`, both SAFE:
[`REVIEW-FINAL.md`](../reviews/19b-owner-state/REVIEW-FINAL.md) (package, sol high: one nit) and
[`SECURITY-REVIEW.md`](../reviews/19b-owner-state/SECURITY-REVIEW.md) (security, astra xhigh: one should-fix). Read both,
plus `briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` and `briefs/19b-rescope.md`. Fix only what is listed. No
production code change.

1. **Should-fix (security review): the optional oracle misreads an escaped Trash label as "ordinary"**
   (`control/owner_state_oracle/compare.py:58`, lines 65–67). The public warning escapes the backslash of an IMAP
   role such as `\Trash` (two literal backslashes); the oracle's expression accepts zero or one. Make the oracle
   understand the escaped public representation; add regressions for direct and ancestor special roles (the
   reviewer's minimal reproduction is in the review); keep production escaping and the separate `G22-rename`
   regression unchanged. Regenerate the affected compact-ledger entries and the quiet-gap entry
   (`control/mail_tests/owner_state_quiet_gaps.json:50`), and correct the report line that calls the point-zero
   rename case "ordinary" (`REPORT.md` around line 2942). Run the optional workflow once by hand to show the ledger
   still matches.
2. **Nit (package review): the storage claim is too broad** (`REPORT.md` around line 2954). Qualify "zero permanent
   journal bytes" as zero growth for the five measured samples, and name the paths that add context transactions
   (for example draft APPEND).
3. **Known limit wording (security review, accepted limits):** state precisely in the re-scope section that an
   explicit new repair after the 15-minute quiet period can create a second identical Sent copy if the first appears
   late (one SMTP delivery, two Sent copies; owner-accepted), while replaying the same operation stays inert.

**Verify:** the oracle self-tests and the new regressions locally; Control base, Control Mail and Control boundary
each passing twice on the finished head; the optional workflow once. Wait on CI with one blocking shell call per run
(`gh run watch <id> --exit-status --interval 60`, or one loop over the named runs); never poll run status one turn
at a time. Add a short "Final fix round" section to `REPORT.md` (what changed, run IDs). Don't run your own review.

## Rules for this run

The "Rules for this run" of `briefs/19b-rescope.md` apply unchanged (worktree and branch only, draft PR #26 against
`pkg/19-mail`, never merge or force-push, privacy check without `--no-verify`, no production code or tool behaviour
change, never weaken a test, no real accounts or provider names, `Codex-Model: gpt-6.1-sol (xhigh)` trailer).
