# 21: review fixes, round 3

Follow-up on `pkg/21-everyday-account-and-chrome` (PR #31). Read `reviews/21-everyday-account-and-chrome/REVIEW-3.md` (CHANGES-NEEDED; TuneD and cached authorization are confirmed fixed, and no other root, image, boot or firmware bypass was found). Fix the one Medium finding as the review proposes:

1. **polkit `imply`:** Flatpak's passwordless `app-update` implies `runtime-install`, so an active `ares` can install system-wide runtimes without the password, despite the explicit `auth_admin` rule.
   - For `ares`, require uncached authentication for `app-update`, or neutralize the implication. Choose the variant that keeps `flatpak --user` passwordless and doesn't break system-wide updates of apps he already installed with the password.
   - Record the choice in the REPORT.
2. **Model implications in the audit:** `polkit-check.js` and the `polkit-review.json` inventory follow `org.freedesktop.policykit.imply`, so an implied action is judged by what it grants. Rerun the inventory and correct the passwordless list.
3. **A live active-session regression:** without the password, `app-update` as `ares` can't be used to install a system-wide runtime.

Rebuild with the throwaway CI path, rerun the in-image checks and the native regressions, and commit the evidence. Board #156 is still open; keep its behaviours. Add a "Review fixes 3" section to the REPORT, then push.
