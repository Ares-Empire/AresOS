# 14zza: Classify approved findings by their whole source line, not gitleaks' redacted Match; qualification 19 on the probe 30 head

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zz still apply, with the changes below.

## Integrator decision on the probe 30 artifact-gate refusal

The refusal is correct in spirit, but it rests on the wrong field. Gitleaks' `Match` is a redacted, possibly truncated excerpt, and an approved class must never depend on it.

1. **Classify each finding by the whole line itself.**
   - Read the actual line at the finding's file and line in the private artifact or log, and match that whole line against the approved class pattern:
     - the kernel `Loaded X.509 cert '<name>: <40 hex>'` line
     - the 507 public ISO names
     - the 14zz cosign checksum line
   - Record the line's SHA-256.
   - Use the redacted `Match` and `Secret` only as a cross-check: the secret's position must fall inside the approved token of that line.
   - A finding whose file or line can't be read, or whose line doesn't match a class, still STOPs.
2. **Where the fix goes:** the classifier is local tooling (`.work/`, not in the pushed tree), so fixing it doesn't change the pushed head.
   - Test it on the actual probe 30 finding that was refused, plus the earlier accepted ones.
   - Then rerun the artifact gate on probe 30's retained artifacts and logs.
3. **If the gate passes,** run **qualification 19 on the same head, under the existing probe 30 acceptance.** No new push and no new probe, unless the fix turns out to need a change in the pushed tree. In that case, make one push, then probe 31 and qualification 19.
4. Then **STOP and report** as in 14zz.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
