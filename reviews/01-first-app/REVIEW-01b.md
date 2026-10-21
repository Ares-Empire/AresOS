Reviewed `878845b..a2d3b92`, excluding binary screenshots. Static review against cached vanilla sources; I did not rerun Gradle in this read-only sandbox.

The three earlier scenarios are fixed, with regression tests that would catch their previous behavior: held-click slot switching, release/repress between ticks, interactive-target interception, and an older failure cancelling newer focus tracking. The marker guards cover protection, hunger, void rescue, pinning, G, and `/aresos give`; tests cover normal defaults and marker persistence.

1. **should-fix — Selecting an app and clicking between ticks can silently lose the launch.**  
   **Where:** [AppInput.java:27](/C:/Users/pab/AresOS-01-first-app/mod/src/client/java/dev/aresos/client/AppInput.java:27), [MinecraftAppInputMixin.java:15](/C:/Users/pab/AresOS-01-first-app/mod/src/client/java/dev/aresos/client/mixin/MinecraftAppInputMixin.java:15).  
   **Why:** Start with an empty slot selected and Notepad in slot 1. Press **1**, then right-click before the next client tick. Vanilla queues the hotbar selection, so the raw input hook still sees the empty slot and launches nothing. At the next tick, vanilla selects Notepad, but the new `startUseItem` hook cancels activation. Switching between two apps this way launches the previously selected app. The new slot-switch test waits six ticks between actions, masking this regression.  
   **Fix:** Preserve press/release edges, but resolve activation after pending hotbar selection is processed and before target interaction. Add fake-launcher tests delivering the number-key press and use press/release without an intervening tick, covering empty-to-app and app-to-different-app transitions.

CHANGES-NEEDED