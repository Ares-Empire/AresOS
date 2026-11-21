No blocking, should-fix, or nit findings in `8f6935eb..a159061a`.

- `mod/src/main/java/dev/aresos/hub/TownKeeper.java`: replacement history survives retries; completion compares against the original place. Cancellation after removal emits one `DOWN` and ends the record. Return before cancellation is processed continues that record; return after an announced cancellation is a fresh build. Refused removal leaves ordinary removal responsible. Pending replacements cannot inflate the first-build count. I found no remaining duplicate, missing, or misclassified announcement in these paths.
- `mod/src/gametest/java/dev/aresos/test/TownGameTests.java:509`: the 48-row table covers the requested cross-product, plus removal waiting and return before a complete retry. Repeated pending and terminal passes check silence. Expectations match the brief’s cancellation and return rules.
- `mod/src/gametest/java/dev/aresos/test/TownArrivalClientGameTest.java:158`: delivery must occur within 0–5 ticks of `controlled.completed`, and within 200 ticks of `controlled.first`.
- `mod/src/gametest/java/dev/aresos/test/mixin/IntegratedServerTestMixin.java:13`: the wrapper addresses the recorded deadlock by advancing Fabric’s barrier while the same initial halt task executes on the server. `done.join()` propagates failure; assertions and subsequent shutdown remain intact. Registration is confined to gametest sources/configuration. The existing product jar contains neither the test mixin nor its configuration.

Existing logs record all 48 rows passing and two completed client suites with both mounted-rejoin regressions passing. These are prior-run evidence; I ran no build, Gradle, client test, or game and changed no files.

SAFE