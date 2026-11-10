# 21: review fixes, round 4

Follow-up on `pkg/21-everyday-account-and-chrome` (PR #31). Read `reviews/21-everyday-account-and-chrome/REVIEW-4.md` (CHANGES-NEEDED; no remaining passwordless root, image, boot, kernel-argument or firmware bypass was found). Fix both Medium findings as the review proposes:

1. **`build.sh` Flatpak guard:** require **exactly** the reviewed implication targets before the edit (`runtime-install` and `runtime-update`), verify the resulting annotation is exactly `runtime-update` after it, and stop the build on anything else. Test added and removed targets.
2. **`vm.py` readiness:**
   - Accept only the exact readiness message as a complete, newline-terminated line. A prefix or suffix (`FAILED ARESOS_JOURNAL_READY`, `ARESOS_JOURNAL_READY_NOT`) or an unterminated record never counts.
   - Add chunked-input and false-marker regressions.
   - Regenerate `vm.py`'s pending-rebind hash with `checkout_sources.records`.

Rerun the native regressions. If `vm.py`'s VM pass is affected, rerun `check_build=build`, and commit the evidence. Board #156 is still open; keep its behaviours. Add a "Review fixes 4" section to the REPORT, then push.
