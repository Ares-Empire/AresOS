Reviewed head `2ac42457`. No blocking or should-fix findings under decision 24.

- **Nit — `mod/src/gametest/java/dev/aresos/test/FreePointerClientGameTest.java:258`:** Empty-slot, non-app-slot and world clicks exercise `MouseHandler` callbacks directly, even in `--session`. They verify capture and swallowed item input, but not native compositor delivery. **Fix:** state this distinction in the report’s Known limits; native entry-click cases can be added later. This is a coverage limitation, not evidence of broken input.

The requested checks otherwise hold:

- The recorded evidence supports the startup/loading/reconnect focus-loss cause. It explicitly distinguishes callback-reproduced turning from native seat motion, which did not reliably reproduce it.
- Capture, turning, attack and use guards apply to connected session desktop worlds. Hotbar clicks share the existing item-launch/error path. Small-window focus leaves the world running without a pause menu; covering and uncovering rules remain intact.
- `LiveMode.DESKTOP_FLYING_SPEED` supplies `0.075f` in both modes. Tests measure approximately 1.5× vanilla flight with matching FOV; server assertions check abilities and absence of effects.
- Helper snapshots follow hello, respect capability negotiation, avoid duplicate delivery and repeat for reconnects. Authentication, view-client routing and existing 1.2 behavior are preserved.
- Primary-button-only opening and the two-frame activation delay are reasonable, localized choices.
- Tests exercise slow/fast exits on all four edges, native app switching/closing, a native hotbar click, both callback/focus orderings, lost releases and flight. The screenshots show the hover border/name while the selected stone slot remains unchanged.

This was read-only inspection. I ran no build, Gradle, tests or game; reported passes were assessed from the supplied evidence.

SAFE