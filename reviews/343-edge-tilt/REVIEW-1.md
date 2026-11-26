# Review 1 of package 343

Codex `gpt-6.2-sol` `high`, read-only, on `d308bde6`. Its nit is in REPORT.md's Known limits.

Reviewed PR #177 at `d308bde6`.

- **Nit — The report overstates the cursor assertion.** The client test sends a mouse callback at `y = 0`, confirms the top band pitches up, then holds Down until pitch reaches `+90°`. That catches additive cancellation with the cursor held there. The recovery predicate checks pitch alone, so a cursor move during the hold could also let it pass. Assert the client’s cursor coordinates during the recovery wait, and describe the cursor input as synthetic in the report. [Client test](mod/src/gametest/java/dev/aresos/test/EdgeTurnClientGameTest.java:289) · [Report](reviews/343-edge-tilt/REPORT.md:19)

**Checks**

- Up produces negative pitch and Down positive pitch at 120°/s. One arrow overrides the top band, both defer to it, and yaw keeps its existing rule. `EdgeLook` converts frame degrees to `Entity.turn`’s 0.15° units, and Minecraft clamps pitch to ±90°. The four arrows are polled behind the same frame gates, leaving Search, Apps and vanilla menu navigation intact. [EdgeTurn](mod/src/main/java/dev/aresos/focus/EdgeTurn.java:102) · [EdgeLook](mod/src/client/java/dev/aresos/client/EdgeLook.java:67)
- Fabric skips the global screenshot counter for both new captures. Package 333 keeps `0105_333-hotbar-app-marks.png`. [Screenshot call](mod/src/gametest/java/dev/aresos/test/EdgeTurnClientGameTest.java:323) · [Report](reviews/343-edge-tilt/REPORT.md:22)
- Only admission passes one second. The watcher and startup reconciliation retain five seconds. The OS test injects `TimeoutExpired` and verifies `journal_full` for the view, a desktop launch attempt, and `UNKNOWN` from the watcher. [Admission](os/config/usr/libexec/aresos-shell:4004) · [Reconciliation](os/config/usr/libexec/aresos-shell:3394) · [OS test](os/tests/test_aresos_shell_views.py:364)

I checked the two saved client-run logs and the passing 35-test OS log during this read-only review.

SAFE