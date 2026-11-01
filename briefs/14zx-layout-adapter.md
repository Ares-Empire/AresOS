# 14zx: Type with the guest's real layout profile; close the stand-in coverage gap; probe 28, qualification 17

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zw still apply, with the changes below.

## Integrator decision on the qualification 16 STOP

Your diagnosis is accepted. The cause was a harness layout-adapter bug: `public_typing` turned every non-German profile into `us`, so the US International check typed `ü` with the plain-US map. The owner tools did their part, from the installed `us-intl` keymap and the 9 s tty3 login to `layout proof` and `layout finish`.

1. **Fix the adapter.**
   - `public_typing` (lines 808 and 810) passes the guest's actual profile (`de`, `us` or `us-intl`) to the typing helpers.
   - Look through the harness for any other place that collapses a profile, such as `'de' if … else 'us'`, a default layout or a fallback map. Fix each one the same way and list it in the report.
   - Don't change the pinned key maps.
2. **Close the coverage gap.** The stand-in walk must run the real `public_typing` → `physical_input` → `type_text` → `physical_keys` chain. Replace only the final QMP send with a recorder.
   - Cover every remaining stage and its profile: US International success, back to German, rollback, keep-stock and the final Windows checks.
   - Each case checks the exact key events for the stage's test text, including `ü` on `us-intl` (`alt_r` + `y`).
   - It must fail on the 14zw code.
3. **Local checks:** the affected regressions, the full stand-in walk, and the pinned gitleaks. Commit.
4. **One push** through the privacy hook (never `--no-verify`). Then **probe and qualification on that same head**, under the 14zw rules: reservations, organization reserve 150, cap 2750.
5. Then **STOP and report**, as in 14zv. On a stop, also say how many rounds the remaining stages would still need, as far as the retained output shows.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
