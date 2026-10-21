# 04b: Nether home, review fixes

Follow-up on branch `pkg/04-nether-home` (PR #4). Read `reviews/04-nether-home/REVIEW.md` and `REPORT.md` first.

**Goal:** fix both review findings. The rule behind finding 1 is: **AresOS never overwrites an existing world's blocks automatically.**

**In scope:**
1. **Never rebuild an existing hub (blocking).**
   - Record that provisioning completed, in a way that survives the loss of `data/aresos/nether_home.dat`. For example, persist it in more than one place, or detect an established save from level data.
   - Build the hub only for an explicitly new world created through the AresOS button.
   - If an established AresHub save is missing its home data: don't build, don't change gamerules, and don't re-enable a disabled desktop marker. Open the world unchanged and show a clear message.
   - Regression test: edit the hub, delete the home-data file, reopen → no block changes, no gamerule changes, and the marker state is unchanged.
2. **Saved vehicles don't override hub arrival (should-fix).**
   - The player always arrives at the hub without remounting.
   - A saved vehicle stays in its original dimension and position. It's never recreated in the Nether at Overworld coordinates.
   - Tests: mounted rejoin with the vehicle in the Nether away from home, and with the vehicle in the Overworld. The player is at the hub after several ticks in both cases.

**Out of scope:** the hub's look (glass enclosure, a separate owner decision) and everything else.

**Acceptance:**
- `./gradlew build runClientGameTest` passes.
- New regressions fail before the fix (show it) and pass after.
- All existing tests pass.
- Add a "04b" section to `REPORT.md`. Stop your Gradle daemons.

**If unsure:** leave the world exactly as it is and tell the player.

**Model:** gpt-6.1-sol, xhigh.
