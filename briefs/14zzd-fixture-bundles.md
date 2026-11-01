# 14zzd: Build test bundles from the manifest, never from the source tree; probe 33, qualification 21

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zzc still apply, with the changes below.

## Integrator decision on the probe 32 STOP

Your diagnosis is accepted. The CI suite runs without `-B`, so earlier imports wrote `__pycache__` into the tree the fixtures copied, and the strict bundle check correctly refused the result. Production is unaffected: the stick is read-only and the entry point runs with `-I -B`. The bug is in the fixtures.

1. **Build every test bundle from the manifest entries only,** the same way the Windows copy helper does: exactly the listed files plus the two manifests. Never copy the payload directory tree.
   - Find every fixture that copies the payload tree (`copytree`, `copy2` loops, globbing) and fix each one the same way. List them in the report.
2. **Prove it under both bytecode modes.**
   - Add one regression that plants a stray `__pycache__/x.pyc` in the source tree. The fixture bundle must be unaffected, and the strict check must still refuse a bundle that really contains the stray file.
   - Locally, run the affected test modules once with `-B` and once without, with `PYTHONDONTWRITEBYTECODE` unset.
3. **Allowances:** probe cap 32 → **34**. The owner-tools cap stays at 21, since qualification 21 hasn't been used. The minute cap stays at 2750: 2310 + 72 + 240 = 2622 fits.
4. **Then:** the other local checks as in 14zzc, one push through the privacy hook, **probe 33 and qualification 21 on that same head**, then STOP and report.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
