# Preexisting-dialog reload fixture: scoped security recheck

**Verdict: SAFE.** Reviewed the fixture-only diff over `63e684a4`, including
`guardedHandoffClick`, its three Node regressions and the settling-removal case.
Read the committed `review-reload-failure-43521476596.json`: both installs
refused a revision-3 view after revision 4 appeared, with identical rows/editables.
That evidence supports fixing fixture scheduling; it does not justify relaxing
the runtime's stale-view check.

The helper requires the intended guarded-reload refusal, waits through read-only
queries for a different document and two identical complete references, verifies
that the old reference still refuses, and dispatches the fresh input once. The
receiver count must remain exactly one before and after that input. Errors from
the dispatched input propagate without retry; a failure to settle also fails the
fixture. Runtime code, asking-read binding and withheld-form refusal are unchanged.

**Verified:** `node --test control/chrome_tests/review-reload.test.mjs` passed all
three tests. Independent in-memory removal of the document/view settling check
was rejected by the delayed-parser regression. A separate never-settling probe
failed with zero guarded input dispatches. Only plain Node ran; no browser,
profile, container or GitHub mutation was involved. Only this review file was added.

**Still required:** hosted verification and every required final workflow on the
new candidate. This scoped verdict does not convert superseded runs into final
acceptance evidence.
