Reviewed **3e22194**, limited to the requested fixes and touched areas.

1. **CLOSED — second abandon.** Card success links directly to `abandon-completion`. Already-cleared recovery requires the recorded prior PASS; an accidental `Missing private layout-pending record` then reaches completion. Other refusals go to Help. AresOS proceeds through check/typing proof to step 8; stock completes keep-stock, its guarded second boot and records.

2. **CLOSED — interrupted finish.** Begin/revert restart recovery uses the last confirmed map once. Interrupted finish allows old once, then proven new once after failure, then Help. Successful login leads to sudo, one abandon and completion. A sudo rejection stops without retry.

   All eight retained policy files match their hashes, sizes and image bindings. They document defaults **deny=3, interval=900s, unlock=600s**; the retained login/sudo stack does **not enable pam_faillock**. The route stays below three: two failed logins stop immediately; one failed login followed by success and a sudo rejection totals two. Earlier failures or uncertain policy require Help before starting.

3. **CLOSED — requirement to preserve the council condition.** INSTALL-STATUS explicitly says **OPEN — synthetic evidence only**, requiring a native mounted-protected-child refusal with zero mutations and cleanup before release. The runtime condition itself remains open; package 14 VM acceptance remains met.

**New defects:** none found.

Confirmed `git diff 79a67d2..3e22194 -- os/owner-tools docs/install-tools .github os/ci` is empty. Reviewed the changed tests; fresh execution was unavailable because Python is absent and WSL returns `E_ACCESSDENIED`. No files changed.

SAFE