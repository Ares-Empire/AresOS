# 13c: Fix the build wrapper's tool path, then continue 13b

Follow-up on branch `pkg/13-keyboard-layout` (PR #12, draft). Read the 13b section of the REPORT. Briefs 13 and 13b still apply, plus the changes below.

## Where 13b stopped

Image attempt 40152936417 stopped at `cosign: command not found` (exit 127) inside `sudo -E bash os/ci/build-keyboard-release.sh`. The action-installed cosign worked in the unprivileged step before it. This is a wrapper integration error. Nothing was built or published, and the ledger stands at about 8/380 minutes.

## Integrator decisions

1. **The fix.** Resolve every external tool the privileged wrapper uses in the unprivileged step, as an absolute path. That includes cosign and anything else not guaranteed under root's `PATH`, for example skopeo, podman, buildah, jq and oras, whatever the wrapper calls.
   - Pass these paths explicitly across the `sudo` boundary.
   - The wrapper refuses a missing, relative or non-executable path with a clear message, before touching credentials.
   - Add a regression that runs the wrapper's tool-resolution part under a stripped `PATH`.
   - Don't widen credential visibility, and don't skip the old image's signature check.
2. **Image attempts.** Allow **up to two more** image dispatches on the same ledger. Each attempt that stops before publishing doesn't count against publishing, but **publish at most once**. If both attempts stop, stop and report.
3. **Image construction.** I accept 13b's JUDGMENT-CALL as the integrator: derive the release from the exact frozen qualified image, with only `usr/bin/aresos-session` and `usr/libexec/aresos-keyboard` allowed to differ and everything else compared. It still goes to the owner before merge.
4. **Then** continue 13b's plan unchanged: publish/sign/verify, the checks-only native run on the final head, one probe and up to two qualification runs. All rules and the 380-minute cap stand.

## Acceptance

13b's acceptance, plus the fix and its regression, and every image attempt's result in the REPORT.

Push (fast-forward only). Mark PR #12 ready for review only if acceptance is met. Don't merge. Never make anything public.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
