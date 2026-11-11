# Brief 20 (Chrome): paused, 2026-11-11 08:30

The package lead paused here on the lead's instruction. Claude's weekly plan is nearly used up. Codex keeps
running on its own, and nothing waits on a timer.

## First: the owner clarified decision 24

The lead relayed this on 2026-11-11 at 08:20, with the owner's words. It applies from Thursday 00:00.

- **The baseline is a normal MCP or CLI tool, safe the way a good MCP is.** It asks before risky calls, shows and
  binds the exact content, checks its inputs, uses the least access it needs, and never gives Claude typed passwords.
- **Proving that no adversarial page can ever slip an action past the question is not the baseline.** Such bypasses
  become documented known limits. They get fixed when the fix is cheap, or when the action carries an AresOS-specific
  risk.
- **For Chrome, the owner wants capability:** "a better tool for AresOS that's more efficient with readings,
  navigation, free tab navigation etc."
- **The re-check panel is on hold.** Its threat model has to change before it runs, and the lead is drafting what
  changes and taking it to the owner. No build changes because of the clarification until the lead confirms the
  concrete list.

## State

**Branch and PR:** branch `pkg/20-chrome`, draft PR #27 into `main`. Nothing is merged into `main`.

**Fix round:** every finding of the panel on `60b94384` is fixed, in two parallel builds. The findings are listed
in `briefs/20-review-fixes.md`, and the seven reviews are in this folder.

- **Part P** (page, extension, binding, questions): finished at `df9b3fc5`. All 80 named cases passed twice in both
  install modes. Base, Mail, boundary and qualification also passed twice.
- **Part S** (state and storage): PR #34, green twice on `1418fcde`, merged by the package lead in `3b37bd57`. Its
  report is `STATE-FIXES-REPORT.md`.
- `7c644c6b` updates the lead's Claude review.

**Decisions made during the round:**

- On another controlled document, an asking call goes through that document's guard. When ownership is unclear,
  the call is held.
- Injection avoids `Runtime.enable`.
- The page script is armed when a page opens a native dialog.
- A dialog that was already open when Claude took the tab goes to the owner: the tool waits a bounded time, never
  hangs, and the tab is usable again once he answers it.
- A dialog opened through a borrowed-realm function asks, unguarded, and is answered once on approval.
- A file the owner picked is bound by its SHA-256 and shown in the question.
- Inline `about:blank` and `srcdoc` editors are covered, not refused.
- Popups a Claude tab opens follow the reload-on-first-act rule. Claude's control of them shows as the opener's
  badge, and each has its own Stop in the existing action popup. Nothing of ours opens a window or takes focus.
- Catalogue snapshots expire 5 minutes after the last page request, or 30 minutes after they were made, whichever
  comes first. The 30-minute cap is in the running integration build.

`REPORT.md` and `STATE-FIXES-REPORT.md` record these as decided rules. The lead writes them into `docs/design/CONTROL.md`
section 6.

**Running now:** the integration build of brief `20-integrate-3.md`.

- Codex session `01a1c8af-1843-7512-8616-bdbf64a067a2`. Its log is `~/AresOS-20-integrate3.log`, and its last message
  will be in `~/AresOS-20-integrate3.last.md`.
- On head `f25ac736`, base, Mail, boundary and qualification have each passed twice.
- Chrome runs `42963287917` and `42963294395` are still running. The build's independent audit of their artifacts
  comes after them, then its report commit and push.
- This file is committed locally on top of `f25ac736` and goes out with that push. If the build stops before
  pushing, push the branch on resume.

**Workflow runs:**

| Branch | `control-chrome.yml` runs used | Allowance |
|---|---|---|
| `pkg/20-chrome` | 174 | about 185 |
| `pkg/20-chrome-state` | 17 | 25 |
| `pkg/20-chrome-adapters` | 6 | 25 |
| `pkg/20-chrome-qual` | 15 | 25 |

All three side branches are merged.

**Still open:**

- The owner's own Enter is recorded as "passes in CI, panel to confirm".
- Test group 12 waits for 18d's precedence harness.
- The moves onto 18d and 19b are listed in `REPORT.md`.
- Image handoffs: the excluded-sites setting at `/etc/aresos/control/chrome-excluded-sites.json`, the `gh` verifier,
  and the service unit with IPv4 and IPv6 allowed. The lead takes these to brief 18c and `laptop-aresos`.

**Worktrees:**

- `~/AresOS-20-chrome` is the working branch.
- `~/AresOS-20-panel` is a read-only review copy, detached at `60b94384`.
- `~/AresOS-20-state`, `~/AresOS-20-adapters` and `~/AresOS-20-qual` belong to branches that are already merged and
  can be removed.

## On resume

1. Read the integration build's last message. Check that the Chrome pair on its final head passed in both install
   modes. If it did, send the lead the head; if not, fix what failed within the run allowance.
2. Wait for the lead's concrete list from the decision-24 clarification. Then rescope the re-check, its angles and
   threat model, and any fix work to that list. The scoped re-check had been prepared: each reviewer checks its own
   findings plus the fix diff, with astra for A to D, sol for the package review and E, and the lead's Claude
   reviewer.

## Where Fable 5.2 would help most next week

Codex's allowance runs out from about Friday.

1. **The re-check under the clarified baseline.** Judge the integrated Chrome tool as a normal, safe MCP tool: risky
   calls ask, exact content is shown and bound, inputs are checked, access is least, and no passwords reach Claude.
   Sort what remains into defects to fix and documented known limits. This hard review also confirms or closes the
   owner's own Enter.
2. **Section 6 rewritten for the clarified decision 24.** Write in the rules decided in this round, and make the
   capability direction the owner asked for concrete: more efficient reading, navigation and free tab navigation.
3. **A simplification plan.** Which parts of the guard and binding machinery the clarified baseline no longer
   requires. Removing them would make reads and navigation faster and the code smaller. Each removal is checked
   against the owner's "ask before removing features" rule.
4. **Stuck integration work.** Move onto 18d (generated rules, `user-mcp.json`, test group 12 in the precedence
   harness) and onto 19b (the shared committed read path in place of Chrome's journal fallback) once those merge.
