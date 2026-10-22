# 09: Separate inventories for Build and Live mode

**Goal:** Build mode (creative) and Live mode (survival, the desktop) each have their **own inventory and hotbar**. Switching with G swaps them. Your app hotbar is exactly as you left it when you return to Live mode, and the blocks you were building with are still there when you go back to Build mode. The README promised this ("Your app hotbar comes back when you return to Live mode"); package 01 left it out.

**Read first:** `README.md` (Game rules), and the existing mode toggle (G), Live mode, app items, pinning (07) and desktop marker code.

**In scope:**
1. **Two stored inventories per player per AresOS world:** Live and Build, covering main inventory, hotbar, offhand, armor, and the selected hotbar slot. Persisted in the save, surviving rejoin and restarts.
2. **G swaps:** save the current mode's inventory, switch game mode, load the other one. Atomic: if anything fails, keep the original inventory and mode, and show a message. **Never lose or duplicate items.**
3. **First switch to Build** starts with an empty inventory (creative gives access to everything). Live keeps the apps exactly as before.
4. **App pins:** pin tracking (07) applies only to the Live inventory. Moving things in Build mode never changes `pinned`. App items brought into Build mode through creative are just items there and don't affect pins.
5. **Edge cases:** dying is impossible in Live, and Build is creative. Disconnecting mid-switch must keep a consistent state. Switching while a container or menu is open closes it first, or refuses with a message (pick one, keep it simple, and record it).
6. **Normal worlds:** nothing changes, and no stored inventories are created.

**Out of scope:** per-dimension inventories, sharing between players, shops, and anything in `os/`.

**Acceptance:**
- `./gradlew build runClientGameTest` passes twice (AGENTS rule), and all earlier tests still pass.
- Tests:
  - Live → Build → Live restores the exact Live inventory, including slot positions, counts, components and the selected slot.
  - The Build inventory persists across switches and rejoin.
  - No item duplication or loss across 50 rapid switches.
  - A failed save or load keeps the original state.
  - Pins only follow Live changes.
  - Normal worlds are unaffected.
- A screenshot of each mode's hotbar. Add `REPORT.md`, and stop your Gradle daemons.

**If unsure:** keep the player's items safe over everything else.

**Model:** gpt-6.1-sol, xhigh.
