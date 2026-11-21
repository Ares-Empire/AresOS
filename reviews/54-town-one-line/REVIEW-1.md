Reviewed head `b0dfb695` read-only. Two findings:

1. **Blocking — a deferred real move can inflate the first-build count.**  
   **Where:** `mod/src/main/java/dev/aresos/hub/TownLines.java:94` and `mod/src/main/java/dev/aresos/hub/TownKeeper.java:434`.  
   The accumulator detects changes through wanted **IDs** and emitted line kinds. A catalogue category change can move an already-built app without changing its ID. If its old logo comes down but its new place is unloaded, `round()` emits neither `DOWN` nor `MOVED`. Its local `cameDown` state disappears after that pass; the later successful build becomes `BUILT` and enters the accumulator again. Thus 32 initial builds, followed by eight remaining apps plus one relocated app, can announce **41 logos for 40 apps**, swallowing the real change.  
   **Fix:** end first-build collection when an actual move or renewal begins, even if rebuilding is deferred. Preserve that operation’s classification across retries. Add a keeper regression covering an unchanged ID set, category change, unloaded destination, and subsequent completion.

2. **Should-fix — first-start announcement latency can regress.**  
   **Where:** `mod/src/main/java/dev/aresos/hub/TownLines.java:100` and `mod/src/gametest/java/dev/aresos/test/TownArrivalClientGameTest.java:158`.  
   The baseline evidence in `.work/pkg54/baseline-client-both.log` shows first start announcing 18 logos at tick 3, then completing at tick 103. Under that same loading schedule, this implementation suppresses tick 3’s announcement until tick 103—or until the 600-tick bound. That violates the brief’s explicit “first start must not get slower” requirement. The successful final runs happened to build all 40 at tick 3; the client test checks eventual messages, without asserting announcement timing.  
   **Fix:** preserve the initial announcement time, for example by updating the same chat entry as the first build progresses, and test a controlled partial-loading first start.

The report’s staging-world explanation **is supported** by its diagnostic logs: staging built 24, reopening began with 24, and missing places reported `NotLoaded`. Its qualification about generation versus entity loading is appropriate.

The required unit scenarios and 40-app New home client flow are present. Per-server cleanup, staging release, bounded expiry, WAY/rebuild handling, the shorter socket-fixture root, and test-game screenshots otherwise look sound on inspection. No builds, Gradle, client tests, or games were run during this review.

CHANGES-NEEDED