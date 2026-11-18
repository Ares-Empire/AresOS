Reviewed `d711bdaa..a5c5d4fe` read-only. No builds, Gradle, client tests or games were run.

1. **Should-fix — a deferred renewal can swallow a subsequent move.**  
   **Where:** `mod/src/main/java/dev/aresos/hub/TownKeeper.java:509`, `:524`, `:539`.  
   After removal succeeds and rebuilding waits, the map retains only `RENEWED`. If the category changes—or planning finds the original place newly obstructed—the next pass can build elsewhere successfully while announcing “was renewed.” Nothing compares the replacement’s destination with its original place; promotion to `MOVED` happens only after a build throws an obstruction exception.  
   **Fix:** retain the original place with the pending replacement and classify completion as `MOVED` when its destination differs. Add a regression that defers renewal, changes its destination before retry, and checks one move announcement.

2. **Should-fix — cancelling a deferred replacement silently loses the take-down.**  
   **Where:** `mod/src/main/java/dev/aresos/hub/TownKeeper.java:434`, `:467`.  
   Start the tested deferred move, then remove that app from My apps before its destination loads. Its old logo is already absent, so the removal loop cannot emit `DOWN`; `retainAll(wanted)` then silently discards the pending change. Neither the move nor the resulting permanent removal is announced.  
   **Fix:** distinguish pending removals that succeeded from attempts whose old logo still stands. Before discarding an unwanted replacement whose removal succeeded, emit one take-down message. Test cancellation, repeated passes and the app’s later return.

3. **Nit — the client assertion does not enforce announcement immediately upon completion.**  
   **Where:** `mod/src/gametest/java/dev/aresos/test/TownArrivalClientGameTest.java:158`.  
   Completion at tick 103 and announcement at tick 199 would pass. The requirement is to speak as soon as all places stand, independently of the deadline.  
   **Fix:** compare announcement time with `controlled.completed`, allowing a small client-delivery tolerance, and check the deadline relative to `controlled.first`.

The original unchanged-ID category-move case is addressed and covered by the keeper regression. The 200-tick clock starts with the first actual build; expiry and later-build assertions are present, and the report explicitly records the lead’s decision. No additional regression was evident in WAY formatting, rebuild handling, ordinary completed changes, staging isolation, or completed-town rejoin/restart behavior.

CHANGES-NEEDED