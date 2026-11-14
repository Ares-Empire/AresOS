# Guarded-reload fixture scoped package review

Reviewed the working fixture/test delta against `63e684a4`, including `guardedHandoffClick`, its three pure Node regressions and the removal probe. Production runtime and approval rules are unchanged.

No actionable FIX found. The retained run `43521476596` receipt identifies revision 3→4 after reload in both installation modes, with identical rows/editables and the runtime correctly refusing the changed view. The helper addresses that fixture timing: it requires the intended reload refusal, obtains a different document and two agreeing reference views using reads, verifies the old reference still refuses, then attempts exactly one guarded click. Receiver-count assertions remain and are supplemented before that final input. An uncertain final result propagates without replay.

Verified:

- `node --test control/chrome_tests/review-reload.test.mjs`: **3 tests passed**, zero failures/skips/cancellations; **36.593166 ms**.
- Independent in-memory helper probe: delayed parser baseline passed with one final input; removing the new-document/stable-view wait was rejected.
- Original reload refusal and final receiver-count checks are preserved. The new tests also reject an unrelated stale-reference reason and demonstrate no retry after an uncertain dispatched input.

The corrected browser fixture and a new final-head CI pair remain to run; these local checks do not establish final acceptance. No browser/profile, container or GitHub state was accessed or changed. No code was edited; this report is the only review artifact written.

SAFE
