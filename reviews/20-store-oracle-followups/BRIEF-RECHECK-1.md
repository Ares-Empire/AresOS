Codex gpt-6-astra, 2026-11-18. I read the revised brief at `255f559a`, BRIEF-REVIEW-1, the revision diff, design documents and relevant implementation/tests. I ran **128 oracle/results tests and 9 Mail/export tests—all passed**, plus scratch barrier probes before dispatch and after admission.

| BRIEF-REVIEW-1 finding | Closed? | Where |
|---|---|---|
| BLOCKER: latch clearing permits same-request effects | **Yes** | Barrier lifecycle and effect gates: [briefs/20-store-oracle-followups.md:63](../../briefs/20-store-oracle-followups.md#L63). Regression: [:128](../../briefs/20-store-oracle-followups.md#L128); build step: [:345](../../briefs/20-store-oracle-followups.md#L345); mutation: [:394](../../briefs/20-store-oracle-followups.md#L394). |
| SHOULD-FIX: package 43 CLI overlap | **Yes** | Canonical channel command and integration owner specified; historical oracle label preserved: [:480](../../briefs/20-store-oracle-followups.md#L480). |
| NIT: executable exports beneath dot-prefixed paths | **Yes** | Executable exports under `control/test-work/`; logs separate; FilePolicy unchanged: [:358](../../briefs/20-store-oracle-followups.md#L358). The previously affected export test passed. |

No new findings.

The barrier covers the whole request, including caught failures after admission and within batches or a confirm’s apply. Neither catching an exception nor successful cleanup resets it; subsequent effect boundaries must check it. Restart-free recovery remains restricted to **this invocation’s first fence append failing, followed by successful truncation to its original offset and successful journal fsync, before indexing or SQLite work**. Later-phase and cleanup failures retain the persistent latch.

The scratch probes produced **zero DATA after failure, then one DATA and one APPEND on a successful new request**. Removing the barrier restored same-request DATA. The named regression is `test_failed_predispatch_flush_blocks_effect_until_next_request`; its paired mutation removes the barrier while retaining narrow latch clearing. Evidence: `assertions.log` and `late.log` in the reviewer's scratch folder `.work/recheck-302/` (not committed).

Items 2/3, the re-pin plan and expected shape, and “What must not change” are unchanged. Step order is preserved. All 13 previous mutation mappings remain, with the barrier mutation added; each names a relevant rejecting test purpose.

The [owner question](../../briefs/20-store-oracle-followups.md#L491) is faithful, understandable, and **“yes” is sound**. The brief is now sufficiently concrete for a gpt-6.1-sol builder.

Final Git status shows **no tracked changes**; the pre-existing untracked review is untouched. No workflows dispatched.

READY