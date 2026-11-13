# 19b pause note (2026-11-11 07:40, package lead)

Claude's planned morning pause. The Codex stage-3 finish round keeps running; the package lead resumes from here.

## 1. First: decision 24 clarified by the owner (relayed by the lead, applies from Thu 2026-11-12 00:00)

The owner has clarified decision 24 (the lead relayed it with his quotes). The baseline is a normal MCP/CLI tool, safe
the way a good MCP is: it asks before risky calls with the exact content shown and bound, checks its inputs, uses
least access and never returns credentials. It is not "nothing could ever go wrong". Extra care applies only to
AresOS-specific risks: the system operator, disks, credentials, and things hard to undo. "If it takes long to get it
right, it takes long," but a more efficient process helps, since many tools are coming.

The lead is drafting what this changes for 19b (likely stage 3's scope, the strict 2.2M-entry gap ledger, and the
security panel's threat model; no double send after a crash stays) and is taking it to the owner. **Don't change the
build because of it until the lead confirms.**

## 2. State

- **Branch / PR:** `pkg/19b-owner-state`, draft PR #26 against `pkg/19-mail`
  (https://github.com/Ares-Empire/AresOS/pull/26). Local and remote heads were equal at 07:39 (`639db28b`); this note
  is committed on top. Codex has uncommitted work in the tree (`storage.py`, oracle `model.py`/`FORMAT.md`,
  `COVERAGE.md`, `KNOWN-GAPS.md`, new `RESTORE-S3-FINISH.json`, `STORAGE-S3-FINISH.json`); leave it alone.
- **Running Codex job (do not touch):** the stage-3 finish round from `briefs/19b-s3-finish.md`. Model
  `gpt-6.1-sol`, effort `xhigh`, session `01a1c8d3-e4e3-74b2-9c25-06aa7458bb5a`, PID 38912, JSON log
  `~/AresOS-19b-s3x.log`, last message `~/AresOS-19b-s3x.last.md` (written when it ends). If it stops on a usage
  limit, resume it with
  `codex exec resume 01a1c8d3-e4e3-74b2-9c25-06aa7458bb5a -m gpt-6.1-sol -c model_reasoning_effort=xhigh -c sandbox_mode="danger-full-access"`.
  Codex weekly usage was 23% at 07:39 (allowance must last to Tue 11-17 10:53).
- **CI at the pause** (head `639db28b`, started by Codex; not yet acceptance):
  Control base 42973307164, Control Mail 42973307351, Control boundary 42973316823 (attempt 2); an earlier base run
  42973107925 on `a5740e00` was in progress.
- **What this round is doing:** applying `STORAGE-S3-FINAL.patch`; the first-write full-disk fix under D3
  (`STORAGE-S3-FIRST-WRITE.py` as regression); then finishing stage 3: every-fault-mode comparison, the complete
  restore fault sweep with the six restore comparisons passing, an empty known-gap list, all Control workflows twice,
  and the report.
- **Decisions on record:** D1–D4 (`briefs/19b-s1-fixes.md`, `briefs/19b-s3-start.md`; D4 with the lead's condition
  that a reply is quiet only after its resolving commit succeeded); owner storage decision board #176, 2026-11-11,
  "Yes, accept" (0.95 KB per sent mail, +0.19 KB per extra recipient, 0.6 KB per delete, 0.9 KB per move; report a
  rise above ~10%), recorded in `briefs/19b-s3-finish.md`. **Still to do:** add that answer with its date to the
  stage-3 section of `REPORT.md` once the running round has finished (it started before the decision).
- **Stage verdicts so far:** stage 1 ended after three fix rounds with three findings folded into stage 2's part A;
  stage 2 SAFE from sol, astra and the Claude oracle reviewer at `7b0e9a05` (CI twice on `31988927`). Stage 3 not yet
  reviewed.

## 3. What's next

1. When the finish round ends: check it (scope, privacy, CI twice on its finished head, known-gap list empty,
   restore sweep passing, the first-write regression, storage figures within ~10% of the owner's table, the
   `warnings.py`/`paging.py` change list for Chrome).
2. Stage-3 reviews in parallel: sol high (stage), astra xhigh (storage faults and owner state), and a Claude oracle
   reviewer (`REVIEW-S3*.md`); fix rounds scoped to findings, at most three. Their scope may change with the lead's
   decision-24 draft.
3. Then message the lead "19b panel ready" with the head commit and wait for the go before the A–D astra panel
   (A approvals and actions, B storage faults, C owner-visible state, D remote evidence), which is also the final
   review of Mail plus 19b.
4. Waiting on CI and Codex: one background waiter per job that wakes only when the job ends, a JUDGMENT-CALL or
   PLAN-GAP appears, or after 3 h (`/private/tmp/claude-501/-Users-pab/5d5bbd0b-a538-400c-b84f-360fe127662f/waiter.sh LOG PID`).
   In every Codex brief, require one blocking `gh run watch` per CI run.

## 4. Where Fable 5.2 would help most next week

1. **Hard reviews once Codex is out (from about Fri):** the stage-3 oracle-independence and storage-fault reviews,
   and if needed parts of the A–D security panel (especially C owner-visible state and B storage faults). The
   Claude oracle reviewer found the most in stage 2 (alteration-test teeth, fault-free false expectations); a
   stronger model on that angle is the best use.
2. **Design text for decision 24's consequences:** rewriting 19b's remaining acceptance (gap ledger, stage-3
   scope, panel threat model) to the owner's "normal good MCP" baseline, and the matching section of the design
   docs, so later tool packages (Chrome and the ones after) inherit a smaller, clearer process.
3. **Stuck bugs:** the restore reconciliation and the every-mode differences the last sample showed (settlement,
   expiry, maintenance, archive, duplicate send, onboarding), if the finish round doesn't close them.
4. **Chrome's follow-up:** working out how Chrome adopts the changed `warnings.py` (a generic warning occurrence)
   and the projection, if 19b lands while Chrome is mid-review.
