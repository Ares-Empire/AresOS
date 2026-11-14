# Fresh package review — cdd1cbcb

Reviewer: gpt-6.1-sol (high), read-only, independent of the concurrent security reviewer.

**FIX — ARIA-labelled credentials remain readable.** `credentialLike()` inspected
HTML labels but omitted the text referenced by `aria-labelledby`, while `name()`
already used it. A normal text input referencing a span saying Password returned
its value in a watched document; a late reader included that Password field in
its approved list and returned the value. Browser-free production-code probes
confirmed both paths. Add privacy-safe referenced-label checks, watched/late and
approved-read tests, German/code labels and a removal mutation.

**FIX — qualification combines different test inventories.** Pair jobs copied the
current test driver into an older runtime, but combine copied only CI helpers.
The merger then compared current-driver proofs with the older test directory.
An in-memory execution of the exact merger reproduced the assertion with
`ab7aba92`, which lacks six current state-test modules. Copy the same driver into
combine and add an older-runtime/current-driver regression.

**Verified:** 70 focused Node tests passed; generated artifacts match; the complete
service unit matches `8b7e799c`. No further actionable defect found in the examined
destination binding, one-call grants, trusted checker or shared-base merge.
Pending CI/latency work was explicitly outside this verdict. No files edited,
browsers/profiles accessed, containers started or GitHub state changed.

CHANGES-NEEDED
