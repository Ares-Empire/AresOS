# Addendum-g scoped security review

**Verdict: SAFE.** Reviewed `c37b865ae972dffbceff64e0aa632946f053a97e` against
`briefs/20-post-18d-g.md`, plus the subsequent fixture-description clarification
that run 248 already contained the earlier operation-header optimization (no
measurement changed). This recheck covers the approved latency targets,
measured-cost replay fixture/test and removal probe, board #216 limit, and the
current REPORT handover/provenance/open-idea wording. No new runtime or browser
class review was opened; asking-read binding and withheld-form refusal are unchanged.

**Verified:**

- Ran all nine `LatencyGate` test bodies using plain Python, loading only that
  test class from its AST. All nine passed. The new test invokes the actual
  `latency-check.py` CLI: optimized plain/audit profiles exit 0; restoring the
  measured history-4000 cost exits 1 and identifies all six calls in each profile.
  Its temporary JSON files stayed inside this worktree's `.work/` and were removed
  by the test.
- Independently compared both replay profiles with the retained run
  `43490400410` summaries: Chrome identity, all six client metrics and all 60
  history-4000 input/wait pairs per profile match exactly. The accepted current
  and `ab7aba92` profiles match the retained run `43502970342` summaries exactly.
  This is a measured pre-optimization cost replay, not a claim that a round-3
  browser run was repeated locally.
- Independently removed the gate's rejection branch in memory. Both restored-cost
  profiles then incorrectly passed, while the unchanged gate rejected them:
  the new removal probe detects loss of rejection. No source file was changed.
- Checked all six ceiling pairs against addendum g. The lead identity/date,
  measurement run, baseline and both profiles are recorded. The owner-accepted
  editable-area limit matches board #216 as recorded in the brief. The REPORT
  retains the 525 ms wait, labels early completion as an open capability idea
  with an estimate rather than demonstrated safety, and identifies remaining
  final-head checks and workflow repetitions.

**Limits:** this review does not establish final acceptance or replace the final
workflow pair. No local browser, browser profile or container was started or
read. No GitHub action was taken. Only this review file was added.
