# Mail fault-job budget: scoped security review

**Verdict: SAFE.** Reviewed the timeout-only workflow diff over `105ed276`, the
retained `mail-43530064032-timeout.json` receipt and the current REPORT handover.
The receipt records sweep 0/6 cancellation at 3617/3616 seconds, four successful
suite jobs and six successful fault shards, with no recorded unittest failure.
The cancelled shards remain incomplete evidence, not passing tests.

The only executable workflow change raises the Mail fault-job timeout from 60
to 120 minutes, consistent with `briefs/20-post-18d.md` section 4's approximate
120-minute target. All eight partitions, commands, assertions, permissions and
artifact collection remain unchanged; the suite-job limit remains 35 minutes.
There is no runtime, browser budget, 525 ms hold, asking-binding or withheld-form
refusal change. This adds bounded execution time without granting new authority
or removing verification.

**Verified:** read the exact workflow diff and receipt; checked the brief's
budget rule and unchanged Mail runner invocation. No test run is needed to
verify this literal CI timeout change. No browser, profile or container was
accessed, and no GitHub action was taken. Only this review file was added.

**Still required:** freeze the new candidate and repeat the full required
verification on that head. The REPORT correctly retains earlier green runs as
intermediate evidence and makes no ready claim.
