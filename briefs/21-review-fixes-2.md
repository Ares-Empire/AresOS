# 21: review fixes, round 2

Follow-up on `pkg/21-everyday-account-and-chrome` (PR #31). Read `reviews/21-everyday-account-and-chrome/REVIEW-2.md` (CHANGES-NEEDED; the sudo timeout, terminal paths and the logind denies are confirmed fixed). Fix both as the review proposes:

1. **Blocker: TuneD profile switching is a passwordless route to boot changes.**
   - Deny `ares` the TuneD actions that change profiles or settings, with and without wheel: `com.redhat.tuned.switch_profile`, `com.redhat.tuned.auto_profile`, and any other `com.redhat.tuned.*` action that can change state. Read-only queries may stay.
   - Test them explicitly in both membership cases.
   - Widen the polkit check so an action that can reach the bootloader or kernel arguments can't slip past a name pattern again. For example: review every `yes` action in the evidence, and record in `polkit-review.json` why each one is safe.
2. **Blocker: cached admin authorization.**
   - For anything that can run code as root or change the system, ares's rules return uncached `AUTH_ADMIN`, never `AUTH_ADMIN_KEEP`: systemd unit management, GVfs admin, and every other place the base falls through to `auth_admin_keep`.
   - Add a regression that authorizes once and shows the next privileged call asks again.
   - If something the owner uses often becomes annoying, record it as a JUDGMENT-CALL rather than keeping the cache.

Rebuild with the throwaway CI path, rerun the in-image checks and the native regressions, and commit the evidence. Board #156 is still open; keep its behaviours. Same rules and resource gates. Add a "Review fixes 2" section to the REPORT, then push.
