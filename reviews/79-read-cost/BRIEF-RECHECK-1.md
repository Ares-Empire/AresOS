Codex gpt-6-astra, 2026-11-17. Read AGENTS.md, BRIEF-REVIEW-1.md, the lead’s calls, `git diff 5ef37bf3..bcd37508`, the revised brief, and the relevant committed, qualification, adapter and storage code. Reviewed head `bcd37508`; no files modified.

| BRIEF-REVIEW-1 finding | Status | Where and why |
|---|---|---|
| BLOCKER: stat shortcut loses rollback detection | **Closed** | [Design](../../briefs/79-read-cost.md#L94), [steps 3–4](../../briefs/79-read-cost.md#L294), [test 3](../../briefs/79-read-cost.md#L255), [test 9](../../briefs/79-read-cost.md#L261), [mutation](../../briefs/79-read-cost.md#L334). Exact bytes are compared on every cached use. Test 9 restores the signature and requires repeated rollback refusals through all three readers **without another write or cache eviction**. Reintroducing the shortcut fails tests 3 and 9. |
| SHOULD-FIX: `shipped` must return a deep copy | **Closed** | [Design](../../briefs/79-read-cost.md#L122), [step 4](../../briefs/79-read-cost.md#L297), [test 13](../../briefs/79-read-cost.md#L265), [mutation](../../briefs/79-read-cost.md#L346). Nested getter mutations are checked before and after invalidation; internal code uses the private baseline. |
| NIT: constant-time claim | **Closed** | [Outcome](../../briefs/79-read-cost.md#L10) and [cost explanation](../../briefs/79-read-cost.md#L166) accurately distinguish removed whole-history work from remaining size-dependent costs. |

No new findings. The latency proof and PR #72 overlap section are unchanged. `e2e4eedc`’s 300-entry leg, ceilings, 60/20 samples, `latency-pair.sh` and `latency-reference.json` remain protected. “Must not change” differs only by the authorized sweep-growth allowance.

All eight steps retain their order; the 16 test numbers and 20 mutation rows agree, with a catching test identified for every mutation. The brief is buildable by gpt-6.1-sol without unresolved design decisions. Implementation tests and mutations remain for the build and review.

READY