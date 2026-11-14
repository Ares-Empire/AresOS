# 22c: review fixes, round 2

Follow-up to `briefs/22c-review-fixes-1.md`, on the same branch. Review: `reviews/22c-ways-back-after-update/REVIEW-2.md` (gpt-6-astra high on `e44a797c`, CHANGES-NEEDED: two should-fix findings, none blocking). It confirms round 1's three fixes and finds two places where an interrupted or refused command still strands recovery.

**Fix both as the review prescribes:**

1. **A refusal before the change closes its intent.** When the reorder script refuses because the list drifted before `set-default` (nothing was changed), the caller records that definite pre-change refusal durably and closes or archives the open intent, so the next command surveys the list as it is. A script failure that may have followed a change keeps the journal open, as today. The regression test goes on through recovery and a restart on each boot choice instead of expecting the open intent.
2. **Restoration is an exclusive phase.** Once a restoration intent exists for a layout trial, `layout finish` refuses and names `layout abandon` as the next step, also from the original login that is still open. The model gets "return to the original session" as a step.

**For each fix:** a test that fails without it (the review gives the sequences) and a revert proof in the report. No rule of the brief is widened; if a fix would need a changed rule, stop and report.

**Acceptance:** the hosted checks-only run shows only the four fingerprint pins of stage 1b failing, nothing skipped; `test_ways_back` and the model module pass locally; the report gets a section "Review fixes 2".

**Out of scope:** stage 1b (guides, bundle, pins), the harness, a VM run.

**Model:** a Claude agent on Opus (Codex is in its reviews-only band until 2026-11-17). The next reviewer checks only these two fixes and what they touched.
