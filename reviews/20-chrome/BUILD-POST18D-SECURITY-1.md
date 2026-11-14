# Fresh security review — cdd1cbcb

Reviewer: gpt-6-astra (xhigh), independent and read-only.

**FIX — credential exclusion misses accessible labels.** `credentialLike()`
ignored `aria-labelledby` and checked associated HTML labels individually,
although the displayed name combined them. Both an ARIA reference to Password
and two labels saying Security and code disclosed values in a watched document.
In a late document, normal reads withheld values but the asking field list
included the credential; approval then disclosed it. Production-code, browser-free
probes reproduced both cases. This is credential disclosure, not an accepted
hostile-page action-recognition limit.

Inspect referenced and combined label text with the value-free traversal before
filled-state checks or value access. Preserve sticky protection. Test watched and
late documents, the revealed-before-take browser fixture, exclusion from questions
and results, replay, ingress absence, and removal probes for both label paths.

No additional harmful defect was found in the reviewed native URL/base handling,
destination/form-owner/target bindings, exact one-call typed reads, transient
values, generated asks, current-owner trusted checker, native precedence harness
or complete shard inventory. The service unit matches `8b7e799c` exactly.

**Verified:** 56 reader tests from the reviewed commit passed; two additional
production-code probes exposed the missing coverage. Three precedence/shard tests
passed. Read-only Python checks confirmed ask coverage and unit identity. Pending
CI, latency measurements, targets and the regression guard were declared ongoing
work, outside this verdict. Later working-tree edits were not reviewed. No
browser/profile, container, edit, commit or GitHub mutation was used.

CHANGES-NEEDED
