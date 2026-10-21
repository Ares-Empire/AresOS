# 01b: First app item, review fixes and AresOS-only rules

Follow-up on branch `pkg/01-first-app` (PR #1). Read `reviews/01-first-app/REVIEW.md` and `REPORT.md` first.

**Goal:** fix the three review findings, and make every AresOS desktop rule apply only inside the AresOS world. Every other world plays like normal Minecraft.

**In scope:**
1. **One launch per click (review finding 1, blocking).**
   - Track real right-click press and release events, independent of vanilla's item-use state.
   - Holding the button, switching hotbar slots and switching back must not launch again.
   - Releasing and pressing again between two client ticks must launch again.
2. **Clicks on interactive targets (finding 2).**
   - Right-clicking with an app item while looking at a door, chest or villager must launch the app exactly once and must **not** interact with the target.
   - Handle app activation before block and entity interactions.
3. **Per-launch focus tracking (finding 3).** Each launch gets its own token. A failed earlier launch must never cancel a newer launch's focus return.
4. **Focus window 30 s (owner decision).** A focus loss counts as "the app opened" if it happens within **30 seconds** of the click (was 10). Keep it one constant.
5. **AresOS world only (owner decision).** The owner's words: "AresOS is just the operating system... any other, normal world should work normally."
   - A world is an AresOS world only if it carries an AresOS marker stored in the world save.
   - Add `/aresos desktop on|off`: singleplayer host only, works without cheats, and sets the marker.
   - New worlds are normal by default.
   - All desktop rules apply only in AresOS worlds: can't die, full hunger, void rescue, pinned apps placed on join, the Build/Live mode key, and `/aresos give`.
   - In a normal world, the mode key shows a short "Not an AresOS world" message and does nothing else.
   - Launching from an app item may stay available everywhere (harmless), but nothing places app items in normal worlds.

**Out of scope:** everything listed as out of scope in brief 01, plus the Nether hub. How the AresOS world gets created comes later; for now `/aresos desktop on` is enough.

**Acceptance:**
- `./gradlew build runClientGameTest` passes.
- New fake-launcher client tests:
  - held-click slot switch → no second launch
  - release and repress between ticks → second launch
  - clicking on a door, a chest and a villager → one launch, no interaction (door state unchanged, no chest screen, no trade screen)
  - an earlier failed launch completing after a newer launch's pause screen was captured → the newer return still works
- Game tests: in a normal world, damage, hunger and void behave like vanilla, and no app items get placed. In a marked world, all existing desktop tests still pass.
- Update `REPORT.md` with a short "01b" section. Ask nothing; record judgment calls there.

**Already decided:** everything in brief 01, plus the 30-second window and the AresOS-world-only rule above.

**If unsure:** the safe default is "behave like vanilla Minecraft".

**Model:** gpt-6.1-sol, xhigh.
