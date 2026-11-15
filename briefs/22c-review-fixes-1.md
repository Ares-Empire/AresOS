# 22c: review fixes, round 1

Follow-up to `briefs/22c-ways-back-after-update.md`, on the same branch. Review: `reviews/22c-ways-back-after-update/REVIEW-1.md` (gpt-6-astra high on `169d2f9e`, CHANGES-NEEDED: three should-fix findings, none blocking). The review found the journal repair sound for the council's dead ends; all three findings are places where a recovery path or a check does not reach as far as the brief's rules say.

**Fix all three as the review prescribes:**

1. **An interrupted layout restoration can resume.** `layout abandon` (for a pending trial and for a repair note) records a durable restoration intent and accepts exactly its own intermediate settings, in both directions of a partial write. The model cuts `abandon` between its writes, as it already cuts `finish`.
2. **The reorder is bound to the list the caller journalled.** `os/release/start-next.sh` receives the expected deployment list from before the change and compares it with its fresh read before `set-default`, beside the target's identity. On a mismatch it changes nothing and reports the outside change. The postcondition and `sync` stay. The remaining race between that last read and the call is the accepted limit.
3. **The installed-state protection covers every command that reads the list**, as the review's third finding lists them.

**For each fix:** a test that fails without it (the review gives the sequences), and a revert proof in the report. No rule of the brief is widened. If a fix would need a changed rule, stop and report.

**Acceptance:** the hosted checks-only run shows only the four fingerprint pins of stage 1b failing, nothing skipped; `test_ways_back` and the model module pass locally; the report gets a section "Review fixes 1" with what changed, the tests, the revert proofs and anything the review got wrong.

**Out of scope:** stage 1b (guides, bundle, pins), the harness, a VM run.

**Model:** a Codex builder (gpt-6.1-sol xhigh) while the allowance lasts, otherwise a Claude agent. The next reviewer checks only these fixes and what they touched.
